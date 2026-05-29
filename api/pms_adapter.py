"""
api/pms_adapter.py — PMS/폼 입력 → BookingRequest 변환 레이어

두 가지 진입점:
    adapt_apaleo(raw: dict) -> BookingRequest
        Apaleo PMS JSON (docs/design_16_api_contract.md 매핑 테이블 기준)

    adapt_form(form_data: dict) -> BookingRequest
        App 1 스태프 폼 직접 입력 — 필드명은 BookingRequest와 동일,
        주로 타입 변환 + 기본값 처리만 수행.

사용:
    from api.pms_adapter import adapt_apaleo, adapt_form
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from api.schemas import (
    BookingRequest,
    ChannelType,
    CustomerType,
    HotelType,
    MarketSegmentType,
    MealType,
    RoomType,
)

# ──────────────────────────────────────────────────────────────────
# 공통 매핑 테이블
# ──────────────────────────────────────────────────────────────────

# Apaleo mealPlan → DSS MealType
_APALEO_MEAL_MAP: dict[str, MealType] = {
    "RO":  "SC",        # Room Only
    "BB":  "BB",        # Bed & Breakfast
    "HB":  "HB",        # Half Board
    "FB":  "FB",        # Full Board
    "AI":  "FB",        # All Inclusive → Full Board (근사치)
    "SC":  "SC",        # Self-Catering
}

# Apaleo channelCode → DSS ChannelType
_APALEO_CHANNEL_MAP: dict[str, ChannelType] = {
    "Direct":     "Direct",
    "DIRECT":     "Direct",
    "Corporate":  "Corporate",
    "CORP":       "Corporate",
    "OTA":        "TA/TO",
    "GDS":        "GDS",
    "TA":         "TA/TO",
    "TO":         "TA/TO",
    "TA/TO":      "TA/TO",
}

# Apaleo channelCode → DSS MarketSegmentType (채널 기반 추정)
_CHANNEL_TO_MARKET: dict[str, MarketSegmentType] = {
    "Direct":    "Direct",
    "Corporate": "Corporate",
    "TA/TO":     "Online TA",
    "GDS":       "Offline TA/TO",
    "Undefined": "Direct",
}

# Apaleo ratePlan / roomType → DSS RoomType (알파벳 코드 A~L)
_APALEO_ROOM_MAP: dict[str, RoomType] = {
    "SINGLE":       "A",
    "Single":       "A",
    "STD":          "A",
    "STANDARD":     "A",
    "DOUBLE":       "D",
    "Double":       "D",
    "DBL":          "D",
    "TWIN":         "D",
    "SUPERIOR":     "E",
    "DELUXE":       "F",
    "SUITE":        "G",
    "Suite":        "G",
    "FAMILY":       "H",
    "LOFT":         "L",
    # 이미 A~L 형태면 그대로 통과
    "A": "A", "B": "B", "C": "C", "D": "D", "E": "E",
    "F": "F", "G": "G", "H": "H", "L": "L", "P": "P",
}

# 손님 meal_plan 자연어 → DSS MealType (pms_schemas.MEAL_MAP과 동일)
_GUEST_MEAL_MAP: dict[str, MealType] = {
    "Bed & Breakfast": "BB",
    "Half Board":      "HB",
    "Full Board":      "FB",
    "Room Only":       "SC",
    "BB":              "BB",
    "HB":              "HB",
    "FB":              "FB",
    "SC":              "SC",
    "Undefined":       "Undefined",
}

# 손님 room_type_preference → DSS RoomType (pms_schemas.ROOM_TYPE_MAP과 동일)
_GUEST_ROOM_MAP: dict[str, RoomType] = {
    "Single":        "A",
    "Double":        "D",
    "Twin":          "D",
    "Suite":         "G",
    "No Preference": "A",
}


# ──────────────────────────────────────────────────────────────────
# 내부 헬퍼
# ──────────────────────────────────────────────────────────────────

def _parse_date(value: Any) -> date:
    """문자열('YYYY-MM-DD') 또는 date/datetime 객체 → date."""
    if isinstance(value, date):
        return value if not isinstance(value, datetime) else value.date()
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise ValueError(f"날짜 파싱 실패: {value!r}")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ──────────────────────────────────────────────────────────────────
# A. Apaleo JSON → BookingRequest
# ──────────────────────────────────────────────────────────────────

def adapt_apaleo(raw: dict) -> BookingRequest:
    """
    Apaleo PMS JSON → BookingRequest 변환.

    Apaleo 필드 매핑 (docs/design_16_api_contract.md 기준):
        adults                        → adults
        children                      → children
        arrival                       → arrival_date  (ISO 날짜 문자열)
        departure                     → departure_date (ISO 날짜 문자열)
        channelCode                   → distribution_channel
        ratePlan.id / roomType        → reserved_room_type
        guestProfile.nationality      → country (ISO alpha-3)
        guestProfile.previousCancellations → previous_cancellations
        mealPlan                      → meal
        hotel                         → hotel ("City Hotel" / "Resort Hotel")
        adr / ratePerNight            → adr
        customerType                  → customer_type
        specialRequests               → total_of_special_requests (건수 추정)
        requiresParking               → required_car_parking_spaces
        isRepeatedGuest               → is_repeated_guest
        bookingChanges                → booking_changes
    """
    # ── 날짜 ──────────────────────────────────────────────────────
    arrival = _parse_date(raw.get("arrival") or raw.get("arrival_date"))
    departure = _parse_date(raw.get("departure") or raw.get("departure_date"))

    # ── 호텔 ──────────────────────────────────────────────────────
    hotel_raw: str = str(raw.get("hotel", "City Hotel"))
    if "resort" in hotel_raw.lower() or "Resort" in hotel_raw:
        hotel: HotelType = "Resort Hotel"
    else:
        hotel = "City Hotel"

    # ── 인원 ──────────────────────────────────────────────────────
    adults = max(1, _safe_int(raw.get("adults"), 1))
    children = _safe_int(raw.get("children"), 0)
    babies = _safe_int(raw.get("babies"), 0)

    # ── 채널 / 마켓 세그먼트 ──────────────────────────────────────
    channel_raw: str = str(raw.get("channelCode") or raw.get("distribution_channel") or "Direct")
    channel: ChannelType = _APALEO_CHANNEL_MAP.get(channel_raw, "Direct")  # type: ignore[assignment]

    market_raw: str = str(raw.get("marketSegment") or raw.get("market_segment") or "")
    if market_raw in ("Direct", "Corporate", "Online TA", "Offline TA/TO",
                      "Groups", "Complementary", "Aviation"):
        market: MarketSegmentType = market_raw  # type: ignore[assignment]
    else:
        market = _CHANNEL_TO_MARKET.get(channel, "Direct")

    # ── 객실 타입 ─────────────────────────────────────────────────
    room_raw: str = str(
        raw.get("roomType") or
        raw.get("ratePlan", {}).get("id", "") if isinstance(raw.get("ratePlan"), dict) else
        raw.get("reserved_room_type", "A")
    ).upper()
    room_type: RoomType = _APALEO_ROOM_MAP.get(room_raw, "A")  # type: ignore[assignment]

    # ── 식사 ──────────────────────────────────────────────────────
    meal_raw: str = str(raw.get("mealPlan") or raw.get("meal") or "BB").upper()
    meal: MealType = _APALEO_MEAL_MAP.get(meal_raw, _APALEO_MEAL_MAP.get(meal_raw.capitalize(), "BB"))  # type: ignore[assignment]
    if meal_raw.upper() not in _APALEO_MEAL_MAP:
        # 대소문자 무관 탐색
        meal = next(
            (v for k, v in _APALEO_MEAL_MAP.items() if k.upper() == meal_raw.upper()),
            "BB",
        )

    # ── 국적 ──────────────────────────────────────────────────────
    country: str = str(
        raw.get("guestProfile", {}).get("nationality") if isinstance(raw.get("guestProfile"), dict) else
        raw.get("nationality") or raw.get("country") or "PRT"
    ).upper()
    if len(country) != 3:
        country = "PRT"

    # ── 고객 타입 ─────────────────────────────────────────────────
    ct_raw: str = str(raw.get("customerType") or raw.get("customer_type") or "Transient")
    valid_ct = ("Transient", "Contract", "Transient-Party", "Group")
    customer_type: CustomerType = ct_raw if ct_raw in valid_ct else "Transient"  # type: ignore[assignment]

    # ── 수치형 ────────────────────────────────────────────────────
    prev_cancel = _safe_int(
        raw.get("guestProfile", {}).get("previousCancellations")
        if isinstance(raw.get("guestProfile"), dict) else
        raw.get("previous_cancellations"),
        0,
    )
    adr = _safe_float(raw.get("adr") or raw.get("ratePerNight"), 100.0)
    adr = max(0.0, adr)

    booking_changes = _safe_int(raw.get("bookingChanges") or raw.get("booking_changes"), 0)
    is_repeated = int(bool(raw.get("isRepeatedGuest") or raw.get("is_repeated_guest", 0)))

    # special_requests: 문자열이면 길이 > 0 → 1건, 없으면 0
    sr_raw = raw.get("specialRequests") or raw.get("special_requests") or ""
    if isinstance(sr_raw, int):
        total_sr = min(5, max(0, sr_raw))
    elif isinstance(sr_raw, str):
        total_sr = 1 if sr_raw.strip() else 0
    else:
        total_sr = 0

    parking = _safe_int(raw.get("requiresParking") or raw.get("required_car_parking_spaces"), 0)

    return BookingRequest(
        hotel=hotel,
        arrival_date=arrival,
        departure_date=departure,
        adults=adults,
        children=children,
        babies=babies,
        distribution_channel=channel,
        market_segment=market,
        reserved_room_type=room_type,
        meal=meal,
        country=country,
        is_repeated_guest=is_repeated,  # type: ignore[arg-type]
        previous_cancellations=prev_cancel,
        booking_changes=booking_changes,
        customer_type=customer_type,
        adr=adr,
        required_car_parking_spaces=parking,
        total_of_special_requests=total_sr,
    )


# ──────────────────────────────────────────────────────────────────
# B. App 1 스태프 폼 직접 입력 → BookingRequest
# ──────────────────────────────────────────────────────────────────

def adapt_form(form_data: dict) -> BookingRequest:
    """
    App 1 스태프 폼 직접 입력 dict → BookingRequest 변환.

    폼은 BookingRequest와 동일한 필드명을 사용한다고 가정.
    주로 수행하는 작업:
        1. arrival_date / departure_date: 문자열 → date
        2. 수치형 필드: 문자열 → int / float
        3. 기본값 보충 (없으면 스키마 기본값 사용)
        4. meal_plan 자연어 → MealType 코드 변환 (GuestBookingRequest 호환)
        5. room_type_preference 자연어 → RoomType 코드 변환 (GuestBookingRequest 호환)
    """
    fd = {k: (v.strip() if isinstance(v, str) else v) for k, v in form_data.items()}

    # ── 날짜 ──────────────────────────────────────────────────────
    arrival = _parse_date(fd["arrival_date"])
    departure = _parse_date(fd["departure_date"])

    # ── 호텔 ──────────────────────────────────────────────────────
    hotel_raw: str = str(fd.get("hotel", "City Hotel"))
    if hotel_raw not in ("City Hotel", "Resort Hotel"):
        hotel_raw = "City Hotel"
    hotel: HotelType = hotel_raw  # type: ignore[assignment]

    # ── 인원 ──────────────────────────────────────────────────────
    adults = max(1, _safe_int(fd.get("adults"), 1))
    children = _safe_int(fd.get("children"), 0)
    babies = _safe_int(fd.get("babies"), 0)

    # ── 채널 / 마켓 세그먼트 ──────────────────────────────────────
    channel_raw: str = str(fd.get("distribution_channel", "Direct"))
    valid_channels: tuple[str, ...] = ("Direct", "Corporate", "TA/TO", "GDS", "Undefined")
    channel: ChannelType = channel_raw if channel_raw in valid_channels else "Direct"  # type: ignore[assignment]

    ms_raw: str = str(fd.get("market_segment", "Direct"))
    valid_ms = ("Direct", "Corporate", "Online TA", "Offline TA/TO",
                "Groups", "Complementary", "Aviation", "Undefined")
    # GuestBookingRequest 호환: 자연어 채널이 오는 경우 변환
    if ms_raw not in valid_ms:
        ms_raw = _CHANNEL_TO_MARKET.get(channel, "Direct")
    market: MarketSegmentType = ms_raw  # type: ignore[assignment]

    # ── 객실 타입 ─────────────────────────────────────────────────
    rt_raw: str = str(fd.get("reserved_room_type") or fd.get("room_type_preference") or "A")
    # GuestBookingRequest 자연어 선호("Double", "Suite" 등) 호환
    room_type: RoomType = (
        _GUEST_ROOM_MAP.get(rt_raw)          # 자연어 형태
        or _APALEO_ROOM_MAP.get(rt_raw.upper())  # 대문자 코드
        or "A"
    )  # type: ignore[assignment]

    # ── 식사 ──────────────────────────────────────────────────────
    meal_raw: str = str(fd.get("meal") or fd.get("meal_plan") or "BB")
    # GuestBookingRequest 자연어("Bed & Breakfast" 등) 호환
    meal: MealType = (
        _GUEST_MEAL_MAP.get(meal_raw)
        or _APALEO_MEAL_MAP.get(meal_raw.upper(), "BB")
    )  # type: ignore[assignment]

    # ── 국적 ──────────────────────────────────────────────────────
    country_raw: str = str(
        fd.get("country") or fd.get("nationality") or "PRT"
    ).upper()
    if len(country_raw) != 3:
        country_raw = "PRT"

    # ── 고객 타입 ─────────────────────────────────────────────────
    ct_raw: str = str(fd.get("customer_type", "Transient"))
    valid_ct = ("Transient", "Contract", "Transient-Party", "Group")
    customer_type: CustomerType = ct_raw if ct_raw in valid_ct else "Transient"  # type: ignore[assignment]

    # ── 수치형 ────────────────────────────────────────────────────
    is_repeated = int(bool(_safe_int(fd.get("is_repeated_guest"), 0)))
    prev_cancel = min(26, max(0, _safe_int(fd.get("previous_cancellations"), 0)))
    booking_changes = min(21, max(0, _safe_int(fd.get("booking_changes"), 0)))
    adr = max(0.0, _safe_float(fd.get("adr"), 100.0))
    parking = min(8, max(0, _safe_int(fd.get("required_car_parking_spaces"), 0)))
    total_sr = min(5, max(0, _safe_int(fd.get("total_of_special_requests"), 0)))

    return BookingRequest(
        hotel=hotel,
        arrival_date=arrival,
        departure_date=departure,
        adults=adults,
        children=children,
        babies=babies,
        distribution_channel=channel,
        market_segment=market,
        reserved_room_type=room_type,
        meal=meal,
        country=country_raw,
        is_repeated_guest=is_repeated,  # type: ignore[arg-type]
        previous_cancellations=prev_cancel,
        booking_changes=booking_changes,
        customer_type=customer_type,
        adr=adr,
        required_car_parking_spaces=parking,
        total_of_special_requests=total_sr,
    )
