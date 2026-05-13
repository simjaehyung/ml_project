"""
app/tab2_flexi.py
탭2 — 신규 예약 Flexi 라우팅 권장

이고은 구현 담당.
[TODO] 표시된 곳만 채우면 됨. 예측 로직은 utils.py가 처리.

화면 구조:
  ┌──────────────────────┬──────────────────────────────────┐
  │  신규 예약 입력 폼    │  분석 결과                        │
  │  (핵심 10개 필드)    │  취소확률 + 라우팅 권장 + SHAP top3 │
  │  [분석하기] 버튼     │  날씨 배너 (계절 평균)             │
  └──────────────────────┴──────────────────────────────────┘
"""

import streamlit as st
import pandas as pd

from utils import (
    compute_discount,
    get_risk_label,
    predict_new_booking,
    RISK_COLORS,
    TOP10_COUNTRIES,
    COUNTRY_DISPLAY,
)

# 입력 폼 기본값 (데모 시나리오 — 고위험 예약)
DEMO_HIGH_RISK = {
    "hotel":                     "City Hotel",
    "lead_time":                 120,
    "arrival_date_month":        7,
    "stays_in_week_nights":      2,
    "stays_in_weekend_nights":   1,
    "adults":                    2,
    "children":                  0,
    "meal":                      "BB",
    "market_segment":            "Online TA",
    "distribution_channel":      "TA/TO",
    "country":                   "PRT",
    "adr":                       95.0,
    "required_car_parking_spaces": 0,
    "total_of_special_requests": 0,
    "is_repeated_guest":         0,
    "previous_cancellations":    0,
    "booking_changes":           0,
    "reserved_room_type":        "A",
    "customer_type":             "Transient",
    "agent":                     1,
    "company":                   0,
    "arrival_date_year":         2017,
    "arrival_date_week_number":  27,
    "arrival_date_day_of_month": 1,
    "babies":                    0,
}


# ── 입력 폼 ───────────────────────────────────────────────────────────────────
def render_input_form(threshold: float) -> dict | None:
    """
    신규 예약 입력 폼.
    반환: 입력 dict (분석 버튼 클릭 시) 또는 None
    """
    with st.form("booking_form"):
        st.markdown("#### 예약 정보 입력")

        col1, col2 = st.columns(2)

        with col1:
            hotel = st.selectbox("호텔", ["City Hotel", "Resort Hotel"])
            country = st.selectbox(
                "고객 국적",
                options=TOP10_COUNTRIES + ["Other"],
                format_func=lambda x: COUNTRY_DISPLAY.get(x, x),
            )
            market_segment = st.selectbox(
                "예약 채널",
                ["Online TA", "Offline TA/TO", "Direct", "Corporate", "Groups"],
            )
            lead_time = st.slider("체크인까지 (일)", 0, 365, 90)
            adr = st.number_input("객실 요금 (ADR, €/박)", min_value=0.0,
                                  max_value=999.0, value=95.0, step=5.0)

        with col2:
            arrival_month = st.selectbox(
                "도착 월",
                options=list(range(1, 13)),
                format_func=lambda m: [
                    "", "1월(Jan)", "2월(Feb)", "3월(Mar)", "4월(Apr)",
                    "5월(May)", "6월(Jun)", "7월(Jul)", "8월(Aug)",
                    "9월(Sep)", "10월(Oct)", "11월(Nov)", "12월(Dec)"
                ][m],
                index=6,
            )
            week_nights    = st.number_input("평일 체류 (박)", 0, 20, 2)
            weekend_nights = st.number_input("주말 체류 (박)", 0, 10, 1)
            special_req    = st.slider("특별 요청 수", 0, 5, 0)
            parking        = st.checkbox("주차 필요")

        st.divider()

        # 데모 버튼 (고위험 예약 자동 입력)
        col_demo, col_submit = st.columns([1, 2])
        with col_demo:
            # [TODO 이고은] 필요하면 "데모 채우기" 버튼 추가 가능
            pass
        with col_submit:
            submitted = st.form_submit_button(
                "🔍 취소 위험 분석",
                use_container_width=True,
                type="primary",
            )

    if not submitted:
        return None

    # 기본값으로 나머지 필드 채우기 (모델에 필요하지만 UI에 없는 것들)
    input_dict = {**DEMO_HIGH_RISK}
    input_dict.update({
        "hotel":                       hotel,
        "country":                     country,
        "market_segment":              market_segment,
        "distribution_channel":        "TA/TO" if "TA" in market_segment else "Direct",
        "lead_time":                   lead_time,
        "adr":                         adr,
        "arrival_date_month":          arrival_month,
        "stays_in_week_nights":        week_nights,
        "stays_in_weekend_nights":     weekend_nights,
        "total_of_special_requests":   special_req,
        "required_car_parking_spaces": int(parking),
    })
    return input_dict


# ── 취소 확률 게이지 ───────────────────────────────────────────────────────────
def render_prob_gauge(cancel_prob: float, threshold: float):
    label, color = get_risk_label(cancel_prob, threshold)
    pct = cancel_prob * 100

    # [TODO 이고은] st.progress + 큰 숫자로 시각화
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(90deg, {color}33 {pct:.0f}%, #f0f0f0 {pct:.0f}%);
            border-left: 5px solid {color};
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 12px;
        ">
            <span style="font-size: 2.2em; font-weight: bold; color: {color}">
                {cancel_prob:.1%}
            </span>
            <span style="color: {color}; font-size: 1em; margin-left: 10px">
                {label} RISK
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Flexi 라우팅 권장 박스 ────────────────────────────────────────────────────
def render_routing_recommendation(cancel_prob: float, adr: float,
                                   threshold: float, total_nights: int):
    label, color = get_risk_label(cancel_prob, threshold)
    discount      = compute_discount(cancel_prob)
    discounted_adr = adr * (1 - discount / 100)
    savings        = (adr - discounted_adr) * total_nights

    if cancel_prob >= threshold:
        st.markdown(
            f"""
            <div style="
                background-color: {color}15;
                border: 2px solid {color};
                border-radius: 10px;
                padding: 16px 20px;
            ">
                <h4 style="color: {color}; margin: 0 0 8px 0">
                    ⚡ Flexi 풀 라우팅 권장
                </h4>
                <table style="width:100%; font-size:0.95em">
                    <tr>
                        <td>권장 할인율</td>
                        <td><b>{discount:.1f}%</b></td>
                    </tr>
                    <tr>
                        <td>적용 ADR</td>
                        <td><b>€{discounted_adr:.0f}/박</b>
                        (원래 €{adr:.0f})</td>
                    </tr>
                    <tr>
                        <td>총 절감액</td>
                        <td><b>€{savings:.0f}</b>
                        ({total_nights}박 기준)</td>
                    </tr>
                </table>
                <p style="font-size:0.8em; color:#888; margin-top:10px">
                    ℹ️ 이 권장은 참고용입니다. 최종 결정은 매니저 확인 필요. (GDPR Art.22)
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.success(
            f"✅ **Standard 배정** — 취소 위험이 낮습니다 ({cancel_prob:.1%}). "
            f"일반 확정 예약으로 처리하세요.",
        )


# ── SHAP top-3 위험 요인 ──────────────────────────────────────────────────────
def render_shap_top3(shap_top_df: pd.DataFrame):
    st.markdown("#### 주요 위험 요인 (SHAP)")

    FEATURE_LABELS = {
        "country_grouped_PRT":              "포르투갈 국적",
        "total_of_special_requests":        "특별 요청 수",
        "lead_time":                        "선예약 기간",
        "required_car_parking_spaces":      "주차 필요 여부",
        "market_segment_Online TA":         "온라인 여행사 채널",
        "adr":                              "객실 요금(ADR)",
        "previous_cancellations":           "과거 취소 이력",
        "customer_type_Transient":          "일반(Transient) 고객",
        "market_segment_Groups":            "그룹 예약",
        "booking_changes":                  "예약 변경 횟수",
    }

    for _, row in shap_top_df.iterrows():
        label = FEATURE_LABELS.get(str(row["feature"]), str(row["feature"]))
        val   = float(row["shap_value"])
        color = RISK_COLORS["HIGH"] if val > 0 else RISK_COLORS["LOW"]
        arrow = "▲" if val > 0 else "▼"
        st.markdown(
            f"<span style='color:{color}'>{arrow}</span> {label} "
            f"<span style='color:{color}; font-size:0.85em'>({val:+.3f})</span>",
            unsafe_allow_html=True,
        )


# ── 날씨 배너 ─────────────────────────────────────────────────────────────────
def render_weather_banner(weather: dict, month: int):
    if not weather:
        st.caption("※ 날씨 데이터 로드 중 (data/seasonal_weather.csv 필요)")
        return

    month_names = ["", "1월", "2월", "3월", "4월", "5월", "6월",
                   "7월", "8월", "9월", "10월", "11월", "12월"]

    st.markdown(
        f"""
        <div style="background:#f8f9fa; border-radius:8px; padding:10px 16px;
                    font-size:0.85em; color:#555; margin-top:8px">
            🌡️ {weather.get('temperature_2m_max', '?'):.0f}°C /
            {weather.get('temperature_2m_min', '?'):.0f}°C &nbsp;|&nbsp;
            💧 강수 {weather.get('precipitation_sum', '?'):.1f}mm &nbsp;|&nbsp;
            💨 바람 {weather.get('wind_speed_10m_max', '?'):.0f}km/h
            <br>
            <span style="color:#999">
                ※ {month_names[month]} 계절 평균값 사용 (실제 예보 데이터 미보유)
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── 탭2 메인 렌더러 ───────────────────────────────────────────────────────────
def render_tab2(model, train_columns: list, explainer, sw_df):
    st.markdown("## ⚡ 신규 예약 Flexi 라우팅 권장")
    st.markdown("신규 예약 정보를 입력하면 취소 위험을 분석하고 Flexi 오퍼 여부를 권장합니다.")
    st.divider()

    # 임계값 설정 (사이드바 또는 상단)
    threshold = st.slider(
        "Flexi 라우팅 임계값",
        min_value=0.40, max_value=0.85, value=0.60, step=0.05,
        help="이 값 이상이면 Flexi 풀 라우팅 권장",
        key="tab2_threshold",
    )

    left_col, right_col = st.columns([1, 1])

    with left_col:
        input_dict = render_input_form(threshold)

    with right_col:
        if input_dict is None:
            st.info("← 왼쪽 폼을 입력하고 [취소 위험 분석] 버튼을 누르세요.")
            st.markdown(
                "**분석 결과 예시:**\n"
                "- 취소 확률 표시\n"
                "- Flexi 라우팅 권장 여부\n"
                "- 권장 할인율 및 적용 요금\n"
                "- 주요 위험 요인 (SHAP 기반)\n"
                "- 도착월 기준 날씨 정보"
            )
            return

        with st.spinner("취소 위험 분석 중..."):
            cancel_prob, shap_top = predict_new_booking(
                input_dict.copy(), model, train_columns, explainer, sw_df
            )

        total_nights = (
            int(input_dict.get("stays_in_week_nights", 2)) +
            int(input_dict.get("stays_in_weekend_nights", 1))
        )

        st.markdown("#### 분석 결과")
        render_prob_gauge(cancel_prob, threshold)

        st.divider()

        render_routing_recommendation(
            cancel_prob,
            float(input_dict.get("adr", 95)),
            threshold,
            total_nights,
        )

        st.divider()

        render_shap_top3(shap_top)

        # 날씨 배너
        from utils import get_seasonal_weather
        weather = get_seasonal_weather(
            input_dict.get("hotel", "City Hotel"),
            int(input_dict.get("arrival_date_month", 7)),
            sw_df,
        )
        render_weather_banner(weather, int(input_dict.get("arrival_date_month", 7)))
