# 프로젝트 전체 로드맵

> 작성: 심재형 (PM) | 최종 업데이트: 2026-05-13  
> 이 문서가 일정·우선순위·산출물의 단일 기준점이다. CLAUDE.md 일정 섹션보다 이 문서가 우선한다.

---

## 목표 재정의

### 현재 목표 (2026-05-13 확정)
> "호텔이 진짜 풀어야 할 세 가지 운영 문제를 같은 데이터와 모델로 다루고,  
> LLM 에이전트 시뮬레이션으로 Flexi 파라미터의 유효성을 최종 검증한다"

```
문제 1 — 어느 채널이 실제로 수익을 내는가?  (Channel Effective Yield)
문제 2 — 어떤 예약을 지켜야 하는가?        (Booking Quality Score)
문제 3 — 취소가 만드는 낭비를 어떻게 줄이는가? (Food Waste Prediction)
피날레 — LLM 에이전트 시뮬레이션          (Flexi 파라미터 검증)
```

취소 예측 모델은 이 모든 것을 푸는 **엔진**이다. 취소 예측 자체가 목적이 아니다.

---

## 결과물 정의

### Phase 1 결과물 (중간발표 2026-05-27)

| 결과물 | 내용 | 상태 |
|-------|------|------|
| 취소 예측 모델 (LightGBM ★) | PR-AUC 0.8189, SHAP 연동 | **✅ 2026-05-11 완료** |
| 앱 탭 1 — 예약 우선순위 리스트 | 취소 확률 순위 + SHAP 위험 근거 | Week 4 완성 |
| 앱 탭 2 — Flexi 라우팅 권장 | 신규 예약 위험 평가 + 할인율 제시 | Week 4 완성 |
| PR-AUC → walk_rate 곡선 | Pool A 데이터 기반, 블라인드 vs 모델 비교 | Week 4 완성 |
| LLM 시뮬레이션 예고 | 방법론 소개 + Week 5 실행 예정 발표 | 중간발표 포함 |

### Phase 2 결과물 (최종발표 2026-06-10)

| 결과물 | 내용 | 담당 |
|-------|------|------|
| **LLM 에이전트 시뮬레이션 ★** | ~13,355 에이전트, AgentSociety 3층 심리모델, 세그먼트별 수락률 | 심재형 |
| 채널 실효 수익 분석 | distribution_channel × ADR × cancel_rate 매트릭스 | 김나리 |
| 예약 품질 점수 | ADR + 체류기간 + special_requests + channel + cancel_proba 복합 점수 | 심재형 |
| 음식 낭비 예측 | meal × cancel_probability → 식재료 발주 조정 권고 | 이고은 |
| SHAP 기반 가정 검증 | 날씨 윈도우 / previous_cancellations ablation | 팀 |

---

## 우선순위 변경 이력

### Flexi 시스템 재설계 (2026-05-13 확정)

**기존:** Pool A(기존 예약) + Pool B(가상 외부 Flexi 구매자, `conversion_rate`)  
**변경:** Pool B 완전 제거 → 기존 고위험 예약이 곧 LLM 에이전트

```
레이어 1 (이론): Mechanism Design + Probabilistic Selling 문헌 근거
레이어 2 (데이터): PR-AUC → walk_rate 곡선 (Pool A 실데이터만)
레이어 3 (정책): 매니저가 threshold·슬롯 수를 설정하는 제어판 UI
레이어 4 (검증): LLM 에이전트 시뮬레이션 — 할인율 파라미터 유효성
```

**이유:** conversion_rate는 반사실적 수요로 어떤 수치도 구조적으로 방어 불가.  
**새 기여:** 실제 예약 데이터 기반 AgentSociety 3층 심리모델 적용 — 기존 몬테카를로 시뮬레이션 대비 고객 이질성 포착.

### 새 방향 3개 추가 (2026-05-11 확정)

`docs/design_09_beyond_cancellation.md` 참조.  
모두 현재 모델 출력 재활용 — 새 ML 작업 없음. **중간발표 핵심 콘텐츠.**

---

## ★ 피크 구간: 5/19 ~ 5/25 (Week 4) ★

> **MVP 마무리주.** SHAP + 탭2 + walk_rate 곡선 → Gate: MVP 배포  
> 모델은 이미 동결됨 (5/11). 이 주는 전부 "연동·완성"에 쓴다.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 5/25(월)  Gate: MVP 배포. 탭1 + 탭2 + walk_rate 동작 확인.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 전체 일정

### ✅ 완료 — 모델 동결 (2026-05-11)

| 작업 | 결과 | 상태 |
|------|------|------|
| LR baseline | PR-AUC 0.7818 | ✅ |
| RF baseline | PR-AUC 0.7785 | ✅ |
| XGBoost 학습 | PR-AUC 0.8053 | ✅ |
| LightGBM 학습 | PR-AUC 0.8189 | ✅ |
| 최종 모델 선정 | **LightGBM ★** (차이 0.0136 ≥ 0.01 기준) | ✅ |
| `results/model_final.pkl` 저장 | LightGBM 저장 완료 | ✅ |
| PR curve 5종 통합 | `results/pr_curve_all.png` | ✅ |

---

### ⚡ Week 4 (5/19~5/25) — MVP 마무리주

> SHAP 연동 + 탭2 + walk_rate 곡선. 중간발표 직전 배포 Gate.

```
5/19(화) ~ 5/20(수)  SHAP 전면 연동
  심재형  │ SHAP beeswarm (전체 피처 중요도)
          │ SHAP waterfall (개별 예약 설명)
  이고은  │ 탭1에 SHAP Top 3 사유 컬럼 추가

5/21(목) ~ 5/22(금)  탭2 + walk_rate 곡선
  심재형  │ Flexi 정책 제어판 탭2 구현
          │   threshold 슬라이더 (0.50~0.85)
          │   Flexi 풀 현황 (슬롯 수·현재 배정 수)
          │ walk_rate 곡선 생성 (threshold sweep)
          │   블라인드 오버부킹 vs 모델 기반 비교
  이고은  │ 탭1 전체 UI 최종 점검

5/23(토) ~ 5/24(일)  임계값 확정 + 통합 테스트
  심재형  │ walk_rate < 2% 달성 지점 → 임계값 확정 (미결 #4 해소)
          │ ACTION 규칙 초안 (미결 #5)
  팀 전체 │ 앱 통합 테스트 (탭1 + 탭2 동시 구동)

5/25(월)  Gate: MVP 배포
```

#### Week 4 Gate 조건 (5/25)

| 조건 | 기준 |
|------|------|
| SHAP 연동 | beeswarm + waterfall 출력 확인 |
| 탭 1 | 예약 리스트 + 위험도 + SHAP Top 3 표시 |
| 탭 2 | threshold 슬라이더 + Flexi 풀 현황 대시보드 |
| walk_rate 곡선 | threshold 0.50~0.85 sweep, 블라인드 vs 모델 비교 포함 |
| 임계값 확정 | walk_rate < 2% 달성 지점 선정 |

---

### Phase 2 — 확장 분석 + LLM 시뮬레이션 (2026-05-28 ~ 2026-06-10)

> MVP가 살아 있는 상태에서 LLM 시뮬레이션을 실행하고, SHAP 나침반을 따라 가정을 검증한다.

#### Week 5 (5/28~6/2) — ★ LLM 에이전트 시뮬레이션 실행주

| 항목 | 내용 | 담당 | 예상 소요 |
|------|------|------|---------|
| **학교 서버 셋업** | `bash src/sim_setup.sh` + Qwen2.5-14B 다운로드 + vLLM 시작 | 심재형 | 5/28 |
| **dry-run 검증** | `python src/sim_run.py --dry-run --n 50` 파이프라인 확인 | 심재형 | 5/29 저녁 |
| **★ 전수 시뮬레이션 런** | `python src/sim_run.py --all --workers 16` (~13,355건, 야간 실행) | 심재형 | 5/30 야간 |
| **결과 분석** | `python src/sim_analyze.py` — 세그먼트별 수락률 + RevPAR | 심재형 | 5/31 |
| **채널 실효 수익 분석** | distribution_channel × ADR × cancel_rate 매트릭스 | 김나리 | 1~2일 |
| **예약 품질 점수 설계** | 가중치 정의 + 점수 분포 시각화 | 심재형 | 2일 |
| SHAP 가정 검증 — previous_cancellations | 포함/제거 PR-AUC 변화 | 이고은 | 1일 |
| 날씨 윈도우 실험 | 도착일 하루 vs 체류기간 전체 PR-AUC 비교 | 김나리 | 1일 |

#### Week 6 (6/3~6/9)

| 항목 | 내용 | 담당 | 예상 소요 |
|------|------|------|---------|
| **시뮬레이션 슬라이드 완성** | 세그먼트별 인사이트 + 최적 임계값 + RevPAR 개선치 | 심재형 | 2일 |
| **음식 낭비 예측 탭** | meal × cancel_proba → 주간 고위험 식사 예약 수 + 절감 추정 | 이고은 | 1~2일 |
| **예약 품질 점수 앱 통합** | 탭 1에 Booking Quality Score 컬럼 추가 | 이고은 | 1일 |
| 채널 분석 발표 슬라이드 반영 | 매트릭스 + 핵심 인사이트 1슬라이드 | 김나리 | 0.5일 |
| 최종 발표 자료 완성 | — | 팀 전체 | 3~4일 |
| 6/9(월) 최종 리허설 | — | 팀 전체 | — |

---

## 발표 스토리 구조 (최종발표 기준)

```
1. 문제 제기
   "호텔이 취소 예측보다 먼저 풀어야 할 세 가지 구조적 문제"

2. 엔진: 취소 예측 모델
   데이터 · 전처리 · 모델 성능 (LightGBM PR-AUC 0.8189) · SHAP 해석

3. 문제 1 해법: 채널 실효 수익
   "Online TA가 실제로 가장 비효율적이다" — 데이터로 증명

4. 문제 2 해법: 예약 품질 점수
   "취소 확률만으로 우선순위를 잡으면 안 된다" — BQS 도입
   앱 탭 1 데모

5. 문제 3 해법: 음식 낭비 예측
   "취소 예측이 ESG 운영 도구가 된다" — 절감 수치 제시

6. Flexi 시스템 (정책 레이어)
   "매니저는 개별 판단이 아닌 정책을 설계한다"
   PR-AUC → walk_rate 곡선 + 탭 2 데모

7. ★ 피날레: LLM 에이전트 시뮬레이션
   "전통적 몬테카를로 시뮬레이션이 포착하지 못하는 고객 이질성을
    AgentSociety 3층 심리모델로 포착했다"
   ~13,355명 × SHAP-검증 7개 피처 페르소나 → 세그먼트별 수락률
   → 최적 임계값 + RevPAR 개선치 제시

8. 한계와 다음 단계
   현장 검증 필요 파라미터 명시 / 일반화 범위 명시
```

---

## 팀원별 Phase 2 역할 요약

| 이름 | Phase 2 핵심 역할 |
|------|-----------------|
| 심재형 | LLM 시뮬레이션 실행·분석 + 예약 품질 점수 설계 + SHAP 가정 검증 총괄 + 발표 구성 |
| 이고은 | 음식 낭비 탭 개발 + BQS 앱 통합 + previous_cancellations 실험 |
| 김나리 | 채널 실효 수익 분석 + 날씨 윈도우 실험 |

---

## 미결 항목 전체 (2026-05-13 기준)

| # | 항목 | 담당 | 마감 | 상태 |
|---|------|------|------|------|
| 4 | Flexi 임계값 확정 (walk_rate < 2% 지점) | PM | 5/25 | Week 4 |
| 5 | ACTION 규칙 설계 (확률 구간 × SHAP → 행동) | PM | 5/25 | Week 4 |
| 10 | 신규 예약 날씨 처리 — 계절 평균값 A안 확정 | 심재형 | 5/25 | Week 4 |
| A | min_prob 0.40 vs 0.50 — 시뮬레이션 규모 vs 신뢰도 | PM | 5/28 | Week 5 시작 시 |
| 6 | `previous_cancellations` 포함/제거 실험 | 이고은 | 6/2 | Week 5 |
| 7 | 날씨 윈도우 실험 | 김나리 | 6/2 | Week 5 |
| B | 시뮬레이션 세그먼트 중 발표 강조 인사이트 | PM | 5/31 | 결과 분석 후 |
| P2 | Booking Quality Score 가중치 설계 | 심재형 | 6/2 | Phase 2 |

---

## 관련 문서 인덱스

| 문서 | 내용 |
|------|------|
| [design_00_problem_definition.md](design_00_problem_definition.md) | 문제 정의 · AS-IS/TO-BE |
| [design_04_preprocessing_decisions.md](design_04_preprocessing_decisions.md) | 전처리 결정사항 |
| [design_05_system_architecture.md](design_05_system_architecture.md) | 전체 파이프라인 + 폴더 구조 |
| [design_06_flexi_system.md](design_06_flexi_system.md) | Flexi 시스템 + LLM 에이전트 설계 |
| [design_07_shap_guide.md](design_07_shap_guide.md) | SHAP 적용 가이드 |
| [design_08_literature_review.md](design_08_literature_review.md) | 선행연구 |
| [design_09_beyond_cancellation.md](design_09_beyond_cancellation.md) | Phase 2 세 방향 (채널·BQS·음식 낭비) |
| [design_10_sim_persona_design.md](design_10_sim_persona_design.md) | LLM 에이전트 페르소나 방법론 |
| [design_11_wireframe.md](design_11_wireframe.md) | Streamlit UI 와이어프레임 |
| [meetings/week3_week4_workplan.md](../meetings/week3_week4_workplan.md) | Week 3~4 업무표 + 발표 준비 |
