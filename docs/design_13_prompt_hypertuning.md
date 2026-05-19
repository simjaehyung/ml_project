# 프롬프트 하이퍼튜닝 프레임워크

> 작성: 심재형 (PM) | 기준일: 2026-05-18  
> 목적: Claim 1 (예측) + Claim 2 (시뮬레이션) 프롬프트 체계적 실험 틀

---

## 기본 구조

프롬프트를 블록 단위로 분리하고 각 블록을 독립적으로 교체 가능하게 만든다.  
ML 하이퍼파라미터 튜닝과 동일한 방식으로 접근한다.

```
Claim 1 (예측):   [CONTEXT] + [FEATURES] + [TASK] + [OUTPUT]
Claim 2 (시뮬레이션): [AGENT] + [SITUATION] + [OFFER] + [DECISION] + [OUTPUT]
```

각 블록은 variant A / B / C 중 하나를 선택한다.  
최적 조합을 찾는 것이 목표.

---

## Claim 1 — Zero-shot 취소 예측 프롬프트

### 블록 1: CONTEXT (도입부)

| variant | 내용 |
|---|---|
| A | `A hotel booking record:` |
| B | `A guest made a hotel reservation with the following details:` |
| C | *(없음 — 피처 바로 시작)* |

### 블록 2: FEATURES (피처 전달 방식)

| variant | 내용 |
|---|---|
| A — 수치 나열 | `Country: {country}` `Lead time: {lead_time} days` `Special requests: {n}` `Parking: {parking}` `Market segment: {segment}` `ADR: €{adr}` `Previous cancellations: {prev_cancel}` |
| B — 자연어 변환 | `A guest from {country} booked {lead_time} days before check-in via {segment}. They made {n} special requests and {"required" if parking else "did not require"} parking. The room rate is €{adr}/night. They have cancelled {prev_cancel} previous bookings.` |
| C — SHAP 중요도 순 | A와 동일하되 SHAP 순위 순서로 나열 (country → parking → special_requests → lead_time → prev_cancel → segment → adr) |

### 블록 3: TASK (질문)

| variant | 내용 |
|---|---|
| A | `What is the probability (0.0 to 1.0) that this booking will be cancelled?` |
| B | `How likely is it that this guest will cancel? Rate from 0.0 (will not cancel) to 1.0 (will cancel).` |
| C | `Assess the cancellation risk of this booking on a scale from 0.0 to 1.0.` |

### 블록 4: OUTPUT (출력 형식)

| variant | 내용 |
|---|---|
| A | `Answer with a single number only.` |
| B | `Respond in JSON: {"probability": 0.XX}` |
| C | `Provide the probability and one key reason. Format: PROB | REASON` |

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

## Claim 2 — Flexi 시뮬레이션 프롬프트

### 블록 1: AGENT (에이전트 정의)

| variant | 내용 |
|---|---|
| A — 없음 | 에이전트 정의 없이 상황 바로 시작 |
| B — 인구통계 | `You are a traveler from {country} who booked a hotel through {segment}.` |
| C — PersonaHub 매칭 | LLM이 SHAP 프로파일을 보고 PersonaHub에서 유사 페르소나 선택 후 삽입 |

### 블록 2: SITUATION (예약 상황)

| variant | 내용 |
|---|---|
| A — 사실 나열 | `Your booking details: check-in in {lead_time} days / {n} special requests / {"parking needed" if parking else "no parking"} / rate: €{adr}/night / previous cancellations: {prev_cancel}` |
| B — 자연어 서술 | `You booked this hotel {lead_time} days from now. {"You have specific room requirements." if n>0 else "You have no specific requirements."} {"You need parking." if parking else ""} Your room costs €{adr} per night.` |
| C — 맥락 추가 | B에 여행 목적 추정 추가: `Based on your booking pattern, this appears to be a {"leisure" if segment in ["Online TA","Direct"] else "business"} trip.` |

### 블록 3: OFFER (Flexi 오퍼 제시)

| variant | 내용 |
|---|---|
| A — 중립 | `The hotel offers you a {discount}% discount if you agree to move to a Flexible room. Flexible rooms may be reassigned based on availability.` |
| B — 이득 프레임 | `You can save €{saving} on your total stay by accepting a Flexible room arrangement with a {discount}% discount.` |
| C — 조건 명시 | `The hotel proposes: {discount}% discount in exchange for flexible room assignment. This means your specific room type may change, though all standard amenities are maintained.` |

### 블록 4: DECISION (결정 요청)

| variant | 내용 |
|---|---|
| A — 개방 | `What do you decide?` |
| B — 상황 환기 | `Given your travel situation and this offer, what do you decide?` |
| C — 구조 없는 힌트 | `Consider whether this trip is firm, whether the discount matters to you, and whether room flexibility is acceptable.` |

> **주의**: D variant (4단계 명시 강제)는 사용하지 않는다. 이전 설계의 과도한 유도 방식.

### 블록 5: OUTPUT (출력 형식)

| variant | 내용 |
|---|---|
| A | `Choose one: ACCEPT_FLEXI / DECLINE_FLEXI / CANCEL` |
| B | `{"decision": "ACCEPT_FLEXI" or "DECLINE_FLEXI" or "CANCEL", "reason": "one sentence"}` |
| C | `Decision (ACCEPT_FLEXI / DECLINE_FLEXI / CANCEL) and your main reason in one sentence.` |

### 평가 지표

- **세그먼트간 수락률 분산** — 아크타입/세그먼트별로 수락률이 다르게 나오는가
- **방향성 일치** — 할인율↑ → 수락률↑, lead_time↑ → 취소율↑ 인가
- **출력 파싱 성공률** — JSON 형식이 안정적으로 나오는가

### 탐색 조합 (우선순위)

```
1차: B1-B2-A3-B4-B5  (자연어 + 중립 오퍼 + 상황 환기 + JSON)  ← 시작점
2차: A1-B2-A3-A4-B5  (에이전트 정의 없음 vs 있음 비교)
3차: B1-B2-B3-B4-B5  (이득 프레임 효과 확인)
4차: C1-B2-A3-B4-B5  (PersonaHub 매칭 효과 확인)
```

---

## 실험 운영 방식

### 샘플 크기

튜닝 단계에서는 전수 실행하지 않는다.

```
전체 고위험 풀: ~20,000건
튜닝용 샘플: 200건 (세그먼트별 균등 샘플링)
최종 조합 확정 후 전수 실행
```

### 결과 기록 템플릿

```
실험 ID: C1-{CONTEXT}-{FEATURES}-{TASK}-{OUTPUT}
실험 ID: C2-{AGENT}-{SITUATION}-{OFFER}-{DECISION}-{OUTPUT}

| 실험 ID       | PR-AUC (C1) | 세그먼트 분산 (C2) | 파싱 성공률 | 비고 |
|---------------|-------------|-----------------|------------|------|
| C1-A-B-A-A   |             |                 |            |      |
| C1-B-B-A-A   |             |                 |            |      |
| C2-B-B-A-B-B |             |                 |            |      |
```

### 결정 원칙

- Claim 1: PR-AUC 최대화 조합 선택
- Claim 2: 세그먼트 분산 최대 + 파싱 성공률 90%+ 조합 선택
- 두 목표가 충돌하면 Claim 1 우선 (방어 논리의 핵심이므로)

---

## 고정 원칙 (모든 variant 공통)

1. 해석 언어 금지 — `"suggesting uncertain plans"` 같은 표현 넣지 않는다
2. 심리 레이어 명시 금지 — `certainty_need`, `price_sensitivity` 등 직접 주입하지 않는다
3. 정답 암시 금지 — 피처 나열 순서가 결론을 유도하지 않도록 한다
4. 출력 형식은 항상 고정 — 파싱 실패는 실험 오염
