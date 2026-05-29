"""
Hotel PMS 목업 서버 — LLM 손님 에이전트 전용 (port 3001)

LLM 에이전트는 이 서버만 바라본다.
FastAPI DSS(port 8000)의 존재를 모른다.

실행:
    uvicorn app_pms.pms_mock:app --port 3001 --reload

흐름:
    LLM 에이전트
        │  POST /api/bookings (GuestBookingRequest)
        ▼
    [이 서버 — PMS, port 3001]
        │  내부적으로 DSS 호출
        │  POST http://localhost:8000/api/v1/bookings (BookingRequest)
        ▼
    [FastAPI DSS, port 8000]
        │  BookingResponse (risk_score, flexi_recommended 포함)
        ▼
    [이 서버 — 번역]
        │  GuestBookingConfirmation (손님 언어)
        ▼
    LLM 에이전트 응답 수신
"""

import uuid
from datetime import date, datetime, timedelta
from typing import Optional

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import BookingRequest
from app_pms.pms_schemas import (
    GuestBookingConfirmation,
    GuestBookingListItem,
    GuestBookingListResponse,
    GuestBookingRequest,
    MEAL_MAP,
    ROOM_DISPLAY_MAP,
    ROOM_TYPE_MAP,
    DEFAULT_CHANNEL,
    DEFAULT_CUSTOMER_TYPE,
    DEFAULT_MARKET_SEGMENT,
    build_dss_message,
)

app = FastAPI(
    title="Hotel PMS API",
    description="Hotel Property Management System — 손님·LLM 에이전트용 예약 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# PMS API 키 (LLM 에이전트에게 부여)
PMS_API_KEY = "pms-guest-key-2026"
DSS_BASE_URL = "http://localhost:8000"

# 인메모리 예약 저장소
_guest_bookings: list[GuestBookingConfirmation] = []


def _verify_pms_key(authorization: str) -> None:
    if authorization != f"Bearer {PMS_API_KEY}":
        raise HTTPException(status_code=401, detail="Invalid PMS API key")


def _translate_to_dss(req: GuestBookingRequest) -> BookingRequest:
    """
    GuestBookingRequest (손님 언어) → BookingRequest (DSS 언어).
    PMS가 내부적으로 채우는 값들:
        - distribution_channel: "Direct" (PMS를 통한 예약)
        - market_segment: "Direct"
        - customer_type: "Transient"
        - booking_changes: 0 (신규 예약)
        - adr: 호텔·룸타입·도착 월 기반 기준 요금 계산
    """
    nights = (req.departure_date - req.arrival_date).days
    # 기준 요금 계산 (목업: 성수기·룸타입 반영)
    base_adr = 80.0
    if req.hotel == "City Hotel":
        base_adr += 20.0
    if req.arrival_date.month in (6, 7, 8):  # 성수기
        base_adr *= 1.3

    return BookingRequest(
        hotel=req.hotel,
        arrival_date=req.arrival_date,
        departure_date=req.departure_date,
        adults=req.adults,
        children=req.children,
        babies=0,
        distribution_channel=DEFAULT_CHANNEL,
        market_segment=DEFAULT_MARKET_SEGMENT,
        reserved_room_type=ROOM_TYPE_MAP.get(req.room_type_preference, "A"),
        meal=MEAL_MAP.get(req.meal_plan, "BB"),
        country=req.nationality,
        is_repeated_guest=0,
        previous_cancellations=0,
        booking_changes=0,
        customer_type=DEFAULT_CUSTOMER_TYPE,
        adr=round(base_adr, 2),
        required_car_parking_spaces=0,
        total_of_special_requests=1 if req.special_requests else 0,
    )


# ──────────────────────────────────────────
# 엔드포인트
# ──────────────────────────────────────────

@app.post(
    "/api/bookings",
    response_model=GuestBookingConfirmation,
    summary="손님 예약 제출 (LLM 에이전트용)",
)
def guest_book(
    req: GuestBookingRequest,
    authorization: str = Header(...),
) -> GuestBookingConfirmation:
    """
    LLM 에이전트가 호출하는 예약 엔드포인트.
    내부적으로 FastAPI DSS를 호출하고 결과를 손님 언어로 번역.
    """
    _verify_pms_key(authorization)

    # 1. 손님 언어 → DSS 언어 번역
    dss_request = _translate_to_dss(req)

    # 2. FastAPI DSS 호출
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                f"{DSS_BASE_URL}/api/v1/bookings",
                json=dss_request.model_dump(mode="json"),
            )
            resp.raise_for_status()
            dss_result = resp.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="DSS 서버 연결 실패. FastAPI DSS(port 8000)가 실행 중인지 확인하세요.",
        )

    # 3. DSS 결과 → 손님 언어 번역
    flexi = dss_result["flexi_recommended"]
    discount = dss_result.get("discount_rate")
    nights = (req.departure_date - req.arrival_date).days
    base_adr = dss_request.adr
    total = round(base_adr * nights * (1 - (discount or 0)), 2)

    confirmation = GuestBookingConfirmation(
        confirmation_number=f"PMS-{uuid.uuid4().hex[:6].upper()}",
        hotel=req.hotel,
        arrival_date=req.arrival_date,
        departure_date=req.departure_date,
        nights=nights,
        adults=req.adults,
        room_type_assigned=ROOM_DISPLAY_MAP.get(req.room_type_preference, "Standard Room"),
        pricing_type="Flexi Rate" if flexi else "Standard Rate",
        rate_per_night=base_adr,
        discount_applied=discount,
        total_amount=total,
        meal_plan=req.meal_plan,
        status="Confirmed",
        message=build_dss_message("Flexi Rate" if flexi else "Standard Rate", discount),
        created_at=datetime.now(),
    )

    _guest_bookings.append(confirmation)
    return confirmation


@app.get(
    "/api/bookings",
    response_model=GuestBookingListResponse,
    summary="손님 예약 목록 조회",
)
def list_guest_bookings(
    authorization: str = Header(...),
) -> GuestBookingListResponse:
    _verify_pms_key(authorization)
    items = [
        GuestBookingListItem(
            confirmation_number=b.confirmation_number,
            hotel=b.hotel,
            arrival_date=b.arrival_date,
            departure_date=b.departure_date,
            pricing_type=b.pricing_type,
            status=b.status,
            total_amount=b.total_amount,
            created_at=b.created_at,
        )
        for b in _guest_bookings
    ]
    return GuestBookingListResponse(bookings=items, total=len(items))
