# AI 사용 기록

> 안내문 기준 AI 사용 기록은 필수 제출 파일이며 평가 비중 15%에 직결됩니다.
> 사용할 때마다 그날 바로 기록합니다.

---

## 기록 형식

```
## YYYY-MM-DD | [도구] | [목적 한 줄 요약]

- **사용 도구**: Claude / ChatGPT / Copilot 등
- **목적**: 무엇을 물어봤는가
- **입력 요청 요약**: 프롬프트 핵심
- **받은 결과 요약**: AI가 제안한 내용
- **실제 반영 여부**: 전부 반영 / 일부 반영 / 폐기
- **팀원**: 심재형 / 이고은 / 김나리
```

---

## 2026-04-30 | Claude | 주제 범위 설정 타당성 검토

- **사용 도구**: Claude
- **목적**: 포르투갈 2개 호텔 한정 범위의 타당성 검토
- **입력 요청 요약**: "2개 호텔 데이터만 쓰는 게 범위가 너무 좁지 않은가"
- **받은 결과 요약**: 다지역 확장 시 호텔별 특성 희석 우려 제시, 2개 호텔 비교 축으로 재정의 제안
- **실제 반영 여부**: 일부 반영 — 2개 호텔 유지하되 비교 분석 축으로 활용
- **팀원**: 심재형

---

## 2026-04-30 | Claude | 가중치 주입 방법 검토 (폐기)

- **사용 도구**: Claude
- **목적**: 도메인 지식을 feature engineering에 반영하는 방법 탐색
- **입력 요청 요약**: "날씨 변수에 계절 가중치를 주입하면 모델 성능이 좋아지지 않을까"
- **받은 결과 요약**: 가중치 주입이 연구 질문(lead_time별 날씨 영향)과 순환 논리를 만들 수 있다고 지적
- **실제 반영 여부**: 폐기 — 원본 변수 그대로 투입, SHAP으로 영향 측정하는 방향으로 전환
- **팀원**: 심재형

---

## 2026-04-30 | Claude | 시간 정합성 문제 검토

- **사용 도구**: Claude
- **목적**: 도착일 실제 날씨를 feature로 쓰는 타당성 확인
- **입력 요청 요약**: "lead_time 평균 104일인데 실제 날씨를 쓰는 게 맞나"
- **받은 결과 요약**: 학습/추론 시점 비대칭 지적. 해결안 3가지 제안 (lead_time 단기 한정 / 합성 예보 / 현재 방식 + 한계 명시)
- **실제 반영 여부**: 일부 반영 — 실제 날씨로 학습 + SHAP interaction 분석 + 한계 명시로 결정
- **팀원**: 심재형

---

## 2026-05-03 | Claude Code | 보류 컬럼 7개 데이터 검증 및 PM 처리 결정

- **사용 도구**: Claude Code (MCP + 로컬 파일 분석)
- **목적**: 이고은이 넘긴 보류 컬럼 7개에 대해 데이터 기반 검증 후 PM 임시 결정
- **입력 요청 요약**: "보류 컬럼들 각각 drop/keep 근거를 데이터로 확인해줘. previous_cancellations는 시점 데이터인지 검증해줘."
- **받은 결과 요약**: 연도별 비율 추세, is_repeated_guest 정합성, 값 분포 4가지 검증 수행. previous_cancellations 감소 추세 발견. previous_bookings_not_canceled 정합성 모순 25% 발견. days_in_waiting_list 간접 누수 가능성 지적.
- **실제 반영 여부**: 전부 반영 — drop 3개(assigned_room_type, previous_bookings_not_canceled, days_in_waiting_list), keep 4개(booking_changes, previous_cancellations 조건부, agent·company 인디케이터)
- **팀원**: 심재형

---

## 2026-05-03 | Claude Code | Week 1 누수 후보 분류표 검증·작성 (Dev A)

- **사용 도구**: Claude Code
- **목적**: 32개 컬럼 누수 검증 스크립트 작성 + 분류표 문서화
- **입력 요청 요약**: "보류 컬럼별 데이터 기반 검증 [Y1~Y4] 작성 + 분류표 220줄 정리"
- **받은 결과 요약**: `notebooks/02_leakage_check.py` 검증 스크립트, `docs/leakage_candidates.md` 분류표 (정상건 reserved≠assigned 18.78%, prev_cancel≥1 그룹 91.64% 등 수치 검증)
- **실제 반영 여부**: 전부 반영 — 검증 결과는 스크립트 직접 실행으로 확인, 분류 결정은 Dev A가 직접
- **팀원**: 이고은 (Dev A)

---

## 2026-05-03 | Claude Code | 날씨 변수 다중공선성 정리 및 CSV 재생성

- **사용 도구**: Claude Code (로컬 파일 분석 + 스크립트 실행)
- **목적**: 김나리 제안(precipitation/temperature/wind 중복 변수 정리) 반영 및 데이터 재생성
- **입력 요청 요약**: "precipitation vs rain 하나만, temperature mean drop, wind mean drop — 김나리 제안 반영해줘"
- **받은 결과 요약**: weather_data.csv 컬럼 확인 후 rain_sum·temperature_2m_mean·wind_speed_10m_mean DROP 결정 근거 제시. bookings_weather_pm.csv 및 train/test CSV 자동 재생성.
- **실제 반영 여부**: 전부 반영 — 3개 컬럼 drop, CSV 재생성
- **팀원**: 심재형

---

## 2026-05-07 | Claude Code | 전처리 파이프라인 구현 + deposit_type 이상 패턴 발견

- **사용 도구**: Claude Code (로컬 파일 분석 + 스크립트 실행)
- **목적**: Week 2 STEP 1 전처리 파이프라인 완성 및 데이터 품질 이슈 점검
- **입력 요청 요약**: "전처리 결정사항 실행 — 날씨 3개 DROP, country Top10+Other OHE, children NaN 처리, month 숫자 변환"
- **받은 결과 요약**: `src/preprocessing_pipeline.py` 생성, train/test_processed.csv 출력. 추가로 deposit_type=Non Refund 취소율 99.2% 이상 패턴 발견 — 단체 예약 블록 운영 방식 또는 사후 기록 가능성 제기.
- **실제 반영 여부**: 파이프라인 전부 반영. deposit_type은 누수 후보로 격상하여 VALIDATION_LOG 기록, Phase 2 ablation 예약.
- **팀원**: 심재형

---

## 2026-05-08 | Claude Code | Week 1 발표 대본·치트시트 + Week 2 STEP 1 Streamlit 학습 (Dev A)

- **사용 도구**: Claude Code
- **목적**: 6-9페이지 발표 대본 작성 + A4 치트시트 PNG 생성 + Streamlit 4패턴 학습
- **입력 요청 요약**: 발표 대본 톤·길이 조절, 컬럼명 한국어 풀이, 출처 모호한 숫자 두루뭉실 처리, Streamlit `tabs`/`dataframe`/`form`/`metric` 단계별 학습
- **받은 결과 요약**: 6-9페이지 발표 대본 (3분~3분30초), `docs/cheatsheet_presentation.{py,png}` A4 치트시트, `dashboard/streamlit_practice.py` 4패턴 골격
- **실제 반영 여부**: 전부 반영 — 발표 톤은 Dev A 본인이 직접 다듬어 사용
- **팀원**: 이고은 (Dev A)

---

## 2026-05-08 | Claude Code | Week 2 STEP 2 previous_cancellations EDA + 정의 어긋남 분석 (Dev A)

- **사용 도구**: Claude Code
- **목적**: PM 가이드 (연도별 분포 + ≥1 취소율 90%+) + design_04 미결 항목 C (정의 어긋남 패턴 분석)
- **입력 요청 요약**: train.csv 기반 EDA 스크립트 작성. `is_repeated_guest=0` & `previous_cancellations≥1` 행의 호텔/세그먼트/lead_time 분포 분석
- **받은 결과 요약**: `src/03_prev_cancel_eda.py` 작성·실행. ① 2016년 ≥1 그룹 취소율 84.98%로 90% 미만 (PM 보고 안건). ② 정의 어긋남 5,520건이 `deposit_type=Non Refund`와 동일한 B2B 블록 패턴 (취소율 99.15%, lead_time 217일, Groups+Offline TA/TO 85.2%) 임을 확인. ③ Week 3 SHAP 감시 항목 + Phase 2 ablation 권고.
- **실제 반영 여부**: 전부 반영 — 결과 문서 `docs/week2_eda_prev_cancel.md` 작성, design_04 미결 항목 C 해소로 갱신
- **팀원**: 이고은 (Dev A)

---

## 2026-05-08 | Claude Code | Week 2 STEP 2 대시보드 와이어프레임 (Dev A)

- **사용 도구**: Claude Code
- **목적**: Week 4 Streamlit 본 앱 (`dashboard/app.py`) 시작점이 될 두 탭 화면 명세 작성
- **입력 요청 요약**: STEP 1 4패턴(`tabs`/`dataframe`/`form`/`metric`) + design_05/06 기반으로 탭1(예약 우선순위) + 탭2(Flexi 라우팅) 화면 레이아웃·위젯·데이터 의존성·미결 안건 정리
- **받은 결과 요약**: `docs/wireframe_dashboard.md` 작성 — 박스 레이아웃 + Streamlit 위젯 매핑 + 팀원별 데이터 의존성 명시 + Week 3 미결 안건 5건
- **실제 반영 여부**: 전부 반영 — Week 4 본 앱 시작 시 이 문서를 시작점으로 사용
- **팀원**: 이고은 (Dev A)

---

## 2026-05-16 | Claude Code | Week 3 STEP 1·2·3 tab1_priority 구현 + 매니저 친화 톤 (Dev A)

- **사용 도구**: Claude Code
- **목적**: PM 뼈대(`app/tab1_priority.py`)의 `[TODO 이고은]` 3개 채우기 + 5/18 Gate 4가지(테이블 표시 / 컬러코딩 / 행 클릭 SHAP / 무크래시) 달성
- **입력 요청 요약**: 컬러코딩 셀만(옵션 A) 적용, SHAP 범위 밖 안내는 `st.info`(옵션 B) 사용, 매니저 친화 톤으로 컬럼·값 한국어 풀이 (BB/HB/FB/SC 식사 코드, Online TA 등 예약 경로 약어, ADR/lead_time 컬럼명), Styler 26만 셀 한도 초과 패치
- **받은 결과 요약**: ① 취소확률 셀에 빨/주/초 컬러코딩(`styled.map` + `_color_risk`) ② SHAP 범위 밖 예약은 `st.info` 박스로 안내 ③ 식사 코드 4종·예약 경로 7종 한국어 매핑 (`MEAL_KR`, `SEGMENT_KR`) ④ 컬럼명 `리드타임→선예약 기간`, `ADR(€)→1박 요금(€)`, `채널→예약 경로` ⑤ Styler 한도 회피 위해 위험도 순 상위 500건만 표시 (매니저 시점에서도 적정 분량)
- **실제 반영 여부**: 전부 반영 — Dev A 본인이 매니저 시점에서 직접 BB·ADR·리드타임·채널 어색함 발견하고 매핑·라벨 결정
- **팀원**: 이고은 (Dev A)
