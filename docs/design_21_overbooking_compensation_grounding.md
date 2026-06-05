# 오버부킹·보상 Grounding — 장면 4~7을 현실 관행에 정박

> 작성: 2026-06-04 (PM 자율작업, 재형님 저녁 중) | 성격: **근거 조사 + 설계 제안**
> 자매 문서: `design_19_cancellation_grounding.md`(취소 동인 정박)
> 목적: 발표 연속서사의 "오버부킹 결정(장면4) → 기대이익(장면5) → 예측 실패 → 보상(장면6~7)"을
>        실제 호텔 운영 관행에 정박해 "지어냈다"는 비판을 막는다.
> ⚠️ 핵심 발견: 우리 `growth_curve.py`의 expected_cost **비용비 가정이 현실과 반대 방향**일 수 있다 (4절).

---

## 0. 한 줄 요약

> 오버부킹 수준·walk 보상은 **잘 정립된 호텔 RM 관행**이 있다. 우리 장면4~5는 그 관행의 시각화이고,
> walk_sim 협상값은 업계 보상과 같은 자릿수다. 단 **"빈 방 손실 vs walk 비용"의 크기 비교는
> reputation을 넣으면 우리가 코드에 박아둔 가정과 반대**일 수 있어, 이 부분은 정직하게 재검토한다.

---

## 1. Walk(예약 초과 → 손님 이전) 보상 — 업계 표준

### 1.1 표준 보상 구성

법적 의무는 **선불 환불뿐**(항공과 달리 호텔 오버부킹 규제 없음 — 우리 법률 슬라이드와 정합). 그러나 업계 관행은:

| 구성 | 내용 |
|------|------|
| 대체 숙소 | 동급 또는 **상위** 호텔 |
| 첫날 숙박비 | 원 호텔이 대체 호텔 **첫날 요금 부담** |
| 교통비 | 대체 호텔까지 이동 비용 |
| 굿윌 | 로열티 포인트·바우처·식사권 (재량) |

### 1.2 브랜드별 공개 정책

| 브랜드 | walk 보상 |
|--------|----------|
| Hyatt | 첫날(동급) + 교통 + 전화 (강한 공개 정책) |
| Marriott | 상한 $200 + 140,000 pts (최상위 등급·럭셔리 기준) |
| 럭셔리(JW·Westin·W) | $200 현금 + 90,000 pts |

→ **핵심: walk 보상 ≈ "첫날 숙박비 + 교통 + 굿윌".** 등급·브랜드·재량으로 편차.

### 1.3 우리 walk_sim과의 대조 (정박 + 정직한 한계)

- walk_sim **D €46** ≈ ADR(~€110) 대비 **약 42%**.
- 업계 "첫날 숙박비" 풀보상은 ~100% ADR + 교통 → **우리 협상값은 현실 walk 보상의 *하단*(굿윌/부분보상 범위)**.
- **발표 표현(정직):** "우리 시뮬이 뽑은 보상 수용 임계값은 업계 walk 보상과 **같은 자릿수**이며, 풀 walk 보상보다 낮은 *굿윌/사전협상* 구간에 위치한다." → 과대주장("정확히 일치") 금지.

---

## 2. 오버부킹 수준 결정 — 업계 관행

### 2.1 이론 (장면5 "기대이익 곡선"의 근거)

> **최적 오버부킹 = 추가 1실 오버부킹의 기대 한계비용 = 기대 한계수익이 되는 지점.**

→ 우리 장면5 "K개 오버부킹 시 기대이익 곡선"은 **이 고전 RM 이론의 정확한 시각화**다. 즉 우리가 새로 지어낸 게 아니라 교과서적 프레임을 데이터로 그린 것.

### 2.2 실무 수치

- 데이터 기반: 계절·요일·채널·노쇼율·이벤트 패턴 분석.
- 업계 관행 한도: **총 객실의 5~15%** (비즈니스 호텔 평일 10~15%, 레저 성수기 5~10%).
- **risk-based 방법이 RevPAR 지수가 더 높다**(연구 결과) → "위험도 기반 오버부킹"이라는 우리 접근의 방어 근거.
- 결정 권한은 **revenue/hotel manager**가 보유(자동화 아님) → 우리 "매니저 승인" 설계와 정합(GDPR Art.22).

---

## 3. Reputation 비용 — 보상 가격대의 상한을 정하는 변수

재형님이 말한 *"너무 비싸지 않으면서 평판 안 떨어뜨리는 가격대"* 의 정량 근거:

| 지표 | 수치 |
|------|------|
| 별점 1 하락 | 매출 **5~9% 감소** |
| 부정 리뷰 1건 | 월 약 **$15,494** 매출 손실 (추정) |
| 부정 리뷰 3건+ | 여행자 **79%가 예약 안 함** |
| 나쁜 리뷰 호텔 | 더 싸도 **40%가 회피** |

→ **walk를 잘못 처리하면 reputation 손실이 보상비를 압도**한다. 이것이 보상 가격대의 *하한(손님 만족)*과 *상한(과지출)* 사이를 정하는 힘이고, **reputation을 목적함수의 제약/비용으로 넣어야** 하는 정량 근거다(윤리 방어 내장).

---

## 4. ⚠️ 핵심 발견 — 우리 expected_cost 비용비 가정이 거꾸로일 수 있다

`src/growth_curve.py`:
```python
COST_RATIOS = [2, 5, 10]   # c_fn / c_fp  (빈방손실 / 오버부킹보상)
```
즉 **빈 방 손실이 walk 보상보다 2~10배 비싸다**고 가정.

**조사 결과 이 방향이 의심스럽다:**

| 비용 | 현실 추정 |
|------|----------|
| c_fn = 빈 방 손실 (취소 놓침) | ≈ **1 × ADR** (perishable, 회복 0) |
| c_fp = walk 비용 (취소 아닌데 오버부킹→이전) | 첫날 ADR + 교통 + **reputation(별점 5~9%·리뷰 $15k)** ⇒ **≥ 1~3 × ADR** |

→ reputation을 포함하면 **c_fp(walk) ≥ c_fn(빈방)** 이라 비율 `c_fn/c_fp ≤ 1`. 우리 코드의 `{2,5,10}`은 **반대 방향**이다.

**함의:**
1. walk가 빈방보다 비싸면 → **보수적 오버부킹**이 정답. 이건 "마찰·평판 최소화" 프레이밍을 오히려 **강화**한다(공격이 아니라 우리편).
2. **권고:** expected_cost 비용비 sweep에 **≤1 구간 추가**(예: `{0.3, 0.5, 1, 2}`)하거나, "참 비용비는 미지 → 범위로 제시, 업계는 walk가 비싸다는 쪽"이라고 명시. 현 `{2,5,10}`만 쓰면 "왜 빈방이 walk보다 훨씬 비싸다고 가정했나"에 답 못 함.
3. 단 reputation 비용은 호텔별 편차가 커서 **점추정 금지, sweep + 가정 명시**(design_18 KPI 규율과 동일).

---

## 5. 장면7 "피처 기반 보상 가격대" — 현실 정박 + 로드맵

재형님 의도(페르소나 노출 X → 체계화된 피처로 가격대)를 현실에 매핑:

| 우리 피처 | 현실 보상 차등 근거 |
|-----------|-------------------|
| 인원수(adults/children) | 가족·다인 → 대체 숙소 확보 난이도↑ → 보상↑ (관행) |
| lead_time(예약 시점) | 임박 예약 walk → 대안 부족 → 불만↑ |
| customer_type / 채널 | 로열티·등급별 보상 차등(브랜드 정책 실재) |
| (※ country) | **보상 차등에 국적 직접 사용 금지** — 차별. 전처리 재점검 메모 참조 |

- **1차 증거:** walk_sim A~E 아키타입(이미 피처로 정의된 페르소나)의 수락률 곡선 = 피처→가격대 매핑의 preliminary 증거.
- **로드맵(정직):** 전체 피처 조합 최적화 + 호텔별 보상 정책 fine-tune은 **실배포 협상 로그 수집 후**(ML②). 발표엔 "방법을 설계했고 1차 증거가 있다"까지.

---

## 6. 발표에서 사는 문장들

- 장면4~5: "오버부킹 수준은 우리가 지어낸 게 아니라 **한계비용=한계수익**이라는 호텔 RM 표준 결정법이고, risk-based 방식이 RevPAR가 높다는 연구가 있다."
- 장면6~7: "보상 가격대는 업계 walk 관행(첫날+교통+굿윌)과 reputation 비용(별점 1 하락 = 매출 5~9%)으로 상·하한이 정해진다. 우리는 그 사이를 **피처로** 찾는다."
- 비용비 정직: "빈 방 vs walk 비용비는 미지수다. reputation을 넣으면 walk가 더 비싸 **보수적 오버부킹**이 맞고, 우리는 그 범위를 sweep으로 제시한다."

---

## 7. 미결 / 다음 단계

| # | 항목 | 비고 |
|---|------|------|
| 1 | expected_cost 비용비 `{2,5,10}` → `≤1` 포함 재검토 | 4절. growth_curve 재실행 or 슬라이드 각주 |
| 2 | reputation을 목적함수 제약으로 수식화 | 장면5 EV에 walk 비용 = comp + λ·reputation |
| 3 | 보상 차등 피처에서 country 배제 명문화 | 전처리 재점검 메모 A-3와 연동 |
| 4 | 장면5 오버부킹 EV 곡선 실제 산출 | ✅ **완료** — 아래 §8 |

---

## 8. 슬라이드7 EV 곡선 산출 결과 (2026-06-05)

> 산출 스크립트: `src/overbooking_ev.py` → `results/overbooking_ev.{png,csv}`
> `sim_hotel.py`(Flexi RevPAR·walk_rate)는 목적이 달라 재사용 불가 → newsvendor 한계분석으로 신규 작성.

**모델 (§2.1 한계비용=한계수익의 정확한 시각화):**
노쇼로 비는 방을 메우려 K실 오버부킹. D=노쇼 수 ~ Poisson-binomial({risk_i})를 risk로 직접 계산(가정 아님, 실데이터 기대값).
`E[Profit(K)] = ADR·E[min(K,D)] − C_walk·E[max(K−D,0)]`,  비용비 `r = C_walk/ADR`.
최적해 = 고전 critical-ratio `P(D≥K) ≥ r/(1+r)`.

**입력 데이터:** `hub_stream.json`(현재 25k 경량판) test split, 일일 도착 코호트 162건(=test 일일 도착 중앙값) 표본. ADR 중앙값 €108. 모집단 평균 risk 0.231 / 실제 취소율 0.386(=문서 0.387과 정합).

**결과 (비용비 sweep):**

| 시나리오 | r=C_walk/ADR | 최적 K* | 근거 |
|---|---|---|---|
| 낙관 (협상 굿윌 하단) | 0.5 | **41** | §1.3 walk 부분보상 |
| 중립 (첫날 풀보상) | 1.0 | **40** | §1.3 첫날 ADR |
| 평판포함 (보수적) | 2.0 | **38** | §4 reputation 포함 시 walk≥ADR |

→ **E[노쇼]≈40 근처에서 곡선이 꺾인다** = "노쇼로 비는 만큼만 메운다"는 직관 그대로.
비용비를 0.5→2.0로 올리면 최적 K*가 41→38로 **보수화**(§4 정직 프레임을 곡선이 그대로 보여줌).

**정직한 한계(발표 각주용):**
1. K는 '고위험 풀만'이 아니라 property 일일 코호트(전체 risk 분포) 기준. 고위험 풀만 보는 뷰는 `--highrisk-only`(E[노쇼]≈147, K*≈145로 평행이동).
2. 비용비는 미지수 → 점추정 금지, 세 곡선의 범위로 제시.
3. hub_stream.json이 25k 경량판으로 다운샘플 → 분포는 보존되나 절대 수치는 일일 코호트 정규화값(슬라이드용 직관). 풀 119k 재실행 시 `--cohort`만 조정.

---

## 출처

- [Getting Walked From a Hotel — The Points Guy](https://thepointsguy.com/hotel/getting-walked-from-a-hotel-compensation/)
- [Hotel Overbookings Strategy — SiteMinder](https://www.siteminder.com/r/hotel-overbookings-pros-and-cons-strategy/)
- [Answering Questions: Hotel Overbooking & Walking Guests — Duetto](https://www.duettocloud.com/library/answering-questions-hotel-overbooking-walking-guests)
- [Overbooking Done Right — Revfine](https://www.revfine.com/overbooking-done-right/)
- [Overbooking Practices in Hotel Revenue Management — eCornell](https://ecornell.cornell.edu/courses/hospitality-and-foodservice-management/overbooking-practices-in-hotel-revenue-management/)
- [Online Reputation: How Hotels Lose Millions — Reflectfy](https://blog.reflectfy.com/online-reputation-how-hotels-are-losing-millions/)
- [The Cost of a Bad Review for Hotels — Deliverback](https://deliverback.com/blog/the-cost-of-a-bad-review-for-hotels/)
- [Overbooking and Performance in Hotel Revenue Management — ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S027843192500115X)
