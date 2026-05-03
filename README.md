# 🏨 호텔 No-Show 의사결정 지원 시스템

> **한양대 머신러닝 팀 프로젝트 (2026)**
> 호텔 예약 취소(no-show) 예측 + SHAP 기반 자동 해석 + 비즈니스 액션 권장이 통합된 시스템

---

## 🎯 프로젝트 개요

본 프로젝트는 단순 예약 취소 예측 모델이 아닌, **매니저가 실제로 의사결정에 사용할 수 있는 통합 시스템**을 목표로 한다. 모델이 "취소 확률 0.78"만 출력하는 게 아니라, **왜 그렇게 예측했는지(SHAP 기반 자동 해석)** 와 **매니저가 무엇을 해야 하는지(비즈니스 액션 권장)** 까지 함께 제공한다.

### 시스템 출력 예시

```
입력: 예약 1건
  - lead_time: 180일
  - previous_cancellations: 2회
  - deposit_type: No Deposit
  - 도착일 강수 예보: 25mm

출력:
  ① 취소 확률: 0.78 (HIGH)

  ② 주도 변수 Top 3 (SHAP 기반 자동 해석):
     • lead_time이 180일로 매우 김 (+0.21)
     • 과거 2회 취소 이력 (+0.15)
     • No Deposit 정책 (+0.12)

  ③ 권장 액션:
     • 도착 30일 전 재확인 콜
     • 선결제 전환 유도 안내 발송
     • 오버부킹 후보로 분류
```

---

## 💡 차별 포인트

학부생으로서 이 데이터에서 발견한 **4가지 어려움을 정직하게 다룬 분석 과정** 자체가 차별 포인트.

### ① 데이터 누수 (Target Leakage)
원본 32개 컬럼 중 도착일 이후 갱신되는 컬럼(`reservation_status_date` 등)을 식별하고 drop. [상세](docs/leakage_columns_review.md)

### ② 외부 데이터의 시간 비대칭성 ⭐
학습 시점엔 도착일 실제 날씨가 확정값이지만, 손님 의사결정 시점엔 일기예보(불확실값). `lead_time` 평균이 104일이라 "손님이 도착일 날씨를 알고 결정"한다는 가정이 깨짐. **모델에 가설을 강제로 주입하지 않고 SHAP interaction으로 lead_time별 영향 차이를 정량화**하는 방향 선택. [검증기록 #3 참조](#)

### ③ 임계값(Threshold) 함정
0.5 기본값은 빈 방 손실 vs 오버부킹 보상비 비대칭을 무시. PR curve 분석 후 **0.35 수준으로 비즈니스 논리 기반 조정**.

### ④ 클래스 불균형 + 평가지표
취소율 37%로 약한 불균형. accuracy 대신 **PR-AUC 메인, F1 보조**로 평가지표 선정. 안내문에 "반드시 직접 해야 하는 일"로 명시된 항목.

---

## 👥 팀 구성

| 역할 | 이름 | 담당 |
| --- | --- | --- |
| Tech Lead + PM | 심재형 | 일정·로그 관리, 시스템 통합, 이야기 생성 모듈, 액션 매핑 룰, Streamlit 대시보드, 두 Dev 안전망 |
| Data / Baseline | 이고은 | 데이터 전처리, EDA, 누수 컬럼 식별, Logistic Regression + Random Forest baseline |
| Main Model + SHAP | 김나리 | XGBoost 학습·튜닝, SHAP 변수 중요도 분석, 오류 케이스 패턴 분석 |

---

## 📅 5주 일정

| 주차 | 핵심 작업 | 산출물 |
| --- | --- | --- |
| Week 1 | 문제 정의, 데이터 확보, 누수 컬럼 결정, 시스템 아키텍처 1차 설계 | 1차 발표, PROBLEM_DEFINITION.md |
| Week 2 | EDA + Baseline 2개 + "왜 PR-AUC인가" 문서 (어려움 ④) | Baseline 성능 비교, 평가지표 선정 문서 |
| Week 3 | XGBoost 학습 + 임계값 0.35 결정 + 오류 분석 시동 (어려움 ③) → 중간발표 | 모델 비교표, 임계값 비즈니스 논리 문서 |
| Week 4 ⭐ | SHAP 분석 3종 + 이야기 생성 + 액션 매핑 + Streamlit 통합 (어려움 ② 검증) | **시스템 메인 산출물** |
| Week 5 | 최종 발표 준비, 팀원별 역할 정리 1부 | 최종 발표, 보고서 |

---

## 🛠 기술 스택

- **언어**: Python 3.11+
- **데이터**: pandas, numpy
- **모델링**: scikit-learn (Logistic Regression, Random Forest), xgboost
- **해석**: shap
- **대시보드**: streamlit
- **외부 API**: requests (Open-Meteo)
- **개발 환경**: Jupyter, Git/GitHub

---

## 📊 데이터

| 데이터 | 출처 | 라이선스 |
| --- | --- | --- |
| Hotel Booking Demand (119,390건) | [Kaggle](https://www.kaggle.com/datasets/jessemostipak/hotel-booking-demand) (Antonio et al., 2019) | CC0 |
| Historical Weather (Lisbon + Algarve) | [Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api) | CC BY 4.0 |

- **호텔 2개**: City Hotel (리스본, 도시형) / Resort Hotel (알가르브, 리조트형)
- **기간**: 2015.7 ~ 2017.8 (약 26개월)
- **취소율**: 평균 37% (City 42%, Resort 28%)

---

## 📂 폴더 구조

```
ml_project/
├── README.md                  # 이 파일
├── PROBLEM_DEFINITION.md      # 문제 정의 (1차 발표 핵심)
├── AI_USAGE_LOG.md            # AI 사용 기록 (필수)
├── VALIDATION_LOG.md          # AI 검증 기록 (최소 3건, 현재 4건)
├── requirements.txt
├── .gitignore
├── data/                      # 데이터 (gitignore)
│   ├── raw/
│   ├── processed/
│   └── splits/
├── notebooks/                 # 실험용 Jupyter 노트북
│   ├── 01_data_exploration.ipynb
│   ├── 02_eda.ipynb
│   ├── 03_baseline_models.ipynb
│   ├── 04_xgboost.ipynb
│   └── 05_shap_analysis.ipynb
├── src/                       # 재사용 가능한 코드
│   ├── data_loader.py
│   ├── preprocess.py
│   ├── train.py
│   ├── evaluate.py
│   ├── story_generator.py     # SHAP → 자연어 이야기 생성
│   └── action_recommender.py  # 확률 + 변수 → 권장 액션 매핑
├── dashboard/                 # Streamlit 대시보드
│   └── app.py                 # 통합 시스템 (예측 + 이야기 + 액션)
└── docs/                      # 발표 자료, 회의록, 보고서
    ├── leakage_columns_review.md
    ├── presentation_outline.md
    ├── system_architecture.md
    └── final_report.md
```

---

## 🚀 시작하기

```bash
# 1. 저장소 클론
git clone https://github.com/simjaehyung/ml_project.git
cd ml_project

# 2. 가상환경 생성 + 패키지 설치
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. 데이터 준비
# Kaggle: jessemostipak/hotel-booking-demand 다운로드 → data/raw/hotel_bookings.csv
# Open-Meteo는 코드 실행 시 자동 호출 (인증 불필요)

# 4. 노트북 실행 (학습)
jupyter notebook notebooks/

# 5. 대시보드 실행 (의사결정 지원 시스템)
streamlit run dashboard/app.py
```

---

## 🤖 AI 도구 사용 정책

본 프로젝트는 AI 도구(Claude, ChatGPT 등) 사용을 적극적으로 활용합니다. 단, 안내문 4·5·6·7번에 따라 다음을 준수합니다.

- 모든 AI 사용 내역은 [AI_USAGE_LOG.md](AI_USAGE_LOG.md)에 기록
- AI 결과 검증·수정 내역은 [VALIDATION_LOG.md](VALIDATION_LOG.md)에 기록 (최소 3건, 현재 4건)
- 문제 정의·평가 지표 선정·결과 해석은 팀원이 직접 결정

### 주요 검증 사례 (VALIDATION_LOG에서 발췌)

| # | 사례 | 결정 |
| --- | --- | --- |
| 1 | `reservation_status_date` feature 사용 제안 | **누수로 판단 → drop** |
| 2 | 다지역 데이터 결합 제안 | 2개 호텔 한정·**비교 축으로 재정의** |
| 3 | 날씨 변수에 lead_time 가중치 주입 제안 | **폐기 → SHAP interaction으로 검증** |
| 4 | 날씨를 메인 프레임으로 설정 | **변수 중 하나로 격하 → 시스템 차별점 재정의** |

---

## 📈 평가 비중 매핑 (수업 안내문 기준)

| 평가 항목 | 비중 | 우리 시스템의 강점 |
| --- | --- | --- |
| 문제 정의 | 15% | 4가지 어려움 사전 식별 + 의사결정 지원이라는 명확한 목적 |
| 데이터/모델링 | 20% | XGBoost + Baseline 비교 + SHAP 통합 |
| 평가/오류분석 | 20% | 4가지 어려움의 빵꾸 조사 과정 + SHAP 기반 오류 분석 |
| **결과물 완성도** | **15%** | **이야기·액션 자동 생성 대시보드 (압도적 차별점)** |
| AI 기록 | 15% | 매주 상시 LOG 작성 |
| 발표/역할 | 15% | 3회 발표 + 데모 임팩트 |

---

## 📝 라이선스

학술 목적, 비공개. 외부 공유 금지.

---

## 🙏 참고 문헌

- Antonio, N., de Almeida, A., & Nunes, L. (2019). *Hotel booking demand datasets*. Data in Brief, 22, 41-49.
- Stack Overflow (2025). *Developer Survey 2025*.
