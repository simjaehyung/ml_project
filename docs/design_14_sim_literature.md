# 시뮬레이션 방법론 — 최신 연구 지형도 (v2)

> 작성: 심재형 (PM) | 기준일: 2026-05-22
> 목적: Claim 1·2 방어 근거 + 프롬프트 설계 근거가 되는 논문 정리

---

## 연구 클러스터 지도

```
[Cluster A]              [Cluster B]                    [Cluster C]
테이블 데이터            LLM 에이전트 시뮬레이션           프롬프트 설계
→ LLM 제로샷 예측        소비자·협상 행동                  통제 vs 자율 트레이드오프
  (Claim 1 근거)          (Claim 2 근거)                   (design_13 근거)
       ↓                         ↓                              ↓
  TabLLM (2022)           AgentSociety (2025)            "Let It Go" (2025)
  ProtoLLM (2025)         MALLES (2026)                  PPol (2026)
  ZET-LLM                 LLM-Consumer (2025)
  SHAP+LLM (2024)         WTP Hotel (2026)
                          Homo Silicus (NBER 2023)
                          AgenticPay (2026)

[Cluster D]
비판/한계 논문
  Sarstedt 2024
  Critical ABM (2025)
  LLM economicus (2024)
  Can LLM Simulate Multi-Turn? (2025)
```

---

## Cluster A — 테이블 데이터 → LLM 제로샷 예측

### TabLLM (arXiv 2210.10723)
**Few-shot Classification of Tabular Data with Large Language Models**

테이블 데이터를 자연어로 직렬화해서 LLM에 주면 제로샷·퓨샷 설정에서 기존 ML 모델을 넘을 수 있다는 것을 처음 체계적으로 보인 논문.

**우리 프로젝트 관련성**: Claim 1의 방법론적 선례. 예약 피처를 자연어로 변환해서 LLM에 주는 방식이 이미 연구되었다는 근거.

---

### ProtoLLM (arXiv 2508.09263) — 2025년 8월
**LLM Empowered Prototype Learning for Zero and Few-Shot Tasks on Tabular Data**

훈련 없이 피처 설명만으로 LLM이 프로토타입을 생성하고 제로샷 분류를 수행.

**우리 프로젝트 관련성**: Claim 1 실험과 거의 동일한 구조. LLM이 태스크 설명 없이도 피처에서 패턴을 인식한다는 최신 근거.

---

### ZET-LLM (OpenReview)
**Surprisingly Simple: LLMs are Zero-Shot Feature Extractors for Tabular and Text Data**

각 피처를 단일 토큰으로 직렬화해서 LLM 임베딩을 특징으로 사용. 매우 단순한 방식으로 제로샷 예측이 작동함을 보임.

**우리 프로젝트 관련성**: "단순하게 피처를 주는 것"이 오히려 효과적일 수 있다는 근거 → design_13 블록 2 variant 선택 실험의 이론적 배경.

---

### SHAP + LLM (arXiv 2512.00163) — 2024년 12월
**Measuring What LLMs Think They Do: SHAP Faithfulness on Financial Tabular Classification**

LLM이 테이블 분류를 수행할 때 실제로 어떤 피처를 보는지 SHAP으로 측정.

**우리 프로젝트 관련성**: Claim 1 실험 이후 "LLM이 실제로 어떤 피처를 중시하는가"를 확인하는 분석 방법. 우리 LGBM SHAP과 LLM SHAP을 비교하면 발표 인사이트가 생긴다.

---

## Cluster B — LLM 에이전트 시뮬레이션

### Homo Silicus (NBER WP 31122) — Horton 2023
**Large Language Models as Simulated Economic Agents: What Can We Learn from Homo Silicus?**

LLM이 최후통첩 게임(Ultimatum Game) 등 경제적 협상 상황에서 인간 특유의 손실 회피(Loss Aversion) 성향을 그대로 모사함을 보임. NBER에서 발표된 기념비적 논문.

**우리 프로젝트 관련성**: Customer Agent가 walk 보상 오퍼에 반응할 때 "손실 회피" 행동이 나타나는 근거. LLM이 경제적 협상 맥락에서 현실적으로 반응한다는 이론적 토대. Claim 2 방어의 핵심 레퍼런스.

**인용 방식**: "NBER Homo Silicus 연구에 따르면 LLM은 협상 상황에서 인간의 손실 회피 성향을 모사합니다. 저희는 이를 근거로 Customer Agent의 반응이 실제 고객과 방향성이 일치한다고 봅니다."

---

### AgentSociety (arXiv 2502.08691) — 2025년 2월
**Large-Scale Simulation of LLM-Driven Generative Agents**

10,000명+ 에이전트, Emotions × Needs × Cognition 3층 심리 구조. 양극화·기본소득 등 실제 사회 현상 재현.

**우리 프로젝트 관련성**: 에이전트 심리 구조 설계의 배경 지식. 우리는 이 구조를 직접 구현하지 않지만, LLM 에이전트가 집단적 패턴을 보인다는 근거.

---

### AgenticPay (2026)
**A Multi-Agent LLM Negotiation System for Buyer-Seller Transactions**

구매자·판매자 에이전트가 숨겨진 예산 한도를 가지고 라운드별 협상. JSON 강제 출력으로 환각 차단. 구조화된 액션(가격 제시·수락 여부)만 출력하도록 통제.

**우리 프로젝트 관련성**: Walk 협상 다중 에이전트 구조의 직접 선례. 우리도 동일하게 JSON 강제 출력 + 2라운드 구조를 채택. Hotel Agent(예산 상한 보유)와 Customer Agent(최소 수락 임계값 보유)의 숨겨진 제약 구조가 AgenticPay와 동일.

**인용 방식**: "AgenticPay 프레임워크를 차용해 JSON 강제 출력으로 환각을 차단하고, Hotel Agent와 Customer Agent 간의 2라운드 협상을 구현했습니다."

---

### LLM Multi-Agent Consumer Behavior (arXiv 2510.18155) — 2025년 10월
**LLM-Based Multi-Agent System for Simulating Marketing and Consumer Behavior**

11명의 이질적 에이전트(나이·직업·소득 다양)가 가격 할인에 반응. 대체 효과·습관 형성이 규칙 없이 자발적으로 출현.

**우리 프로젝트 관련성**: 이질적 페르소나 × 가격 오퍼 구조가 우리 Claim 2와 동일. 아키타입별로 다른 반응이 나온다는 선례.

---

### MALLES (arXiv 2603.17694) — 2026년 3월
**Multi-agent LLMs-based Economic Sandbox with Consumer Preference Alignment**

119,252명 실제 거래 데이터로 LLM을 사후 훈련해서 소비자 선호를 추출.

**우리 프로젝트 관련성**: 실제 거래 데이터 → 에이전트 선호 추출 → 시뮬레이션 파이프라인이 우리 Stage 2·3 로드맵과 동일한 방향. 우리는 post-training이 아닌 프롬프트 수준에서 접근.

---

### WTP Hotel (arXiv 2602.09802) — 2026년 2월
**Would a Large Language Model Pay Extra for a View?**

호텔룸 속성(뷰·층수·취소 정책·가격) 240개 선택 딜레마를 LLM에 제시해 지불의향(WTP) 추론. 취소 정책이 WTP에 영향을 주는 독립 변수로 작동.

**우리 프로젝트 관련성**: 호텔 도메인에서 LLM이 취소 정책 + 가격에 반응하는 의사결정을 한다는 직접 근거. Walk 오퍼(보상금 + 대안 호텔)에 LLM이 반응하는 구조와 동일.

---

## Cluster C — 프롬프트 설계: 통제 vs 자율

### "Let It Go or Control It All?" (System Dynamics Review, 2025)
**The Dilemma of Prompt Engineering in Generative Agent-Based Models**

22개 연구 분석. 프롬프트 과잉 통제(over-control) 시 창발이 사라진다고 경고.

**우리 프로젝트 관련성**: design_13의 "해석 언어 금지, 심리 레이어 명시 금지" 원칙의 이론적 근거. 4단계 추론 강제를 버린 이유와 정확히 일치.

---

### Persona Policies PPol (arXiv 2605.12894) — 2026년 5월
**Beyond Cooperative Simulators: Generating Realistic User Personas**

MAP-Elites 알고리즘으로 도메인별 페르소나 생성기를 자동 진화.

**우리 프로젝트 관련성**: design_13의 ARCHETYPE 블록 variant 설계와 방향이 같음. Phase 2 이후 자동화 방향으로 참고 가능.

---

## Cluster D — 비판·한계 논문

| 논문 | 핵심 비판 | 우리 대응 |
|---|---|---|
| Sarstedt 2024, *Psychology & Marketing* | 실리콘 샘플 65% 불일치. 단, 파일럿 탐색에는 권장 | 우리 포지셔닝이 파일럿 탐색이므로 권장 범위 내 |
| Critical Review LLM ABM (arXiv 2504.03274) | 63% 논문이 주관적 검증만 사용. 현실 재현 주장 위험 | 현실 재현 주장 안 함. 방향성 탐색만 주장 |
| LLM economicus (arXiv 2408.02784) | LLM 행동경제학 편향이 모델마다 불일치 | Claim 1로 직접 검증. 이론 가정 대신 숫자로 |
| Can LLM Simulate Multi-Turn? (arXiv 2503.20749) | 개별 행동 정확도 ~12%, 집단 F1 ~20~34% | 개별 예측 아님. 아키타입별 집단 패턴 비교 — 비판 범위 밖 |

---

## 우리 포지셔닝 (v2)

```
[선행 연구가 다룬 것]
  테이블 → LLM 예측: TabLLM, ProtoLLM
  LLM 에이전트 소비자 시뮬레이션: MALLES, 2510.18155
  호텔 WTP: WTP Hotel
  경제적 협상 행동: Homo Silicus
  다중 에이전트 협상: AgenticPay
  프롬프트 통제 딜레마: "Let It Go"

[선행 연구가 아직 다루지 않은 것]  ← 우리가 있는 자리
  실제 호텔 예약 데이터셋에서
  LLM 제로샷 예측 성능을 측정하고 (Claim 1)
  그 성능을 근거로 동일 데이터 기반 오버부킹 Walk 보상 협상의
  타당성을 주장하는 (Claim 2) 연결 구조

  그리고 LLM 시뮬레이션이 실제 ML 모델 학습용
  합성 레이블을 생성하는 브릿지 역할임을 명시 (3단계 로드맵)
```

**Claim 1 → Claim 2 연결 고리 + 3단계 로드맵이 우리의 독자적 기여다.**
각 부분의 선행 연구는 있지만, 이 둘을 같은 데이터셋 위에서 연결하고
ML 대체 로드맵까지 제시한 연구는 없다.
