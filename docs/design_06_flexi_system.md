# Flexi Rate 시스템 설계 문서

> 작성: 심재형 (PM) | 최초: 2026-05-06 | 전면 개정: 2026-05-13
> 개정 이유: Pool A/B 이분 구조 폐기 → AI 에이전트 기반 시뮬레이션으로 전환

---

## 1. 핵심 개념 — 취소 예측 기반 정밀 오버부킹

### 기존 오버부킹 vs Flexi 오버부킹

```
기존 방식 (블라인드 오버부킹)
  과거 평균 취소율 35% → 전체 예약의 35%를 일괄 초과 판매
  → 어느 예약이 취소될지 모르고 찍는 것

Flexi 방식 (정밀 오버부킹)
  모델이 "이 예약들은 취소될 가능성이 높다"고 예측
  → 그 예약자들에게 Flexi 오퍼 제시
  → 수락 여부에 따라 수익 구조가 결정됨
```

**핵심 주장:** 취소 예측 정확도(PR-AUC)가 높을수록 walk 발생 없이 수익을 확보하는 능력이 높아진다. 이 시스템에서 **모델 성능이 곧 운영 수익과 직결**된다.

---

## 2. 운영 구조

### 객실 인벤토리 분류

```
호텔 물리 객실 N실
  │
  ├─ Standard 풀
  │    cancel_prob ≤ threshold → 정상 확정
  │    정가 청구, 즉시 확정
  │
  └─ Flexi 풀 (고위험 예약 대상)
       cancel_prob > threshold → Flexi 오퍼 제시
       할인가 청구 (5~18%), 체크인 D-1 확정
       수락 시: 할인 적용된 수익 확보
       거절 시: 실제 취소 여부에 따라 결정
```

### 할인율 공식 (확정)

```
할인율 = 5% + (cancel_prob − 0.5) × 26%
         단, 5% ≤ 할인율 ≤ 18%
```

| cancel_prob | 할인율 | 손님 체감 |
|------------|--------|----------|
| 0.60 | 7.6% | 소폭 저렴 |
| 0.70 | 10.2% | 매력적 |
| 0.80 | 12.8% | 가격 메리트 큼 |
| 0.90 | 15.4% | 명확한 트레이드오프 |
| ≥ 0.97 | 18.0% (상한) | 최대 할인 |

### 일일 운영 흐름

| 시각 | 동작 |
|------|------|
| 매일 10:00 | 익일 도착 예약 취소 확률 재계산 |
| 17:00 | Flexi 오퍼 대상 확정 (threshold 기준) |
| 17:30 | 매니저 경계 케이스 검토 + 최종 승인 |
| 18:00 | 대상 예약자에게 오퍼 발송 |

---

## 3. 커뮤니케이션 전략 — 정보 분리 원칙

손님에게 "당신의 취소 확률이 80%라서 Flexi 대상입니다"라는 사실은 절대 공개하지 않는다.

| 호텔 내부 정보 | 손님에게 보이는 것 |
|--------------|-----------------|
| 취소 확률 0.84 | 없음 |
| "High Risk 분류" | 없음 |
| 모델이 이 예약 선택 | 없음 |

**손님에게 보이는 것은 오직 상품 조건의 차이뿐이다.**

```
┌─────────────────────────────────┐
│  Standard Rate         €120/박  │
│  ✓ 즉시 객실 확정               │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│  Flexi Rate            €102/박  │  ← 15% 할인
│  ✓ 동일 등급 객실               │
│  ℹ 객실은 체크인 전날 최종 배정  │
│  ✓ 미배정 시 전액 환불 + 보상    │
└─────────────────────────────────┘
```

### 자기선택 효과 (self-selection)

할인에 매력을 느껴 Flexi를 선택하는 손님 = 일정이 유동적인 손님일 가능성이 높다.
모델이 예측한 고위험 + 손님의 자발적 Flexi 선택이 겹치면 실제 취소율이 더 높아져 walk 위험이 줄어든다.
이것이 Flexi 시스템의 구조적 안정성 원천이다.

GDPR Art.22 준수: 자동화된 라우팅이지만 최종 결정은 매니저 승인 후 발송.

---

## 4. 시뮬레이션 — 구 설계의 문제와 AI 에이전트 전환

### 구 설계 (Pool A / Pool B) 와 그 한계

이전 설계는 두 개의 분리된 손님 풀을 가정했다.

```
[구 설계]
Pool A — 기존 예약자 (실제 데이터)
Pool B — 신규 Flexi 구매자 (가상의 외부 수요)
  → Pool A가 취소하면 Pool B가 그 자리를 채운다
```

**구조적 약점:** Pool B의 전환율(`conversion_rate`)은 데이터가 없는 반사실적 파라미터다.
"왜 0.85인가"라는 질문에 어떤 값을 써도 방어하기 어렵다.
이론(Fay & Xie 2008, Probabilistic Selling)은 Pool B의 존재를 정당화하지만, 크기(magnitude)는 정당화하지 못한다.

### 신 설계 — AI 에이전트로 Pool B 제거

```
[신 설계]
Pool A 고위험 예약자 (cancel_prob > threshold)
  → 각자 LLM 에이전트로 시뮬레이션
  → ACCEPT_FLEXI / DECLINE_FLEXI / CANCEL 결정
  → 결정에 따라 수익 구조 결정
```

**Pool B 불필요.** 고위험 예약자들이 Flexi 오퍼에 어떻게 반응하는지를 직접 시뮬레이션하면 반사실적 외부 수요를 가정할 필요가 없다.

---

## 5. AI 에이전트 시뮬레이션 설계

### 에이전트 규모 및 구성

```
테스트셋: 40,687건 (2017-01 ~ 2017-08)
  ↓ cancel_prob ≥ 0.40 필터
고위험 풀: 13,355건
  ↓ 전수 실행 (샘플링 없음)
LLM 에이전트: 13,355명
```

각 에이전트는 **실제 예약 피처로 구성된 페르소나**를 가진다.
합성 데이터가 아니라 실제 호텔 예약 기록에서 파생된 것이 핵심이다.

### 페르소나 구성 피처 (SHAP 순위 기반)

| 피처 | SHAP 순위 (LGBM) | 에이전트 심리 변환 |
|------|----------------|-----------------|
| `country` | 1위 | 국적별 취소 문화 → STATIC PROFILE |
| `required_car_parking_spaces` | 2위 | 주차 필요 = 장소 의존성 → 확실성 욕구 |
| `total_of_special_requests` | 3위 | 요청 수 = 이 호텔이어야 하는 이유 → 헌신도 |
| `lead_time` | 4위 | 예약 시점 = 여행 확실성 → 유연성 태도 |
| `previous_cancellations` | 5위 | 취소 이력 = 행동 패턴 → 감정 상태 |
| `market_segment` | 6위 | 예약 채널 = 가격 민감도 |
| `adr` | 9위 | 절대 가격 → 할인 매력도 계산 |

피처 선택의 근거는 SHAP 분석 결과다. "왜 이 피처인가"에 데이터로 답할 수 있다.

### 심리 레이어 — AgentSociety 3층 모델 적용

AgentSociety(arXiv 2502.08691)의 Emotions × Needs × Cognition 구조를 호텔 도메인에 적용했다.

```
Emotions  →  Emotional State
               cancel_prob + lead_time + prev_cancellations
               "UNCERTAIN / COMMITTED / HABIT OF CANCELLING"

Needs     →  Commitment Level + Certainty Need
               total_of_special_requests + parking + children
               "LOW / MEDIUM / HIGH"

Cognition →  Price Sensitivity + Flexibility Attitude
               market_segment + adr + customer_type + lead_time
               "가격 비교형 / 관계 우선형 / 경직된"
```

### 에이전트 추론 구조 (4단계 강제)

LLM-Based Multi-Agent Consumer Behavior Simulation (arXiv 2510.18155)의 구조화된 추론 방식을 적용. 에이전트는 다음 4개 질문에 순서대로 답하도록 프롬프트로 강제된다.

```
1. 이 여행에 얼마나 확신하는가? (Emotional State + Commitment)
2. €X 할인이 나에게 의미 있는가? (Price Sensitivity + 절대 금액)
3. 방 배정 변경이 문제인가? (Certainty Need + special_requests)
4. Flexi 조건이 내 유연성과 맞는가? (Flexibility Attitude)
→ decision: ACCEPT_FLEXI / DECLINE_FLEXI / CANCEL
```

### 의사결정 → 호텔 수익 매핑

| 에이전트 결정 | 호텔 수익 | 해석 |
|-------------|----------|------|
| `ACCEPT_FLEXI` | ADR × (1 − discount/100) × nights × (1 − cancel_prob × 0.5) | 할인된 확정 수익 — 취소 확률도 50% 감소 (Flexi 약정 효과) |
| `CANCEL` | ADR × nights × 0.45 | 즉시 취소 → 재판매 시도 (45% 성공 가정, 보수적) |
| `DECLINE_FLEXI` + 실제 취소 | ADR × nights × 0.45 | 거절했는데 결국 취소 → 재판매 |
| `DECLINE_FLEXI` + 실제 체크인 | ADR × nights (full) | 거절 + 이행 → 정상 수익 |

### Walk Rate 계산 (정규 근사 모델)

Flexi 수락자(ACCEPT_FLEXI) 집합에서 실제 도착 수의 분포를 모델링한다.

```python
# 각 수락자는 독립 베르누이(p_show)
p_show = 1 - cancel_prob × FLEXI_CANCEL_REDUCTION  # 0.50

expected = p_show.sum()
variance = (p_show × (1 - p_show)).sum()

# 호텔 오버부킹 버퍼 5% 적용
capacity = expected × 1.05

# walk_rate = P(실제 도착 > 수용 가능)
walk_rate = 1 - norm.cdf(capacity, loc=expected, scale=sqrt(variance))
```

목표: **walk_rate < 2%**

---

## 6. 시뮬레이션 실행 구조

### 코드 파일 구성

```
src/
  sim_agent.py      LLM 게스트 에이전트 — 페르소나 생성 + Flexi 반응
  sim_hotel.py      호텔 환경 — RevPAR / walk_rate 계산
  sim_run.py        실행 오케스트레이터 — 배치 실행 + 저장
  sim_analyze.py    결과 분석 + 3종 시각화
  sim_setup.sh      학교 서버 셋업 (vLLM + Qwen2.5-14B)
```

### 실행 명령

```bash
# 학교 서버 (야간 전수 실행, ~28분)
python src/sim_run.py --all --workers 16

# 분석
python src/sim_analyze.py
```

### 산출물

| 파일 | 내용 |
|------|------|
| `results/sim_responses.jsonl` | 에이전트별 결정 + 이유 (13,355건) |
| `results/sim_threshold_sweep.png` | 임계값 × RevPAR / walk_rate |
| `results/sim_acceptance_breakdown.png` | 국적별 · 채널별 수락률 |
| `results/sim_prob_vs_acceptance.png` | 취소 확률 구간별 결정 분포 |
| `results/sim_sweep_results.csv` | 임계값별 수치 테이블 |

---

## 7. 연구사적 포지셔닝

```
[연구 흐름 1]              [연구 흐름 2]              [연구 흐름 3]
전통 호텔 RM 시뮬레이션    ABM 관광 행동 모델         LLM 소비자 행동 시뮬레이션
IEEE 2015                 ABM + ML (2025)           AgentSociety / CitySim (2025)
몬테카를로 오버부킹        룰 기반 관광객 에이전트    1만+ LLM 에이전트
        ↘                          ↓                   ↙
                    [공백 지점]
        "실제 예약 데이터 기반 LLM 게스트 에이전트로
         Flexi 파라미터를 검증한 호텔 RM 시뮬레이션"
                    ← 직접 다루는 선행 연구 없음
```

이 시뮬레이션이 기존 연구와 다른 점:
1. **실제 데이터 기반 페르소나** — 합성 에이전트가 아니라 2년치 실제 예약 기록에서 파생
2. **SHAP 검증된 피처 선택** — "왜 이 피처인가"에 데이터로 답할 수 있음
3. **심리 레이어 도메인 적용** — AgentSociety 구조를 호텔 예약 결정에 특화

---

## 8. 평가 지표 및 예상 결과 구조

### 3개 핵심 지표

```
지표 1 — RevPAR 개선율
  (Flexi 시나리오 수익 − 기준선 수익) / 기준선 수익 × 100
  임계값별 sweep → 최대화 임계값 탐색

지표 2 — Walk Rate
  walk_rate < 2% 조건 내에서의 최적 임계값
  목표: 손님을 내보내는 일이 거의 없어야 함

지표 3 — 세그먼트별 수락률
  국적 × 채널 × lead_time 구간별 ACCEPT_FLEXI 비율
  → "어떤 유형의 고객이 Flexi를 받아들이는가" 인사이트
```

### 발표에서 보여줄 최종 숫자 형태

```
[임계값 sweep 결과]
  threshold 0.50 → accept_rate A%, walk_rate X%, RevPAR +Y%
  threshold 0.60 → accept_rate B%, walk_rate X%, RevPAR +Y%  ← ★ 최적
  threshold 0.70 → accept_rate C%, walk_rate X%, RevPAR +Y%

[세그먼트 인사이트]
  Online TA × lead_time > 90일 → 수락률 가장 높음 (가격 탐색형)
  Direct 예약 × special_req ≥ 2 → 수락률 낮음 (이 호텔이어야 하는 손님)
  PRT 국적 × prev_cancel ≥ 1 → 수락보다 CANCEL이 많음 (취소 패턴 반복)
```

### PR-AUC와 운영 수익의 연결

```
PR-AUC 향상 → 취소 예측 정확도 향상
  → 고위험 예약을 더 정확하게 식별
  → walk_rate가 낮아지는 동시에 RevPAR는 높아짐
  → 같은 walk_rate 제약에서 더 낮은 threshold 사용 가능
  → 더 많은 방을 Flexi 풀로 운영

"PR-AUC가 단순 성능 수치가 아니라 실제 운영 가치와 직결됨"을 이 그래프로 증명한다.
```

---

## 9. 발표 Q&A 방어 논리

| 예상 질문 | 방어 |
|----------|------|
| "LLM 반응 = 실제 고객 행동이라는 근거가 있나?" | "직접 검증이 아니라 시뮬레이션입니다. 할인율 파라미터의 방향성(높은 할인 → 높은 수락률, 특별요청 많음 → 낮은 수락률)이 도메인 상식에 부합하는지를 확인하는 것이 목적입니다." |
| "왜 이 7개 피처인가?" | "SHAP Top 10 중 LLM이 자연어로 해석 가능하고 행동 경제학적으로 의미 있는 피처를 선택했습니다. SHAP 순위가 피처 선택의 정당화 근거입니다." |
| "13,355건이면 충분한가?" | "국적 11개 × 채널 5개 × lead_time 구간 5개 = 275개 세그먼트를 분석하려면 각 셀 최소 30건이 필요합니다. 13,355건은 대부분의 세그먼트를 커버합니다." |
| "이전 Pool B 방식과 무엇이 다른가?" | "Pool B는 데이터에 없는 반사실적 외부 수요를 가정해야 했습니다. 신 설계는 실제 고위험 예약자들의 반응을 직접 시뮬레이션하므로 반사실적 파라미터가 없습니다." |

---

## 10. 만드는 것 / 만들지 않는 것

| 항목 | 범위 | 담당 |
|------|------|------|
| 취소 확률 예측 모델 (LightGBM) | ✓ 완료 | 심재형 |
| SHAP 위험 근거 출력 | ✓ 완료 | 심재형 |
| Flexi 라우팅 권장 UI (앱 탭 2) | ✓ Week 4 | 이고은 |
| **AI 에이전트 Flexi 시뮬레이션** | ✓ Week 5 | 심재형 |
| 실제 PMS 연동 | 범위 외 | 호텔 인프라 |
| 실제 결제 / 카드 hold | 범위 외 | 호텔 인프라 |
| 협력 호텔 네트워크 | 범위 외 | 호텔 B2B |

**발표 포지셔닝:**
> "저희는 두뇌를 만듭니다. 취소 예측 엔진 + 13,355명 LLM 에이전트 시뮬레이션으로 Flexi 시스템이 실제로 작동하는지를 데이터로 증명합니다."

---

## 11. 미결 항목

| # | 항목 | 시점 |
|---|------|------|
| A | 최적 임계값 확정 — 시뮬레이션 결과 보고 | Week 5 실행 후 |
| B | 세그먼트별 인사이트 중 발표 강조 포인트 선정 | Week 6 초 |
| C | walk_rate 2% 초과 시 오버부킹 버퍼(OVERBOOKING_BUFFER) 재조정 | 결과 보고 결정 |
| D | FLEXI_CANCEL_REDUCTION 0.50 가정의 민감도 분석 | Week 5 |
