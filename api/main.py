"""
api/main.py — 실제 LightGBM 모델 연결 FastAPI 서버

main_mock.py의 목업 risk 계산을 실제 LightGBM 모델 추론으로 교체.
URL, 스키마, CORS 설정은 main_mock.py와 완전히 동일 — 이고은의 프론트엔드 코드 변경 없음.

실행:
    uvicorn api.main:app --port 8000 --reload

변경 내용:
    - create_booking(): mock risk 계산 → api.predictor.predict() 호출
    - _seed_bookings(): 유지 (초기 더미 데이터 20건)
    - 나머지 엔드포인트: main_mock.py와 동일
"""

import json
import random
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.predictor import predict
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
    title="Hotel DSS API",
    description="Hotel No-Show DSS — 실제 LightGBM 모델 연결 서버",
    version="1.0.0",
)

# CORS: Next.js 개발 서버(3000, 3001)에서 FastAPI(8000)로 요청 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────
# 인메모리 예약 저장소
# ──────────────────────────────────────────
_bookings: list[BookingListItem] = []
_analyses: dict[str, BookingAnalysis] = {}  # booking_id → 분석 데이터


# 발표용 실제 스냅샷(테스트셋 기간 'as-of' 예약). src/build_demo_snapshot.py 산출물.
SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "data" / "demo_snapshot.json"


def _load_snapshot() -> Optional[dict]:
    try:
        if SNAPSHOT_PATH.exists():
            data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
            if data.get("bookings"):
                return data
    except Exception:
        pass
    return None


def _seed_bookings() -> None:
    """앱 시작 시 예약 주입 — 발표용 실제 스냅샷 우선(data/demo_snapshot.json), 없으면 랜덤 더미."""
    snap = _load_snapshot()
    if snap:
        for r in snap["bookings"]:
            _bookings.append(BookingListItem(
                booking_id=r["booking_id"],
                hotel=r["hotel"],
                country=r["country"],
                arrival_date=date.fromisoformat(r["arrival_date"]),
                nights=r["nights"],
                adults=r["adults"],
                risk_score=r["risk_score"],
                flexi_recommended=r["flexi_recommended"],
                discount_rate=r.get("discount_rate"),
                status=r["status"],
                created_at=datetime.fromisoformat(r["created_at"]),
            ))
        return

    # ── 폴백: 랜덤 더미 20건 (스냅샷 없을 때 demo-stable) ──
    countries = ["PRT", "GBR", "FRA", "ESP", "DEU", "IRL", "BEL", "BRA", "NLD", "ITA"]
    hotels = ["City Hotel", "Resort Hotel"]
    statuses: list[BookingStatus] = ["confirmed", "high-risk", "flexi-routed"]

    for i in range(20):
        risk = round(random.uniform(0.1, 0.95), 4)
        flexi = risk >= CURRENT_THRESHOLD
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


CURRENT_THRESHOLD: float = 0.65


def _confidence(score: float) -> ConfidenceLevel:
    if score < 0.35 or score > 0.75:
        return "HIGH"
    return "MEDIUM"


_FACTOR_POOL = [
    RiskFactor(feature="lead_time", label="리드타임 120일 이상", shap_value=0.64),
    RiskFactor(feature="country_grouped_PRT", label="국적: 포르투갈 (PRT)", shap_value=0.94),
    RiskFactor(feature="total_of_special_requests", label="특별 요청 없음", shap_value=0.53),
    RiskFactor(feature="market_segment_Online TA", label="채널: Online TA", shap_value=0.41),
    RiskFactor(feature="previous_cancellations", label="이전 취소 이력 있음", shap_value=1.12),
    RiskFactor(feature="required_car_parking_spaces", label="주차 요청 없음", shap_value=0.29),
    RiskFactor(feature="adults", label="성인 1명 단독 예약", shap_value=0.22),
]

_RATIONALE_MAP = {
    True:  "리드타임이 길고 특별 요청이 없어 가격 탐색형 예약으로 분류됩니다. Flexi Rate 제안으로 빈 방 위험을 선제 관리하세요.",
    False: "취소 위험도가 낮아 Standard 배정을 권장합니다.",
}


def _make_seed_analysis(b: BookingListItem) -> BookingAnalysis:
    factors = random.sample(_FACTOR_POOL, min(3, len(_FACTOR_POOL)))
    adr_est = random.uniform(80, 160)
    nights_est = b.nights
    return BookingAnalysis(
        booking_id=b.booking_id,
        risk_score=b.risk_score,
        flexi_recommended=b.flexi_recommended,
        discount_rate=b.discount_rate,
        confidence=_confidence(b.risk_score),
        top_risk_factors=factors,
        flexi_rationale=_RATIONALE_MAP[b.flexi_recommended],
        estimated_loss_if_cancel=round(adr_est * nights_est, 1),
        estimated_flexi_discount=round(adr_est * nights_est * (b.discount_rate or 0), 1),
    )


_seed_bookings()

for _b in _bookings:
    _analyses[_b.booking_id] = _make_seed_analysis(_b)


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
    App 1 폼 제출 → 실제 LightGBM 모델로 위험도 예측.
    SHAP TreeExplainer를 사용해 top 3 위험 요인도 함께 반환.
    """
    risk_score, top_risk_factors = predict(booking)

    flexi = risk_score >= CURRENT_THRESHOLD
    raw_disc = 0.05 + (risk_score - 0.5) * 0.26
    disc = round(max(0.05, min(0.18, raw_disc)), 4) if flexi else None

    if risk_score >= 0.7:
        status: BookingStatus = "high-risk"
    elif flexi:
        status = "flexi-routed"
    else:
        status = "confirmed"

    response = BookingResponse(
        booking_id=f"BK-{uuid.uuid4().hex[:6].upper()}",
        risk_score=round(risk_score, 4),
        flexi_recommended=flexi,
        discount_rate=disc,
        top_risk_factors=top_risk_factors,
        confidence=_confidence(risk_score),
        status=status,
        created_at=datetime.now(),
    )

    nights = (booking.departure_date - booking.arrival_date).days

    list_item = BookingListItem(
        booking_id=response.booking_id,
        hotel=booking.hotel,
        country=booking.country,
        arrival_date=booking.arrival_date,
        nights=nights,
        adults=booking.adults,
        risk_score=round(risk_score, 4),
        flexi_recommended=flexi,
        discount_rate=disc,
        status=status,
        created_at=response.created_at,
    )
    _bookings.append(list_item)

    # 분석 데이터 저장 (상세 페이지용)
    rationale = (
        "리드타임이 길고 취소 이력이 있어 고위험으로 분류됩니다. Flexi Rate 제안으로 빈 방 위험을 선제 관리하세요."
        if flexi else
        "취소 위험도가 낮아 Standard 배정을 권장합니다."
    )
    _analyses[response.booking_id] = BookingAnalysis(
        booking_id=response.booking_id,
        risk_score=round(risk_score, 4),
        flexi_recommended=flexi,
        discount_rate=disc,
        confidence=_confidence(risk_score),
        top_risk_factors=top_risk_factors,
        flexi_rationale=rationale,
        estimated_loss_if_cancel=round(booking.adr * nights, 1),
        estimated_flexi_discount=round(booking.adr * nights * (disc or 0), 1),
    )

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
    summary="예약 위험도 상세 분석 (SHAP 포함)",
)
def get_booking_analysis(booking_id: str) -> BookingAnalysis:
    if booking_id in _analyses:
        return _analyses[booking_id]
    # _analyses에 없으면 bookings에서 기본 분석 생성
    for b in _bookings:
        if b.booking_id == booking_id:
            return _make_seed_analysis(b)
    raise HTTPException(status_code=404, detail=f"Booking {booking_id} not found")


@app.get(
    "/api/v1/dashboard/summary",
    response_model=DashboardSummary,
    summary="대시보드 KPI 요약",
)
def dashboard_summary() -> DashboardSummary:
    high_risk = [b for b in _bookings if b.risk_score >= CURRENT_THRESHOLD]
    # Flexi 권장 건수(=라우팅 대상). status는 high-risk가 우선이라, 권장 플래그로 집계.
    flexi_routed = [b for b in _bookings if b.flexi_recommended]
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
    # walk rate: 임계값 높을수록 walk rate 증가 (더 공격적 오버부킹)
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

@app.get(
    "/api/v1/internal/state",
    response_model=DashboardSummary,
    summary="[내부] App 1 PMS가 DSS 상태 확인용 (외부 미노출)",
)
def internal_state() -> DashboardSummary:
    """App 1이 예약 후 DSS 상태를 확인하는 내부 엔드포인트."""
    return dashboard_summary()
