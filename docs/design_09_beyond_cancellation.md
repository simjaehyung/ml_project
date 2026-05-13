# 취소 예측을 넘어 — 이 데이터로 풀어야 할 진짜 문제들

> 작성: 심재형 (PM) | 기준일: 2026-05-11  
> 배경: 취소 예측 모델이 완성된 뒤, 같은 데이터로 호텔 운영에 실질적 변화를 만들 수 있는 방향 탐색

---

## 왜 취소 예측만으로는 부족한가

지금 이 프로젝트의 1차 결과물은 "이 예약이 취소될 확률"이다.  
그 확률을 Flexi 라우팅에 쓰고, 매니저 대시보드에 시각화한다.  

하지만 취소 예측은 **호텔이 가진 문제의 증상**을 다루는 것이지, 구조를 다루는 것이 아니다.

```
증상: "이 예약이 취소될 것 같다"
구조: "왜 이 유형의 예약들이 계속 취소되는가"
     "어떤 채널이 실제로 수익을 내는가"
     "취소 예측 결과를 수익 외 다른 운영 문제에 연결할 수 있는가"
```

이 문서는 동일한 데이터와 모델 출력을 이용해 풀 수 있는 세 가지 구조적 문제를 정의한다.

---

## 방향 1 — 채널 실효 수익 분석 (Channel Effective Yield)

### 문제 정의

호텔은 Online TA(Booking.com, Expedia 등)가 "가장 많이 팔아준다"고 인식한다.  
하지만 이 인식은 **취소 비용을 반영하지 않은 액면 ADR** 기준이다.

### 계산 구조

```
Effective ADR = ADR × (1 - cancel_rate)

예시:
  Online TA    → ADR €95,  취소율 42% → Effective ADR €55.1
  Direct       → ADR €105, 취소율 18% → Effective ADR €86.1
  Corporate    → ADR €88,  취소율  9% → Effective ADR €80.1
  GDS          → ADR €112, 취소율 28% → Effective ADR €80.6
```

여기에 lead_time을 교차하면 같은 채널 안에서도 행동이 완전히 다르다.

```
Online TA × lead_time > 90일  → 취소율 ?%  (가격 탐색형, 더 좋은 딜 나오면 이탈)
Online TA × lead_time < 14일  → 취소율 ?%  (목적이 분명한 막판 예약)
```

### 분석 방법

```python
# 채널 × lead_time 구간 × 취소율 매트릭스
df['lead_bucket'] = pd.cut(df['lead_time'], bins=[0,14,30,90,180,999],
                           labels=['0-14','15-30','31-90','91-180','181+'])

yield_matrix = (df.groupby(['distribution_channel', 'lead_bucket'])
                  .agg(avg_adr=('adr','mean'),
                       cancel_rate=('is_canceled','mean'),
                       n=('is_canceled','count'))
                  .assign(effective_adr=lambda x: x.avg_adr * (1 - x.cancel_rate)))
```

### 호텔에게 의미 있는 이유

이 분석 결과가 나오면 채널 전략의 근거가 바뀐다.

- 마케팅 예산 배분 — 실효 수익이 낮은 채널 의존도 줄이기
- Direct 채널 육성 투자 여부 결정
- 채널별 Flexi 오퍼 우선순위 조정 (고취소 채널 예약에 먼저 오퍼)

### 관련 연구

- Talluri & van Ryzin (2004). *The Theory and Practice of Revenue Management.* — 채널별 수익 최적화의 이론 기반
- Hospitality Net (2025). *Guest segmentation in 2025: Moving beyond broad-brush marketing with AI.* — 마이크로세그먼테이션이 2025년 핵심 트렌드로 확인됨
- [ScienceDirect (2022) — Data-driven market segmentation in hospitality using unsupervised ML](https://www.sciencedirect.com/science/article/pii/S2666827022000895)

---

## 방향 2 — 예약 품질 점수 (Booking Quality Score)

### 문제 정의

`cancel_probability`는 "이 예약이 사라질 확률"을 말한다.  
하지만 호텔이 진짜 원하는 건 **"이 예약이 실제로 가치 있는 예약인가"** 다.

취소 가능성이 낮더라도 ADR이 매우 낮거나, 단 1박이거나, 아무 요청도 없는 예약은 품질이 낮다.  
반대로 취소 확률이 약간 있더라도 ADR이 높고, 장기 체류이고, 특별 요청이 많고, 직접 예약이라면 — 호텔이 지켜야 할 예약이다.

### 점수 구성 요소

| 변수 | 방향 | 근거 |
|------|------|------|
| `adr` | 높을수록 ↑ | 직접 수익 기여 |
| `stays_in_week_nights + stays_in_weekend_nights` | 길수록 ↑ | 장기 투숙 = 고정비 대비 수익 |
| `total_of_special_requests` | 많을수록 ↑ | 예약 몰입도 (commitment) 신호 |
| `is_repeated_guest` | 재방문 ↑ | 충성 고객 |
| `previous_bookings_not_canceled` | 많을수록 ↑ | 이행 이력 |
| `distribution_channel` | Direct > GDS > TA | 채널 신뢰도 |
| `cancel_probability` (모델 출력) | 낮을수록 ↑ | 취소 위험 |

### 핵심 개념: special_requests가 말하는 것

```
special_requests = 0
  → 이 손님은 이 호텔을 '선택'하지 않았다. 가격으로 걸렸다.
  → 더 싼 옵션이 나오면 이탈 가능성 높음

special_requests = 3+
  → 침대 타입, 층수, 전망, 알레르기까지 챙겼다.
  → 이 호텔에 와야 할 이유가 있는 손님.
```

이 인사이트는 현재 취소 예측 모델에서 SHAP feature importance로 확인 가능하다.  
`total_of_special_requests`가 실제로 얼마나 기여하는지를 보면 이 가설을 데이터로 검증할 수 있다.

### 활용 방향

```
Booking Quality Score 높음 + cancel_probability 높음
  → "이 예약은 지키고 싶다. 리텐션 개입 대상."
  → Flexi 오퍼 대신 체류 전 특전 제공 (업그레이드, 웰컴 패키지)

Booking Quality Score 낮음 + cancel_probability 높음
  → "이 예약은 Flexi 오퍼 우선 대상."
  → 취소 시 손실이 작고, 오버부킹 슬롯으로 관리 가능

Booking Quality Score 높음 + cancel_probability 낮음
  → "터치하지 않는다. Standard 확정."
```

### 관련 연구

- 아직 표준화된 "Booking Quality Score" 개념은 학술 문헌에 명시적으로 없음 → **이 프로젝트의 차별화 지점**
- 기반이 되는 이론: Prospect Theory (Kahneman & Tversky, 1979) — special_requests가 많은 손님은 손실 회피 심리가 강해 예약 이행 가능성이 높다
- CLV(Customer Lifetime Value) 추정 연구들이 유사 방향을 다루나, 대부분 고객 ID 필요 — 이 데이터셋 기반의 ID-free 품질 추정은 공백 영역

---

## 방향 3 — 음식 낭비 예측 및 ESG 운영 지원

### 문제 정의

`meal` 컬럼은 지금까지 취소 예측의 피처로만 쓰였다.  
하지만 이 변수는 **호텔의 물리적 운영 비용과 직결**된다.

```
HB (Half Board: 조식 + 석식) 예약이 취소되면
  → 이미 발주된 식재료 → 낭비
  → 조리 인력 배치 → 낭비
  → 탄소발자국 → ESG 보고 항목
```

전 세계 호텔 음식 낭비 추정 비용: **연간 1,000억 달러 이상** (Frontiers AI, 2024)  
이 중 상당 부분이 예약 취소 및 no-show에서 발생한다.

### 분석 구조

```python
# 식사 플랜 × 취소 확률 → 예상 낭비 위험 예약
meal_risk = test_df.copy()
meal_risk['cancel_proba'] = model.predict_proba(X_test)[:,1]
meal_risk['food_waste_risk'] = (
    meal_risk['cancel_proba'] > 0.65
) & (
    meal_risk['meal'].isin(['HB', 'FB'])
)

# 주간 예상 낭비 위험 예약 수 → 식재료 발주 조정 권고
weekly_risk = (meal_risk[meal_risk['food_waste_risk']]
               .groupby('arrival_date_week_number')
               .agg(high_risk_meal_bookings=('food_waste_risk','sum'),
                    avg_cancel_proba=('cancel_proba','mean')))
```

### 운영 출력 형태

```
이번 주 도착 예정 HB/FB 예약 중 고위험:
  12건 (전체 HB/FB 예약 34건 중 35%)
  → 식재료 발주 권고: 정상 기준 대비 -25%
  → 예상 절감: 식재료 원가 약 €180 / CO₂ 약 14kg
```

### 왜 이게 의미 있는가

1. **ESG 보고 의무화** — EU CSRD(Corporate Sustainability Reporting Directive) 2024년부터 대형 기업 적용, 2025~26년 중소 호텔까지 확대 예정. 음식 낭비 데이터가 보고 항목이 된다.

2. **비용 절감** — 취소 예측이 수익을 지키는 도구라면, 음식 낭비 예측은 비용을 줄이는 도구. 두 방향이 같은 모델에서 나온다.

3. **기존 연구 공백** — 예약 데이터 기반의 사전적(predictive) 음식 낭비 예측은 아직 초기 단계. 사후적 모니터링(Leanpath, Winnow) 도구는 있으나, 예약 단계에서의 예측은 드물다.

### 관련 연구

- [Frontiers AI (2024) — Exploring the potential of AI-driven food waste management strategies in hospitality](https://pmc.ncbi.nlm.nih.gov/articles/PMC11799730/)
- [Emerald Journal of Tourism Futures (2025) — Revolutionizing the hospitality industry: AI technologies for food management and reduction of food waste](https://www.emerald.com/jtf/article/doi/10.1108/JTF-02-2025-0033/1298666/Revolutionizing-the-hospitality-industry-the)
- [Journal of Sustainable Tourism (2024) — Digital innovation for food waste reduction in hotels](https://www.tandfonline.com/doi/full/10.1080/09669582.2024.2438233)

---

## 세 방향의 관계

```
취소 예측 모델 (cancel_probability)
        │
        ├── 방향 1: 채널 실효 수익 분석
        │     채널 × lead_time × ADR × cancel_rate
        │     → "어느 채널에서 어떤 예약을 받을 것인가"
        │
        ├── 방향 2: 예약 품질 점수
        │     ADR + 체류기간 + special_requests + channel + cancel_proba
        │     → "이 예약을 지킬 것인가, Flexi로 보낼 것인가"
        │
        └── 방향 3: 음식 낭비 예측
              meal × cancel_probability
              → "식재료를 얼마나 발주할 것인가"
```

세 방향 모두 **새로운 ML 모델이 필요 없다.**  
현재 모델의 출력(`cancel_probability`)을 재활용하거나,  
기존 데이터의 집계 분석만으로 충분히 도출 가능하다.

---

## 프로젝트 통합 방안

### Phase 1 MVP 범위 (~ 2026-05-27)

MVP는 건드리지 않는다. 취소 예측 + Flexi 라우팅 탭으로 완성한다.

### Phase 2 실험 범위 (2026-05-28 ~ 2026-06-10)

| 주차 | 방향 | 추가 작업량 |
|------|------|-----------|
| Week 5 | 방향 1: 채널 실효 수익 분석 | 집계 분석 + 시각화 1~2일 |
| Week 5 | 방향 2: special_requests SHAP 검증 | SHAP 이미 있음 — 확인만 |
| Week 6 | 방향 3: 음식 낭비 예측 탭 (optional) | 간단한 필터링 + 수치 출력 |

### 발표 포지셔닝 변화

```
Before:
  "호텔 예약 취소 예측 기반 DSS입니다"

After:
  "호텔이 진짜 풀어야 할 세 가지 문제 —
   어느 채널이 실제로 수익을 내는가,
   어떤 예약을 지켜야 하는가,
   취소가 만드는 낭비를 어떻게 줄이는가 —
   를 같은 데이터와 같은 모델로 다룹니다."
```

---

## 미결 항목

| # | 항목 | 담당 | 시점 |
|---|------|------|------|
| 1 | 방향 1 채널 매트릭스 — City vs Resort 분리 여부 | PM | Week 5 착수 시 결정 |
| 2 | 방향 2 Booking Quality Score 가중치 설계 | 심재형 | Week 5 |
| 3 | 방향 3 앱 탭 추가 여부 — 발표 범위 포함할지 | PM | Week 6 초 결정 |
| 4 | 세 방향을 발표에서 별도 섹션으로 다룰지 / 부록으로 처리할지 | PM | Week 6 |
