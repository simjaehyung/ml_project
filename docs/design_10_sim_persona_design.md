# Flexi 시뮬레이션 — LLM 에이전트 페르소나 설계

> 작성: 심재형 (PM) | 기준일: 2026-05-13
> 목적: 최종발표 피날레 — Flexi 파라미터 검증 시뮬레이션의 방법론 문서

---

## 1. 왜 LLM 에이전트인가

### 기존 호텔 RM 시뮬레이션의 한계

전통적인 RevMan 시뮬레이션(대표 논문: IEEE 2015)은 취소 패턴을 통계적 분포로 모델링한다.

```
[기존 방식]
  예약 도착률 λ ~ Poisson
  취소 확률 p ~ Beta(α, β)
  → 몬테카를로 전진 시뮬레이션
  → 오버부킹 한도 최적화
```

이 구조의 한계:
- 모든 고객을 동일한 분포에서 샘플링 — 이질성 무시
- "Online TA로 예약한 포르투갈인이 특별요청 없이 180일 전 예약"과 "Direct로 예약한 독일인이 요청 3개 + 주차"를 동일하게 취급
- 할인 오퍼에 대한 반응 모델 없음 — 행동 경제학적 요소 부재

### LLM 에이전트가 해결하는 것

```
[우리의 방식]
  실제 예약 데이터 피처 → 자연어 페르소나
  → LLM이 맥락을 추론 → 의사결정
  → 이질적 반응 패턴 포착 가능
```

핵심 차이: **동일한 Flexi 오퍼라도 페르소나에 따라 다른 결정이 나온다.**

---

## 2. 이 아이디어의 연구사적 위치

```
[연구 흐름 1]              [연구 흐름 2]              [연구 흐름 3]
전통 호텔 RM 시뮬레이션    ABM 관광 행동 모델         LLM 소비자 행동 시뮬레이션
  ↓                          ↓                          ↓
IEEE 2015                 ABM + ML (2025)           AgentSociety (2025)
몬테카를로 오버부킹        룰 기반 관광객 에이전트    1만+ LLM 에이전트
                                    ↘               ↙
                             [공백 지점]
               "실제 예약 데이터 기반 LLM 게스트 에이전트 시뮬레이션"
                   ← 직접 다루는 선행 연구 없음
```

참고 논문:
- A Simulation-Based Overbooking Approach For Hotel Revenue Management (IEEE 2015)
- AgentSociety: Large-Scale LLM-Driven Simulation (arXiv 2502.08691)
- LLM-Based Multi-Agent System for Consumer Behavior Simulation (arXiv 2510.18155)
- Agent Based Modeling and AI integration for smart tourism simulations (2025)

---

## 3. 페르소나 설계 원칙

### 원칙: SHAP 결과로 정당화된 피처만 사용

페르소나를 구성하는 7개 피처는 전부 SHAP Top 10 내에 있는 것들이다.  
"왜 이 피처를 선택했는가"라는 질문에 데이터로 답할 수 있다.

| 피처 | SHAP 순위 (LGBM) | 행동적 함의 | 에이전트 심리 레이어 |
|------|----------------|------------|-------------------|
| `country` | 1위 (1.064) | 국적별 취소 문화 차이 | STATIC PROFILE |
| `required_car_parking_spaces` | 2위 (0.680) | 주차 필요 = 장소 의존성 높음 | 확실성 욕구 (Certainty Need) |
| `total_of_special_requests` | 3위 (0.644) | 요청 수 = 이 호텔이어야 하는 이유 | 헌신도 (Commitment) |
| `lead_time` | 4위 (0.531) | 예약 시점 = 여행 확실성 | 유연성 태도 (Flexibility Attitude) |
| `previous_cancellations` | 5위 (0.394) | 취소 이력 = 행동 패턴 | 감정 상태 (Emotional State) |
| `market_segment` | 6위 (0.371) | 예약 채널 = 가격 민감도 | 가격 민감도 (Price Sensitivity) |
| `adr` | 9위 (0.253) | 절대 가격 = 할인 매력도 | 오퍼 계산 (Offer) |

---

## 4. 심리 레이어 설계 (AgentSociety 구조 차용)

AgentSociety(2502.08691)의 **Emotions × Needs × Cognition 3층 모델**을 호텔 예약 도메인에 적용.

```
[AgentSociety 원본]       [우리의 적용]
─────────────────────     ──────────────────────────────────
Emotions Layer         →  Emotional State
  (현재 감정 상태)           취소 확률 + lead_time + prev_cancel
                             → "UNCERTAIN / COMMITTED / HABIT OF CANCELLING"

Needs Layer            →  Commitment + Certainty Need
  (현재 필요와 욕구)          total_of_special_requests + parking + children
                             → "LOW / MEDIUM / HIGH"

Cognition Layer        →  Price Sensitivity + Flexibility Attitude
  (인지적 처리 방식)          market_segment + adr + customer_type + lead_time
                             → "가격 비교형 / 관계 우선형 / 경직된"
```

### 5개 파생 심리 지표

```python
derive_commitment(row)         # 특별 요청 수 + 주차 → 여행 투자 수준
derive_price_sensitivity(row)  # 채널 + ADR → 가격 민감도
derive_certainty_need(row)     # 어린이 + 주차 + 특별 요청 → 방 배정 확실성 욕구
derive_flexibility_attitude(row)  # 고객 유형 + lead_time + prev_cancel → 유연성 태도
derive_emotional_state(row, cancel_prob)  # 취소 확률 + 상황 → 현재 감정
```

### 추론 구조 (LLM-Based Multi-Agent 2510.18155 차용)

프롬프트가 에이전트에게 4단계 추론을 강제한다:

```
1. 이 여행에 얼마나 확신하는가? (Emotional State + Commitment)
2. €X 할인이 나에게 의미 있는가? (Price Sensitivity + 절대 금액)
3. 방 배정 변경이 문제인가? (Certainty Need + 특별 요청)
4. Flexi 조건이 내 상황에 맞는가? (Flexibility Attitude)
→ decision: ACCEPT_FLEXI / DECLINE_FLEXI / CANCEL
```

---

## 5. 시뮬레이션 규모와 통계적 의의

### 규모: 약 20,000 에이전트

```
테스트셋: 40,687건 (2017-01 ~ 2017-08)
  ↓ cancel_prob ≥ 0.40 필터
고위험 풀: ~20,000건 (추정)
  ↓ 전수 실행 (샘플링 없음)
LLM 에이전트 ~20,000명
```

### 왜 이 규모가 필요한가

국적 × 채널 × lead_time 구간 세그먼트별 수락률 분포를 보려면:
- PRT × Online TA × 180일+ 에이전트가 최소 30건 이상 있어야 통계적으로 의미 있음
- 세그먼트 수: 국적 11개 × 채널 5개 × lead_time 구간 5개 = 275개 조합
- 각 셀 최소 30건 → 최소 8,000건 필요 → 20,000건이면 대부분의 셀 충족

### 실행 추정 시간 (Qwen2.5-14B, A5000 × 2)

```
20,000건 × 2초/건 / 16 스레드 = 약 41분
```

야간 실행 권장.

---

## 6. 발표에서 "우리가 주장할 수 있는 것"

### 방어 가능한 주장

> "우리는 전통적 몬테카를로 시뮬레이션이 포착하지 못하는 고객 이질성을 LLM 에이전트로 모델링했습니다.  
> 2년치 실제 예약 데이터의 SHAP 검증된 7개 피처로 약 20,000명의 페르소나를 구성하고,  
> AgentSociety의 Emotions × Needs × Cognition 3층 심리 모델을 호텔 도메인에 적용했습니다."

### 예상 공격 Q&A

| 공격 | 방어 |
|------|------|
| "LLM 반응 = 실제 행동이라는 근거가 있나?" | "직접 검증이 아니라 시뮬레이션입니다. 할인율 파라미터의 방향성(높은 할인 → 높은 수락률)이 상식에 부합하는지를 확인하는 것이 목적입니다." |
| "왜 이 7개 피처인가?" | "SHAP Top 10 중 LLM이 자연어로 해석 가능한 피처를 선택했습니다. SHAP 순위가 피처 선택의 근거입니다." |
| "500건으로도 충분하지 않나?" | "국적 × 채널 × lead_time 세그먼트별 분포를 보려면 각 셀에 최소 30건이 필요합니다. 20,000건이어야 통계적으로 의미 있는 세그먼트 분석이 가능합니다." |
| "Qwen이 실제 호텔 고객처럼 추론하나?" | "프롬프트에 4단계 추론을 강제하고 5개 심리 지표를 제공합니다. 에이전트는 자신의 상황을 명시적으로 검토하고 결정합니다." |

---

## 7. 실행 계획

| 날짜 | 작업 |
|------|------|
| Week 5 초 (5/28) | 학교 서버 셋업 (sim_setup.sh) + 모델 다운로드 |
| 5/29 저녁 | vLLM 시작 + dry-run 50건 확인 |
| 5/30 야간 | 전수 실행 (20,000건, --all 모드) |
| 5/31 | sim_analyze.py 결과 분석 + 세그먼트별 인사이트 |
| Week 6 (6/3) | 최종발표 슬라이드 통합 |

---

## 미결 항목

| # | 항목 | 시점 |
|---|------|------|
| A | min_prob 0.40 vs 0.50 — 규모 vs 신뢰도 | 5/28 결정 |
| B | 세그먼트별 결과 중 발표에서 강조할 인사이트 | 5/31 분석 후 |
| C | walk_rate 2% 미달 시 오버부킹 버퍼 조정 방법 | 결과 보고 결정 |
