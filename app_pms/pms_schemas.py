"""
Hotel PMS — 손님 API 스키마 (LLM 에이전트 전용)

이 파일은 LLM 손님 에이전트가 PMS와 주고받는 데이터 형식이다.
LLM 에이전트는 이 스키마만 알면 된다.
FastAPI DSS 내부 개념(risk_score, shap_values, flexi_recommended)은
이 레이어 바깥으로 절대 노출하지 않는다.

엔드포인트 (App 1 Next.js, port 3001):
    POST /api/bookings   ← 손님 예약 제출
    GET  /api/bookings   ← 본인 예약 조회
    GET  /api/availability  ← 객실 가용성 확인
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════
# SECTION 1: 손님이 PMS에 보내는 데이터
# 실제 호텔 예약 폼에서 손님이 입력하는 것만 포함
# 나머지(channel, market_segment 등)는 PMS가 내부적으로 채움
# ══════════════════════════════════════════════════════════════════

class GuestBookingRequest(BaseModel):
    """
    LLM 손님 에이전트가 PMS에 보내는 예약 요청.
    DSS 내부 개념 없음. 진짜 손님이 입력하는 수준.
    """

    # 호텔 선택
    hotel: Literal["City Hotel", "Resort Hotel"]

    # 날짜
    arrival_date: date
    departure_date: date   # departure_date > arrival_date 필수

    # 인원
    adults: int = Field(ge=1, le=9)
    children: int = Field(ge=0, le=5, default=0)

    # 방 선호 (PMS가 실제 배정 결정)
    room_type_preference: Literal["Single", "Double", "Twin", "Suite", "No Preference"] = "No Preference"

    # 식사
    meal_plan: Literal["Bed & Breakfast", "Half Board", "Full Board", "Room Only"] = "Bed & Breakfast"

    # 손님 정보
    nationality: str = Field(min_length=3, max_length=3)   # ISO alpha-3
    special_requests: str = Field(default="", max_length=300)

    # 에이전트 메타데이터 (로깅·분석용, 예측에 미사용)
    agent_id: str = Field(description="LLM 에이전트 식별자. 예: 'guest-agent-B'")
    persona_description: str = Field(
        default="",
        description="페르소나 설명. 예: '마지막 순간 예약형 레저 여행자, 취소 이력 2회'",
    )


# ══════════════════════════════════════════════════════════════════
# SECTION 2: PMS가 손님에게 돌려주는 확인서
# DSS 내부 결과를 손님 언어로 번역한 것
# ══════════════════════════════════════════════════════════════════

class GuestBookingConfirmation(BaseModel):
    """
    PMS가 LLM 에이전트에게 반환하는 예약 확인서.

    PMS 내부에서 일어나는 일 (에이전트에게 숨겨짐):
        GuestBookingRequest
            ↓ (PMS 번역)
        BookingRequest (DSS 형식)
            ↓ (FastAPI DSS 호출)
        BookingResponse (risk_score, flexi_recommended 포함)
            ↓ (PMS 번역)
        GuestBookingConfirmation  ← 에이전트가 받는 것
    """

    confirmation_number: str     # 예: "PMS-A3F29C"
    hotel: Literal["City Hotel", "Resort Hotel"]
    arrival_date: date
    departure_date: date
    nights: int
    adults: int

    # 객실 배정 결과
    room_type_assigned: str      # 예: "Double Room"

    # 요금제 — 이것만 보고 에이전트가 Flexi 여부를 알 수 있음
    pricing_type: Literal["Standard Rate", "Flexi Rate"]
    # Standard Rate: 취소 위험 낮음 → 일반 배정
    # Flexi Rate: 취소 위험 높음 → Flexi 풀, 할인 적용

    rate_per_night: float        # EUR
    discount_applied: Optional[float]   # None이면 할인 없음 (Standard)
                                         # 0.05~0.18이면 Flexi 할인율
    total_amount: float          # rate_per_night * nights * (1 - discount_applied)

    meal_plan: str
    status: Literal["Confirmed", "Pending", "Waitlisted"]

    # 손님에게 보여주는 안내 메시지
    message: str
    # 예시:
    # Standard: "예약이 확정되었습니다. 도착을 기다리겠습니다."
    # Flexi:    "Flexi 요금제로 예약되었습니다. 16.4% 할인이 적용되었으며,
    #            체크인 7일 전까지 무료 취소 가능합니다."

    created_at: datetime


# ══════════════════════════════════════════════════════════════════
# SECTION 3: 손님 예약 조회 (GET /api/bookings)
# ══════════════════════════════════════════════════════════════════

class GuestBookingListItem(BaseModel):
    """GET /api/bookings 응답의 개별 항목."""
    confirmation_number: str
    hotel: Literal["City Hotel", "Resort Hotel"]
    arrival_date: date
    departure_date: date
    pricing_type: Literal["Standard Rate", "Flexi Rate"]
    status: Literal["Confirmed", "Pending", "Waitlisted", "Cancelled"]
    total_amount: float
    created_at: datetime

class GuestBookingListResponse(BaseModel):
    bookings: list[GuestBookingListItem]
    total: int


# ══════════════════════════════════════════════════════════════════
# SECTION 4: PMS 내부 번역 유틸
# App 1이 GuestBookingRequest → BookingRequest 변환 시 사용
# ══════════════════════════════════════════════════════════════════

# 손님 식사 선택 → DSS 모델 meal 코드 매핑
MEAL_MAP: dict[str, str] = {
    "Bed & Breakfast": "BB",
    "Half Board":      "HB",
    "Full Board":      "FB",
    "Room Only":       "SC",
}

# 손님 방 선호 → DSS 모델 room_type 코드 매핑
ROOM_TYPE_MAP: dict[str, str] = {
    "Single":        "A",
    "Double":        "D",
    "Twin":          "D",
    "Suite":         "G",
    "No Preference": "A",
}

# 손님 방 선호 → 화면 표시용 이름 매핑
ROOM_DISPLAY_MAP: dict[str, str] = {
    "Single":        "Single Room",
    "Double":        "Double Room",
    "Twin":          "Twin Room",
    "Suite":         "Suite",
    "No Preference": "Standard Room",
}

# PMS를 통한 예약은 항상 "Direct" 채널로 처리
DEFAULT_CHANNEL = "Direct"
DEFAULT_MARKET_SEGMENT = "Direct"
DEFAULT_CUSTOMER_TYPE = "Transient"

def build_dss_message(pricing_type: str, discount: Optional[float]) -> str:
    """GuestBookingConfirmation.message 생성."""
    if pricing_type == "Standard Rate":
        return "예약이 확정되었습니다. 체크인 당일 프런트데스크에서 확인해 주세요."
    pct = round((discount or 0) * 100, 1)
    return (
        f"Flexi 요금제로 예약되었습니다. {pct}% 할인이 적용되었으며, "
        "체크인 7일 전까지 무료 취소 가능합니다. "
        "취소 시 대기 손님에게 객실이 제공됩니다."
    )
