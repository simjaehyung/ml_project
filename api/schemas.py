"""
Hotel DSS — FastAPI 스키마 (단일 진실 공급원)

호출 가능한 대상:
    - App 1 PMS (App 1 내부에서 proxy 호출)
    - App 2 DSS 대시보드 (읽기 전용 polling)

LLM 손님 에이전트는 이 파일을 직접 참조하지 않는다.
LLM은 app_pms/pms_schemas.py 기준으로 App 1 PMS와만 통신한다.

변경 시 반드시 상대방에게 공지하고 types.ts도 동시에 수정.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════
# SECTION 1: 공유 enum 상수
# 프론트엔드에서도 동일한 문자열을 사용해야 한다.
# ══════════════════════════════════════════════════════════════════

HotelType = Literal["City Hotel", "Resort Hotel"]
ChannelType = Literal["Direct", "Corporate", "TA/TO", "GDS", "Undefined"]
MarketSegmentType = Literal[
    "Direct", "Corporate", "Online TA", "Offline TA/TO",
    "Groups", "Complementary", "Aviation"
]
RoomType = Literal["A", "B", "C", "D", "E", "F", "G", "H", "L"]
MealType = Literal["BB", "HB", "FB", "SC", "Undefined"]
CustomerType = Literal["Transient", "Contract", "Transient-Party", "Group"]
BookingStatus = Literal["confirmed", "high-risk", "flexi-routed"]
ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW"]
# HIGH  : risk_score < 0.35 또는 > 0.75 (모델이 명확히 판단)
# MEDIUM: 0.35 ~ 0.75 구간 (불확실 구간)
# LOW   : 입력값 이상 탐지 시 (극단값, 미지 국가 코드 등)


# ══════════════════════════════════════════════════════════════════
# SECTION 2: App 1 폼 → FastAPI (Request)
# ══════════════════════════════════════════════════════════════════

class BookingRequest(BaseModel):
    """
    App 1 신규 예약 폼에서 FastAPI로 보내는 데이터.
    프론트엔드는 이 모든 필드를 정확히 이 이름으로 전송해야 한다.

    서버가 자동 계산하는 것 (폼에 없어도 됨):
      - lead_time     : arrival_date - 오늘 날짜
      - stays_*       : arrival_date와 departure_date로 계산
      - arrival_date_* : arrival_date 파싱
      - 날씨 피처      : hotel + arrival_date_month 기반 계절 평균값
    """

    # 호텔
    hotel: HotelType

    # 날짜
    arrival_date: date
    departure_date: date  # stays_in_* 계산에 사용. departure > arrival 강제

    # 인원
    adults: int = Field(ge=1, le=55)
    children: int = Field(ge=0, le=10, default=0)
    babies: int = Field(ge=0, le=10, default=0)

    # 채널
    distribution_channel: ChannelType
    market_segment: MarketSegmentType

    # 방·식사
    reserved_room_type: RoomType
    meal: MealType

    # 고객
    country: str = Field(min_length=3, max_length=3)  # ISO 3166-1 alpha-3, 예: "GBR", "PRT"
    is_repeated_guest: Literal[0, 1] = 0
    previous_cancellations: int = Field(ge=0, le=26, default=0)
    booking_changes: int = Field(ge=0, le=21, default=0)

    # 조건
    customer_type: CustomerType
    adr: float = Field(ge=0, description="Average Daily Rate (EUR)")
    required_car_parking_spaces: int = Field(ge=0, le=8, default=0)
    total_of_special_requests: int = Field(ge=0, le=5, default=0)

    # deposit_type은 모델에서 제외됨 (CLAUDE.md 확정 결정).
    # PMS 폼에는 있어도 되지만 예측에 사용하지 않음.


# ══════════════════════════════════════════════════════════════════
# SECTION 3: FastAPI → App 1/2 (Response)
# ══════════════════════════════════════════════════════════════════

class RiskFactor(BaseModel):
    """SHAP 기반 위험 요인 1개. top_risk_factors 리스트에 3개 들어감."""
    feature: str    # 내부 피처명. 예: "lead_time"
    label: str      # 화면 표시용 자연어. 예: "리드타임 92일 (평균보다 41일 길다)"
    shap_value: float  # 양수 = 취소 위험 증가 기여, 음수 = 감소 기여


class BookingResponse(BaseModel):
    """
    POST /api/v1/bookings 응답.
    App 1 제출 모달과 App 2 대시보드 신규 행 모두 이 스키마 사용.
    """
    booking_id: str                          # 서버 생성 UUID 앞 8자리. 예: "BK-3F9A1C"
    risk_score: float = Field(ge=0.0, le=1.0)
    flexi_recommended: bool                  # risk_score >= current_threshold
    discount_rate: Optional[float] = Field(  # flexi_recommended == True 일 때만 존재
        None, ge=0.05, le=0.18,
        description="5% + (risk_score - 0.5) * 26%, 범위 [0.05, 0.18]"
    )
    top_risk_factors: list[RiskFactor]       # 정확히 3개. SHAP |value| 내림차순
    confidence: ConfidenceLevel
    status: BookingStatus                    # 초기값: high-risk 또는 confirmed
    created_at: datetime


# ══════════════════════════════════════════════════════════════════
# SECTION 4: App 2 대시보드 목록 조회
# ══════════════════════════════════════════════════════════════════

class BookingListItem(BaseModel):
    """
    GET /api/v1/bookings 응답의 개별 예약 요약.
    App 2 DataTable 한 행에 해당.
    """
    booking_id: str
    hotel: HotelType
    country: str                             # ISO alpha-3
    arrival_date: date
    nights: int = Field(ge=1)
    adults: int = Field(ge=1)
    risk_score: float = Field(ge=0.0, le=1.0)
    flexi_recommended: bool
    discount_rate: Optional[float]
    status: BookingStatus
    created_at: datetime


class BookingListResponse(BaseModel):
    """GET /api/v1/bookings 전체 응답."""
    bookings: list[BookingListItem]
    total: int


# ══════════════════════════════════════════════════════════════════
# SECTION 5: App 2 대시보드 요약 KPI
# ══════════════════════════════════════════════════════════════════

class DashboardSummary(BaseModel):
    """
    GET /api/v1/dashboard/summary 응답.
    App 2 상단 KPI 카드 4개에 매핑.
    """
    total_bookings: int          # KPI 카드 1
    high_risk_count: int         # KPI 카드 2 (risk_score >= current_threshold)
    flexi_routed_count: int      # KPI 카드 3
    avg_risk_score: float        # KPI 카드 4
    current_threshold: float     # Flexi 임계값 현재 설정값 (기본: 0.65)
    last_updated: datetime


# ══════════════════════════════════════════════════════════════════
# SECTION 6: Flexi 임계값 미리보기
# ══════════════════════════════════════════════════════════════════

class FlexiPreview(BaseModel):
    """
    GET /api/v1/flexi/preview?threshold=0.65 응답.
    App 2 Flexi 패널 슬라이더 실시간 업데이트에 사용.
    """
    threshold: float = Field(ge=0.50, le=0.85)
    estimated_pool_size: int           # 해당 임계값에서 Flexi 대상 예약 수
    estimated_walk_rate: float         # 예상 walk rate (0~1)
    baseline_walk_rate: float          # 블라인드 오버부킹 기준선 (비교용)
    walk_rate_improvement: float       # baseline - estimated (양수 = 개선)


# ══════════════════════════════════════════════════════════════════
# SECTION 7: 삭제됨 — LLM 에이전트 직접 접근 제거 (Option B 전환)
#
# LLM 에이전트는 FastAPI DSS를 직접 호출하지 않는다.
# 경로: LLM → App 1 PMS API → FastAPI DSS
# LLM 전용 스키마: app_pms/pms_schemas.py 참고
# ══════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════
# SECTION 8: 에러 응답
# ══════════════════════════════════════════════════════════════════

class ErrorResponse(BaseModel):
    """모든 에러 응답의 공통 형식."""
    code: str       # 예: "INVALID_DATE_RANGE", "UNKNOWN_COUNTRY"
    message: str    # 사람이 읽는 설명
    field: Optional[str] = None   # 어느 필드가 문제인지 (있을 때만)


# ══════════════════════════════════════════════════════════════════
# SECTION 9: 예약 전체 분석 (매니저 상세 페이지)
# ══════════════════════════════════════════════════════════════════

class BookingAnalysis(BaseModel):
    """
    GET /api/v1/bookings/{id}/analysis 응답.
    매니저 전체 상세 페이지에서 사용.
    """
    booking_id: str
    risk_score: float
    flexi_recommended: bool
    discount_rate: Optional[float]
    confidence: ConfidenceLevel
    top_risk_factors: list[RiskFactor]   # 상위 10개 (상세 페이지용)
    flexi_rationale: str                  # Flexi 결정 근거 자연어
    estimated_loss_if_cancel: float       # 취소 시 예상 손실액 (EUR)
    estimated_flexi_discount: float       # Flexi 할인 비용 (EUR)
