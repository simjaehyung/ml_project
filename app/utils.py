"""
app/utils.py
공통 유틸리티 — 모델 로드, 예측, SHAP, 디스카운트 계산

앱 시작 시 한 번만 로드되고 캐시됨.
탭1·탭2 모두 이 모듈에서 데이터를 가져다 씀.
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import shap
import streamlit as st
import matplotlib.pyplot as plt

ROOT    = Path(__file__).resolve().parent.parent
DATA    = ROOT / "data"
RESULTS = ROOT / "results"

CAT_COLS = [
    "hotel", "meal", "market_segment", "distribution_channel",
    "reserved_room_type", "customer_type", "country_grouped",
]

TOP10_COUNTRIES = ["PRT", "GBR", "FRA", "ESP", "DEU",
                   "ITA", "IRL", "BRA", "NLD", "USA"]

COUNTRY_DISPLAY = {
    "PRT": "Portugal", "GBR": "UK", "FRA": "France", "ESP": "Spain",
    "DEU": "Germany", "ITA": "Italy", "IRL": "Ireland", "BRA": "Brazil",
    "NLD": "Netherlands", "USA": "USA", "Other": "Other",
}

RISK_COLORS = {
    "HIGH":   "#e74c3c",
    "MEDIUM": "#f39c12",
    "LOW":    "#27ae60",
}


# ── 리스크 등급 ────────────────────────────────────────────────────────────────
def get_risk_label(cancel_prob: float, threshold: float = 0.6) -> tuple[str, str]:
    if cancel_prob >= 0.70:
        return "HIGH",   RISK_COLORS["HIGH"]
    elif cancel_prob >= threshold:
        return "MEDIUM", RISK_COLORS["MEDIUM"]
    else:
        return "LOW",    RISK_COLORS["LOW"]


# ── Flexi 할인율 공식 (CLAUDE.md 확정) ───────────────────────────────────────
def compute_discount(cancel_prob: float) -> float:
    raw = 5.0 + (cancel_prob - 0.5) * 26.0
    return round(max(5.0, min(18.0, raw)), 1)


# ── 모델 + 테스트셋 + SHAP 로드 ───────────────────────────────────────────────
@st.cache_resource(show_spinner="모델과 데이터를 불러오는 중...")
def load_model_and_data():
    # 모델
    with open(RESULTS / "model_final.pkl", "rb") as f:
        model = pickle.load(f)

    # 원본 (표시용)
    raw = pd.read_csv(DATA / "test.csv")

    # 전처리 + OHE
    processed = pd.read_csv(DATA / "test_processed.csv")
    train_p   = pd.read_csv(DATA / "train_processed.csv")

    train_e = pd.get_dummies(train_p,   columns=CAT_COLS)
    test_e  = pd.get_dummies(processed, columns=CAT_COLS)
    test_e  = test_e.reindex(columns=train_e.columns, fill_value=0)

    X_te = test_e.drop("is_canceled", axis=1)
    y_te = test_e["is_canceled"]

    # 취소 확률
    cancel_probs = model.predict_proba(X_te)[:, 1]

    # 표시용 DataFrame 구성
    n  = min(len(raw), len(cancel_probs))
    df = raw.iloc[:n].copy().reset_index(drop=True)
    df["cancel_prob"]       = cancel_probs[:n]
    df["is_canceled_actual"] = y_te.values[:n]

    # 표시용 컬럼 정리
    df["risk_label"] = df["cancel_prob"].apply(
        lambda p: get_risk_label(p)[0]
    )
    df["total_nights"] = df["stays_in_weekend_nights"] + df["stays_in_week_nights"]
    df["expected_loss"] = df["adr"] * df["cancel_prob"] * df["total_nights"]

    # SHAP (상위 5,000건만 — 대시보드 속도)
    sample_idx   = df.nlargest(5000, "cancel_prob").index
    X_shap       = X_te.iloc[sample_idx]
    explainer    = shap.TreeExplainer(model)
    shap_values  = explainer(X_shap)

    return model, df, X_te, shap_values, X_shap, train_e.columns.tolist(), explainer


# ── 계절별 날씨 평균값 로드 ────────────────────────────────────────────────────
@st.cache_data
def load_seasonal_weather() -> pd.DataFrame:
    path = DATA / "seasonal_weather.csv"
    if not path.exists():
        # 파일 없으면 빈 DataFrame (김나리 스크립트 실행 전)
        return pd.DataFrame()
    return pd.read_csv(path)


def get_seasonal_weather(hotel: str, month: int, sw_df: pd.DataFrame) -> dict:
    if sw_df.empty:
        return {}
    row = sw_df[(sw_df["hotel"] == hotel) & (sw_df["arrival_date_month"] == month)]
    if row.empty:
        return {}
    return row.iloc[0].to_dict()


# ── 단일 예약 예측 (탭2용) ────────────────────────────────────────────────────
def predict_new_booking(
    input_dict: dict,
    model,
    train_columns: list,
    explainer,
    sw_df: pd.DataFrame,
) -> tuple[float, pd.DataFrame]:
    """
    UI 입력 dict → (cancel_prob, shap_top3_df)
    shap_top3_df: feature / shap_value / direction 컬럼
    """
    # 날씨 자동 채우기 (계절 평균)
    weather = get_seasonal_weather(
        input_dict.get("hotel", "City Hotel"),
        int(input_dict.get("arrival_date_month", 7)),
        sw_df,
    )
    for col in ["precipitation_sum", "temperature_2m_max", "temperature_2m_min",
                "wind_speed_10m_max", "precipitation_hours",
                "relative_humidity_2m_mean", "cloud_cover_mean"]:
        if col not in input_dict and col in weather:
            input_dict[col] = weather[col]

    # country_grouped
    country = input_dict.pop("country", "Other")
    input_dict["country_grouped"] = country if country in TOP10_COUNTRIES else "Other"

    # 단일 행 DataFrame
    row_df = pd.DataFrame([input_dict])

    # OHE (train 컬럼 기준으로 정렬)
    for col in CAT_COLS:
        if col not in row_df.columns:
            row_df[col] = "Unknown"

    row_e = pd.get_dummies(row_df, columns=CAT_COLS)
    row_e = row_e.reindex(columns=train_columns, fill_value=0)

    # is_canceled 컬럼 제거
    if "is_canceled" in row_e.columns:
        row_e = row_e.drop(columns=["is_canceled"])

    cancel_prob = float(model.predict_proba(row_e)[:, 1][0])

    # SHAP top-3
    sv           = explainer(row_e)
    shap_vals    = sv.values[0]
    feature_names = row_e.columns.tolist()

    top_idx = np.argsort(np.abs(shap_vals))[::-1][:5]
    shap_top = pd.DataFrame({
        "feature":    [feature_names[i] for i in top_idx],
        "shap_value": [shap_vals[i]      for i in top_idx],
    })
    shap_top["direction"] = shap_top["shap_value"].apply(
        lambda v: "위험 증가 ↑" if v > 0 else "위험 감소 ↓"
    )
    return cancel_prob, shap_top


# ── SHAP waterfall 플롯 (탭1용) ───────────────────────────────────────────────
def plot_shap_waterfall(shap_values, idx: int, max_display: int = 10) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 5))
    shap.plots.waterfall(shap_values[idx], max_display=max_display, show=False)
    fig = plt.gcf()
    plt.tight_layout()
    return fig
