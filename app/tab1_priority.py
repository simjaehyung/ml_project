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
        # 운영 문제 #2: 채널 실효 수익 분석 (나리 · Week 5)
        # effective_adr = ADR × (1 - cancel_rate)
        # 가설: Online TA가 ADR 높아도 취소율이 높아 실효 수익 낮음.
        # Week 5 나리님 분석 들어오면 진짜 비교 수치로 대체.
        if "market_segment" in df.columns:
            online_ta_cnt = (df["market_segment"] == "Online TA").sum()
        else:
            online_ta_cnt = 0
        st.metric(
            label="💰 채널 실효 경보",
            value="Week 5 분석 대기",
            delta=f"Online TA {online_ta_cnt:,}건 모니터링 중",
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
        sort_by = st.selectbox(
            "정렬 기준",
            ["취소확률 높은 순", "품질점수 높은 순", "1박 요금 높은 순", "체류일 긴 순"],
        )

    return threshold, hotel_filter, sort_by


# ── 테이블 색 적용 ─────────────────────────────────────────────────────────────
def _color_risk(val, threshold):
    label, color = get_risk_label(val, threshold)
    return f"background-color: {color}22; color: {color}; font-weight: bold"


# 식사 코드 한국어 매핑 — 호텔 업계 약어를 매니저·청중 모두 알 수 있게.
MEAL_KR = {
    "BB":        "조식만",
    "HB":        "조·석식",
    "FB":        "세 끼",
    "SC":        "식사 없음",
    "Undefined": "정보 없음",
}

# 예약 경로(market_segment) 한국어 매핑 — Online TA 같은 영어 약어 풀이.
SEGMENT_KR = {
    "Online TA":     "온라인 여행사",
    "Offline TA/TO": "오프라인 여행사",
    "Groups":        "단체",
    "Direct":        "직접 예약",
    "Corporate":     "법인",
    "Complementary": "무료/프로모션",
    "Aviation":      "항공 제휴",
    "Undefined":     "정보 없음",
}


def _build_display_df(df: pd.DataFrame, threshold: float, hotel_filter: str, sort_by: str) -> pd.DataFrame:
    filtered = df.copy()

    if hotel_filter != "전체":
        filtered = filtered[filtered["hotel"] == hotel_filter]

    # 운영 문제 #3: 예약 품질 점수 BQS (PM · Week 5)
    # 공식: BQS = w1·ADR + w2·stays + w3·special_requests - w4·cancel_proba
    # 가중치(w1~w4)는 PM이 Week 5에 확정. 일단 임시값으로 컬럼 자리만 잡음.
    sr_col = "total_of_special_requests"
    sr = filtered[sr_col] if sr_col in filtered.columns else 0
    filtered["bqs"] = (
        filtered["adr"]          * 0.01    # w1 (임시)
        + filtered["total_nights"] * 0.5   # w2 (임시)
        + sr                       * 1.0   # w3 (임시)
        - filtered["cancel_prob"]  * 5.0   # w4 (임시)
    ).round(1)

    sort_map = {
        "취소확률 높은 순":   ("cancel_prob",  False),
        "품질점수 높은 순":   ("bqs",          False),   # 운영 문제 #3 (PM Week 5)
        "1박 요금 높은 순":   ("adr",          False),
        "체류일 긴 순":       ("total_nights", False),
    }
    sort_col, asc = sort_map.get(sort_by, ("cancel_prob", False))
    # reset_index 하면 원본 df 인덱스가 사라져 render_shap_panel의 df.iloc[selected_idx]가 엉뚱한 행을 잡음.
    # 원본 인덱스 보존 — SHAP 패널 행 매핑이 정확히 맞도록.
    filtered = filtered.sort_values(sort_col, ascending=asc)

    # 식사·예약 경로 코드 → 한국어 풀이 (영어 약어 그대로면 청중 헷갈림)
    filtered["meal"]           = filtered["meal"].map(MEAL_KR).fillna(filtered["meal"])
    filtered["market_segment"] = filtered["market_segment"].map(SEGMENT_KR).fillna(filtered["market_segment"])

    # 표시 컬럼 선택 — bqs (품질점수)는 운영 문제 #3 자리
    display = filtered[[
        "country", "hotel", "market_segment", "lead_time",
        "adr", "total_nights", "meal", "bqs", "cancel_prob",
    ]].rename(columns={
        "country":        "국적",
        "hotel":          "호텔",
        "market_segment": "예약 경로",
        "lead_time":      "선예약 기간",   # "리드타임"보다 매니저 친화적
        "adr":            "1박 요금(€)",   # ADR 풀어서 — 청중도 즉시 이해
        "total_nights":   "체류(박)",
        "meal":           "식사",
        "bqs":            "품질점수",      # 운영 문제 #3 (PM Week 5 가중치 확정)
        "cancel_prob":    "취소확률",
    })

    display["1박 요금(€)"] = display["1박 요금(€)"].round(0).astype(int)
    display["취소확률"]     = display["취소확률"].round(3)

    # 표시 행 제한 — Pandas Styler 한도(26만 셀) 회피 + 매니저는 상위 위험만 봄.
    # 전체 4만 건 × 8컬럼 = 32만 셀로 한도 초과 → 상위 500건으로 자름.
    DISPLAY_LIMIT = 500
    # filtered의 원본 df 인덱스가 보존된 상태에서 head — display와 original_indices가 같은 행을 가리킴.
    original_indices = filtered.index.tolist()[:DISPLAY_LIMIT]
    display = display.head(DISPLAY_LIMIT).reset_index(drop=True)

    return display, original_indices


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

    # 컬러코딩 — 취소확률 셀에 위험 등급별 배경색·글자색 적용.
    # HIGH(빨강) ≥ 0.70 / MEDIUM(주황) ≥ threshold / LOW(초록) 그 외.
    # utils.get_risk_label 기준을 따라 컬러팔레트 일관성 유지.
    styled = display_df.style.map(
        lambda v: _color_risk(v, threshold), subset=["취소확률"]
    ).format({
        "취소확률":      "{:.0%}",     # 0.812 → 81% (매니저 친화적, 소수점 빼기)
        "1박 요금(€)":   "€{:,}",      # 1500 → €1,500
        "품질점수":      "{:.1f}",     # 26.900000 → 26.9 (소수점 한 자리)
    })

    st.caption(
        f"전체 {len(df):,}건 중 위험도 순 **상위 {len(display_df):,}건** 표시 · "
        f"임계값 {threshold:.2f} 이상 = 고위험 강조"
    )
    st.caption(
        "ℹ️ **품질점수(BQS)** 는 임시 가중치 placeholder — Week 5 PM 가중치 확정 시 정확값으로 갱신됩니다."
    )

    event = st.dataframe(
        styled,
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
    cols[0].metric("국적",           str(row.get("country", "-")))
    cols[1].metric("1박 요금",       f"€{row.get('adr', 0):.0f}")
    cols[2].metric("선예약 기간",    f"{row.get('lead_time', 0):.0f}일")

    # SHAP waterfall — X_shap 기준 인덱스 매핑
    shap_positions = X_shap.index.tolist()
    if selected_idx in shap_positions:
        shap_pos = shap_positions.index(selected_idx)
        st.markdown("#### 주요 위험 요인 (SHAP)")
        fig = plot_shap_waterfall(shap_values, shap_pos, max_display=8)
        st.pyplot(fig, use_container_width=True)
    else:
        # SHAP 범위 밖 예약 안내 — 매니저가 "왜 그래프가 없지?" 헷갈리지 않게.
        # info 톤 채택: 시스템 의도 동작(속도 우선)이라 경고가 아닌 정보 전달이 의미상 정확.
        st.info(
            "이 예약은 SHAP 분석 샘플 밖입니다. 위 메트릭(국적·ADR·선예약)을 참고해 주세요.",
            icon="ℹ️",
        )

    # ── Week 5·6 운영 분석 자리 (placeholder) ────────────────────────────
    # 발표 슬라이드 "취소 예측이 풀 수 있는 운영 문제 3개" 와 연동:
    #   • 채널 실효 수익 (effective_adr = ADR × (1-cancel_rate))  — 나리 Week 5
    #   • 식사 플랜 영향 (food_risk = cancel_prob>0.65 & meal in HB/FB) — 이고은 Week 6
    # 진짜 값·차트는 Week 5·6 데이터 들어오면 채움. 지금은 자리만.
    st.divider()
    with st.expander("📊 이 예약의 채널·식사 운영 영향 (Week 5·6 진행 예정)", expanded=False):
        st.markdown(
            "- **채널 실효 수익** — 이 예약의 `예약 경로`별 effective_adr 비교 차트\n"
            "- **음식 낭비 영향** — 식사 플랜과 취소 확률 조합의 발주 조정 권고"
        )
        st.caption("🚧 Week 5·6 분석 결과로 대체 예정 (나리·이고은 협업)")


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
