"""
Hotel PMS 서버 — LLM 손님 에이전트 전용 (port 3001)

LLM 에이전트는 이 서버만 바라본다.
FastAPI DSS(port 8001)의 존재를 모른다.

실행:
    uvicorn app_pms.pms_mock:app --port 3001 --reload

흐름:
    LLM 에이전트
        │  POST /api/bookings (GuestBookingRequest)
        ▼
    [이 서버 — PMS, port 3001]
        │  내부적으로 DSS 호출
        │  POST http://localhost:8001/api/v1/bookings (BookingRequest)
        ▼
    [FastAPI DSS, port 8001]
        │  BookingResponse (risk_score, flexi_recommended 포함)
        ▼
    [이 서버 — 번역]
        │  GuestBookingConfirmation (손님 언어)
        ▼
    LLM 에이전트 응답 수신
"""

import uuid
from collections import deque
from datetime import datetime
from typing import Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, Query
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
    PMSReservationRecord,
    PMSReservationListResponse,
    PMSActivityEvent,
    PMSActivityResponse,
    PMSStats,
)

app = FastAPI(
    title="Hotel PMS API",
    description="Hotel Property Management System — 손님·LLM 에이전트용 예약 API",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# PMS API 키 (LLM 에이전트에게 부여)
PMS_API_KEY = "pms-guest-key-2026"
DSS_BASE_URL = "http://localhost:8001"

# ── 페르소나 메타데이터 (agent_id → 표시 정보)
PERSONA_META: dict[str, dict] = {
    "guest-ana":    {"name": "Ana Rodrigues",  "type": "Business Traveler", "nationality": "PRT"},
    "guest-james":  {"name": "James Mitchell", "type": "Leisure Tourist",   "nationality": "GBR"},
    "guest-marie":  {"name": "Marie Dubois",   "type": "Family Vacation",   "nationality": "FRA"},
    "guest-thomas": {"name": "Thomas Müller",  "type": "Conference",        "nationality": "DEU"},
    "guest-paulo":  {"name": "Paulo Santos",   "type": "Solo Traveler",     "nationality": "BRA"},
}

# 인메모리 저장소
_guest_bookings: list[GuestBookingConfirmation] = []
_pms_records: list[PMSReservationRecord] = []
_activity_log: deque[PMSActivityEvent] = deque(maxlen=200)


def _get_persona(agent_id: str) -> dict:
    return PERSONA_META.get(agent_id, {
        "name": agent_id,
        "type": "Unknown",
        "nationality": "???",
    })


def _log(
    agent_id: str,
    action: str,
    message: str,
    confirmation_number: Optional[str] = None,
    hotel: Optional[str] = None,
    pricing_type: Optional[str] = None,
    discount_pct: Optional[float] = None,
) -> None:
    persona = _get_persona(agent_id)
    _activity_log.appendleft(PMSActivityEvent(
        event_id=uuid.uuid4().hex[:8],
        timestamp=datetime.now(),
        agent_id=agent_id,
        persona_name=persona["name"],
        persona_type=persona["type"],
        action=action,
        message=message,
        confirmation_number=confirmation_number,
        hotel=hotel,
        pricing_type=pricing_type,
        discount_pct=discount_pct,
    ))


def _verify_pms_key(authorization: str) -> None:
    if authorization != f"Bearer {PMS_API_KEY}":
        raise HTTPException(status_code=401, detail="Invalid PMS API key")


def _translate_to_dss(req: GuestBookingRequest) -> BookingRequest:
    """GuestBookingRequest → BookingRequest (DSS 언어)."""
    base_adr = 80.0
    if req.hotel == "City Hotel":
        base_adr += 20.0
    if req.arrival_date.month in (6, 7, 8):
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
# 에이전트용 엔드포인트 (인증 필요)
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
    """LLM 에이전트가 호출하는 예약 엔드포인트."""
    _verify_pms_key(authorization)

    persona = _get_persona(req.agent_id)
    _log(req.agent_id, "booking",
         f"{persona['name']}이(가) {req.hotel}에 예약을 시도합니다 "
         f"({req.arrival_date} ~ {req.departure_date}, {req.adults}명)")

    dss_request = _translate_to_dss(req)

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"{DSS_BASE_URL}/api/v1/bookings",
                json=dss_request.model_dump(mode="json"),
            )
            resp.raise_for_status()
            dss_result = resp.json()
    except httpx.ConnectError:
        _log(req.agent_id, "error", "DSS 서버 연결 실패")
        raise HTTPException(
            status_code=503,
            detail="DSS 서버 연결 실패. FastAPI DSS(port 8001)가 실행 중인지 확인하세요.",
        )

    flexi = dss_result["flexi_recommended"]
    discount = dss_result.get("discount_rate")
    nights = (req.departure_date - req.arrival_date).days
    base_adr = dss_request.adr
    total = round(base_adr * nights * (1 - (discount or 0)), 2)
    confirmation_number = f"PMS-{uuid.uuid4().hex[:6].upper()}"
    pricing_type = "Flexi Rate" if flexi else "Standard Rate"
    room_display = ROOM_DISPLAY_MAP.get(req.room_type_preference, "Standard Room")

    confirmation = GuestBookingConfirmation(
        confirmation_number=confirmation_number,
        hotel=req.hotel,
        arrival_date=req.arrival_date,
        departure_date=req.departure_date,
        nights=nights,
        adults=req.adults,
        room_type_assigned=room_display,
        pricing_type=pricing_type,
        rate_per_night=base_adr,
        discount_applied=discount,
        total_amount=total,
        meal_plan=req.meal_plan,
        status="Confirmed",
        message=build_dss_message(pricing_type, discount),
        created_at=datetime.now(),
    )

    # 내부 관리자용 레코드 저장
    record = PMSReservationRecord(
        confirmation_number=confirmation_number,
        agent_id=req.agent_id,
        persona_name=persona["name"],
        persona_type=persona["type"],
        persona_nationality=req.nationality,
        hotel=req.hotel,
        arrival_date=req.arrival_date,
        departure_date=req.departure_date,
        nights=nights,
        adults=req.adults,
        room_type_assigned=room_display,
        pricing_type=pricing_type,
        rate_per_night=base_adr,
        discount_applied=discount,
        total_amount=total,
        meal_plan=req.meal_plan,
        status="Confirmed",
        dss_booking_id=dss_result.get("booking_id"),
        dss_risk_score=dss_result.get("risk_score"),
        created_at=datetime.now(),
    )
    _pms_records.append(record)
    _guest_bookings.append(confirmation)

    disc_pct = round((discount or 0) * 100, 1) if discount else None
    _log(
        req.agent_id, "confirmed",
        f"예약 확정: {confirmation_number} | {pricing_type}"
        + (f" (-{disc_pct}%)" if disc_pct else ""),
        confirmation_number=confirmation_number,
        hotel=req.hotel,
        pricing_type=pricing_type,
        discount_pct=disc_pct,
    )

    return confirmation


@app.get(
    "/api/bookings",
    response_model=GuestBookingListResponse,
    summary="손님 예약 목록 조회 (에이전트용)",
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


# ──────────────────────────────────────────
# 관리자 UI용 엔드포인트 (인증 없음 — 내부 UI 전용)
# ──────────────────────────────────────────

@app.get(
    "/admin/reservations",
    response_model=PMSReservationListResponse,
    summary="[관리자] 전체 예약 목록 (에이전트 메타 포함)",
)
def admin_list_reservations() -> PMSReservationListResponse:
    """PMS UI가 호출. 에이전트 정보 + DSS 연결 정보 포함."""
    sorted_records = sorted(_pms_records, key=lambda r: r.created_at, reverse=True)
    return PMSReservationListResponse(reservations=sorted_records, total=len(sorted_records))


@app.get(
    "/admin/activity",
    response_model=PMSActivityResponse,
    summary="[관리자] 실시간 활동 로그",
)
def admin_activity(limit: int = Query(50, ge=1, le=200)) -> PMSActivityResponse:
    """PMS UI가 polling. 최신 N개 이벤트 반환."""
    events = list(_activity_log)[:limit]
    return PMSActivityResponse(events=events, total=len(events))


@app.get(
    "/admin/stats",
    summary="[관리자] 간단 통계",
)
def admin_stats() -> PMSStats:
    flexi = sum(1 for r in _pms_records if r.pricing_type == "Flexi Rate")
    standard = sum(1 for r in _pms_records if r.pricing_type == "Standard Rate")
    unique_agents = len({r.agent_id for r in _pms_records})
    return PMSStats(
        total_reservations=len(_pms_records),
        flexi_count=flexi,
        standard_count=standard,
        unique_agents=unique_agents,
        recent_activity=len(_activity_log),
    )
