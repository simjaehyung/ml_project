"""
app/app.py
Hotel No-Show DSS — 메인 Streamlit 앱

실행:
  streamlit run app/app.py

탭 구조:
  탭1 — 예약 위험 관리 (이고은)
  탭2 — 신규 예약 Flexi 라우팅 (이고은)
"""

import sys
from pathlib import Path

# app/ 디렉토리를 경로에 추가 (utils, tab 모듈 import용)
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

from utils import load_model_and_data, load_seasonal_weather
from tab1_priority import render_tab1
from tab2_flexi import render_tab2

# ── 페이지 설정 ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hotel No-Show DSS",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 헤더 ─────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <h1 style="margin-bottom: 0">🏨 Hotel No-Show Decision Support System</h1>
    <p style="color: #888; font-size: 0.95em; margin-top: 4px">
        LightGBM 취소 예측 (PR-AUC 0.8189) · SHAP 설명 · Flexi 라우팅 권장
    </p>
    """,
    unsafe_allow_html=True,
)
st.divider()

# ── 데이터 로드 (캐시됨 — 최초 1회만) ────────────────────────────────────────
model, df, X_te, shap_values, X_shap, train_columns, explainer = load_model_and_data()
sw_df = load_seasonal_weather()

# ── 탭 ────────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs([
    "📋 예약 위험 관리",
    "⚡ Flexi 라우팅 권장",
])

with tab1:
    render_tab1(df, shap_values, X_shap)

with tab2:
    render_tab2(model, train_columns, explainer, sw_df)
