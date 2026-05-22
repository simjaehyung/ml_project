# 프롬프트 하이퍼튜닝 프레임워크 (v2)

> 작성: 심재형 (PM) | 기준일: 2026-05-22
> 목적: Claim 1 (예측) + Claim 2 (Walk 협상 시뮬레이션) 프롬프트 체계적 실험 틀

---

## 기본 구조

프롬프트를 블록 단위로 분리하고 각 블록을 독립적으로 교체 가능하게 만든다.
ML 하이퍼파라미터 튜닝과 동일한 방식으로 접근한다.

```
Claim 1 (예측):
  [CONTEXT] + [FEATURES] + [TASK] + [OUTPUT]

Claim 2 (Walk 협상):
  Hotel Agent  → [HOTEL_ROLE] + [OFFER]        (규칙 기반, LLM 없음)
  Customer Agent → [ARCHETYPE] + [OVERBOOKING_CONTEXT] + [HOTEL_OFFER] + [ROUND_HISTORY] + [OUTPUT_FORMAT]
```

---

## Claim 1 — Zero-shot 취소 예측 프롬프트

### 블록 1: CONTEXT

| variant | 내용 |
|---|---|
| A | `A hotel booking record:` |
| B | `A guest made a hotel reservation with the following details:` |
| C | *(없음 — 피처 바로 시작)* |

### 블록 2: FEATURES

| variant | 내용 |
|---|---|
| A — 수치 나열 | `Country: {country}` `Lead time: {lead_time} days` `Special requests: {n}` `Parking: {parking}` `Market segment: {segment}` `ADR: €{adr}` `Previous cancellations: {prev_cancel}` |
| B — 자연어 변환 | `A guest from {country} booked {lead_time} days before check-in via {segment}. They made {n} special requests and {"required" if parking else "did not require"} parking. The room rate is €{adr}/night. They have cancelled {prev_cancel} previous bookings.` |
| C — SHAP 중요도 순 | A와 동일하되 SHAP 순위 순서로 나열 (country → parking → special_requests → lead_time → prev_cancel → segment → adr) |

### 블록 3: TASK

| variant | 내용 |
|---|---|
| A | `What is the probability (0.0 to 1.0) that this booking will be cancelled?` |
| B | `How likely is it that this guest will cancel? Rate from 0.0 (will not cancel) to 1.0 (will cancel).` |
| C | `Assess the cancellation risk of this booking on a scale from 0.0 to 1.0.` |

### 블록 4: OUTPUT

| variant | 내용 |
|---|---|
| A | `Answer with a single number only.` |
| B | `Respond in JSON: {"probability": 0.XX}` |
| C | `Provide the probability and one key reason. Format: PROB \| REASON` |

### 평가 지표

- **PR-AUC** — 메인 (LGBM과 동일 기준으로 비교)
- **Calibration** — 예측값 분포가 실제 취소율(37%)과 유사한가

### 탐색 조합 (우선순위)

```
1차: B2-A3-A4  (자연어 + 확률 질문 + 숫자만)  ← 시작점
2차: A2-A3-A4  (수치 나열 vs 자연어 비교)
3차: B2-A3-B4  (JSON 출력 안정성 확인)
4차: C2-A3-A4  (SHAP 순서 효과 확인)
```

---

## Claim 2 — Walk 보상 협상 시뮬레이션 프롬프트

### 다중 에이전트 구조

```
[Hotel Agent]                        [Customer Agent]
  규칙 기반                              LLM
  초기 오퍼 계산                         아키타입 페르소나
  라운드별 조정                           수락 / 카운터 / 거절
        ↓                                      ↑
        └────────── JSON 메시지 교환 ───────────┘
```

Hotel Agent는 LLM을 사용하지 않는다. 오퍼 금액은 규칙으로 고정.
LLM은 Customer Agent만 담당 — 불확실한 것은 고객 반응뿐.

---

### Customer Agent 프롬프트 블록

#### 블록 1: ARCHETYPE (아키타입 페르소나)

| variant | 내용 |
|---|---|
| A — 인구통계만 | `You are a traveler from {country} who booked via {segment}. Your party: {adults} adults{", " + str(children) + " children" if children > 0 else ""}.` |
| B — 여행 맥락 포함 | A에 추가: `This appears to be a {"leisure" if segment in ["Online TA","Direct"] else "business"} trip. You checked in {lead_time} days after booking.` |
| C — 아키타입 명시 | `You are Archetype {archetype_label}: {archetype_description}` (예: "Archetype D: budget-conscious solo OTA traveler, price-sensitive, no special requirements") |

#### 블록 2: OVERBOOKING_CONTEXT (상황 설명)

| variant | 내용 |
|---|---|
| A — 사실 전달 | `You have arrived at the hotel. The hotel informs you that your room is unavailable due to overbooking.` |
| B — 감정 맥락 포함 | A에 추가: `You have already travelled to reach the hotel. You have {n} special requests on record.` |

#### 블록 3: HOTEL_OFFER (오퍼 제시)

| variant | 내용 |
|---|---|
| A — 중립 | `The hotel offers €{offer_amount} compensation and will arrange a comparable room at a nearby hotel.` |
| B — 대안 명시 | `The hotel offers €{offer_amount} compensation. They will cover your transfer to Hotel {alt_hotel_name} (same star rating, {distance}km away).` |

#### 블록 4: ROUND_HISTORY (Round 2에서만 사용)

```
Previous round:
  Hotel offered: €{prev_offer}
  Your response: {prev_decision} / counter: €{prev_counter}
  Hotel's adjusted offer: €{current_offer}
```

Round 1에서는 이 블록을 포함하지 않는다.

#### 블록 5: OUTPUT_FORMAT (강제 JSON)

모든 variant에서 반드시 JSON만 출력하도록 강제한다.

```
Round 1 출력 스키마:
{"decision": "ACCEPT" | "COUNTER" | "REJECT", "counter_amount": 숫자 | null, "reason": "한 문장"}

Round 2 출력 스키마:
{"decision": "ACCEPT" | "REJECT", "reason": "한 문장"}
```

출력 형식 지시:
```
Respond ONLY in JSON. No other text.
{"decision": "ACCEPT" or "COUNTER" or "REJECT", "counter_amount": number or null, "reason": "one sentence"}
```

### 평가 지표

- **아키타입별 수락 임계값 분포** — 아키타입 간 차이가 통계적으로 유의한가
- **방향성 일치** — 오퍼 금액↑ → 수락률↑ 인가
- **출력 파싱 성공률** — JSON 형식이 안정적으로 나오는가 (목표 95%+)
- **카운터 오퍼 분포** — 아키타입별 요구 금액 분산이 다른가

### 탐색 조합 (우선순위)

```
1차: B1-A2-A3-B5  (맥락 포함 페르소나 + 중립 오퍼 + JSON)  ← 시작점
2차: C1-A2-A3-B5  (아키타입 명시 vs 맥락 포함 비교)
3차: B1-B2-B3-B5  (감정 맥락 + 대안 명시 효과)
4차: A1-A2-A3-B5  (페르소나 없음 베이스라인)
```

---

## 실험 운영 방식

### 샘플 크기

```
Claim 1:
  전체 테스트셋: 40,687건
  튜닝용 샘플: 200건 (세그먼트별 균등)
  최적 조합 확정 후 전수 실행

Claim 2:
  아키타입 5개 × 보상 구간 5개 × 40회 = 1,000회
  튜닝용: 아키타입 2개 × 구간 3개 × 10회 = 60회로 먼저 방향 확인
```

### 결과 기록 템플릿

```
실험 ID: C1-{CONTEXT}-{FEATURES}-{TASK}-{OUTPUT}
실험 ID: C2-{ARCHETYPE}-{CONTEXT}-{OFFER}-{OUTPUT}

| 실험 ID         | PR-AUC (C1) | 수락임계값 분산 (C2) | 파싱 성공률 | 비고 |
|----------------|-------------|-------------------|------------|------|
| C1-B-B-A-A    |             |                   |            |      |
| C2-B-A-A-B5   |             |                   |            |      |
```

### 결정 원칙

- Claim 1: PR-AUC 최대화 조합 선택
- Claim 2: 아키타입별 수락 임계값 분산 최대 + 파싱 성공률 95%+ 조합 선택
- 두 목표가 충돌하면 Claim 1 우선 (방어 논리의 핵심)

---

## 고정 원칙 (모든 variant 공통)

1. 해석 언어 금지 — `"suggesting uncertain plans"` 같은 표현 삽입 금지
2. 심리 레이어 명시 금지 — `certainty_need`, `price_sensitivity` 직접 주입 금지
3. 정답 암시 금지 — 피처 나열 순서가 결론을 유도하지 않도록
4. 출력 형식 항상 고정 — 파싱 실패는 실험 오염
5. Hotel Agent는 LLM 없이 규칙만 — 불확실성 오염 방지
