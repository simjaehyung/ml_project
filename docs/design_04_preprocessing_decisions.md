# 전처리 결정 기록 — Hotel No-Show DSS

> 작성 기준일: 2026-05-08  
> 목적: 전처리 과정에서 고민했던 모든 항목의 흔적과 최종 결정을 한 곳에 정리.  
> 근거 문서: `docs/leakage_candidates.md`, `docs/weather_data_design.md`, `docs/week2_feedback.md`, `VALIDATION_LOG.md`

---

## 0. 데이터 흐름 요약

```
hotel_bookings.csv (Kaggle, 119,390 × 32)
          + weather_data.csv (Open-Meteo API, 7개 변수)
          ↓ Left Join (hotel + arrival_date 기준, 매칭률 100%)
bookings_weather.csv (119,390 × 43)
          ↓ 확정 누수 2개 DROP + PM 추가 결정 3개 DROP + agent/company 인디케이터 변환
bookings_weather_pm.csv (119,390 × 38)   ← Week 2 EDA 시작점
          ↓ preprocessing_pipeline.py
          ↓ 날씨 3개 DROP / deposit_type DROP / country 그룹핑 / children NaN→0 / meal Undefined→SC / month 숫자화 / arrival_date 제거
train_processed.csv (78,703 × 33)
test_processed.csv  (40,687 × 33)
```

**최종 컬럼 수 변화:** 32 → 43 → 38 → 33

---

## 1. 시간 기반 Train/Test Split

### 결정

| 항목 | 내용 |
|------|------|
| 전체 기간 | 2015-07 ~ 2017-08 (26개월) |
| Train | 2015-07 ~ 2017-02 → **78,703행** |
| Test | 2017-03 ~ 2017-08 (마지막 6개월) → **40,687행** |
| Train 취소율 | 36.6% |
| Test 취소율 | 38.7% |

### 왜 무작위 분할을 안 했나

운영 환경에서는 항상 과거로 학습해 미래를 예측한다. 무작위 분할을 하면 학습 데이터에 미래 정보가 섞여 성능이 과대평가된다.

예: 2017년 1월에 취소한 손님의 이력이 그 손님의 2016년 12월 예약 행을 설명하는 feature로 학습에 쓰이는 상황.

### 인정하는 한계

테스트셋이 여름 성수기(6~8월)에 편중되어 있다. 성수기 특성이 과대 반영될 수 있어, Phase 2에서 월별 성능 분리 분석으로 보완 예정.

---

## 2. 누수 컬럼 결정 — 전체 32개 검토

### 판정 원칙

**"손님이 예약 버튼을 누른 그 순간에, 이 값이 이미 확정되어 있는가?"**

확정되지 않거나 이후에 갱신될 수 있다면 누수 또는 보류.

---

### 2-1. 확정 DROP (2개) — 타깃과 동치 또는 100% 미래 정보

#### `reservation_status`

- **이유:** 값이 `Check-Out` / `Canceled` / `No-Show` 셋뿐. `Check-Out ↔ is_canceled=0`, `Canceled/No-Show ↔ is_canceled=1` 로 정의상 100% 동치.
- **검증:** `pd.crosstab(df.is_canceled, df.reservation_status)` 비대각 셀 0건 확인 (2026-05-03).
- **결정:** 즉시 DROP.

#### `reservation_status_date`

- **이유:** "마지막 예약 상태가 갱신된 날짜" → 정상건은 체크아웃 일자, 취소건은 취소 처리일. 어느 쪽이든 예약 시점엔 알 수 없는 미래값.
- **검증:** `(reservation_status_date - arrival_date).dt.days` — 정상건 100%가 도착일 이후(+3일 중앙값). 취소건 95.28%는 도착 전 (취소 신청일), 4.72%는 도착 후 (노쇼 사후 처리 추정).
- **결정:** 즉시 DROP.

---

### 2-2. PM 판단 DROP (3개) — 검증 후 결정

#### `assigned_room_type`

- **고민:** 정의상 "체크인 시점 배정"이지만, 취소건에도 값이 채워져 있어서 예약 시점 정보 아닌가?
- **검증 결과 [Y1]:**

| 그룹 | 불일치율 (reserved ≠ assigned) |
|------|-------------------------------|
| 정상 체크인 | **18.78%** |
| 취소·노쇼 | **1.81%** |

→ 취소건은 사실상 reserved=assigned 디폴트로 채워진 것 (체크인 자체가 안 일어났으니 배정도 없음). 정상건만 체크인 시 다른 방으로 배정 → **시점 갱신값 = 누수.**

- **고민했던 대안 (c):** `room_changed = (reserved ≠ assigned)` 파생 변수 → 정상건에서만 의미 있어 타깃 종속(가설 주입 순환 함정)으로 사전 배제.
- **최종 결정:** `assigned_room_type` DROP. `reserved_room_type`만 모델 입력으로 사용 (예약 시점 확정값).

---

#### `previous_bookings_not_canceled`

- **고민:** 과거 정상 예약 이력 → 예약 시점에 알 수 있는 정보 아닌가?
- **검증 결과 [Y3]:** `is_repeated_guest=1`인 3,810명 중 25.51%가 이 컬럼 값 0. 재방문 손님인데 정상 예약 이력이 없다는 건 정의 모순.
- **추가 고민:** 신호는 강하다 (≥1 그룹 취소율 5.52% vs =0 그룹 38.03%). 근데 정의가 어긋난 컬럼을 신뢰할 수 있나?
- **최종 결정:** 정합성 모순으로 신호 신뢰도 낮음 → DROP.

---

#### `days_in_waiting_list`

- **고민:** "대기자 명단에 있던 일수"인데, 언제 확정되는가? 예약 시 0이었다가 대기 해제 시 갱신되는 변수라면 미래 정보.
- **추가 문제:** 사전 통계상 대부분 0 (정보량 낮음). 타인 취소로 대기 해제되는 구조에서는 타인의 취소 결과가 간접 반영됨.
- **검증:** 타임스탬프 없어 직접 검증 불가. 보수적 판단.
- **최종 결정:** 확정 시점 모호 + 정보량 낮음 + 간접 누수 위험 → DROP.

---

### 2-3. 조건부 KEEP (1개) — 논란 끝에 유지

#### `previous_cancellations`

- **고민:** 손님 ID 컬럼 없어 행 단위 시간 누수 검증 불가. 대리키로 검증하자는 AI 제안도 있었으나, 대리키 자체가 추가 가정이라 가설 주입 함정으로 폐기 (VALIDATION_LOG #8).
- **신호 강도:** ≥1 그룹 취소율 **91.64%** vs =0 그룹 33.91% (차이 57.7%p). 가장 강한 예측 신호 중 하나.
- **비직관적 발견:** 연도별로 감소 추세. 하지만 논리적 모순은 없음.
- **또 다른 발견 (VALIDATION_LOG #8):** `is_repeated_guest=0`인데 `previous_cancellations≥1`인 행 약 2,674개 존재 → 두 컬럼 정의가 어긋남. Week 2 EDA 재검증 안건.
- **최종 결정:** 논리적 모순 없고 신호 강도 높음 → KEEP. Phase 2(Week 5)에서 제거 ablation 실험 예약. 미결 항목 #6.

---

### 2-4. 인디케이터 변환 KEEP (2개) — 결측 자체가 신호

#### `agent`

- **고민:** 결측률 13.69%. 단순 drop하면 "에이전시 미경유 직접 예약"이라는 정보도 같이 버리게 됨.
- **검증:** 결측 행 취소율 24.66% / 비결측 39.00% (차이 −14.34%p). 결측 자체가 강한 신호.
- **최종 결정:** 0/1 인디케이터 변환 (결측 → 0, 비결측 → 1). 에이전시 ID는 카디널리티가 높아 버림.

#### `company`

- **고민:** 결측률 94.31%. 비결측 6,797건만이 법인 예약이고 이 그룹은 취소율이 다름.
- **검증:** 결측 취소율 38.22% / 비결측 17.52% (차이 +20.70%p). 결측 자체가 강한 역신호.
- **최종 결정:** 0/1 인디케이터 변환 (결측 → 0, 비결측 → 1).

---

### 2-5. 보류 후 KEEP — 추론 시점 문제

#### `booking_changes`

- **고민:** "예약 후 변경 횟수"는 예약 시점엔 항상 0. 시간이 지나면서 누적되는 값.
- **검증 결과 [Y2]:** 변경 있음(≥1) 취소율 15.67% vs 변경 없음 40.85% (차이 25%p). 매우 강한 신호.
- **핵심 딜레마:** 이게 누수인지 헌신도(commitment) 신호인지 데이터만으로는 판단 불가. 추론 시점에 따라 달라짐:
  - 예약 직후 예측 → `booking_changes=0`뿐 → 사용 불가
  - 도착 직전 예측 → 그 시점까지 누적값 → 사용 가능
- **최종 결정:** 우리는 **도착 직전(체크인 임박)** 시나리오로 추론 → KEEP. 시나리오 명시가 핵심.

---

### 2-6. ❌ DROP 확정 (deposit_type)

#### `deposit_type` — Non Refund 취소율 99.2%

- **발견 시점:** 2026-05-07 전처리 파이프라인 실행 중.
- **현상:**

| deposit_type | 취소율 | 건수 |
|-------------|--------|------|
| No Deposit | 26.6% | ~68,000 |
| Non Refund | **99.2%** | 10,461 |
| Refundable | 7.4% | 135 |

- **가설 A (채택):** B2B 여행사 블록 계약 운영 방식.
  - Non Refund의 61%가 Groups, 37%가 Offline TA/TO.
  - 호텔-여행사 간 allotment 계약에서 `Non Refund`는 **요금제 유형**을 나타낼 뿐, release date 이전 블록 반납은 패널티 없이 취소 가능한 구조가 일반적.
  - 개인 예약의 "환불불가(보증금 몰취)"와 달리, 여행사의 "Non Refund 취소"는 실제 재정 손실 없는 블록 반납일 가능성이 높음.
  - 99.2% 취소율이 경제적으로 성립하는 이유: 여행사는 돈을 잃는 게 아니라 미판매 블록을 반납하는 것.
- **가설 B:** 사후 기록 오염. 취소 이후 시스템이 deposit_type을 "Non Refund"로 업데이트 → 미래 정보가 역으로 섞임. (배제하지 않지만, 가설 A로 운영)
- **판단 불가 이유:** 데이터에 타임스탬프 없음. 원본 논문(Antonio et al. 2019)도 명시 안 함.
- **최종 결정 (2026-05-08): DROP.** 어느 가설이 맞든 A/B 구분이 불가한 상태에서 모델에 포함하면 "B2B 블록 반납 = 취소" 신호가 과도하게 학습됨. 제거가 더 방어 가능한 선택. `preprocessing_pipeline.py`에 반영 완료.
- **발표 방어:** "Non Refund 99.2%는 B2B allotment 패턴 또는 사후 기록 오염 — 둘 다 모델 오염 위험이 있어 DROP"
- **Phase 2(Week 5):** deposit_type 포함 vs 제외 ablation 실험으로 기여분 정량화 예정.

---

## 3. 날씨 변수 결정

### 수집 정보

- 출처: Open-Meteo Historical Weather API
- City Hotel: 리스본 좌표 / Resort Hotel: 알가르브 좌표
- 결합 키: `hotel` + `arrival_date` (도착일 하루 날씨)
- 매칭률: 100%

### 초수집 10개 → 최종 7개 (3개 DROP)

| 컬럼 | 결정 | 이유 |
|------|------|------|
| `precipitation_sum` | ✅ KEEP | 주요 날씨 지표 |
| `precipitation_hours` | ✅ KEEP | 강수 시간 (precipitation_sum과 상관 0.82 — 미결) |
| `temperature_2m_max` | ✅ KEEP | 극단값 |
| `temperature_2m_min` | ✅ KEEP | 극단값 |
| `wind_speed_10m_max` | ✅ KEEP | 극단값 (돌풍) |
| `relative_humidity_2m_mean` | ✅ KEEP | |
| `cloud_cover_mean` | ✅ KEEP | |
| `rain_sum` | ❌ DROP | `precipitation_sum`과 상관 **1.000** — 포르투갈 온대기후에서 강수=비 |
| `temperature_2m_mean` | ❌ DROP | max·min으로 충분히 표현됨 (상관 0.967/0.969) |
| `wind_speed_10m_mean` | ❌ DROP | max로 대체 가능 (상관 0.913). 취소에는 극단값이 더 직접적 |

**고민 흔적 — AI 제안 기각 2건 (VALIDATION_LOG #3, #4):**
- 계절별 날씨 가중치 주입 제안 → 기각. "날씨가 중요하다"는 가설을 사전에 넣는 순환 논리.
- 날씨를 프로젝트 메인 프레임으로 설정 제안 → 기각. lead_time 평균 104일 환경에서 실제 날씨로 학습하는 것 자체가 시간 비대칭성 문제. 어떤 결과가 나와도 valid하도록 "외부 변수 중 하나"로 격하.

### ✅ 해소: `precipitation_sum` vs `precipitation_hours` 상관

실측 상관: **0.824** (0.9 미만) → 현재 단계에서 제거 불필요.  
→ Phase 2에서 변수 중요도 확인 후 재판단.

### 날씨 데이터의 근본 가정 (MVP 기준)

- 가정 A: 손님이 취소 시점에 참고한 예보 ≈ 도착일 실제 날씨
- 가정 B: 매니저는 체크인 임박 시점에 DSS를 실행한다
- 가정 C: 날씨는 취소 결정에 영향을 주는 요인 중 하나다 (인과관계 아님, 상관 패턴)

**시간 비대칭성 실증 (EDA 발견):**
```
lead_time ≤ 30일:  강수량 ↑ → 취소율 ↑ (명확한 상관)
lead_time > 90일:  강수량 vs 취소율 무관 (상관 없음)
```
→ 날씨가 예약 시점이 임박할수록 취소 결정에 영향을 줌을 데이터로 확인.

---

## 4. 카테고리 변수 처리

| 컬럼 | 처리 | 사유 |
|------|------|------|
| `country` | Top10 + "Other" 그룹핑 후 OHE | 고유값 177개 → OHE 그대로 하면 컬럼 폭발. Top10 기준은 train 분포에서만 계산 (test 누수 방지) |
| `arrival_date_month` | 숫자 변환 (1~12) | 시계열 정보 유지 |
| `meal` | OHE (단, "Undefined"→"SC" 통합) | "Undefined"와 "SC"(식사 없음)가 동일 의미일 가능성 높음 |
| `hotel` | OHE | |
| `market_segment` | OHE | |
| `distribution_channel` | OHE | |
| `reserved_room_type` | OHE | `assigned_room_type` 대신 사용 |
| `deposit_type` | ❌ DROP | Non Refund 99.2% — B2B allotment 패턴 또는 사후 기록 오염 → DROP 확정 (2026-05-08) → 섹션 2-6 참조 |
| `customer_type` | OHE | |
| `agent` | 0/1 인디케이터 | 결측=직접 예약 신호 |
| `company` | 0/1 인디케이터 | 결측=비법인 예약 신호 |

### `country` 처리 고민 흔적

옵션 세 가지를 검토했다:
- (a) 전체 OHE → 177개 컬럼 생성, 대부분 희소 → 모델 복잡도 불필요 증가
- (b) 대륙 그룹핑 → 지리적 의미는 있지만 포르투갈·영국 같은 중요 국가의 구체 신호가 묻힘
- (c) Top10 + Other OHE → 정보 보존하면서 차원 축소

**결정: (c) Top10 + Other.** SHAP 결과 보고 Phase 2에서 인코딩 방식 재설계 가능. Top10 국가: `PRT·GBR·FRA·ESP·DEU·ITA·IRL·BEL·NLD·BRA`.

---

## 5. 수치형 변수 처리

| 컬럼 | 처리 | 사유 |
|------|------|------|
| `children` NaN | 0으로 채우기 | 거의 대부분 0. 결측 = 어린이 없음으로 해석 안전 |
| `adr = 0` (1,504건, 2%) | 그대로 유지 | 0원 예약 이유 불명확. 트리 모델에서 이상값 자체가 신호가 될 수 있음 |
| `adults = 0` (273건, 0.3%) | 그대로 유지 | 건수 적고 제거 시 오히려 편향 가능 |

---

## 6. 스케일링

| 모델 | 스케일링 |
|------|---------|
| Logistic Regression | StandardScaler 적용 (필수 — 계수가 scale에 민감) |
| Random Forest | 적용 안 함 (트리 기반 불필요) |
| XGBoost / LightGBM | 적용 안 함 |

---

## 7. 제거된 컬럼 전체 요약

| 컬럼 | 제거 이유 | 단계 |
|------|-----------|------|
| `reservation_status` | 타깃과 100% 동치 | bookings_weather_pm 생성 시 |
| `reservation_status_date` | 미래 시점값 | bookings_weather_pm 생성 시 |
| `assigned_room_type` | 체크인 시점 갱신값 | bookings_weather_pm 생성 시 |
| `days_in_waiting_list` | 확정 시점 모호 + 간접 누수 | bookings_weather_pm 생성 시 |
| `previous_bookings_not_canceled` | 정의 모순 (is_repeated_guest와 불일치) | bookings_weather_pm 생성 시 |
| `rain_sum` | precipitation_sum과 상관 1.000 | preprocessing_pipeline.py |
| `temperature_2m_mean` | max·min으로 충분 | preprocessing_pipeline.py |
| `wind_speed_10m_mean` | max로 대체 | preprocessing_pipeline.py |
| `arrival_date` | time_split 임시 컬럼, ML 불필요 | preprocessing_pipeline.py |
| `deposit_type` | Non Refund 99.2% — B2B 패턴 또는 사후 기록 오염, A/B 구분 불가 | preprocessing_pipeline.py |

**총 제거:** 10개 (날씨 3 + 누수 5 + 임시 1 + deposit_type 1)  
**최종 컬럼 수:** 33개 (OHE 전)

---

## 8. 전처리 후 데이터 상태

```
train_processed: 78,703행 × 33컬럼  NaN 0건  취소율 36.6%
test_processed:  40,687행 × 33컬럼  NaN 0건  취소율 38.7%
```

**OHE 적용 후 예상 컬럼 수 (참고):**
- country_grouped (11) + meal (5) + hotel (2) + market_segment + distribution_channel + reserved_room_type (8) + customer_type (4) 등 (deposit_type 제외)
- 대략 65~70개 예상 (실제 OHE 후: 70컬럼 확인됨)

---

## 9. 미결/감시 항목 (이 문서 기준)

| # | 항목 | 담당 | 시점 |
|---|------|------|------|
| A | `deposit_type` — ✅ DROP 확정 (2026-05-08). Phase 2(Week 5) ablation으로 기여분 정량화 예정 | 심재형 | ✅ 완료 |
| B | `precipitation_sum` vs `precipitation_hours` 상관 0.82 — LR 계수 영향 확인 | 김나리 | ✅ 완료 (0.824, 0.9 미만 — 제거 불필요) |
| C | `previous_cancellations` is_repeated_guest 정의 어긋남 해석 | 이고은 | ✅ 2026-05-08 해소 — `docs/week2_eda_prev_cancel.md` 참조. 5,520건이 deposit_type=Non Refund와 동일한 B2B 블록 패턴 (취소율 99.15%, lead_time 2.15배, Groups+Offline 85%) → ≥1 신호의 89%가 재방문 이력 아닌 B2B 블록. Week 3 SHAP에서 두 변수 동시 기여 여부 감시 |
| D | `meal "Undefined"` → `"SC"` 통합 — 파이프라인 한 줄 추가 | 심재형 | 다음 파이프라인 업데이트 |
| E | `previous_cancellations` 제거 ablation | 이고은 | Week 5 Phase 2 |
| F | `country` 인코딩 재설계 (SHAP 결과 보고 결정) | 팀 | Week 6 Phase 2 |

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-05-03 | 이고은 — 누수 분류표 + 검증 [Y1~Y4] 작성 |
| 2026-05-03 | 심재형 — 보류 컬럼 1차 결정 (5건) |
| 2026-05-03 | 심재형 (김나리 제안 반영) — 날씨 다중공선성 3개 DROP 확정 |
| 2026-05-07 | 심재형 — 전처리 파이프라인 완성 + deposit_type 이슈 발견 |
| 2026-05-07 | 심재형 — country Top10+Other 확정, meal Undefined→SC 미결로 남김 |
| 2026-05-08 | 심재형 — 이 문서 작성 (전체 결정 흔적 통합) |
| 2026-05-08 | 심재형 — design_02_leakage_decisions 원시 검증 데이터 Appendix로 통합, design_02 삭제 |
| 2026-05-08 | 이고은 — Week 2 STEP 2 EDA 완료, 미결 항목 C 해소 (`docs/week2_eda_prev_cancel.md`) |
| 2026-05-11 | 심재형 — deposit_type DROP 확정 반영 (섹션 2-6, 4, 7, 8), 컬럼 수 34→33, precipitation 미결 해소 |

---

## Appendix. 원시 검증 데이터 (이고은, 2026-05-03)

> 이 섹션은 `leakage_candidates.md`(구 design_02)에 있던 실제 검증 수치를 보존한 것이다.
> 본문의 결정 근거가 된 raw data.

### [Y1] assigned_room_type 불일치율

| 그룹 | n | 불일치율 (reserved ≠ assigned) |
|---|---:|---:|
| 정상 체크인 (is_canceled=0) | 75,166 | **18.78%** |
| 취소·노쇼 (is_canceled=1) | 44,224 | **1.81%** |
| 전체 | 119,390 | 12.49% (14,917건) |

### [Y2] booking_changes 값별 취소율

| 변경 횟수 | n | 취소율 |
|---:|---:|---:|
| 0 | 101,314 | 40.85% |
| 1 | 12,701 | 14.23% |
| 2 | 3,805 | 20.13% |
| 3 | 927 | 15.53% |
| 4+ | 643 | 18.35% |

→ 변경 없음(=0) 40.85% vs 변경 있음(≥1) **15.67%** — 차이 25.18%p.

### [Y3] previous_* 컬럼 — is_repeated_guest=1 필터 (n=3,810)

| 컬럼 | mean | max | ==0 비율 |
|---|---:|---:|---:|
| `previous_cancellations` | 0.4698 | 21 | 75.67% |
| `previous_bookings_not_canceled` | 3.5850 | 72 | **25.51%** |

→ `is_repeated_guest=1`인데 `previous_bookings_not_canceled=0`인 행이 25.51% — 정의 모순 근거.

### [Y4] agent / company 결측 취소율 차이

| 컬럼 | 결측 취소율 | 비결측 취소율 | 차이 |
|---|---:|---:|---:|
| `agent` | 24.66% | 39.00% | **−14.34%p** |
| `company` | 38.22% | 17.52% | **+20.70%p** |

→ 결측 자체가 예약 경로를 나타내는 강한 신호 → 인디케이터 변환 근거.
