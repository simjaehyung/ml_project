# Week 2 리뷰 — PM 평가 문서

> 작성: 심재형 (PM) | 기준일: 2026-05-11
> 대상 기간: 2026-05-05 ~ 2026-05-11
> 다음 주: Week 3 (5/12~5/18) — XGBoost + LightGBM → 모델 동결

---

## 1. 목표 vs 실제 달성

| # | 계획 목표 | 담당 | 상태 | 비고 |
|---|---------|------|------|------|
| 1 | 전처리 파이프라인 완성 | 심재형 | ✅ 완료 | `src/preprocessing_pipeline.py` |
| 2 | Dummy Classifier baseline | 심재형 | ✅ 완료 | PR-AUC 0.3870 확정 |
| 3 | LR baseline (PR-AUC 산출) | 김나리 | ⚠️ 결과 있음 | PR-AUC 0.8084, F1 0.7113 — 파이프라인 불일치 |
| 4 | RF baseline (PR-AUC 산출) | 김나리 | ⚠️ 결과 있음 | PR-AUC 0.8143, F1 0.6456 — 파이프라인 불일치 |
| 5 | PR curve 3종 통합 그래프 | 심재형 | ✅ 완료 | `results/pr_curve_baseline.png` — 정식 파이프라인 기준 (0.39→0.78 수준) |
| 6 | MVP 가정 확정 문서 | PM | ✅ 완료 | 3개 항목 전부 확정 |
| 7 | Streamlit 학습 + 앱 골격 | 이고은 | ✅ 완료 | 4패턴 + 탭 구조 구현 |
| 8 | previous_cancellations EDA | 이고은 | ✅ 완료 | 커밋 e7b4be1 — B2B 블록 패턴 확인 (94.97% 취소, 5,520건) |
| 9 | precipitation 상관 확인 | 김나리 | ✅ 완료 | 상관 0.824 (< 0.9) — 미결 #2 해소 |
| 10 | 대시보드 와이어프레임 | 이고은 | ✅ 완료 | 커밋 f725d4f — 탭1·탭2 UI 전체 설계 (209줄) |

**완료율: 9/10 (90%)** — 미완료는 #3·#4(LR·RF) 파이프라인 불일치뿐. 정식 수치는 `run_baselines.py` 기준으로 확정됨.

---

## 2. 팀원별 상세

### 심재형

| 항목 | 결과 |
|------|------|
| 전처리 파이프라인 | ✅ 33컬럼 → OHE 전 기준. train/test_processed 생성. NaN 0건 |
| Dummy baseline | ✅ PR-AUC 0.3870. 기준선 확정 |
| deposit_type 이슈 발견 | ✅ Non Refund 취소율 99.2% 발견 → 가설 A 채택 후 DROP 확정 |
| 설계 문서 | ✅ design_04, design_05, design_06, SCHEDULE, CLAUDE.md 업데이트 |

**이슈:** deposit_type 결정이 문서 간 불일치 (아래 섹션 4 참조).

---

### 이고은

| 항목 | 결과 |
|------|------|
| Streamlit 4패턴 실습 | ✅ `dashboard/streamlit_practice.py` — 탭1/탭2 구조, 할인율 공식 구현, `@st.cache_data` 적용 |
| previous_cancellations EDA | ✅ 커밋 e7b4be1 — B2B 블록 패턴 독립 검증 (아래 상세) |
| 대시보드 와이어프레임 | ✅ 커밋 f725d4f — 탭1·탭2 전체 UI 설계 (`docs/wireframe_dashboard.md`, 209줄) |

**Streamlit 상세 평가:**

잘 된 부분:
- 탭1/탭2 구조 완성, UI 흐름 파악 정확
- 할인율 공식(`5% + (위험 - 0.5) × 26%`)을 PM 문서에서 직접 읽고 정확하게 구현
- `@st.cache_data` 같은 최적화를 스스로 적용
- 주석에 "Week 4에서 fake_risk 자리에 모델 예측값 들어감" 명시 — 이후 작업 흐름 파악하고 있음

예정된 한계 (Week 4에서 해결):
- 취소 위험 78%는 하드코딩 더미값. Week 4에서 모델 예측값으로 교체.
- 탭1 데이터가 전처리 전 원본. STEP 2에서 processed 데이터로 교체 필요.

**previous_cancellations EDA 상세 (커밋 e7b4be1, `src/03_prev_cancel_eda.py`):**

| 구분 | 값 |
|------|-----|
| previous_cancellations ≥ 1 그룹 취소율 | **2015: 98.96% / 2016: 84.98% / 전체: 94.97%** |
| previous_cancellations = 0 그룹 취소율 | 전체 33.91% |
| 정의 불일치 건수 | **5,520건** — previous_cancellations ≥ 1이면서 취소 기록 없음 |
| B2B 패턴 일치율 | 5,520건의 89%가 Groups + Offline TA/TO |
| 평균 lead_time (이상 그룹) | 217일 (B2B allotment 블록 발주 주기와 일치) |

→ deposit_type Non Refund B2B 패턴을 previous_cancellations에서 **독립적으로 재확인**. 동일 B2B 거래가 두 컬럼에 모두 신호를 남기고 있음. Week 4 SHAP에서 두 변수 동시 독식 여부 감시 필요.

**위상 2 ablation 설계 (이고은 제안):**
1. deposit_type만 제거 (현재 상태)
2. previous_cancellations만 제거
3. 둘 다 제거
→ Phase 2 Week 5 실험 우선순위 상향 확정.

**대시보드 와이어프레임 상세 (커밋 f725d4f, `docs/wireframe_dashboard.md`):**

| 탭 | 구성 요소 |
|----|---------|
| 탭1 (예약 우선순위) | 필터 패널 (날짜·호텔·위험등급) + KPI 3종 + 위험도 정렬 테이블 + 상세 expander (SHAP Top 3) |
| 탭2 (Flexi 라우팅) | 신규 예약 입력 폼 + 취소 확률 출력 + 스토리 생성기 + SHAP waterfall + 매니저 승인 단계 (GDPR) |

데이터 의존성 표 + 컴포넌트별 선행 조건 + Week 3 미결 5항목 포함. Week 4 연동 시 그대로 사용 가능한 수준.

**평가:** Streamlit 구조 파악 + PM 문서 정확한 이해 + EDA에서 B2B 패턴 독립 재확인 + 와이어프레임 완성까지 — 이번 주 기대치를 크게 초과한 산출물. Week 3 탭1 연동 시작에 막힘이 없을 것으로 예상.

---

### 김나리

| 항목 | 결과 |
|------|------|
| LR baseline | ⚠️ 완료 — PR-AUC 0.8084, F1 0.7113. 파이프라인 불일치 (아래 상세) |
| RF baseline | ⚠️ 완료 — PR-AUC 0.8143, F1 0.6456. 동일 파이프라인 불일치 |
| precipitation 상관 확인 | ✅ 완료 — 0.824 (0.9 미만, 미결 #2 해소) |

**파이프라인 불일치 상세 (실제 코드 확인 완료):**

실제 제출 코드의 핵심 문제는 `select_dtypes(include=["object"])`로 cat_cols를 자동 탐지한 것이다.
`train_processed.csv`가 아닌 `train.csv` (전처리 전 원본)를 썼기 때문에 이 방식으로 잡힌 컬럼들이 모두 오염됐다.

```
실제 코드가 쓴 입력: train.csv / test.csv  (38컬럼)
실제 코드가 잡은 cat_cols (자동 탐지):
  ['hotel', 'arrival_date_month', 'meal', 'country', 'market_segment',
   'distribution_channel', 'reserved_room_type', 'deposit_type', 'customer_type']
OHE 후 컬럼 수: 235개

올바른 파이프라인:
  입력: train_processed.csv (33컬럼)
  cat_cols: deposit_type 제외, country→country_grouped (Top10+Other)
  arrival_date_month: 이미 int 1~12로 변환됨 → OHE 불필요
  OHE 후 컬럼 수: 70개
```

| 항목 | 김나리 코드 | 올바른 파이프라인 | 영향 |
|------|-----------|----------------|------|
| 입력 파일 | `train.csv` (38컬럼) | `train_processed.csv` (33컬럼) | deposit_type 등 미제거 |
| `deposit_type` | OHE 포함 (신호 오염) | DROP | PR-AUC ~0.03 과대추정 |
| `country` | 전체 177국 OHE | `country_grouped` Top10+Other (11개) | 컬럼 폭발 |
| `arrival_date_month` | 문자열 OHE (12컬럼 생성) | 이미 int 1~12 → OHE 안 함 | 중복 |
| OHE 후 컬럼 수 | **235개** | **70개** | — |

모델 설정 자체(C=1, max_iter=1000, StandardScaler, n_estimators=100, random_state=42)는 계획과 정확히 일치. 코드 구조도 깔끔하고 재현 가능. 파이프라인 진입점(입력 파일)만 잘못됐다.

**평가:** 코드 품질과 구조는 좋음. `train_processed.csv`로 입력 파일만 바꾸면 Week 3 LightGBM은 바로 올바른 파이프라인으로 실행 가능. Week 3 가이드에 수정 공지 완료됐으니 별도 안내 불필요.

---

## 3. 실제 결과 (수치)

### Baseline 현황

| 모델 | PR-AUC | F1@0.5 | 상태 |
|------|--------|--------|------|
| Dummy (most_frequent) | **0.3870** | 0.0000 | ✅ 완료 |
| Logistic Regression | 0.8084 (노션) → **0.7818** (정식) | 0.7073 | ✅ deposit_type 제외 재실행 완료 |
| Random Forest | 0.8143 (노션) → **0.7785** (정식) | 0.6454 | ✅ deposit_type 제외 재실행 완료 |

- Dummy PR-AUC 0.3870 = 테스트셋 취소율 38.7%와 일치 (이론적으로 정확한 값)
- **실질 기준선: 어떤 모델이든 PR-AUC > 0.39 이상이어야 의미 있음**
- LR·RF 모두 Dummy 대비 큰 폭 개선 (0.39 → 0.78 수준)
- 노션 수치(0.81) vs 정식 파이프라인 수치(0.78) — **약 0.03 차이가 deposit_type 기여분**
- LR PR-AUC(0.7818) > RF PR-AUC(0.7785) — deposit_type 제거 후 트리 모델 이점 희미해짐
- RF F1@0.5(0.6454) < LR F1@0.5(0.7073) — 0.5 임계값 기준 LR 우위 패턴 유지

**정식 파이프라인 기준 (deposit_type DROP + country Top10+Other):**
`src/run_baselines.py` → `results/pr_curve_baseline.png` + `results/baseline_results.md` 갱신 완료.

### 전처리 파이프라인 결과

```
train_processed: 78,703행 × 33컬럼  취소율 36.6%  NaN 0건
test_processed:  40,687행 × 33컬럼  취소율 38.7%  NaN 0건

제거 컬럼 (preprocessing_pipeline.py 기준):
  날씨 3개: temperature_2m_mean, wind_speed_10m_mean, rain_sum
  deposit_type: DROP 확정 (Non Refund 99.2% 취소율 — B2B allotment 패턴 또는 사후 기록 오염)
  arrival_date: time_split 임시 컬럼

country_grouped Top10: PRT, GBR, FRA, ESP, DEU, ITA, IRL, BEL, NLD, BRA + Other
```

### EDA 핵심 발견 (eda.ipynb)

| 변수 | 발견 | 활용 |
|------|------|------|
| lead_time | 취소 예약 평균 lead_time이 정상보다 훨씬 길다 | Week 3 SHAP 확인 예상 |
| deposit_type | Non Refund 취소율 99.2% — B2B allotment 패턴 | DROP 확정 |
| previous_cancellations | 이력 있음 그룹 취소율 91.64% vs 없음 33.91% | SHAP에서 상위 예상 |
| market_segment | Online TA / Groups 취소율 높음 | SHAP 확인 필요 |
| **날씨 시간 비대칭성** | lead_time ≤ 30일에서만 강수량 ↑ → 취소율 ↑. lead_time > 90일은 무상관 | 발표 슬라이드 핵심 근거 |

### 기타 전처리 발견

| 항목 | 건수 | 발견 | MVP 처리 |
|------|------|------|---------|
| `adr = 0` | 1,504건 (2%) | 평균 요금 0원. 원인 불명 | 그냥 둔다 — 트리 모델에서 이상값 자체가 신호가 될 수 있음 |
| `adults = 0` | 273건 (0.3%) | 어른 없는 예약. 어린이·유아만 있거나 데이터 오류 | 그냥 둔다 — 건수 적고 제거 시 오히려 편향 |
| `meal = "Undefined"` | 756건 | "SC"(식사 없음)와 의미가 같을 가능성 높음 | SC로 통합 예정 — 파이프라인에 한 줄 추가 (Week 3 내) |

---

## 4. 주요 이슈 — deposit_type 결정 불일치

Week 2에서 가장 중요한 발견이면서 동시에 문서 정합성이 깨진 항목.

### 발견 내용

전처리 중 확인된 수치:

```
deposit_type = "No Deposit"  → 취소율 26.6%  (68,000건)  ← 정상
deposit_type = "Non Refund"  → 취소율 99.2%  (10,461건)  ← 이상
deposit_type = "Refundable"  → 취소율  7.4%  (135건)
```

"Non Refund"는 환불 불가 요금제다. 환불도 못 받는데 99.2%가 취소한다는 것이 경제적으로 말이 안 되어 두 가지 가설을 검토했다.

### 가설 분석

**가설 A — B2B 여행사 allotment 계약 (채택)**

Non Refund의 61%가 Groups(단체), 37%가 Offline TA/TO(오프라인 여행사).

호텔-여행사 간 B2B allotment 계약에서 `Non Refund`는 요금제 유형을 나타낼 뿐이다. 개인 예약의 "환불불가(보증금 몰취)"와는 다르다. B2B 계약에는 통상 release date 조항이 있어, 그 이전에 블록을 반납하면 패널티 없이 취소 가능하다. 즉, 여행사는 돈을 잃는 게 아니라 미판매 블록을 반납하는 것이다.

→ 99.2% 취소율이 경제적으로 성립하는 이유가 여기에 있다.

**가설 B — 사후 기록 오염 (배제하지 않음)**

취소 이후 시스템이 deposit_type을 "Non Refund"로 업데이트. 타임스탬프가 없어 완전히 배제할 수 없지만, 가설 A가 경제 논리상 더 설득력 있음.

**왜 구분 못 하나:** 이 데이터셋에 deposit_type이 언제 기록됐는지 타임스탬프가 없다. 원본 논문(Antonio et al. 2019)도 이 부분을 명시하지 않는다.

**모델에서 쓰면 어떻게 되나:** 트리 모델은 패턴을 매우 잘 잡는다. "Non Refund → 취소" 신호가 너무 강해서 모델이 이 컬럼 하나에 과도하게 의존할 가능성이 높다. Week 3 SHAP에서 deposit_type이 맨 위에 있을 것이 예상된다.

### 타임라인

| 시점 | 내용 |
|------|------|
| 2026-05-07 | Non Refund 취소율 99.2% 발견. 가설 A(B2B allotment) 채택 |
| week2_feedback.md | **"KEEP (2026-05-08 확정) — 가설 A 인지 하에 포함"** 으로 기록 (이후 번복) |
| preprocessing_pipeline.py | **DROP** 처리 (코드 기준) |
| CLAUDE.md | **DROP 확정** (6번째 컬럼으로 명시) |

### 현재 불일치

| 문서 | deposit_type 결정 |
|------|-----------------|
| `week2_feedback.md` | KEEP (2026-05-08) ← **오래된 기록, 삭제됨** |
| `design_04_preprocessing_decisions.md` | OHE (감시 중) ← **업데이트 필요** |
| `preprocessing_pipeline.py` | **DROP** ← 실제 코드 |
| `CLAUDE.md` | **DROP 확정** ← 최신 의사결정 |

**결론:** 코드와 CLAUDE.md 기준 DROP이 최종 결정. design_04는 업데이트 필요 (Week 3 내).

### DROP 근거 (발표 방어용)

- Non Refund의 61% = Groups, 37% = Offline TA/TO → B2B allotment 계약 블록 반납 패턴
- 개인 예약의 "환불불가 취소"가 아님 — 여행사는 release date 이전 블록 반납 시 패널티 없음
- 타임스탬프 없어 사후 기록 오염(가설 B) 완전 배제 불가
- Week 3 SHAP: deposit_type 독식 여부 모니터링 → Phase 2 ablation 실험

---

## 5. MVP 가정 — 최종 확정 상태

| 항목 | 결정 | 상태 |
|------|------|------|
| 날씨 윈도우 | 도착일 하루만 (Phase 2에서 체류기간 전체 실험) | ✅ 확정 |
| `previous_cancellations` | 포함 (Phase 2 Week 5에서 ablation) | ✅ 확정 |
| `country` 처리 | Top10 + "Other" OHE (Phase 2에서 SHAP 보고 재설계) | ✅ 확정 |

---

## 6. Week 3 진입 전 해소 필요 항목

### 긴급 (Week 3 시작 전)

| # | 항목 | 담당 | 기한 | 이유 |
|---|------|------|------|------|
| A | **LR baseline PR-AUC 산출** | 김나리 | ✅ 완료 | 정식: 0.7818 (`src/run_baselines.py`) |
| B | **RF baseline PR-AUC 산출** | 이고은 | ✅ 완료 | 정식: 0.7785 (`src/run_baselines.py`) |
| C | previous_cancellations EDA 완료 보고 | 이고은 | ✅ 완료 | 커밋 e7b4be1, B2B 블록 패턴 확인 |

### Week 3 초반 처리

| # | 항목 | 담당 | 기한 |
|---|------|------|------|
| D | precipitation_sum vs precipitation_hours 상관 수치 확인 | 김나리 | ✅ 완료 (0.824) |
| E | design_04 deposit_type 섹션 업데이트 | 심재형 | ✅ 완료 |
| F | meal "Undefined" → "SC" 통합 파이프라인 반영 | 심재형 | ✅ 완료 |

---

## 7. Week 3 목표 (확인)

| STEP | 항목 | 담당 |
|------|------|------|
| 0 | LR + RF 결과 통합 (Week 2 이월) | 김나리 + 이고은 |
| 1 | XGBoost 학습 + PR-AUC | 심재형 |
| 1 | LightGBM 학습 + PR-AUC | 김나리 |
| 2 | 전체 PR curve 5종 비교표 | 심재형 |
| 2 | 모델 확정 기준 합의 → 최종 모델 1개 선정 (5/18 Gate) | PM |
| 3 | 모델 출력 인터페이스 확정 → 이고은에게 전달 | 심재형 |

**Gate:** 5/18(월)까지 모델 동결. 이후 피처·모델 변경 금지.

---

## 8. PM 총평

**심재형:** 계획 대비 100% 이상 완료. deposit_type 이슈를 발견·가설 검토·DROP 결정까지 혼자 처리했고, 정식 파이프라인(`run_baselines.py`)으로 baseline 3종 수치를 재확정했다. 발표에서 쓸 수 있는 서사가 여기서 나왔다. 문서 정합성(design_04, CLAUDE.md, week3_plan) 전부 이번 주에 정리됐다.

**이고은:** 이번 주 가장 많은 산출물을 낸 팀원. Streamlit 골격 + previous_cancellations EDA + 대시보드 와이어프레임 세 가지가 모두 커밋으로 확인됐다. EDA에서 previous_cancellations의 B2B 패턴(89% Groups+Offline, lead_time 217일)을 독립적으로 재확인한 것은 deposit_type 결정을 사후 검증한 것과 같다. 와이어프레임은 탭1·탭2 전체 UI 설계를 포함하며 Week 4 연동에 바로 쓸 수 있는 수준. 이번 주 기대치를 크게 초과했다. Week 3에는 탭1 연동에 집중하면 된다.

**김나리:** LR·RF baseline 두 개 모두 완료 확인 (이번 주 공유된 ipynb 두 개로 확인). precipitation 상관 수치(0.824)도 확인됐다. 단, 입력 파일이 `train.csv`(38컬럼)였고 `select_dtypes`로 자동 탐지된 cat_cols에 deposit_type·전체 country·문자열 arrival_date_month가 포함돼 OHE 235컬럼이 나왔다. PR-AUC 0.03 과대추정의 원인. 코드 구조 자체는 깔끔하고 재현 가능 — 입력 파일만 `train_processed.csv`로 바꾸면 Week 3 LightGBM은 올바른 파이프라인으로 바로 시작할 수 있다. Week 3 가이드에 수정 공지 완료.

**전체:** 완료율 9/10. 파이프라인 불일치로 노션 수치(0.81)와 정식 수치(0.78) 사이에 0.03 갭이 있었지만 원인이 명확히 규명됐고 정식 수치로 baseline이 확정됐다. Week 3 진입 조건 전부 충족.
