# 시뮬레이션 방법론 — 최신 연구 지형도

> 작성: 심재형 (PM) | 기준일: 2026-05-18  
> 목적: Claim 1·2 방어 근거 + 프롬프트 설계 근거가 되는 논문 정리

---

## 연구 클러스터 지도

```
[Cluster A]              [Cluster B]               [Cluster C]
테이블 데이터            LLM 에이전트              프롬프트 설계
→ LLM 제로샷 예측       소비자 시뮬레이션          통제 vs 자율 트레이드오프
  (Claim 1 근거)          (Claim 2 근거)             (design_13 근거)
       ↓                       ↓                          ↓
  TabLLM (2022)          AgentSociety (2025)        "Let It Go" (2025)
  ProtoLLM (2025)        MALLES (2026)              PPol (2026)
  ZET-LLM                LLM-Consumer (2025)
  SHAP+LLM (2024)        WTP Hotel (2026)

[Cluster D]
비판/한계 논문
  Sarstedt 2024
  Critical ABM (2025)
  LLM economicus (2024)
```

---

## Cluster A — 테이블 데이터 → LLM 제로샷 예측

### TabLLM (arXiv 2210.10723)
**Few-shot Classification of Tabular Data with Large Language Models**

테이블 데이터를 자연어로 직렬화해서 LLM에 주면 제로샷·퓨샷 설정에서 기존 ML 모델을 넘을 수 있다는 것을 처음 체계적으로 보인 논문. 자연어 변환 방식이 성능에 직접 영향을 준다.

**우리 프로젝트 관련성**: Claim 1의 방법론적 선례. 예약 피처를 자연어로 변환해서 LLM에 주는 방식이 이미 연구되었다는 근거.

---

### ProtoLLM (arXiv 2508.09263) — 2025년 8월
**LLM Empowered Prototype Learning for Zero and Few-Shot Tasks on Tabular Data**

훈련 없이 피처 설명만으로 LLM이 프로토타입을 생성하고 제로샷 분류를 수행. 태스크와 피처 설명만 주면 LLM이 판단 기준을 스스로 구성한다.

**우리 프로젝트 관련성**: Claim 1 실험과 거의 동일한 구조. LLM이 태스크 설명 없이도 피처에서 패턴을 인식한다는 최신 근거.

---

### ZET-LLM (OpenReview)
**Surprisingly Simple: LLMs are Zero-Shot Feature Extractors for Tabular and Text Data**

각 피처를 단일 토큰으로 직렬화해서 LLM 임베딩을 특징으로 사용. 매우 단순한 방식으로 제로샷 예측이 작동함을 보임.

**우리 프로젝트 관련성**: "단순하게 피처를 주는 것"이 오히려 효과적일 수 있다는 근거. 과도한 자연어 변환보다 직접 피처 나열이 나을 수도 있음 → design_13 블록 2 variant 선택 실험의 이론적 배경.

---

### SHAP + LLM (arXiv 2512.00163) — 2024년 12월
**Measuring What LLMs Think They Do: SHAP Faithfulness on Financial Tabular Classification**

LLM이 테이블 분류를 수행할 때 실제로 어떤 피처를 보는지 SHAP으로 측정. LLM의 내부 가중치와 SHAP 중요도가 얼마나 일치하는지 검증.

**우리 프로젝트 관련성**: Claim 1 실험 이후 "LLM이 실제로 어떤 피처를 중시하는가"를 확인하는 분석 방법으로 활용 가능. 우리 모델 SHAP과 LLM SHAP을 비교하면 발표 인사이트가 생긴다.

---

## Cluster B — LLM 에이전트 소비자 시뮬레이션

### AgentSociety (arXiv 2502.08691) — 2025년 2월
**Large-Scale Simulation of LLM-Driven Generative Agents**

10,000명+ 에이전트, Emotions × Needs × Cognition 3층 심리 구조. 양극화·기본소득·허리케인 등 4가지 실제 사회 현상 재현.

**우리 프로젝트 관련성**: 에이전트 심리 구조 설계의 원본 출처. 현재 design_12에서는 이 구조를 직접 활용하지 않는 방향으로 선회했지만, 배경 지식으로 유지.

---

### LLM Multi-Agent Consumer Behavior (arXiv 2510.18155) — 2025년 10월
**LLM-Based Multi-Agent System for Simulating Marketing and Consumer Behavior**

11명의 이질적 에이전트(나이·직업·소득 다양)가 가격 할인에 반응. 대체 효과·습관 형성·그룹 행동이 규칙 없이 자발적으로 출현.

**우리 프로젝트 관련성**: Flexi 할인율 반응 시뮬레이션의 직접 선례. 이질적 페르소나 × 가격 오퍼 구조가 우리 Claim 2와 동일.

---

### MALLES (arXiv 2603.17694) — 2026년 3월
**Multi-agent LLMs-based Economic Sandbox with Consumer Preference Alignment**

119,252명 실제 거래 데이터로 LLM을 사후 훈련(post-training)해서 소비자 선호를 추출. 개인 프로필에 구매 이력·카테고리 선호·프로모션 민감도를 캡처하는 모듈 포함.

**우리 프로젝트 관련성**: 가장 구조적으로 유사한 논문. 실제 거래 데이터 → 에이전트 선호 추출 → 시뮬레이션 파이프라인이 우리 Claim 2의 Phase 2(호텔 데이터 누적 → calibration)와 동일한 방향. 단, 우리는 post-training이 아니라 프롬프트 수준에서 접근.

---

### WTP Hotel (arXiv 2602.09802) — 2026년 2월
**Would a Large Language Model Pay Extra for a View?**

호텔룸 속성(뷰·층수·취소 정책·가격) 240개 선택 딜레마를 LLM에 제시해 지불의향(WTP) 추론. 학생·비즈니스 페르소나별 가격 민감도 차이 확인. 취소 정책이 WTP에 영향을 주는 독립 변수로 작동.

**우리 프로젝트 관련성**: 호텔 도메인에서 LLM이 취소 정책 + 가격에 반응하는 의사결정을 한다는 직접 근거. Flexi 오퍼(할인 × 취소 조건 변경)가 이 논문의 실험 구조와 동일.

---

### Can LLM Simulate Multi-Turn? (arXiv 2503.20749) — 2025년 3월
**Evidence from Real Online Customer Behavior Data**

실제 31,865개 쇼핑 세션으로 측정. 개별 행동 정확도 ~12%, 집단 결과(구매/이탈) F1 ~20~34%.

**우리 프로젝트 관련성**: 비판 논문이지만 오히려 우리 방어 근거가 됨. 개별 예측이 아니라 세그먼트 집단 패턴을 보는 우리 방식이 이 논문의 비판 범위 밖임.

---

## Cluster C — 프롬프트 설계: 통제 vs 자율

### "Let It Go or Control It All?" (System Dynamics Review, 2025)
**The Dilemma of Prompt Engineering in Generative Agent-Based Models**

22개 연구를 분석해서 프롬프트 과잉 통제(over-control) 패턴을 식별. 프롬프트가 너무 구체적이면 에이전트 행동이 미리 결정되어 창발이 사라진다고 경고. 에이전트 정체성·기억·계획·행동 4개 컴포넌트에서 통제 패턴 유형화.

**우리 프로젝트 관련성**: design_13의 "고정 원칙 — 해석 언어 금지, 심리 레이어 명시 금지"의 이론적 근거. 우리가 4단계 추론 강제를 버린 이유와 정확히 일치.

---

### Persona Policies PPol (arXiv 2605.12894) — 2026년 5월
**Beyond Cooperative Simulators: Generating Realistic User Personas**

MAP-Elites 알고리즘으로 도메인별 페르소나 생성기를 자동 진화. 행동 축(terseness, skepticism, frustration 등)을 자동으로 발견하고 다양화. 플러그앤플레이 방식으로 시뮬레이터 프롬프트에 추가.

**우리 프로젝트 관련성**: design_13의 AGENT 블록 variant 설계와 방향이 같음. 단, PPol은 자동화 알고리즘 수준이고 우리는 수동 variant 실험 수준. Phase 2 이후 자동화 방향으로 참고 가능.

---

## Cluster D — 비판·한계 논문 (알고 있어야 할 것)

| 논문 | 핵심 비판 | 우리 대응 |
|---|---|---|
| Sarstedt 2024, *Psychology & Marketing* | 실리콘 샘플 65% 불일치. 단, 파일럿 탐색에는 권장 | 우리 포지셔닝이 파일럿 탐색이므로 권장 범위 내 |
| Critical Review LLM ABM (arXiv 2504.03274) | 63% 논문이 주관적 검증만 사용. 현실 재현 주장 위험 | 현실 재현 주장 안 함. 방향성 탐색만 주장 |
| LLM economicus (arXiv 2408.02784) | LLM 행동경제학 편향 모델마다 불일치 | Claim 1로 직접 검증. 이론 가정 대신 숫자로 |

---

## 우리 포지셔닝

```
[선행 연구가 다룬 것]
  테이블 → LLM 예측: TabLLM, ProtoLLM
  LLM 에이전트 소비자 시뮬레이션: MALLES, 2510.18155
  호텔 WTP: 2602.09802
  프롬프트 통제 딜레마: "Let It Go"

[선행 연구가 아직 다루지 않은 것]  ← 우리가 있는 자리
  실제 호텔 예약 데이터셋에서
  LLM 제로샷 예측 성능을 측정하고 (Claim 1)
  그 성능을 근거로 동일 데이터 기반 Flexi 시뮬레이션의
  타당성을 주장하는 (Claim 2) 연결 구조
```

Claim 1 → Claim 2 연결 고리가 우리의 독자적 기여다.  
각 부분의 선행 연구는 있지만, 이 둘을 같은 데이터셋 위에서 연결한 연구는 없다.
