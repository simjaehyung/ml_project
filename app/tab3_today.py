"""
app/tab3_today.py
탭3 — 오늘 신규 예약 위험 관리

이고은 구현 담당.
탭1이 *전체 test 우선순위*라면, 탭3는 *오늘 들어온 신규 예약 배치 단위* 관리.

화면 구조:
  ┌────────────────────────────────────────────────────────┐
  │ 데이터셋 선택 + 임계값 + 새로고침                          │
  │ KPI 카드 3개 (신규 N건 / 고위험 N건 / 권장 Flexi 슬롯)    │
  │ 위험도 정렬 테이블 (탭1과 동일 컬러코딩)                    │
  │ 빈방 손실률 기반 슬롯·가격 결정 (Phase 2 placeholder)      │
  └────────────────────────────────────────────────────────┘

현재는 mock — Phase 2에 `src/ingest_bookings.py` 백엔드 연동 예정.
"""

import pandas as pd
import streamlit as st

from tab1_priority import MEAL_KR, SEGMENT_KR, _color_risk
from utils import compute_discount


# 데이터셋 선택 옵션 (mock — Phase 2에선 진짜 파일 단위)
DATASET_OPTIONS = {
    "오늘 신규 (mock 100건)":   "today",
    "최근 7일 (체크인 임박)":   "recent",
    "이번 주 도착 예정":         "this_week",
    "전체 test set":            "all",
}


def _filter_dataset(df: pd.DataFrame, option: str) -> pd.DataFrame:
    """데이터셋 선택에 따라 필터."""
    if option == "today":
        # mock — 무작위 100건 (Phase 2에선 ingest_bookings.py가 오늘 자 CSV 처리)
        return df.sample(min(100, len(df)), random_state=42).copy()
    elif option == "recent":
        # 체크인 임박 = lead_time ≤ 7 (Phase 2엔 도착일 기준 필터)
        return df[df["lead_time"] <= 7].copy()
    elif option == "this_week":
        # 도착이 7일 이내 (lead_time ≤ 7 동일하지만 의미 다르게)
        return df[df["lead_time"] <= 14].copy()
    return df.copy()


def _build_display_df_t3(df: pd.DataFrame) -> tuple[pd.DataFrame, list]:
    """탭1의 표 빌더와 비슷. 차이: 정렬은 항상 취소확률 순."""
    filtered = df.copy().sort_values("cancel_prob", ascending=False)

    # 식사·예약 경로·국적 한국어/결측 처리 (탭1과 동일)
    filtered["meal"]           = filtered["meal"].map(MEAL_KR).fillna(filtered["meal"])
    filtered["market_segment"] = filtered["market_segment"].map(SEGMENT_KR).fillna(filtered["market_segment"])
    filtered["country"]        = filtered["country"].fillna("정보 없음")

    # BQS 임시 가중치 (탭1과 동일 공식 — Week 5 PM 확정 시 갱신)
    sr_col = "total_of_special_requests"
    sr = filtered[sr_col] if sr_col in filtered.columns else 0
    filtered["bqs"] = (
        filtered["adr"]          * 0.01
        + filtered["total_nights"] * 0.5
        + sr                       * 1.0
        - filtered["cancel_prob"]  * 5.0
    ).round(1)

    display = filtered[[
        "country", "hotel", "market_segment", "lead_time",
        "adr", "total_nights", "meal", "bqs", "cancel_prob",
    ]].rename(columns={
        "country":        "국적",
        "hotel":          "호텔",
        "market_segment": "예약 경로",
        "lead_time":      "선예약 기간",
        "adr":            "1박 요금(€)",
        "total_nights":   "체류(박)",
        "meal":           "식사",
        "bqs":            "품질점수",
        "cancel_prob":    "취소확률",
    })

    display["1박 요금(€)"] = display["1박 요금(€)"].round(0).astype(int)
    display["취소확률"]     = display["취소확률"].round(3)

    # 표시 행 제한 (Pandas Styler 26만 셀 한도 회피)
    DISPLAY_LIMIT = 500
    original_indices = filtered.index.tolist()[:DISPLAY_LIMIT]
    display = display.head(DISPLAY_LIMIT).reset_index(drop=True)

    return display, original_indices


def render_tab3(df: pd.DataFrame):
    st.markdown("## 📥 오늘 신규 예약 위험 관리")
    st.markdown(
        "오늘 들어온 신규 예약 배치를 위험도 순으로 확인하고, "
        "Flexi 풀 슬롯·가격 의사결정을 지원합니다."
    )
    st.caption(
        "🚧 현재는 mock 데이터 — Phase 2에 `src/ingest_bookings.py` 백엔드 연동 예정 "
        "(매일 아침 10시 자동 갱신)"
    )
    st.divider()

    # 상단 컨트롤 — 데이터셋·임계값·새로고침
    col_a, col_b, col_c = st.columns([2, 1, 1])
    with col_a:
        dataset_label = st.selectbox(
            "데이터셋 선택",
            options=list(DATASET_OPTIONS.keys()),
            help="실제 운영에선 ingest_bookings.py 가 오늘자 CSV를 자동 처리. 현재는 mock.",
        )
    with col_b:
        threshold = st.slider(
            "고위험 임계값",
            min_value=0.30, max_value=0.90, value=0.60, step=0.05,
            key="tab3_threshold",
        )
    with col_c:
        st.markdown("&nbsp;", unsafe_allow_html=True)  # 라벨 정렬용
        if st.button("🔄 새로고침 (mock)", use_container_width=True,
                     help="실제 운영에선 ingest_bookings 재실행"):
            st.cache_data.clear()
            st.toast("데이터 갱신됨 (mock)", icon="✅")

    # 매니저 입력 — 호텔 현장 정보 (모델은 모르는 것)
    st.markdown("##### 🏨 호텔 현장 정보 — 매니저가 직접 입력")
    col_x, col_y, col_z = st.columns(3)
    with col_x:
        empty_rooms = st.number_input(
            "오늘 남은 빈방 수",
            min_value=0, max_value=500, value=10, step=1,
            help="현재 예약되지 않은 빈방. PMS에서 확인.",
        )
    with col_y:
        total_rooms = st.number_input(
            "호텔 총 객실 수",
            min_value=10, max_value=1000, value=100, step=10,
            help="City Hotel·Resort Hotel 합산 또는 단일 호텔 기준.",
        )
    with col_z:
        safety_ratio = st.slider(
            "안전 상한 배수",
            min_value=1.0, max_value=1.5, value=1.2, step=0.1,
            help="빈방 수 × 안전 상한 = 최대 Flexi 슬롯. walk_rate < 2% 목표 기준 1.2.",
        )

    # 데이터셋 필터링
    filtered_df = _filter_dataset(df, DATASET_OPTIONS[dataset_label])
    n_total = len(filtered_df)

    if n_total == 0:
        st.warning("선택한 데이터셋에 예약이 없습니다.")
        return

    # ─── KPI 카드 3개 ──────────────────────────────────────────
    high_risk      = filtered_df[filtered_df["cancel_prob"] >= threshold]
    n_high         = len(high_risk)
    expected_loss  = (high_risk["adr"] * high_risk["cancel_prob"] * high_risk["total_nights"]).sum()

    # design_06 공식 + 매니저 현장 정보 결합
    # 권장 슬롯 = min(모델 예상 취소 수, 빈방 수 × 안전 상한)
    expected_cancels   = int(round(high_risk["cancel_prob"].sum())) if n_high > 0 else 0
    safety_cap         = int(empty_rooms * safety_ratio)
    recommended_slots  = min(expected_cancels, safety_cap)
    avg_high_prob      = high_risk["cancel_prob"].mean() if n_high > 0 else 0.6
    suggested_discount = compute_discount(avg_high_prob)

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "📥 신규 예약 (선택 데이터셋)",
        f"{n_total:,}건",
        delta=f"{dataset_label}",
        delta_color="off",
    )
    c2.metric(
        "⚠️ 고위험 예약",
        f"{n_high:,}건",
        delta=f"임계값 {threshold:.2f} 이상 · 전체의 {n_high/n_total*100:.1f}%",
        delta_color="inverse",
    )
    c3.metric(
        "🎯 권장 Flexi 슬롯",
        f"{recommended_slots}개",
        delta=(
            f"모델 예상 취소 {expected_cancels}개 vs 빈방 안전 상한 {safety_cap}개"
            f" → 작은 값 채택"
        ),
        delta_color="off",
        help="design_06 공식: min(round(Σ P(취소)), 빈방 × 1.2). 매니저 현장 정보 반영.",
    )

    st.divider()

    # ─── 위험도 테이블 ─────────────────────────────────────────
    display_df, _ = _build_display_df_t3(filtered_df)

    st.markdown("### 신규 예약 위험도 리스트")
    st.caption(
        f"위험도 순 상위 **{len(display_df):,}건** 표시 · "
        f"임계값 {threshold:.2f} 이상 = 고위험 강조"
    )
    st.caption(
        "ℹ️ 품질점수(BQS) 는 임시 가중치 placeholder — Week 5 PM 가중치 확정 시 정확값으로 갱신"
    )

    styled = display_df.style.map(
        lambda v: _color_risk(v, threshold), subset=["취소확률"]
    ).format({
        "취소확률":      "{:.0%}",
        "1박 요금(€)":   "€{:,}",
        "품질점수":      "{:.1f}",
    })

    st.dataframe(
        styled,
        use_container_width=True,
        height=480,
    )

    st.divider()

    # ─── Flexi 풀 의사결정 박스 — 매니저 승인 흐름 ─────────────────
    st.markdown("### ⚡ Flexi 풀 슬롯·가격 결정")

    if recommended_slots == 0:
        st.success(
            "📭 권장 슬롯 0개 — 빈방 또는 고위험 예약이 충분하지 않습니다. "
            "Standard 운영을 유지하세요."
        )
    else:
        # 평균 ADR + 평균 할인율로 *예상 추가 수익* 계산
        avg_adr           = high_risk["adr"].mean() if n_high > 0 else 0
        avg_nights        = high_risk["total_nights"].mean() if n_high > 0 else 1
        flexi_price       = avg_adr * (1 - suggested_discount / 100)
        expected_revenue  = recommended_slots * flexi_price * avg_nights

        # walk 위험 — 예상 취소가 슬롯보다 적으면 발생
        walk_risk_count   = max(0, recommended_slots - expected_cancels)

        st.markdown(
            f"""
            <div style="
                background-color: #fff4d4;
                border-left: 5px solid #f0b400;
                border-radius: 8px;
                padding: 16px 20px;
                margin-bottom: 12px;
            ">
                <h4 style="margin: 0 0 12px 0; color: #5a4400">
                    🎯 권장: <b>{recommended_slots}개</b> 슬롯을 Flexi 풀에 등록
                </h4>
                <table style="width:100%; font-size:0.95em; color:#5a4400">
                    <tr>
                        <td>평균 할인율</td>
                        <td><b>{suggested_discount:.1f}%</b>
                        (고위험 평균 위험도 {avg_high_prob:.1%} 기준)</td>
                    </tr>
                    <tr>
                        <td>적용 ADR (평균)</td>
                        <td><b>€{flexi_price:.0f}/박</b> (원래 €{avg_adr:.0f})</td>
                    </tr>
                    <tr>
                        <td>예상 추가 수익</td>
                        <td><b>€{expected_revenue:,.0f}</b>
                        ({recommended_slots}슬롯 × {avg_nights:.1f}박)</td>
                    </tr>
                    <tr>
                        <td>예상 빈방 손실 회피</td>
                        <td><b>€{expected_loss:,.0f}</b> 중 일부 회수</td>
                    </tr>
                    <tr>
                        <td>예상 walk 위험</td>
                        <td><b>{walk_risk_count}건</b>
                        (슬롯 - 예상 취소, 0이 안전)</td>
                    </tr>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            "**최종 결정은 매니저 권한입니다** "
            "— ℹ️ AI 권장이지 자동 실행 아님 (GDPR Art.22)"
        )

        col_ok, col_no = st.columns(2)
        with col_ok:
            if st.button(
                f"✅ {recommended_slots}개 슬롯을 Flexi 풀에 등록",
                type="primary", use_container_width=True,
            ):
                st.success(
                    f"등록 완료 (mock) — {recommended_slots}개 슬롯이 Flexi 풀에 추가. "
                    f"Phase 2에 PMS 자동 반영 예정."
                )
        with col_no:
            if st.button("⏸ 보류 — Standard 유지", use_container_width=True):
                st.info("Standard 운영 유지 — Flexi 슬롯 등록 안 함.")

    # Phase 2 안내 (작게)
    with st.expander("🚧 Phase 2 진행 예정", expanded=False):
        st.markdown(
            """
            - **PMS 연동**: 빈방 수 자동 동기화 (현재는 매니저 입력)
            - **`src/ingest_bookings.py`**: 오늘 자 신규 예약 CSV 자동 처리
            - **walk 보상 정책**: 실제 보상 단가 반영한 비용 모델
            - **호텔별·시즌별 안전 상한 조정** (현재 1.2 고정)
            """
        )
