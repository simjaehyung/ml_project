"""
Hotel PMS — 손님 API 스키마 (LLM 에이전트 전용)

이 파일은 LLM 손님 에이전트가 PMS와 주고받는 데이터 형식이다.
LLM 에이전트는 이 스키마만 알면 된다.
FastAPI DSS 내부 개념(risk_score, shap_values, flexi_recommended)은
이 레이어 바깥으로 절대 노출하지 않는다.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════
# SECTION 1: 손님이 PMS에 보내는 데이터
# ══════════════════════════════════════════════════════════════════

class GuestBookingRequest(BaseModel):
    """LLM 손님 에이전트가 PMS에 보내는 예약 요청."""

    hotel: Literal["City Hotel", "Resort Hotel"]
    arrival_date: date
    departure_date: date
    adults: int = Field(ge=1, le=9)
    children: int = Field(ge=0, le=5, default=0)
    room_type_preference: Literal["Single", "Double", "Twin", "Suite", "No Preference"] = "No Preference"
    meal_plan: Literal["Bed & Breakfast", "Half Board", "Full Board", "Room Only"] = "Bed & Breakfast"
    nationality: str = Field(min_length=3, max_length=3)
    special_requests: str = Field(default="", max_length=300)
    agent_id: str = Field(description="LLM 에이전트 식별자. 예: 'guest-ana'")
    persona_description: str = Field(
        default="",
        description="페르소나 설명. 예: '비즈니스 여행객, 취소 이력 있음'",
    )


# ══════════════════════════════════════════════════════════════════
# SECTION 2: PMS가 손님에게 돌려주는 확인서
# ══════════════════════════════════════════════════════════════════

class GuestBookingConfirmation(BaseModel):
    """PMS가 LLM 에이전트에게 반환하는 예약 확인서."""

    confirmation_number: str
    hotel: Literal["City Hotel", "Resort Hotel"]
    arrival_date: date
    departure_date: date
    nights: int
    adults: int
    room_type_assigned: str
    pricing_type: Literal["Standard Rate", "Flexi Rate"]
    rate_per_night: float
    discount_applied: Optional[float]
    total_amount: float
    meal_plan: str
    status: Literal["Confirmed", "Pending", "Waitlisted"]
    message: str
    created_at: datetime


# ══════════════════════════════════════════════════════════════════
# SECTION 3: 손님 예약 조회
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
# SECTION 4: 내부 레코드 (PMS 관리자 UI용) — 에이전트에게 미노출
# ══════════════════════════════════════════════════════════════════

class PMSReservationRecord(BaseModel):
    """PMS 내부 저장용 레코드. 에이전트 메타데이터 + DSS 연결 정보 포함."""
    confirmation_number: str
    agent_id: str
    persona_name: str
    persona_type: str
    persona_nationality: str
    hotel: Literal["City Hotel", "Resort Hotel"]
    arrival_date: date
    departure_date: date
    nights: int
    adults: int
    room_type_assigned: str
    pricing_type: Literal["Standard Rate", "Flexi Rate"]
    rate_per_night: float
    discount_applied: Optional[float]
    total_amount: float
    meal_plan: str
    status: str
    dss_booking_id: Optional[str] = None
    dss_risk_score: Optional[float] = None
    created_at: datetime


class PMSReservationListResponse(BaseModel):
    reservations: list[PMSReservationRecord]
    total: int


# ══════════════════════════════════════════════════════════════════
# SECTION 5: 활동 로그 (실시간 피드용)
# ══════════════════════════════════════════════════════════════════

class PMSActivityEvent(BaseModel):
    """실시간 에이전트 활동 이벤트."""
    event_id: str
    timestamp: datetime
    agent_id: str
    persona_name: str
    persona_type: str
    action: Literal["thinking", "booking", "confirmed", "error"]
    message: str
    confirmation_number: Optional[str] = None
    hotel: Optional[str] = None
    pricing_type: Optional[Literal["Standard Rate", "Flexi Rate"]] = None
    discount_pct: Optional[float] = None

class PMSActivityResponse(BaseModel):
    events: list[PMSActivityEvent]
    total: int


class PMSStats(BaseModel):
    total_reservations: int
    flexi_count: int
    standard_count: int
    unique_agents: int
    recent_activity: int


# ══════════════════════════════════════════════════════════════════
# SECTION 6: PMS 내부 번역 유틸
# ══════════════════════════════════════════════════════════════════

MEAL_MAP: dict[str, str] = {
    "Bed & Breakfast": "BB",
    "Half Board":      "HB",
    "Full Board":      "FB",
    "Room Only":       "SC",
}

ROOM_TYPE_MAP: dict[str, str] = {
    "Single":        "A",
    "Double":        "D",
    "Twin":          "D",
    "Suite":         "G",
    "No Preference": "A",
}

ROOM_DISPLAY_MAP: dict[str, str] = {
    "Single":        "Single Room",
    "Double":        "Double Room",
    "Twin":          "Twin Room",
    "Suite":         "Suite",
    "No Preference": "Standard Room",
}

DEFAULT_CHANNEL = "Direct"
DEFAULT_MARKET_SEGMENT = "Direct"
DEFAULT_CUSTOMER_TYPE = "Transient"

def build_dss_message(pricing_type: str, discount: Optional[float]) -> str:
    if pricing_type == "Standard Rate":
        return "예약이 확정되었습니다. 체크인 당일 프런트데스크에서 확인해 주세요."
    pct = round((discount or 0) * 100, 1)
    return (
        f"Flexi 요금제로 예약되었습니다. {pct}% 할인이 적용되었으며, "
        "체크인 7일 전까지 무료 취소 가능합니다. "
        "취소 시 대기 손님에게 객실이 제공됩니다."
    )
