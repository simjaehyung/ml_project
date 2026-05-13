"""
app/tab1_priority.py
탭1 — 예약 위험 관리 대시보드

이고은 구현 담당.
[TODO] 표시된 곳만 채우면 됨. 데이터 파이프라인은 utils.py가 처리.

화면 구조:
  ┌─────────────────────────────────────────────┐
  │  [KPI 카드 3개]                              │
  ├──────────────────────────┬──────────────────┤
  │  필터 바                  │                  │
  │  예약 우선순위 테이블      │  SHAP waterfall  │
  │  (클릭 → 우측 패널 업데이트)│  (행 선택 시)   │
  └──────────────────────────┴──────────────────┘
"""

import pandas as pd
import streamlit as st

from utils import (
    compute_discount,
    get_risk_label,
    plot_shap_waterfall,
    RISK_COLORS,
)


# ── KPI 카드 ──────────────────────────────────────────────────────────────────
def render_kpi_cards(df: pd.DataFrame, threshold: float):
    high_risk   = df[df["cancel_prob"] >= threshold]
    total_loss  = high_risk["expected_loss"].sum()
    food_waste  = high_risk[high_risk["meal"].isin(["HB", "FB"])].shape[0]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="⚠️ 고위험 예약",
            value=f"{len(high_risk):,}건",
            delta=f"전체 {len(df):,}건 중 {len(high_risk)/len(df)*100:.1f}%",
            delta_color="inverse",
        )

    with col2:
        st.metric(
            label="💸 예상 취소 손실",
            value=f"€{total_loss:,.0f}",
            delta="ADR × 취소확률 × 체류일 합산",
            delta_color="off",
        )

    with col3:
        st.metric(
            label="🍽️ 음식 낭비 위험",
            value=f"{food_waste}건",
            delta="고위험 × HB/FB 식사 플랜",
            delta_color="inverse",
        )


# ── 필터 바 ───────────────────────────────────────────────────────────────────
def render_filters(df: pd.DataFrame) -> tuple[float, str]:
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        threshold = st.slider(
            "취소 위험 임계값",
            min_value=0.30, max_value=0.90, value=0.60, step=0.05,
            help="이 값 이상의 예약만 고위험으로 분류",
        )
    with col2:
        hotel_filter = st.selectbox(
            "호텔", ["전체", "City Hotel", "Resort Hotel"]
        )
    with col3:
        # [TODO 이고은] 도착일 범위 필터 추가 가능 (st.date_input)
        sort_by = st.selectbox("정렬 기준", ["취소확률 높은 순", "ADR 높은 순", "체류일 긴 순"])

    return threshold, hotel_filter, sort_by


# ── 테이블 색 적용 ─────────────────────────────────────────────────────────────
def _color_risk(val, threshold):
    label, color = get_risk_label(val, threshold)
    return f"background-color: {color}22; color: {color}; font-weight: bold"


def _build_display_df(df: pd.DataFrame, threshold: float, hotel_filter: str, sort_by: str) -> pd.DataFrame:
    filtered = df.copy()

    if hotel_filter != "전체":
        filtered = filtered[filtered["hotel"] == hotel_filter]

    sort_map = {
        "취소확률 높은 순": ("cancel_prob", False),
        "ADR 높은 순":      ("adr",         False),
        "체류일 긴 순":     ("total_nights", False),
    }
    sort_col, asc = sort_map.get(sort_by, ("cancel_prob", False))
    filtered = filtered.sort_values(sort_col, ascending=asc).reset_index(drop=True)

    # 표시 컬럼 선택
    display = filtered[[
        "country", "hotel", "market_segment", "lead_time",
        "adr", "total_nights", "meal", "cancel_prob",
    ]].rename(columns={
        "country":        "국적",
        "hotel":          "호텔",
        "market_segment": "채널",
        "lead_time":      "선예약(일)",
        "adr":            "ADR(€)",
        "total_nights":   "체류(박)",
        "meal":           "식사",
        "cancel_prob":    "취소확률",
    })

    display["ADR(€)"]   = display["ADR(€)"].round(0).astype(int)
    display["취소확률"]   = display["취소확률"].round(3)

    # 원본 인덱스 보존 (SHAP 연동용)
    return display, filtered.index.tolist()


# ── 예약 우선순위 테이블 ───────────────────────────────────────────────────────
def render_priority_table(
    df: pd.DataFrame,
    threshold: float,
    hotel_filter: str,
    sort_by: str,
) -> int | None:
    """
    반환: 선택된 행의 원본 df 인덱스 (선택 없으면 None)
    """
    display_df, original_indices = _build_display_df(df, threshold, hotel_filter, sort_by)

    # [TODO 이고은] 컬러코딩: 취소확률 컬럼에 배경색 적용
    # styled = display_df.style.applymap(
    #     lambda v: _color_risk(v, threshold), subset=["취소확률"]
    # )

    st.caption(f"총 {len(display_df):,}건 표시 중 (임계값 {threshold} 이상 강조)")

    event = st.dataframe(
        display_df,
        use_container_width=True,
        height=420,
        on_select="rerun",
        selection_mode="single-row",
    )

    selected_rows = event.selection.rows
    if selected_rows:
        local_idx    = selected_rows[0]
        original_idx = original_indices[local_idx]
        return original_idx

    return None


# ── SHAP 패널 ─────────────────────────────────────────────────────────────────
def render_shap_panel(
    selected_idx: int | None,
    df: pd.DataFrame,
    shap_values,
    X_shap: pd.DataFrame,
):
    if selected_idx is None:
        st.info("← 왼쪽 테이블에서 예약을 선택하면 위험 요인 분석이 표시됩니다.")
        return

    row = df.iloc[selected_idx]
    cancel_prob = float(row["cancel_prob"])
    label, color = get_risk_label(cancel_prob)

    st.markdown(f"### 예약 상세")
    st.markdown(
        f"**취소 확률: "
        f"<span style='color:{color}; font-size:1.4em'>{cancel_prob:.1%}</span>** "
        f"({label})",
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    cols[0].metric("국적",     str(row.get("country", "-")))
    cols[1].metric("ADR",      f"€{row.get('adr', 0):.0f}")
    cols[2].metric("선예약",   f"{row.get('lead_time', 0):.0f}일")

    # SHAP waterfall — X_shap 기준 인덱스 매핑
    shap_positions = X_shap.index.tolist()
    if selected_idx in shap_positions:
        shap_pos = shap_positions.index(selected_idx)
        st.markdown("#### 주요 위험 요인 (SHAP)")
        fig = plot_shap_waterfall(shap_values, shap_pos, max_display=8)
        st.pyplot(fig, use_container_width=True)
    else:
        # [TODO 이고은] SHAP 계산 범위 밖 예약 선택 시 안내
        st.caption("※ 이 예약은 SHAP 분석 샘플 외 예약입니다.")


# ── 탭1 메인 렌더러 ───────────────────────────────────────────────────────────
def render_tab1(df: pd.DataFrame, shap_values, X_shap: pd.DataFrame):
    st.markdown("## 📋 예약 위험 우선순위 관리")
    st.markdown("취소 확률 기반으로 고위험 예약을 우선순위화하고 위험 요인을 분석합니다.")
    st.divider()

    # 필터
    threshold, hotel_filter, sort_by = render_filters(df)
    st.divider()

    # KPI
    render_kpi_cards(df, threshold)
    st.divider()

    # 테이블 + SHAP 패널
    left_col, right_col = st.columns([3, 2])

    with left_col:
        selected_idx = render_priority_table(df, threshold, hotel_filter, sort_by)

    with right_col:
        render_shap_panel(selected_idx, df, shap_values, X_shap)
