"""
api/predictor.py — 실제 LightGBM 모델 + SHAP 추론 엔진

모델: results/model_final.pkl (LGBMClassifier, PR-AUC 0.8189)
피처: 70개 (model.feature_name_ 순서와 정확히 일치해야 함)
날씨: data/seasonal_weather.csv (hotel × month 계절 평균값)

사용:
    from api.predictor import predict
    risk_score, risk_factors = predict(booking_request)
"""

from __future__ import annotations

import pickle
from datetime import date
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import shap

from api.schemas import BookingRequest, RiskFactor

# ──────────────────────────────────────────────────────────────────
# 경로 설정
# ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "results" / "model_final.pkl"
WEATHER_PATH = ROOT / "data" / "seasonal_weather.csv"

# ──────────────────────────────────────────────────────────────────
# 모델 + SHAP 초기화 (모듈 로드 시 1회)
# ──────────────────────────────────────────────────────────────────
with open(MODEL_PATH, "rb") as _f:
    _model = pickle.load(_f)

_explainer = shap.TreeExplainer(_model)

# ──────────────────────────────────────────────────────────────────
# 날씨 계절 평균값 로드
# seasonal_weather.csv 없으면 하드코딩 폴백 사용
# ──────────────────────────────────────────────────────────────────
_WEATHER_COLS = [
    "precipitation_sum",
    "temperature_2m_max",
    "temperature_2m_min",
    "wind_speed_10m_max",
    "precipitation_hours",
    "relative_humidity_2m_mean",
    "cloud_cover_mean",
]

# seasonal_weather.csv → dict: (hotel, month) → {col: value}
_SEASONAL_WEATHER: dict[tuple[str, int], dict[str, float]] = {}

if WEATHER_PATH.exists():
    _sw_df = pd.read_csv(WEATHER_PATH)
    for _, row in _sw_df.iterrows():
        key = (str(row["hotel"]), int(row["arrival_date_month"]))
        _SEASONAL_WEATHER[key] = {col: float(row[col]) for col in _WEATHER_COLS}
else:
    # 포르투갈 기후 기반 하드코딩 폴백
    # (City Hotel = 리스본, Resort Hotel = 알가르브)
    _FALLBACK_CITY = {
        1:  {"precipitation_sum": 2.40, "temperature_2m_max": 15.00, "temperature_2m_min": 11.63, "wind_speed_10m_max": 22.49, "precipitation_hours": 5.01, "relative_humidity_2m_mean": 84.17, "cloud_cover_mean": 74.78},
        2:  {"precipitation_sum": 2.90, "temperature_2m_max": 13.90, "temperature_2m_min":  9.88, "wind_speed_10m_max": 31.06, "precipitation_hours": 5.33, "relative_humidity_2m_mean": 77.27, "cloud_cover_mean": 54.24},
        3:  {"precipitation_sum": 1.09, "temperature_2m_max": 14.48, "temperature_2m_min":  9.85, "wind_speed_10m_max": 24.75, "precipitation_hours": 3.67, "relative_humidity_2m_mean": 79.56, "cloud_cover_mean": 47.55},
        4:  {"precipitation_sum": 2.12, "temperature_2m_max": 16.51, "temperature_2m_min": 11.93, "wind_speed_10m_max": 26.25, "precipitation_hours": 4.75, "relative_humidity_2m_mean": 79.17, "cloud_cover_mean": 57.25},
        5:  {"precipitation_sum": 4.50, "temperature_2m_max": 19.13, "temperature_2m_min": 13.86, "wind_speed_10m_max": 24.21, "precipitation_hours": 5.73, "relative_humidity_2m_mean": 79.25, "cloud_cover_mean": 49.54},
        6:  {"precipitation_sum": 0.09, "temperature_2m_max": 23.70, "temperature_2m_min": 16.79, "wind_speed_10m_max": 24.88, "precipitation_hours": 0.44, "relative_humidity_2m_mean": 72.00, "cloud_cover_mean": 35.16},
        7:  {"precipitation_sum": 0.09, "temperature_2m_max": 27.16, "temperature_2m_min": 18.75, "wind_speed_10m_max": 25.68, "precipitation_hours": 0.11, "relative_humidity_2m_mean": 69.06, "cloud_cover_mean": 19.27},
        8:  {"precipitation_sum": 0.01, "temperature_2m_max": 27.05, "temperature_2m_min": 18.80, "wind_speed_10m_max": 24.96, "precipitation_hours": 0.07, "relative_humidity_2m_mean": 67.79, "cloud_cover_mean": 23.87},
        9:  {"precipitation_sum": 0.39, "temperature_2m_max": 24.70, "temperature_2m_min": 17.40, "wind_speed_10m_max": 22.49, "precipitation_hours": 0.38, "relative_humidity_2m_mean": 70.88, "cloud_cover_mean": 29.17},
        10: {"precipitation_sum": 2.50, "temperature_2m_max": 21.22, "temperature_2m_min": 16.32, "wind_speed_10m_max": 20.48, "precipitation_hours": 4.79, "relative_humidity_2m_mean": 80.49, "cloud_cover_mean": 63.36},
        11: {"precipitation_sum": 2.36, "temperature_2m_max": 17.30, "temperature_2m_min": 13.08, "wind_speed_10m_max": 21.55, "precipitation_hours": 3.74, "relative_humidity_2m_mean": 81.44, "cloud_cover_mean": 47.62},
        12: {"precipitation_sum": 1.54, "temperature_2m_max": 15.68, "temperature_2m_min": 10.95, "wind_speed_10m_max": 19.23, "precipitation_hours": 2.54, "relative_humidity_2m_mean": 84.98, "cloud_cover_mean": 52.14},
    }
    _FALLBACK_RESORT = {
        1:  {"precipitation_sum": 1.18, "temperature_2m_max": 16.17, "temperature_2m_min": 12.91, "wind_speed_10m_max": 26.60, "precipitation_hours": 3.09, "relative_humidity_2m_mean": 77.84, "cloud_cover_mean": 65.48},
        2:  {"precipitation_sum": 0.80, "temperature_2m_max": 15.68, "temperature_2m_min": 11.87, "wind_speed_10m_max": 35.92, "precipitation_hours": 1.54, "relative_humidity_2m_mean": 75.05, "cloud_cover_mean": 60.71},
        3:  {"precipitation_sum": 0.17, "temperature_2m_max": 16.42, "temperature_2m_min": 10.58, "wind_speed_10m_max": 27.15, "precipitation_hours": 0.79, "relative_humidity_2m_mean": 69.93, "cloud_cover_mean": 26.78},
        4:  {"precipitation_sum": 1.18, "temperature_2m_max": 18.07, "temperature_2m_min": 13.35, "wind_speed_10m_max": 26.56, "precipitation_hours": 3.48, "relative_humidity_2m_mean": 75.47, "cloud_cover_mean": 49.64},
        5:  {"precipitation_sum": 3.15, "temperature_2m_max": 20.04, "temperature_2m_min": 15.19, "wind_speed_10m_max": 29.30, "precipitation_hours": 3.97, "relative_humidity_2m_mean": 72.94, "cloud_cover_mean": 40.48},
        6:  {"precipitation_sum": 0.00, "temperature_2m_max": 24.73, "temperature_2m_min": 18.52, "wind_speed_10m_max": 28.16, "precipitation_hours": 0.00, "relative_humidity_2m_mean": 62.96, "cloud_cover_mean": 15.99},
        7:  {"precipitation_sum": 0.00, "temperature_2m_max": 28.02, "temperature_2m_min": 21.49, "wind_speed_10m_max": 26.69, "precipitation_hours": 0.00, "relative_humidity_2m_mean": 60.85, "cloud_cover_mean":  9.69},
        8:  {"precipitation_sum": 0.00, "temperature_2m_max": 27.27, "temperature_2m_min": 21.52, "wind_speed_10m_max": 25.86, "precipitation_hours": 0.02, "relative_humidity_2m_mean": 64.08, "cloud_cover_mean": 16.33},
        9:  {"precipitation_sum": 0.10, "temperature_2m_max": 24.64, "temperature_2m_min": 19.27, "wind_speed_10m_max": 24.42, "precipitation_hours": 0.26, "relative_humidity_2m_mean": 67.29, "cloud_cover_mean": 22.18},
        10: {"precipitation_sum": 3.48, "temperature_2m_max": 21.58, "temperature_2m_min": 17.61, "wind_speed_10m_max": 25.07, "precipitation_hours": 4.96, "relative_humidity_2m_mean": 77.66, "cloud_cover_mean": 54.25},
        11: {"precipitation_sum": 1.73, "temperature_2m_max": 18.76, "temperature_2m_min": 14.32, "wind_speed_10m_max": 25.74, "precipitation_hours": 2.35, "relative_humidity_2m_mean": 74.53, "cloud_cover_mean": 35.01},
        12: {"precipitation_sum": 2.39, "temperature_2m_max": 16.87, "temperature_2m_min": 13.67, "wind_speed_10m_max": 26.34, "precipitation_hours": 2.79, "relative_humidity_2m_mean": 79.75, "cloud_cover_mean": 45.92},
    }
    for m in range(1, 13):
        _SEASONAL_WEATHER[("City Hotel", m)] = _FALLBACK_CITY[m]
        _SEASONAL_WEATHER[("Resort Hotel", m)] = _FALLBACK_RESORT[m]


# ──────────────────────────────────────────────────────────────────
# Top10 국가 (훈련 기준)
# ──────────────────────────────────────────────────────────────────
_TOP10_COUNTRIES = {"PRT", "GBR", "FRA", "ESP", "DEU", "IRL", "BEL", "BRA", "NLD", "ITA"}

# ──────────────────────────────────────────────────────────────────
# 피처 순서 (모델과 정확히 일치)
# ──────────────────────────────────────────────────────────────────
FEATURE_ORDER: list[str] = _model.feature_name_

# ──────────────────────────────────────────────────────────────────
# 자연어 레이블 템플릿
# ──────────────────────────────────────────────────────────────────
_LABEL_TEMPLATES: dict[str, str] = {
    "lead_time":                        "리드타임 {value:.0f}일",
    "arrival_date_year":                "도착 연도 {value:.0f}년",
    "arrival_date_month":               "도착 월 {value:.0f}월",
    "arrival_date_week_number":         "도착 주차 {value:.0f}주",
    "arrival_date_day_of_month":        "도착 일 {value:.0f}일",
    "stays_in_weekend_nights":          "주말 숙박 {value:.0f}박",
    "stays_in_week_nights":             "평일 숙박 {value:.0f}박",
    "adults":                           "성인 {value:.0f}명",
    "children":                         "어린이 {value:.0f}명",
    "babies":                           "유아 {value:.0f}명",
    "is_repeated_guest":                "재방문 고객" if None else "재방문 여부",
    "previous_cancellations":           "이전 취소 이력 {value:.0f}회",
    "booking_changes":                  "예약 변경 횟수 {value:.0f}회",
    "agent":                            "에이전트 코드 {value:.0f}",
    "company":                          "회사 코드 {value:.0f}",
    "adr":                              "1박 평균 요금 {value:.0f}EUR",
    "required_car_parking_spaces":      "주차 공간 {value:.0f}개",
    "total_of_special_requests":        "특별 요청 {value:.0f}건",
    "precipitation_sum":                "강수량 {value:.1f}mm (계절 평균)",
    "temperature_2m_max":               "최고 기온 {value:.1f}°C (계절 평균)",
    "temperature_2m_min":               "최저 기온 {value:.1f}°C (계절 평균)",
    "wind_speed_10m_max":               "최대 풍속 {value:.1f}km/h (계절 평균)",
    "precipitation_hours":              "강수 시간 {value:.1f}h (계절 평균)",
    "relative_humidity_2m_mean":        "평균 습도 {value:.1f}% (계절 평균)",
    "cloud_cover_mean":                 "평균 구름량 {value:.1f}% (계절 평균)",
    "hotel_City_Hotel":                 "City Hotel",
    "hotel_Resort_Hotel":               "Resort Hotel",
    "meal_BB":                          "식사 플랜: BB (조식 포함)",
    "meal_FB":                          "식사 플랜: FB (풀 보드)",
    "meal_HB":                          "식사 플랜: HB (하프 보드)",
    "meal_SC":                          "식사 플랜: SC (자취/없음)",
    "meal_Undefined":                   "식사 플랜: 미정",
    "market_segment_Aviation":          "마켓 세그먼트: 항공",
    "market_segment_Complementary":     "마켓 세그먼트: 무료 제공",
    "market_segment_Corporate":         "마켓 세그먼트: 기업",
    "market_segment_Direct":            "마켓 세그먼트: 직접",
    "market_segment_Groups":            "마켓 세그먼트: 단체",
    "market_segment_Offline_TA/TO":     "마켓 세그먼트: 오프라인 여행사",
    "market_segment_Online_TA":         "마켓 세그먼트: 온라인 여행사 (OTA)",
    "market_segment_Undefined":         "마켓 세그먼트: 미정",
    "distribution_channel_Corporate":   "유통 채널: 기업",
    "distribution_channel_Direct":      "유통 채널: 직접",
    "distribution_channel_GDS":         "유통 채널: GDS",
    "distribution_channel_TA/TO":       "유통 채널: 여행사",
    "distribution_channel_Undefined":   "유통 채널: 미정",
    "reserved_room_type_A":             "예약 객실 타입: A",
    "reserved_room_type_B":             "예약 객실 타입: B",
    "reserved_room_type_C":             "예약 객실 타입: C",
    "reserved_room_type_D":             "예약 객실 타입: D",
    "reserved_room_type_E":             "예약 객실 타입: E",
    "reserved_room_type_F":             "예약 객실 타입: F",
    "reserved_room_type_G":             "예약 객실 타입: G",
    "reserved_room_type_H":             "예약 객실 타입: H",
    "reserved_room_type_L":             "예약 객실 타입: L",
    "reserved_room_type_P":             "예약 객실 타입: P",
    "customer_type_Contract":           "고객 유형: 계약",
    "customer_type_Group":              "고객 유형: 단체",
    "customer_type_Transient":          "고객 유형: 일반",
    "customer_type_Transient-Party":    "고객 유형: 일반-파티",
    "country_grouped_BEL":              "국적: 벨기에 (BEL)",
    "country_grouped_BRA":              "국적: 브라질 (BRA)",
    "country_grouped_DEU":              "국적: 독일 (DEU)",
    "country_grouped_ESP":              "국적: 스페인 (ESP)",
    "country_grouped_FRA":              "국적: 프랑스 (FRA)",
    "country_grouped_GBR":              "국적: 영국 (GBR)",
    "country_grouped_IRL":              "국적: 아일랜드 (IRL)",
    "country_grouped_ITA":              "국적: 이탈리아 (ITA)",
    "country_grouped_NLD":              "국적: 네덜란드 (NLD)",
    "country_grouped_Other":            "국적: 기타",
    "country_grouped_PRT":              "국적: 포르투갈 (PRT)",
}


def _get_label(feature: str, value: float) -> str:
    """피처명 + 값 → 화면 표시용 자연어 레이블."""
    template = _LABEL_TEMPLATES.get(feature, feature)
    try:
        return template.format(value=value)
    except (KeyError, ValueError):
        return template


def _build_features(booking: BookingRequest) -> pd.DataFrame:
    """
    BookingRequest → 70개 피처 DataFrame (FEATURE_ORDER 순서 일치).
    모델에 넘기기 전 단일 행 DataFrame.
    """
    arrival: date = booking.arrival_date
    departure: date = booking.departure_date
    today: date = date.today()

    # ── 날짜 파생 피처 ──────────────────────────────────────────────
    lead_time = (arrival - today).days
    arrival_year = arrival.year
    arrival_month = arrival.month
    arrival_week = arrival.isocalendar()[1]  # .week (Python 3.8 호환)
    arrival_day = arrival.day

    # ── 숙박 유형 분리 ──────────────────────────────────────────────
    total_nights = (departure - arrival).days
    weekend_nights = 0
    for d in range(total_nights):
        day_of_week = (arrival + __import__("datetime").timedelta(days=d)).weekday()
        if day_of_week >= 5:  # 토=5, 일=6
            weekend_nights += 1
    week_nights = total_nights - weekend_nights

    # ── 날씨 피처 (계절 평균값) ────────────────────────────────────
    weather_key = (booking.hotel, arrival_month)
    weather = _SEASONAL_WEATHER.get(weather_key, {col: 0.0 for col in _WEATHER_COLS})

    # ── country_grouped OHE ────────────────────────────────────────
    country_code = booking.country.upper()
    country_group = country_code if country_code in _TOP10_COUNTRIES else "Other"

    # ── 딕셔너리 초기화 (모든 OHE 컬럼 0으로) ─────────────────────
    row: dict[str, float] = {col: 0.0 for col in FEATURE_ORDER}

    # ── 수치형 피처 채우기 ────────────────────────────────────────
    row["lead_time"]                    = float(lead_time)
    row["arrival_date_year"]            = float(arrival_year)
    row["arrival_date_month"]           = float(arrival_month)
    row["arrival_date_week_number"]     = float(arrival_week)
    row["arrival_date_day_of_month"]    = float(arrival_day)
    row["stays_in_weekend_nights"]      = float(weekend_nights)
    row["stays_in_week_nights"]         = float(week_nights)
    row["adults"]                       = float(booking.adults)
    row["children"]                     = float(booking.children)
    row["babies"]                       = float(booking.babies)
    row["is_repeated_guest"]            = float(booking.is_repeated_guest)
    row["previous_cancellations"]       = float(booking.previous_cancellations)
    row["booking_changes"]              = float(booking.booking_changes)
    row["agent"]                        = 0.0   # 직접 예약 기본값
    row["company"]                      = 0.0   # 직접 예약 기본값
    row["adr"]                          = float(booking.adr)
    row["required_car_parking_spaces"]  = float(booking.required_car_parking_spaces)
    row["total_of_special_requests"]    = float(booking.total_of_special_requests)

    # ── 날씨 피처 ─────────────────────────────────────────────────
    for col in _WEATHER_COLS:
        row[col] = float(weather.get(col, 0.0))

    # ── hotel OHE ─────────────────────────────────────────────────
    hotel_col = f"hotel_{booking.hotel.replace(' ', '_')}"
    if hotel_col in row:
        row[hotel_col] = 1.0

    # ── meal OHE ──────────────────────────────────────────────────
    meal_col = f"meal_{booking.meal}"
    if meal_col in row:
        row[meal_col] = 1.0

    # ── market_segment OHE ────────────────────────────────────────
    # schemas.py 값: "Online TA" → 피처명: "market_segment_Online_TA"
    ms_normalized = booking.market_segment.replace(" ", "_").replace("/", "/")
    ms_col = f"market_segment_{ms_normalized}"
    if ms_col in row:
        row[ms_col] = 1.0

    # ── distribution_channel OHE ──────────────────────────────────
    dc_col = f"distribution_channel_{booking.distribution_channel}"
    if dc_col in row:
        row[dc_col] = 1.0

    # ── reserved_room_type OHE ────────────────────────────────────
    rt_col = f"reserved_room_type_{booking.reserved_room_type}"
    if rt_col in row:
        row[rt_col] = 1.0

    # ── customer_type OHE ─────────────────────────────────────────
    ct_col = f"customer_type_{booking.customer_type}"
    if ct_col in row:
        row[ct_col] = 1.0

    # ── country_grouped OHE ───────────────────────────────────────
    cg_col = f"country_grouped_{country_group}"
    if cg_col in row:
        row[cg_col] = 1.0

    # ── DataFrame 생성 (열 순서 강제) ────────────────────────────
    df = pd.DataFrame([row], columns=FEATURE_ORDER)
    return df


def predict(booking: BookingRequest) -> tuple[float, list[RiskFactor]]:
    """
    BookingRequest → (risk_score, top 3 RiskFactor).

    Returns:
        risk_score   : float, 0~1 (predict_proba[:, 1][0])
        risk_factors : list[RiskFactor], 3개, |shap_value| 내림차순
    """
    df = _build_features(booking)

    # ── 예측 ──────────────────────────────────────────────────────
    risk_score: float = float(_model.predict_proba(df)[:, 1][0])

    # ── SHAP ──────────────────────────────────────────────────────
    shap_values = _explainer.shap_values(df)

    # SHAP 버전별 출력 형태:
    #   구버전 (list): [neg_class (1,70), pos_class (1,70)]  → sv[1][0]
    #   신버전 (ndarray): (1, 70) — 양성 클래스 단일 배열    → sv[0]
    if isinstance(shap_values, list) and len(shap_values) == 2:
        sv_pos = shap_values[1][0]   # pos class, first sample → shape (70,)
    elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 2:
        sv_pos = shap_values[0]      # first sample → shape (70,)
    elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 1:
        sv_pos = shap_values         # already (70,)
    else:
        # fallback: 첫 번째 원소를 flatten
        sv_pos = np.array(shap_values).ravel()[:len(FEATURE_ORDER)]

    feature_values = df.iloc[0].values  # (70,)

    # ── Top 3 추출 ────────────────────────────────────────────────
    abs_sv = np.abs(sv_pos)
    top_indices = np.argsort(abs_sv)[::-1][:3]

    risk_factors: list[RiskFactor] = []
    for idx in top_indices:
        feat_name = FEATURE_ORDER[idx]
        feat_val = float(feature_values[idx])
        sv = float(sv_pos[idx])
        risk_factors.append(RiskFactor(
            feature=feat_name,
            label=_get_label(feat_name, feat_val),
            shap_value=round(sv, 6),
        ))

    return round(risk_score, 6), risk_factors
