# 취소사유 Grounding — P1 자가취소를 현실 동인 분포에 정박

> 작성: 2026-06-04 | 성격: **근거 조사 + 설계 제안**
> 목적: design_17 트랙 II Phase 3(P1 자가취소)의 최대 약점 — *"취소 상황을 우리가 임의 부여 → 자기실현적"* — 을 메운다.
> 한 수: **취소 트리거를 현실 취소 동인 분포(문헌 + 우리 데이터셋 원논문)에서 샘플링**하면 "자의적"이 아니게 된다.

---

## 0. 왜 이 문서인가

P1(하이쿠 자가취소)은 "수집 시연"이 목적이라 정확도 비측정성은 감수했다(design_17 결정 #4). 그러나 **취소 상황 자체를 우리가 설계**하면 결과가 자기실현적이라는 비판에 노출된다.

**해법:** 취소 트리거를 무작위/임의가 아니라 **실증된 취소 동인 분포에서 추출**한다. 그러면 발표에서 이렇게 말할 수 있다:

> "우리는 취소 트리거를 지어내지 않았다. 우리 데이터셋의 **원논문(Antonio et al. 2019)**과 후속 실증 연구가 밝힌 현실 취소 동인 분포에서 샘플링했다."

이것이 P1의 가장 큰 구멍을 메우는 방어 카드다.

---

## 1. 현실 취소 동인 — 실증 근거

### 1.1 우리 데이터셋의 원논문 (가장 강한 근거)

우리가 쓰는 Kaggle Hotel Booking Demand는 **Antonio, Almeida & Nunes (2019)**가 리스본 City Hotel·알가르브 Resort Hotel **실제 PMS**에서 추출한 데이터다. 즉 "남의 호텔"이 아니라 **우리가 다루는 바로 그 두 호텔**의 동인 연구가 존재한다.

| 동인 | 방향 | 비고 |
|------|------|------|
| **Lead time** | 길수록 ↑ 취소 | 가장 큰 동인 중 하나, 특히 온라인 예약 |
| **Country (국적)** | 국가별 편차 큼 | lead time과 함께 최대 영향 |
| **Deposit type** | Non-refund일수록 ↓ 취소(논문) | ⚠️ 우리 데이터에선 역설(99.2% 취소) → 사후오염 의심으로 DROP |
| **ADR (요금)** | 높을수록 ↑ | top-3 동인 |
| Market segment / 채널 | Online TA ↑ | 채널별 취소율 큰 차이 |
| Reserved room type | 유형별 편차 | |
| Total special requests | 많을수록 ↓ 취소 | 몰입 신호 |

후속 연구가 꼽은 **top-3 동인: lead time · ADR · deposit type.** (우리 SHAP에서도 lead_time·country·previous_cancellations 상위 — 일치)

### 1.2 채널·리드타임·인원 정량

- **채널별 취소율:** 온라인 17% > 오프라인 12% > 여행사 4%
- **리드타임 임계:** lead time > 60일이면 취소 확률 **65% 증가**
- **인원:** 1인 29.98% → 2인 **39.32%** (동반 인원 ↑ 시 취소 ↑)

### 1.3 행동 동인 (왜 취소하는가)

- **무료취소 정책 악용:** 가격 하락 시 취소·재예약(cancel & rebook). OTA가 조장.
- **복수 호텔 동시 예약 후 추리기:** 여러 곳 잡아두고 하나만 남김 — 가장 흔한 취소 원인으로 지목.
- **일정/계획 변경:** 출장·회의 연기 등(긴 lead time·비즈니스 세그먼트와 결합).

### 1.4 취소자 행동 유형 (세그먼트 분포)

Mallorca 200만 건(2021–24) 군집 분석 — BCR(booking/cancellation/risk window) 모델:

| 세그먼트 | 비중 | 성격 |
|----------|------|------|
| Impulsive Cancellers | **58%** | 즉흥·짧은 결정창. 역설적으로 non-refundable 비율 최고(21.3%) |
| Strategic Cancellers | 23% | 가격 비교·재예약형 |
| Moderate Risk Planners | 8% | |
| Risk-Averse Early Planners | 7% | |
| Long-Term Cancellers | 5% | 긴 lead time, 막판 취소 |

---

## 2. 우리 데이터·페르소나로의 매핑

| 현실 취소 동인 | Kaggle 피처 | 우리 페르소나(예) |
|---------------|------------|------------------|
| 무료취소·가격하락 재예약 | `market_segment=Online TA` | Strategic 성향 |
| 복수예약 후 추리기 | `previous_cancellations`, `booking_changes` | Impulsive 성향 |
| 출장·회의 일정 변경 | `lead_time`(김), `customer_type` | Thomas(회의), Ana(출장) |
| 긴 선예약 계획 변경 | `lead_time`(SHAP 상위) | Long-Term |
| 국적별 취소 문화 | `country`(SHAP 1위, PRT) | 페르소나 국적 |
| 동반 인원 | `adults` | 가족(Marie) vs 단독 |
| 몰입(취소 안 함) | `total_of_special_requests`↑ | Risk-Averse |

→ 우리 5 페르소나(Ana/James/Marie/Thomas/Paulo)는 이미 이 동인 축과 정합. design_10 페르소나 설계에 **취소 동인 라벨**만 추가하면 grounding 완성.

---

## 3. P1 적용 제안 — Grounded 취소 트리거 분포

Phase 3에서 각 예약에 취소 상황을 부여할 때, **임의 대신 아래 분포에서 샘플링**:

```
취소 트리거 분포 (현실 동인 기반, 합산 100%)
  더 싼 가격 발견 / 재예약        ~30%   (Online TA · Strategic, §1.3·1.4)
  복수예약 정리(다른 곳 확정)      ~25%   (Impulsive, previous_cancellations)
  일정·회의 변경                  ~20%   (lead_time 김 · 비즈니스)
  단순 변심·계획 취소              ~15%   (Impulsive 일반)
  가격/조건 불만                  ~10%   (ADR 높음)
  └ 유지(취소 안 함) 확률은 위험점수·special_requests로 가중
```

- **수락 vs 미수락 분기:** Flexi 수락자 = 통보 후 취소(객실 회수) / 미수락자 = 막판 취소·노쇼 (design_17 5.1 Phase 3)
- **walk-rate 검증:** `notice_days`로 사전 통보율 측정 → walk_rate < 2% 목표(design_06)와 연결
- **비율 출처 명시:** 위 가중치는 §1 문헌값의 **근사**다. 정밀 보정은 Phase 2 이후 로드맵. 발표엔 "현실 동인 분포에서 샘플링(근사)"로 정직하게 표기.

---

## 4. 발표에서 사는 한 문장

> "P1 자가취소의 트리거는 우리가 지어낸 게 아니라, **이 데이터셋의 원논문(Antonio et al. 2019, 같은 리스본·알가르브 호텔)**과 후속 실증 연구가 밝힌 현실 취소 동인 — 가격 재예약·복수예약 정리·일정 변경·리드타임 — 의 분포에서 샘플링했다. 그래서 자기실현이 아니라 **현실 동인으로 정박된 운영 데이터 수집 시연**이다."

---

## 5. 미결 / 다음 단계

| # | 항목 | 비고 |
|---|------|------|
| 1 | §3 분포 가중치 확정 | 문헌 근사 → 팀 합의로 고정 |
| 2 | 페르소나에 취소 동인 라벨 추가 | design_10 보완 (충돌 위험: agents.py 공유 — 작업방 조율) |
| 3 | deposit_type 역설 재언급 | DROP 유지하되 "논문은 ↓인데 데이터는 ↑" 대비를 슬라이드 각주로 |
| 4 | walk_rate 검증 연결 | 기존 walk_sim 1,000건(Slide 07)과 Phase 3 출력 정합 |

---

## 출처

- [Big Data in Hotel Revenue Management: Exploring Cancellation Drivers — Antonio, de Almeida, Nunes (2019)](https://journals.sagepub.com/doi/10.1177/1938965519851466)
- [Predicting Hotel Bookings Cancellation with a ML Classification Model — Antonio, Almeida, Nunes](https://www.semanticscholar.org/paper/Predicting-Hotel-Bookings-Cancellation-with-a-Model-Antonio-Almeida/38fb00e49a34a15f692add91e889a51a3b994904)
- [Hotel Booking Demand dataset (Kaggle, 원 데이터)](https://www.kaggle.com/datasets/jessemostipak/hotel-booking-demand)
- [Decoding booking cancellations: Quantitative insights — ScienceDirect (2025)](https://www.sciencedirect.com/science/article/pii/S0261517725002547)
- [Global Cancellation Rate Reaches 40% — Hospitality Technology](https://hospitalitytech.com/global-cancellation-rate-hotel-reservations-reaches-40-average)
- [Where do Cancellations come from? — Experience CRM](https://experience-crm.fr/en/where-do-cancellations-come-from/)
- [Navigating uncertainty: adaptive ML for cancellation prediction — Springer (2025)](https://link.springer.com/article/10.1007/s40558-025-00349-9)
