# 선행연구 정리 — Hotel Booking Demand 기반 취소 예측 · 오버부킹 최적화

> 작성일: 2026-05-08  
> 목적: 동일 데이터셋(Antonio et al., 2019) 또는 인접 주제를 다룬 선행연구를 한곳에 모아 발표 및 방법론 결정 시 참조

---

## 목차

1. [데이터셋 원전](#1-데이터셋-원전)
2. [취소 예측 — ML 모델 비교](#2-취소-예측--ml-모델-비교)
3. [취소 예측 — 해석 가능성 (SHAP·LIME)](#3-취소-예측--해석-가능성-shaplime)
4. [취소 예측 — DSS·시스템 통합](#4-취소-예측--dss시스템-통합)
5. [오버부킹 최적화 — 수리 모델 · 수익 관리](#5-오버부킹-최적화--수리-모델-수익-관리)
6. [외부 변수 (날씨·검색량) 활용 연구](#6-외부-변수-날씨검색량-활용-연구)
7. [요약 비교표](#7-요약-비교표)
8. [우리 프로젝트 포지셔닝](#8-우리-프로젝트-포지셔닝)

---

## 1. 데이터셋 원전

### [D1] Antonio, N., de Almeida, A., & Nunes, L. (2019). Hotel booking demand datasets.
- **출처:** *Data in Brief*, Vol. 22, pp. 41–49
- **링크:** https://www.sciencedirect.com/science/article/pii/S2352340918315191
- **요약:**  
  포르투갈 2개 실제 호텔 (H1: 리조트 호텔 알가르브 / H2: 시티 호텔 리스본)의  
  2015-07~2017-08 예약 데이터를 공개한 데이터 기술 논문.  
  - H1(Resort): 40,060건, H2(City): 79,330건, 총 31개 변수  
  - 개인 식별 정보 제거 후 공개 (Kaggle 업로드 원천)  
  - `reservation_status`, `reservation_status_date`가 타깃 누수 위험 변수임을 명시  
  - `country`는 체크인 시 정정될 수 있어 주의 필요 — 이후 저자 후속 논문에서 누수로 재분류
- **우리 프로젝트 관련성:** 우리가 사용하는 데이터의 직접 출처 논문. 변수 설명, 수집 방법, 알려진 결함을 확인할 수 있는 1차 참조.

---

## 2. 취소 예측 — ML 모델 비교

### [P1] Antonio, N., de Almeida, A., & Nunes, L. (2019). Predicting Hotel Booking Cancellations: Exploring Key Drivers. *Big Data in Hotel Revenue Management.*
- **출처:** *Cornell Hospitality Quarterly / SAGE*, https://journals.sagepub.com/doi/abs/10.1177/1938965519851466
- **요약:**  
  동일 데이터셋에서 취소 드라이버를 탐색.  
  - 취소 상위 예측 변수: `lead_time`, `deposit_type`, `distribution_channel`, `previous_cancellations`  
  - LR / RF / XGBoost 비교 → XGBoost AUC 0.95 이상으로 최고  
  - `country`를 피처로 사용할 때 체크인 시점 정보 오염 가능성을 경고

### [P2] Using machine learning and big data for efficient forecasting of hotel booking cancellations (2020).
- **출처:** *International Journal of Hospitality Management*, https://www.sciencedirect.com/science/article/abs/pii/S0278431920300980
- **요약:**  
  - RF, XGBoost, Neural Network을 비교, XGBoost·RF 앙상블이 AUC ~0.95로 최우수  
  - 클래스 불균형 처리: class_weight 조정이 SMOTE 대비 동등하거나 우수  
  - `lead_time`, `deposit_type`, `total_of_special_requests` 상위 피처

### [P3] Prediction of hotel booking cancellations: Integration of machine learning and probability model based on interpretable feature interaction (2023).
- **출처:** *Decision Support Systems*, https://www.sciencedirect.com/science/article/abs/pii/S0167923623000349
- **요약:**  
  - ML + 피처 상호작용 기반 해석 모델 결합  
  - LR, CART, RF, XGBoost, GBDT, KNN, GNB 비교  
  - XGBoost·RF가 AUC 0.9526 / 0.9553으로 최고  
  - 피처 상호작용을 반영하면 개별 피처만 사용할 때보다 해석 가능성 향상

### [P4] Predicting hotel booking cancellations: a comprehensive machine learning approach (2025).
- **출처:** *Journal of Revenue and Pricing Management*, https://link.springer.com/article/10.1057/s41272-025-00532-x
- **요약:**  
  - LightGBM, XGBoost, ANN-MLP, RF 포함 종합 비교  
  - 고차원 피처 중요도 필터링 → 차원 축소 후 성능 유지 확인  
  - PR-AUC 불균형 환경에서 ROC-AUC보다 신뢰도 높음 언급

### [P5] Navigating uncertainty: enhancing hotel cancellation predictions with adaptive machine learning (2025).
- **출처:** *Information Technology & Tourism*, https://link.springer.com/article/10.1007/s40558-025-00349-9
- **요약:**  
  - 슬라이딩 윈도우 훈련·검증 프로토콜 + SHAP 기반 피처 중요도 추적  
  - 팬데믹 전후 체제 전환 시 피처 중요도 순위가 크게 변화  
  - 적응형 재학습(adaptive retraining)이 정적 모델 대비 성능 우위

### [P6] Explainable profit-driven hotel booking cancellation prediction (2024).
- **출처:** *European Journal of Operational Research*, https://www.sciencedirect.com/science/article/abs/pii/S0377221724006696
- **요약:**  
  - 이익 기반(profit-driven) 손실 함수 + 이종 스태킹 앙상블  
  - 오분류 비용(FP: 오버부킹 보상 vs FN: 빈 방 손실)을 비대칭으로 반영  
  - 임계값 최적화와 비용 민감 학습을 결합

### [P7] Hotel Booking Cancellation Prediction Using Applied Bayesian Models (2024).
- **출처:** *arXiv*, https://arxiv.org/abs/2410.16406
- **요약:**  
  - 베이지안 접근법으로 불확실성 정량화  
  - 확률 구간(credible interval) 제공 → DSS에서 신뢰 범위 제시 가능  
  - 기존 점추정 모델 대비 운영 의사결정에 더 유용한 정보 제공 주장

### [P8] Predicting hotel booking cancellations using tree-based neural network (2024).
- **출처:** *PMC / NCBI*, https://pmc.ncbi.nlm.nih.gov/articles/PMC11623061/
- **요약:**  
  - 트리 기반 신경망 구조로 해석성과 성능 동시 확보 시도  
  - 전통 트리 모델 대비 경계 사례(borderline)에서 성능 향상

---

## 3. 취소 예측 — 해석 가능성 (SHAP·LIME)

### [I1] A comprehensive approach to enhancing short-term hotel cancellation forecasts through dynamic machine learning models (2025).
- **출처:** *Journal of Hospitality & Tourism Research (SAGE)*, https://journals.sagepub.com/doi/10.1177/13548166251318768
- **요약:**  
  - SHAP을 시계열 슬라이딩 윈도우와 결합해 체제별(전팬데믹/팬데믹/후팬데믹) 피처 중요도 변화 추적  
  - 팬데믹 이후 `lead_time` 중요도 감소, `country` 중요도 증가 확인  
  - 단기 예측(7~30일 전)에서 동적 재학습 프로토콜이 정적 모델보다 MAE 20% 감소

### [I2] Unveiling cancellation dynamics: A two-stage model for predictive analytics (2025).
- **출처:** *Decision Support Systems*, https://www.sciencedirect.com/science/article/abs/pii/S0169023X2500062X
- **요약:**  
  - 1단계: 취소 여부 예측 / 2단계: 취소 시점 예측 — 2단계 모델로 세분화  
  - SHAP 기반으로 각 단계 피처 기여도 분리  
  - 2단계 시점 예측이 오버부킹 전략에서 실질적 RevPAR 개선 기여

---

## 4. 취소 예측 — DSS·시스템 통합

### [S1] Antonio, N., de Almeida, A., & Nunes, L. (2019). An Automated Machine Learning Based Decision Support System to Predict Hotel Booking Cancellations.
- **출처:** *Data Science Journal*, https://datascience.codata.org/articles/10.5334/dsj-2019-032
- **요약:**  
  - PMS 데이터 자동 학습 + 예측 오류에서 지속 업데이트하는 클라우드 기반 AutoML DSS  
  - Accuracy 84%, Precision 82%, AUC 88% (당시 기준)  
  - Analytics-as-a-Service 형태로 RMS 컴포넌트로 통합 가능  
  - **이 논문이 우리 프로젝트 DSS 아키텍처의 직접 선행연구**

### [S2] Leveraging Machine Learning for Sustainable Hotel Management: Predicting Booking Cancellations to Optimize Operations (2024).
- **출처:** *Springer LNCS*, https://link.springer.com/chapter/10.1007/978-3-031-78471-2_6
- **요약:**  
  - 취소 예측 → 하우스키핑/운영 인력 배치 최적화 연동  
  - 지속가능성(에너지 절감) 관점에서 공실 감소 효과 정량화  
  - Streamlit 기반 운영자 인터페이스 구현 사례 언급

### [S3] Forecasting hotel cancellations through machine learning (2024).
- **출처:** *Expert Systems (Wiley)*, https://onlinelibrary.wiley.com/doi/10.1111/exsy.13608
- **요약:**  
  - 예약 접수 시점부터 도착일까지 피처 가용성 변화를 타임라인으로 모델링  
  - "booking time" vs "check-in time" 정보 분리 실험  
  - 조기 예약 단계 정보만으로도 AUC 0.87 이상 달성 — 실시간 개입 가능 시점 확인

---

## 5. 오버부킹 최적화 — 수리 모델 · 수익 관리

### [O1] Hotel Revenue Management: Benefits of Simultaneous Overbooking and Allocation Problem Formulation in Price Optimization (2019).
- **출처:** *Computers & Industrial Engineering*, https://www.sciencedirect.com/science/article/abs/pii/S0360835219305327
- **요약:**  
  - 오버부킹 + 객실 배정 + 가격을 동시 최적화하는 혼합정수 프로그래밍 모델  
  - 분리 최적화 대비 RevPAR 약 6% 향상 보고  
  - 취소 확률을 모델 입력으로 사용 — **ML 취소 예측과 직접 연동 가능한 구조**

### [O2] A stochastic approach to hotel revenue optimization (2004).
- **출처:** *Computers & Operations Research*, https://www.sciencedirect.com/science/article/abs/pii/S0305054803003009
- **요약:**  
  - 확률적 수요를 네트워크 최적화 모형으로 정식화  
  - 취소·노쇼 분포 추정 → 최적 오버부킹 수준의 해석적 해 도출  
  - Walk 비용 C_walk, 공실 비용 C_empty, 취소 분포 F(x)의 관계식 확립  
  - **우리 Flexi 시뮬레이션의 수리적 기반으로 참조 가능**

### [O3] Optimal overbooking decision for hotel rooms revenue management (2015).
- **출처:** *ResearchGate / Sysmath*, https://sysmath.cjoe.ac.cn/jweb_xtkxysx/EN/10.12341/jssms11713
- **요약:**  
  - 이항·포아송 분포 기반 오버부킹 최적 수량 결정 모델  
  - Walk rate < 2% 제약 하에서 기대 수익 최대화 정식화  
  - **우리 미결항목 #11 (walk_rate < 2% 검증)의 이론적 근거**

### [O4] Model of Price Optimization as a Part of Hotel Revenue Management — Stochastic Approach (2021).
- **출처:** *Mathematics (MDPI)*, https://www.mdpi.com/2227-7090/9/13/1552
- **요약:**  
  - 확률 수요 환경에서 가격·오버부킹을 통합한 동적 계획법  
  - 시뮬레이션 결과: 수익 민감도가 취소율 추정 오차에 비선형 반응  
  - 취소 예측 모델 정밀도 1% 향상이 RevPAR 개선에 기여함을 수치로 확인

---

## 6. 외부 변수 (날씨·검색량) 활용 연구

### [W1] Daily Tourism Demand Forecasting with the iTransformer Model (2024).
- **출처:** *Sustainability (MDPI)*, https://www.mdpi.com/2071-1050/16/23/10678
- **요약:**  
  - 일별 관광 수요 예측에 날씨·검색량·절기 데이터 복합 사용  
  - 날씨 변수(기온, 강수, 풍속)가 수요 변동의 약 12% 설명  
  - Transformer 기반 멀티소스 입력 구조 → 피처 그룹별 기여 분리 가능

### [W2] Hotel demand forecasting with multi-scale spatiotemporal features (2024).
- **출처:** *Tourism Management*, https://www.sciencedirect.com/science/article/abs/pii/S027843192400207X
- **요약:**  
  - 공간(경쟁 호텔 군집) + 시간(날씨·이벤트) 멀티스케일 피처 결합  
  - 도시 호텔은 날씨보다 이벤트·가격 피처가 지배적  
  - 리조트 호텔은 날씨(특히 일조량·기온) 피처가 상대적으로 중요

### [W3] Forecasting resort hotel tourism demand using deep learning — systematic literature review (2023).
- **출처:** *PMC / NCBI*, https://pmc.ncbi.nlm.nih.gov/articles/PMC10375847/
- **요약:**  
  - 리조트 호텔 수요 예측 연구 40편 메타분석  
  - 날씨 데이터를 독립 피처로 포함한 연구: 전체의 약 30%, 성능 향상 일관적이지 않음  
  - **날씨 ablation 실험의 필요성을 지지하는 근거** (우리 미결항목 #9)  
  - 도착일 단일 날씨 vs 체류기간 전체 날씨: 후자가 리조트에서 더 유효한 경향

### [W4] Open-Meteo Historical Weather API
- **출처:** https://open-meteo.com/en/features
- **요약:**  
  - 80년치 시간 단위 날씨, 전 지구 10km 해상도  
  - 무료·무인증 API — 우리 데이터 수집에 실제 사용  
  - 제공 변수: `temperature_2m_max`, `temperature_2m_min`, `precipitation_sum`,  
    `rain_sum`, `precipitation_hours`, `wind_speed_10m_max`, `wind_speed_10m_mean` 포함

---

## 7. 요약 비교표

| ID | 논문 | 연도 | 데이터 | 주요 모델 | 지표 | 날씨 | 해석성 |
|----|------|------|--------|-----------|------|------|--------|
| D1 | Antonio et al. — Dataset | 2019 | H1+H2 (동일) | — | — | ✗ | — |
| P1 | Antonio et al. — Big Data Rev. Mgmt | 2019 | H1+H2 (동일) | LR/RF/XGB | AUC 0.95+ | ✗ | 피처 중요도 |
| P2 | ML & Big Data (IJHM) | 2020 | H1+H2 (동일) | RF/XGB/NN | AUC 0.95 | ✗ | 피처 중요도 |
| P3 | DSS Feature Interaction | 2023 | H1+H2 (동일) | XGB/RF 등 7종 | AUC 0.9553 | ✗ | SHAP + 상호작용 |
| P4 | JRPM Comprehensive | 2025 | H1+H2 (동일) | LGBM/XGB/ANN | PR-AUC 언급 | ✗ | 피처 중요도 |
| P5 | Adaptive ML (ITT) | 2025 | H1+H2 (동일) | XGB 슬라이딩 | AUC | ✗ | SHAP 시계열 |
| P6 | Profit-driven EJOR | 2024 | H1+H2 (동일) | 스태킹 앙상블 | 이익 기반 | ✗ | SHAP |
| I1 | Dynamic ML SAGE | 2025 | 유럽 호텔들 | XGB 동적 | MAE | ✗ | SHAP 체제별 |
| I2 | Two-stage DSS | 2025 | H1+H2 (동일) | 2단계 모델 | AUC + 시점 | ✗ | SHAP |
| S1 | AutoML DSS (Antonio) | 2019 | PMS 실데이터 | AutoML | Acc 84% AUC 88% | ✗ | — |
| S3 | Expert Systems (Wiley) | 2024 | H1+H2 (동일) | RF/XGB | AUC 0.87+ | ✗ | 타임라인 |
| O1 | Overbooking+Alloc CIE | 2019 | 시뮬레이션 | MIP | RevPAR +6% | ✗ | — |
| O2 | Stochastic Rev. Opt | 2004 | 이론 | 확률 모델 | 기대 수익 | ✗ | — |
| O3 | Optimal Overbooking | 2015 | 이론 | 이항/포아송 | Walk rate | ✗ | — |
| W1 | iTransformer Tourism | 2024 | 일별 관광 | Transformer | MAPE | ✓ | 피처 그룹 |
| W2 | Spatiotemporal (TM) | 2024 | 다국 호텔 | CNN+LSTM | RMSE | ✓ | 공간+시간 |
| W3 | Resort SLR (PMC) | 2023 | 메타분석 | 다수 | 다양 | ✓ (30%) | — |

---

## 8. 우리 프로젝트 포지셔닝

### 선행연구와의 차별점

| 측면 | 대부분의 선행연구 | 우리 프로젝트 |
|------|-----------------|--------------|
| 날씨 데이터 | 없음 (P1~P6 전부 미포함) | Open-Meteo API로 호텔 위치·도착일 기준 7개 변수 추가 |
| 목표 | 취소 예측 정확도 최대화 | 취소 예측 → **운영 의사결정 지원** (우선순위 리스트 + Flexi 라우팅) |
| 임계값 | 0.5 기본값 또는 F1 최대화 | **비용 비대칭 반영** — 빈 방 손실 vs 워크 비용 비율로 최적화 (미결 #4) |
| 오버부킹 | 예측 모델만 (O1~O4는 별도 이론) | **예측 + Flexi 풀 라우팅으로 오버부킹 없이 수익 확보** |
| 해석성 | SHAP 후처리 | **SHAP → 가정 수정 → 재실험** 반복 루프를 설계 철학으로 명시 |
| 일반화 | 타 호텔 이전 가능성 주장 | **명시적으로 이 데이터셋에서의 유효성 확인으로 범위 한정** |

### 발표 시 인용 권장 순서

1. **데이터 출처 정당화**: [D1] Antonio et al. (2019) Data in Brief
2. **모델 선택 근거**: [P2] IJHM (2020) — XGBoost/RF 우위 / [P4] JRPM (2025) — PR-AUC 언급
3. **SHAP 선택 근거**: [P3] DSS (2023) — 해석 가능성 통합 / [I1] SAGE (2025) — SHAP 동적 추적
4. **DSS 아키텍처**: [S1] Antonio et al. DSS (2019) — 직접 선행연구
5. **오버부킹·Flexi 수리적 근거**: [O2] Stochastic (2004) / [O3] Optimal Overbooking (2015)
6. **날씨 변수 정당화**: [W3] Resort SLR (2023) — 일부 유효 / [W2] Spatiotemporal (2024) — 리조트에서 상대적 중요성
7. **날씨 ablation 필요성**: [W3] 메타분석 결과 일관성 부족 → Phase 2 실험 정당화

---

*참조 링크 전체 목록*

- [D1] https://www.sciencedirect.com/science/article/pii/S2352340918315191
- [P1] https://journals.sagepub.com/doi/abs/10.1177/1938965519851466
- [P2] https://www.sciencedirect.com/science/article/abs/pii/S0278431920300980
- [P3] https://www.sciencedirect.com/science/article/abs/pii/S0167923623000349
- [P4] https://link.springer.com/article/10.1057/s41272-025-00532-x
- [P5] https://link.springer.com/article/10.1007/s40558-025-00349-9
- [P6] https://www.sciencedirect.com/science/article/abs/pii/S0377221724006696
- [P7] https://arxiv.org/abs/2410.16406
- [P8] https://pmc.ncbi.nlm.nih.gov/articles/PMC11623061/
- [I1] https://journals.sagepub.com/doi/10.1177/13548166251318768
- [I2] https://www.sciencedirect.com/science/article/abs/pii/S0169023X2500062X
- [S1] https://datascience.codata.org/articles/10.5334/dsj-2019-032
- [S2] https://link.springer.com/chapter/10.1007/978-3-031-78471-2_6
- [S3] https://onlinelibrary.wiley.com/doi/10.1111/exsy.13608
- [O1] https://www.sciencedirect.com/science/article/abs/pii/S0360835219305327
- [O2] https://www.sciencedirect.com/science/article/abs/pii/S0305054803003009
- [O3] https://sysmath.cjoe.ac.cn/jweb_xtkxysx/EN/10.12341/jssms11713
- [O4] https://www.mdpi.com/2227-7090/9/13/1552
- [W1] https://www.mdpi.com/2071-1050/16/23/10678
- [W2] https://www.sciencedirect.com/science/article/abs/pii/S027843192400207X
- [W3] https://pmc.ncbi.nlm.nih.gov/articles/PMC10375847/
- [W4] https://open-meteo.com/en/features
