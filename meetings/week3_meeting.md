# Week 3 팀 회의 안건

> 일시: 2026-05-12 (화) | 진행: 심재형  
> 참석: 심재형 · 이고은 · 김나리

---

## 0. 이번 회의 목적 (5분)

두 가지를 동시에 처리한다.

1. **Week 2 결과 확인** — 수치 공유 + 파이프라인 정렬
2. **프로젝트 방향 재정의** — Flexi 비중 하향 + 3개 새 방향 추가

두 번째가 더 중요하다. 오늘 합의된 방향이 Phase 2 전체 역할 분담에 영향을 준다.

---

## 1. Week 2 결과 빠른 확인 (10분)

### Baseline 수치 (정식 파이프라인 기준)

| 모델 | PR-AUC | F1@0.5 |
|------|--------|--------|
| Dummy | 0.3870 | — |
| Logistic Regression | 0.7818 | 0.7073 |
| Random Forest | 0.7785 | 0.6454 |

- **LR > RF** 역전 현상: deposit_type 제거 후 트리 이점이 희미해짐 → XGBoost/LightGBM에서 어떻게 바뀔지가 이번 주 핵심
- 노션 수치(0.81)와 정식 수치(0.78)의 0.03 차이 = deposit_type이 모델에 기여하던 신호량

### 파이프라인 기준 재공지 (전원 확인)

```python
# 입력
train = pd.read_csv("data/train_processed.csv")   # 33컬럼
test  = pd.read_csv("data/test_processed.csv")    # 33컬럼

# cat_cols — deposit_type 없음
cat_cols = ["hotel", "meal", "market_segment", "distribution_channel",
            "reserved_room_type", "customer_type", "country_grouped"]

# OHE 후 컬럼 수: 70개
```

arrival_date_month는 이미 int 1~12로 변환됨 — OHE 하지 말 것.

---

## 2. 프로젝트 방향 재정의 — PM 공지 (15분)

### 2-1. 목표가 바뀌었다

**기존:** "취소 예측 기반 DSS"  
**변경:** "호텔이 진짜 풀어야 할 세 가지 운영 문제"

```
문제 1 — 어느 채널이 실제로 수익을 내는가?
문제 2 — 어떤 예약을 지켜야 하는가?
문제 3 — 취소가 만드는 낭비(음식)를 어떻게 줄이는가?
```

취소 예측 모델은 이 세 문제를 푸는 엔진이다. 새 ML 모델은 없다. 현재 모델 출력을 재활용한다.

### 2-2. Flexi 시스템 비중 하향

**삭제:** Pool B 수익 시뮬레이션 (`conversion_rate`, `net_gain` 수치)  
**이유:** conversion_rate는 반사실적 수요 — 어떤 수치를 써도 구조적으로 방어 불가

**유지:**
- PR-AUC → walk_rate 곡선 (Pool A 실데이터만, threshold sweep)
- 블라인드 오버부킹 vs 모델 정밀 오버부킹 비교
- 이론 근거 (Mechanism Design, Probabilistic Selling)

**앱 탭 2 재설계:**  
"신규 예약 위험 평가기" → "Flexi 풀 운영 제어판"  
매니저가 threshold 슬라이더와 슬롯 수를 설정한다. 개별 예약 판단은 없다.

### 2-3. Phase 2 새 방향 (Week 5~6)

Phase 1(~ 5/27)은 건드리지 않는다. Phase 2에서 아래를 추가한다.

| 방향 | 내용 | 담당 |
|------|------|------|
| 채널 실효 수익 | distribution_channel × ADR × cancel_rate 매트릭스 | **김나리** |
| 예약 품질 점수 | ADR + 체류기간 + special_requests + cancel_proba 복합 점수 | **심재형** |
| 음식 낭비 예측 | meal × cancel_proba → 식재료 발주 조정 권고 탭 | **이고은** |

**관련 문서:** `docs/design_09_beyond_cancellation.md` (오늘 작성)  
**전체 일정:** `docs/project_roadmap.md` (오늘 작성)

> 질문 있으면 지금. 이 방향 합의가 안 되면 Phase 2 역할 배분 확정 불가.

---

## 3. Week 3 실행 계획 (10분)

### 타임라인

```
5/12(화) ~ 5/14(목)  병렬
  심재형  │ XGBoost 학습 + PR-AUC 기록
  김나리  │ LightGBM 학습 + PR-AUC 기록
  이고은  │ 탭 1 구현 시작 (예약 리스트 + 위험도 표시)

5/15(금) ~ 5/16(토)
  심재형  │ PR curve 5종 통합 그래프 생성
          │ 모델 확정 기준 초안 → 팀 합의 (아래 안건 3-1)
  이고은  │ 탭 1 계속

5/17(일) ~ 5/18(월)
  심재형  │ 모델 출력 인터페이스 확정 → 이고은 전달
  이고은  │ 모델 연동 준비

─── 5/18(월) Gate: 모델 동결 ───
```

### 5/18 Gate 조건

| 조건 | 기준 |
|------|------|
| XGBoost PR-AUC | 노션 기록 |
| LightGBM PR-AUC | 노션 기록 |
| 최종 모델 1개 선정 | 팀 합의 |
| `results/baseline_results.md` | 5종 비교표 완성 |
| 모델 파일 저장 | `results/model_final.pkl` |

---

## 4. 합의 안건 — 모델 확정 기준 (미결 #3) (10분)

5/16~17에 실제 수치 보고 결정. 오늘은 기준안만 합의.

### 제안안

> PR-AUC 차이가 **0.01 미만**이면 → LightGBM (속도·메모리 우위)  
> PR-AUC 차이가 **0.01 이상**이면 → PR-AUC 높은 쪽

### 논의 포인트

- 이 기준에 동의하는가
- 다른 조건(해석 가능성, 앱 연동 편의성 등) 추가할 것인가

**결정 시한:** 5/17(일) 심재형 점검 시 최종 확정.

---

## 5. SHAP 감시 항목 공유 (5분)

Week 3 모델 돌리면서 미리 인지할 것.

| 변수 | 감시 내용 | 이유 |
|------|---------|------|
| `previous_cancellations` | SHAP 상위 독식 여부 | ≥1 그룹 취소율 91.64%, 89%가 B2B 블록 패턴 |
| `lead_time` | SHAP 기여 방향과 크기 | Week 2 EDA에서 취소 예약 평균 lead_time이 정상보다 훨씬 길었음 |
| `market_segment_Online TA` | SHAP 기여 방향 | Week 2 EDA에서 취소율 높음 확인 |

두 변수(previous_cancellations + deposit_type 대체 신호)가 SHAP 상위를 동시 독식하면 Phase 2 ablation 우선순위 상향.

---

## 6. 팀원별 이번 주 단일 집중 목표

| 이름 | 이번 주 단 하나의 목표 |
|------|----------------------|
| 심재형 | XGBoost PR-AUC 기록 + 5종 통합 PR curve 완성 |
| 김나리 | LightGBM PR-AUC 기록 (train_processed.csv 기준) |
| 이고은 | 탭 1 뼈대 완성 (심재형 모델 연동 대기 상태까지) |

---

## 7. 다음 회의 (Week 4 시작)

> 일시: 2026-05-19 (화)  
> 확인 사항: 모델 동결 여부 + SHAP 초기 결과 + 탭 1 완성도

---

## 결정 필요 항목 요약

| # | 항목 | 결정 시한 |
|---|------|---------|
| 1 | Phase 2 방향 재정의 합의 (채널·BQS·음식 낭비) | **오늘** |
| 2 | 모델 확정 기준 합의 | **오늘** (확정은 5/17) |

---

## 📊 수치 해석 자료 — 회의 중 참조용

> 이 섹션은 안건별로 "지금 우리가 가진 수치가 무엇을 말하는가"를 정리한 것이다.  
> 회의 중 논의 흐름에 맞게 펼쳐서 쓴다.

---

### A. Baseline 수치 해석

**데이터셋 기본값**

| 항목 | 수치 |
|------|------|
| Train | 78,703행 / 취소율 36.6% |
| Test | 40,687행 / 취소율 38.7% |
| 전체 기간 | 2015-07 ~ 2017-08 (26개월) |
| Test 기간 | 2017-03 ~ 2017-08 (마지막 6개월) |

**모델 수치 비교**

| 모델 | PR-AUC | F1@0.5 | 비고 |
|------|--------|--------|------|
| Dummy (기준선) | **0.3870** | 0.0000 | 테스트셋 취소율(38.7%)과 수렴 — 이론적으로 정확한 값 |
| Logistic Regression | **0.7818** | 0.7073 | 구버전(노션) 0.8084 → deposit_type 제거 후 0.03 하락 |
| Random Forest | **0.7785** | 0.6454 | 구버전(노션) 0.8143 → deposit_type 제거 후 0.036 하락 |
| XGBoost | **—** | — | 이번 주 심재형 산출 예정 |
| LightGBM | **—** | — | 5/16 정오까지 김나리 산출 필요 |

**해석 포인트 (회의 중 설명용)**

```
① 왜 Dummy PR-AUC = 0.3870인가?
   → most_frequent 예측기는 모든 예약을 "미취소"로 예측.
   → 양성(취소) 클래스를 하나도 못 잡으므로 F1@0.5 = 0.
   → PR-AUC의 이론값: 상수 예측기 = 양성 클래스 비율(≈ 취소율)
   → 테스트셋 취소율 38.7% ≈ Dummy PR-AUC 0.3870 ✓

② LR > RF인 이유가 무엇인가?
   → deposit_type 제거 전: RF가 "Non Refund=취소" 신호를 트리로 잘 잡아 유리했음
   → deposit_type 제거 후: 그 이점이 사라짐 → LR과 RF가 거의 동등 수준으로 수렴
   → XGBoost/LightGBM이 나머지 피처에서 비선형 패턴을 얼마나 더 찾는지가 이번 주 핵심

③ 노션 수치(0.81) vs 정식 수치(0.78) — 0.03 차이의 의미
   → deposit_type이 모델에 기여하던 신호량이 정확히 0.03
   → 발표 시 "우리는 B2B 패턴 오염 신호를 의도적으로 제거했으며, 그 비용은 PR-AUC 0.03이다" 로 방어
```

---

### B. previous_cancellations — 핵심 수치

**이 변수를 특별히 봐야 하는 이유: deposit_type 제거 후 이 변수가 그 신호를 대리할 가능성 있음**

| 구분 | 수치 |
|------|------|
| previous_cancellations = 0 그룹 취소율 | **33.91%** |
| previous_cancellations ≥ 1 그룹 취소율 (2015) | **98.96%** |
| previous_cancellations ≥ 1 그룹 취소율 (2016) | **84.98%** |
| previous_cancellations ≥ 1 그룹 취소율 (전체) | **94.97%** |
| ≥1 그룹과 =0 그룹 취소율 차이 | **57.1%p** — 데이터셋에서 가장 강한 이진 신호 |

**정의 불일치 행 (5,520건)**

| 항목 | 수치 |
|------|------|
| is_repeated_guest=0이면서 previous_cancellations≥1인 행 수 | **5,520건** (전체의 약 4.6%) |
| 이 5,520건의 취소율 | **~99.15%** |
| 이 5,520건 중 Groups + Offline TA/TO 비율 | **89%** |
| 이 5,520건의 평균 lead_time | **217일** (전체 평균 104일의 2.1배) |

```
해석:
  → 5,520건은 "첫 예약인 척하는 B2B 블록 반납"
  → deposit_type=Non Refund와 동일 패턴 (B2B allotment 블록 취소)
  → deposit_type을 제거해도 previous_cancellations가 동일 B2B 신호를 잡을 가능성 높음
  → Week 3 XGBoost/LightGBM SHAP에서 previous_cancellations가 상위를 독식하면
    "deposit_type 대리 변수"로 작동 중인 것 → Phase 2 ablation 우선순위 상향
```

---

### C. deposit_type — 왜 DROP했나 (발표 방어 수치)

| deposit_type | 취소율 | 건수 |
|-------------|--------|------|
| No Deposit | **26.6%** | ~68,000건 |
| Non Refund | **99.2%** | 10,461건 |
| Refundable | **7.4%** | 135건 |

```
Non Refund 10,461건의 구성:
  → Groups: 61% (B2B 단체 블록)
  → Offline TA/TO: 37% (오프라인 여행사 allotment)
  → 합계: B2B 채널 98%

왜 DROP인가:
  → 99.2% 취소는 "개인이 보증금 포기하고 취소"가 아님
  → B2B allotment 계약에서 release date 이전 블록 반납 = 패널티 없는 취소
  → 모델이 이 신호를 잡으면 "B2B 블록 반납 = 취소 예측"으로 과학습
  → 타임스탬프 없어 사후 기록 오염(가설 B)도 배제 불가
  → 발표 멘트: "어느 가설이 맞든 A/B 구분 불가 상태에서 포함하면 방어 불가 — DROP"
```

---

### D. 날씨 변수 핵심 발견 — 발표 서사의 핵심

```
lead_time ≤ 30일:  강수량 ↑ → 취소율 ↑  (명확한 양의 상관)
lead_time > 90일:  강수량 vs 취소율 상관 없음
```

**의미:**
- 예약 시점이 도착일에 임박할수록 날씨가 취소 결정에 영향을 준다
- 3개월 전에 예약한 사람은 날씨를 모르기 때문에 도착일 날씨와 무관
- 이것이 "날씨 데이터를 넣은 이유"를 데이터로 증명하는 슬라이드 핵심 근거

**날씨 DROP 결정 수치 (다중공선성)**

| 제거 변수 | 대체 변수 | 상관 |
|----------|----------|------|
| rain_sum | precipitation_sum | **1.000** (완전 동일) |
| temperature_2m_mean | max·min 조합 | 0.967 / 0.969 |
| wind_speed_10m_mean | wind_speed_10m_max | 0.913 |
| precipitation_sum vs precipitation_hours | — | **0.824** (0.9 미만 → 제거 불필요) |

---

### E. 채널 실효 수익 — Phase 2 방향 1 예시 수치

(실제 수치는 Phase 2에서 산출. 아래는 설명용 예시.)

```
Effective ADR = ADR × (1 - cancel_rate)

예시 (design_09 기준):
  Online TA    → ADR €95,  취소율 42% → Effective ADR €55.1
  Direct       → ADR €105, 취소율 18% → Effective ADR €86.1
  Corporate    → ADR €88,  취소율  9% → Effective ADR €80.1
  GDS          → ADR €112, 취소율 28% → Effective ADR €80.6
```

→ "Online TA가 가장 많이 팔아준다"는 인식이 Effective ADR 기준에서는 역전될 수 있다는 것을 보여주는 프레임

---

### F. 기타 주요 수치 (회의 중 참고)

**booking_changes — KEEP 결정 근거**

| 변경 횟수 | 취소율 |
|----------|--------|
| 0 (변경 없음) | **40.85%** |
| ≥1 (한 번이라도 변경) | **15.67%** |
| 차이 | **25.18%p** |

→ 예약 변경 = 손님 몰입도(commitment) 신호. 변경할수록 취소율 급감.

**agent / company 인디케이터 근거**

| 변수 | 결측(직접예약) 취소율 | 비결측 취소율 | 차이 |
|------|---------------------|------------|------|
| agent | 24.66% | 39.00% | −14.34%p |
| company | 38.22% | 17.52% | +20.70%p |

→ 결측 자체가 예약 경로 신호 → ID 버리고 0/1 인디케이터로 변환한 이유

**전처리 후 최종 데이터 상태**

```
컬럼 수 변화: 32(원본) → 43(날씨 합류) → 38(누수 제거) → 33(파이프라인 최종)
OHE 후 컬럼 수: 70개
NaN: 0건 (train/test 모두)

제거된 10개 컬럼:
  확정 누수 5개: reservation_status, reservation_status_date,
                 assigned_room_type, days_in_waiting_list,
                 previous_bookings_not_canceled
  날씨 중복 3개: rain_sum, temperature_2m_mean, wind_speed_10m_mean
  임시 1개: arrival_date
  판단 제거 1개: deposit_type (B2B 패턴 + 사후 기록 오염 의심)
```

---

### G. 모델 확정 기준 안건 — 판단 프레임

```
오늘 합의할 기준안:

  PR-AUC 차이 < 0.01  → LightGBM 선택 (속도·메모리 우위)
  PR-AUC 차이 ≥ 0.01  → PR-AUC 높은 쪽 선택

논의할 질문:
  Q1. 해석 가능성(SHAP)은 XGBoost vs LightGBM 사이에 차이가 있는가?
      → 둘 다 TreeSHAP 완전 지원. 차이 없음.

  Q2. 앱 연동 편의성 차이가 있는가?
      → predict_proba() 포맷 동일. 최종 모델 교체 시 pkl 파일명만 바꾸면 됨.

  Q3. 5/16 정오까지 LightGBM 수치 없으면?
      → XGBoost 단독 동결. 추가 합의 불필요.
      → LightGBM 수치는 이후 baseline_results.md에 기록 후 Phase 2 참고용으로 보관.
```
