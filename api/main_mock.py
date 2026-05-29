"""
FastAPI 목업 서버 — 이고은 UI 개발용
실제 LightGBM 모델 없이 하드코딩된 응답 반환.

실행:
    uvicorn api.main_mock:app --port 8000 --reload

심재형이 실제 모델 연결 완료 후 → main.py로 교체.
이고은의 코드는 바꿀 필요 없음 (URL, 스키마 동일).
"""

import random
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    BookingAnalysis,
    BookingListItem,
    BookingListResponse,
    BookingRequest,
    BookingResponse,
    BookingStatus,
    ConfidenceLevel,
    DashboardSummary,
    ErrorResponse,
    FlexiPreview,
    RiskFactor,
)

app = FastAPI(
    title="Hotel DSS API (Mock)",
    description="Hotel No-Show DSS — 목업 서버 (이고은 UI 개발용)",
    version="0.1.0-mock",
)

# CORS: Next.js 개발 서버(3000)에서 FastAPI(8000)로 요청 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────
# 인메모리 예약 저장소 (목업용)
# ──────────────────────────────────────────
_bookings: list[BookingListItem] = []


def _seed_bookings() -> None:
    """앱 시작 시 더미 예약 20건 주입."""
    countries = ["PRT", "GBR", "FRA", "ESP", "DEU", "IRL", "BEL", "BRA", "NLD", "ITA"]
    hotels = ["City Hotel", "Resort Hotel"]
    statuses: list[BookingStatus] = ["confirmed", "high-risk", "flexi-routed"]

    for i in range(20):
        risk = round(random.uniform(0.1, 0.95), 4)
        flexi = risk >= 0.65
        disc = round(0.05 + (risk - 0.5) * 0.26, 4) if flexi else None
        disc = max(0.05, min(0.18, disc)) if disc is not None else None

        if risk >= 0.7:
            status: BookingStatus = "high-risk"
        elif flexi:
            status = "flexi-routed"
        else:
            status = "confirmed"

        _bookings.append(BookingListItem(
            booking_id=f"BK-{uuid.uuid4().hex[:6].upper()}",
            hotel=random.choice(hotels),
            country=random.choice(countries),
            arrival_date=date.today() + timedelta(days=random.randint(7, 180)),
            nights=random.randint(1, 7),
            adults=random.randint(1, 4),
            risk_score=risk,
            flexi_recommended=flexi,
            discount_rate=disc,
            status=status,
            created_at=datetime.now() - timedelta(hours=random.randint(0, 72)),
        ))


_seed_bookings()

CURRENT_THRESHOLD: float = 0.65


# ──────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────

def _mock_risk_factors() -> list[RiskFactor]:
    """SHAP 기반 위험 요인 목업 3개."""
    return [
        RiskFactor(
            feature="lead_time",
            label="리드타임 92일 (평균보다 41일 길다)",
            shap_value=0.38,
        ),
        RiskFactor(
            feature="distribution_channel_OTA",
            label="OTA 채널 (취소율 평균 44.2%)",
            shap_value=0.21,
        ),
        RiskFactor(
            feature="deposit_type_No_Deposit",
            label="디포짓 없음",
            shap_value=0.14,
        ),
    ]


def _mock_risk_factors_full(booking_id: str) -> list[RiskFactor]:
    """예약 상세 페이지용 SHAP 요인 10개 (목업)."""
    import hashlib
    seed = int(hashlib.md5(booking_id.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    factors = [
        RiskFactor(feature="previous_cancellations", label="과거 취소 이력 2회 (고위험 신호)", shap_value=round(rng.uniform(2.5, 4.5), 3)),
        RiskFactor(feature="total_of_special_requests", label="특별 요청 0건 (관여도 낮음)", shap_value=round(rng.uniform(0.5, 1.2), 3)),
        RiskFactor(feature="lead_time", label=f"리드타임 {rng.randint(60,150)}일 (평균보다 길다)", shap_value=round(rng.uniform(0.3, 0.8), 3)),
        RiskFactor(feature="distribution_channel_TA/TO", label="OTA/TA 채널 (취소율 44%)", shap_value=round(rng.uniform(0.2, 0.6), 3)),
        RiskFactor(feature="country_grouped_FRA", label="국적 FRA (취소율 높은 세그먼트)", shap_value=round(rng.uniform(0.1, 0.4), 3)),
        RiskFactor(feature="market_segment_Online_TA", label="Online TA 세그먼트", shap_value=round(rng.uniform(0.1, 0.3), 3)),
        RiskFactor(feature="arrival_date_month", label="성수기(7-8월) 도착", shap_value=round(rng.uniform(-0.1, 0.2), 3)),
        RiskFactor(feature="stays_in_week_nights", label="평일 숙박 4박", shap_value=round(rng.uniform(-0.2, 0.1), 3)),
        RiskFactor(feature="adults", label="성인 2명 (일반적 패턴)", shap_value=round(rng.uniform(-0.3, 0.1), 3)),
        RiskFactor(feature="adr", label="ADR €120 (중간 가격대)", shap_value=round(rng.uniform(-0.4, -0.1), 3)),
    ]
    # shap_value 절댓값 내림차순 정렬
    factors.sort(key=lambda f: abs(f.shap_value), reverse=True)
    return factors


def _confidence(score: float) -> ConfidenceLevel:
    if score < 0.35 or score > 0.75:
        return "HIGH"
    return "MEDIUM"


# ──────────────────────────────────────────
# 엔드포인트
# ──────────────────────────────────────────

@app.post(
    "/api/v1/bookings",
    response_model=BookingResponse,
    summary="신규 예약 제출 및 위험도 예측",
)
def create_booking(booking: BookingRequest) -> BookingResponse:
    """
    App 1 폼 제출 → 목업 위험도 반환.
    실제 모델 연결 후 main.py에서 LightGBM 추론으로 교체.
    """
    # 목업: lead_time에 따라 위험도 흉내
    lead_time = (booking.arrival_date - date.today()).days
    base_risk = min(0.95, max(0.05, lead_time / 400 + random.uniform(-0.1, 0.2)))
    if booking.distribution_channel == "TA/TO":
        base_risk = min(0.95, base_risk + 0.15)
    if booking.previous_cancellations > 0:
        base_risk = min(0.95, base_risk + 0.1 * booking.previous_cancellations)
    risk = round(base_risk, 4)

    flexi = risk >= CURRENT_THRESHOLD
    raw_disc = 0.05 + (risk - 0.5) * 0.26
    disc = round(max(0.05, min(0.18, raw_disc)), 4) if flexi else None

    if risk >= 0.7:
        status: BookingStatus = "high-risk"
    elif flexi:
        status = "flexi-routed"
    else:
        status = "confirmed"

    response = BookingResponse(
        booking_id=f"BK-{uuid.uuid4().hex[:6].upper()}",
        risk_score=risk,
        flexi_recommended=flexi,
        discount_rate=disc,
        top_risk_factors=_mock_risk_factors(),
        confidence=_confidence(risk),
        status=status,
        created_at=datetime.now(),
    )

    # 저장소에 추가 (App 2 대시보드에서 바로 보이도록)
    _bookings.append(BookingListItem(
        booking_id=response.booking_id,
        hotel=booking.hotel,
        country=booking.country,
        arrival_date=booking.arrival_date,
        nights=(booking.departure_date - booking.arrival_date).days,
        adults=booking.adults,
        risk_score=risk,
        flexi_recommended=flexi,
        discount_rate=disc,
        status=status,
        created_at=response.created_at,
    ))

    return response


@app.get(
    "/api/v1/bookings",
    response_model=BookingListResponse,
    summary="예약 목록 조회",
)
def list_bookings(
    status: Optional[BookingStatus] = Query(None),
    min_risk: Optional[float] = Query(None, ge=0, le=1),
) -> BookingListResponse:
    result = list(_bookings)
    if status:
        result = [b for b in result if b.status == status]
    if min_risk is not None:
        result = [b for b in result if b.risk_score >= min_risk]
    result.sort(key=lambda b: b.risk_score, reverse=True)
    return BookingListResponse(bookings=result, total=len(result))


@app.get(
    "/api/v1/bookings/{booking_id}",
    response_model=BookingListItem,
    summary="예약 단건 조회",
)
def get_booking(booking_id: str) -> BookingListItem:
    for b in _bookings:
        if b.booking_id == booking_id:
            return b
    raise HTTPException(status_code=404, detail=f"Booking {booking_id} not found")


@app.get(
    "/api/v1/bookings/{booking_id}/analysis",
    response_model=BookingAnalysis,
    summary="예약 전체 분석 (매니저 상세 페이지용)",
)
def get_booking_analysis(booking_id: str) -> BookingAnalysis:
    """
    매니저가 예약 상세 페이지를 열 때 호출.
    SHAP 상위 10개 요인 + Flexi 근거 반환.
    """
    booking = None
    for b in _bookings:
        if b.booking_id == booking_id:
            booking = b
            break
    if not booking:
        raise HTTPException(status_code=404, detail=f"Booking {booking_id} not found")

    # Flexi 할인율 공식: 5% + (risk - 0.5) * 26%, 범위 [5%, 18%]
    raw_disc = 0.05 + (booking.risk_score - 0.5) * 0.26
    disc = round(max(0.05, min(0.18, raw_disc)), 4) if booking.flexi_recommended else None

    # 예상 손실 계산 (목업: ADR × nights × 0.8 가정)
    est_nights = booking.nights
    est_adr = booking.risk_score * 200  # 목업 ADR 추정
    est_loss = round(est_adr * est_nights * 0.8, 2)
    est_discount_cost = round(est_adr * est_nights * (disc or 0), 2)

    # Flexi 근거 자연어
    if booking.flexi_recommended:
        rationale = (
            f"취소 위험도 {round(booking.risk_score*100)}%로 임계값(65%)을 초과합니다. "
            f"Flexi 요금제 적용 시 {round((disc or 0)*100, 1)}% 할인이 제공되며, "
            f"취소 시 예상 손실({est_loss:.0f}EUR)보다 할인 비용({est_discount_cost:.0f}EUR)이 적습니다."
        )
    else:
        rationale = f"취소 위험도 {round(booking.risk_score*100)}%로 임계값(65%) 이하입니다. 일반 요금제 배정을 권장합니다."

    return BookingAnalysis(
        booking_id=booking.booking_id,
        risk_score=booking.risk_score,
        flexi_recommended=booking.flexi_recommended,
        discount_rate=disc,
        confidence="HIGH" if booking.risk_score < 0.35 or booking.risk_score > 0.75 else "MEDIUM",
        top_risk_factors=_mock_risk_factors_full(booking_id),
        flexi_rationale=rationale,
        estimated_loss_if_cancel=est_loss,
        estimated_flexi_discount=est_discount_cost,
    )


@app.get(
    "/api/v1/dashboard/summary",
    response_model=DashboardSummary,
    summary="대시보드 KPI 요약",
)
def dashboard_summary() -> DashboardSummary:
    high_risk = [b for b in _bookings if b.risk_score >= CURRENT_THRESHOLD]
    flexi_routed = [b for b in _bookings if b.status == "flexi-routed"]
    avg = round(sum(b.risk_score for b in _bookings) / len(_bookings), 4) if _bookings else 0.0
    return DashboardSummary(
        total_bookings=len(_bookings),
        high_risk_count=len(high_risk),
        flexi_routed_count=len(flexi_routed),
        avg_risk_score=avg,
        current_threshold=CURRENT_THRESHOLD,
        last_updated=datetime.now(),
    )


@app.get(
    "/api/v1/flexi/preview",
    response_model=FlexiPreview,
    summary="임계값 변경 시 Flexi 풀 예측 미리보기",
)
def flexi_preview(
    threshold: float = Query(0.65, ge=0.50, le=0.85),
) -> FlexiPreview:
    pool = [b for b in _bookings if b.risk_score >= threshold]
    # 목업 walk rate: 임계값 높을수록 walk rate 증가 (더 공격적 오버부킹)
    est_walk = round(max(0.005, 0.12 - threshold * 0.15 + random.uniform(-0.01, 0.01)), 4)
    baseline = 0.035  # 블라인드 오버부킹 기준선
    return FlexiPreview(
        threshold=threshold,
        estimated_pool_size=len(pool),
        estimated_walk_rate=est_walk,
        baseline_walk_rate=baseline,
        walk_rate_improvement=round(baseline - est_walk, 4),
    )


# ──────────────────────────────────────────
# Option B: LLM은 FastAPI를 직접 호출하지 않는다
# LLM → App 1 PMS → FastAPI
#
# App 1 PMS가 내부적으로 이 엔드포인트를 proxy 호출한다.
# LLM 에이전트용 API는 app_pms/pms_mock.py 참고.
# ──────────────────────────────────────────

# 아래 엔드포인트는 App 1 PMS가 내부 호출할 때 사용하는
# "내부 프록시 확인용" 엔드포인트 (외부 노출 없음)

@app.get(
    "/api/v1/internal/state",
    response_model=DashboardSummary,
    summary="[내부] App 1 PMS가 DSS 상태 확인용 (외부 미노출)",
)
def internal_state() -> DashboardSummary:
    """App 1이 예약 후 DSS 상태를 확인하는 내부 엔드포인트."""
    return dashboard_summary()
