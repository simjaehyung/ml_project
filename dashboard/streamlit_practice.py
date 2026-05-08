"""
Streamlit 4패턴 연습장 (Week 2 STEP 1)
- Dev A 학습용. Week 4 본 앱 코드 아님.
- 실행: streamlit run dashboard/streamlit_practice.py
"""
import pandas as pd
import streamlit as st


# 데이터 로드 — @st.cache_data 데코레이터를 붙이면 한 번 읽은 결과를 캐시에 저장.
# 화면을 갱신(rerun)할 때마다 csv를 다시 읽지 않아 빨라짐.
# train.csv는 PM이 시간 분할로 만든 파일이라 repo에 추적됨 → 팀원도 바로 실행 가능.
@st.cache_data
def load_bookings():
    return pd.read_csv("data/train.csv")

# 가장 단순한 화면 — streamlit이 잘 뜨는지 확인용
st.title("호텔 No-Show DSS · 연습장")
st.write("Streamlit이 제대로 뜨면 성공.")


# ─── 패턴 ① st.tabs ───
# 화면을 탭 두 개로 분할. Week 4 본 앱의 골격이 이 두 탭.
tab1, tab2 = st.tabs(["예약 우선순위", "Flexi 라우팅"])

with tab1:
    st.subheader("탭1 — 기존 예약 취소 위험 순위")

    # ─── 패턴 ② st.dataframe ───
    # csv 로드 후 핵심 컬럼만 골라 상위 20건 표시.
    # Week 4에서는 여기에 모델 예측 점수가 붙어 위험 순으로 정렬될 예정.
    df = load_bookings()
    st.write(f"총 **{len(df):,}건**의 예약 데이터 (학습용 미리보기)")

    cols_show = ["hotel", "lead_time", "arrival_date_month",
                 "adr", "reserved_room_type", "is_canceled"]
    st.dataframe(df[cols_show].head(20), use_container_width=True)

with tab2:
    st.subheader("탭2 — 신규 예약 Flexi 라우팅 권장")

    # ─── 패턴 ③ st.form ───
    # 폼은 여러 입력 위젯을 묶고, 제출 버튼을 눌렀을 때 한 번에 값이 확정되는 구조.
    # 일반 위젯은 값이 바뀔 때마다 화면이 매번 갱신되는데, 폼 안에 넣으면
    # 제출 전까지 갱신을 미룸 → 입력값 여러 개를 한 번에 처리할 때 적합.
    with st.form("new_booking"):
        st.write("**신규 예약 정보 입력**")

        lead_time = st.number_input(
            "리드타임 (예약일 ~ 도착일 사이 일수)",
            min_value=0, max_value=365, value=30,
        )
        adr = st.number_input(
            "ADR (1박당 객실 요금, EUR)",
            min_value=0.0, value=100.0, step=10.0,
        )

        # 폼 안의 제출 버튼. 일반 st.button과 달리 반드시 폼 안에 있어야 함.
        submitted = st.form_submit_button("위험도 예측")

        if submitted:
            st.success(f"입력 완료 — 리드타임 {lead_time}일 / ADR {adr} EUR")

            # ─── 패턴 ④ st.metric ───
            # 큰 숫자 카드. delta(증감 표시)와 함께 쓰면 변화량까지 강조 가능.
            # Week 4에선 fake_risk 자리에 모델 predict_proba 결과가 들어감.
            fake_risk = 0.78  # 임시값 (실제 모델 없는 학습용)

            # PM Flexi 설계 문서의 할인율 공식:
            # 할인율 = 5% + (위험점수 - 0.5) × 26%, 단 5% ≤ 할인율 ≤ 18%
            discount = max(0.05, min(0.18, 0.05 + (fake_risk - 0.5) * 0.26))

            # st.columns(2)로 화면을 두 열로 나눠 카드 나란히 배치
            c1, c2 = st.columns(2)
            c1.metric(
                label="취소 위험",
                value=f"{fake_risk:.0%}",
                delta="+5%p",            # 기준선 대비 변화 표시
                delta_color="inverse",    # +가 빨강(나쁨)으로 — 위험도 같은 지표에 적합
            )
            c2.metric(
                label="권장 할인율",
                value=f"{discount:.1%}",
            )

            st.caption("Week 4에선 모델 실제 예측값 + PM 공식 기반 할인율로 대체됨.")
