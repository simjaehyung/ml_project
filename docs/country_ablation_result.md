# 국적(country) 피처 — 성능-윤리 트레이드오프 ablation 결과

> 작성: PM 자율작업 (country ablation) | 성격: **정량 측정 + 발표 방어 카드**
> 계기: `docs/preprocessing_reexamination_2026-06-04.md` A-3 (국적 SHAP 1위 → 차별 리스크) + A-2 (top10 누수)
> 스크립트: `src/country_ablation.py` | 데이터: `data/{train,test}_processed.csv` (고정 시간기반 test, 2017-01~08)

---

## 측정 설계

| 안 | 처리 | 의미 |
|---|------|------|
| (a) WITH | `country_grouped` OHE 포함 (현행) | 국적을 위험 동인으로 그대로 사용 |
| (b) DROP | 국적 계열 전부 제거 | 윤리 부채 0, 국적 신호 완전 포기 |
| (c) is_domestic | PRT=1 vs 그 외=0 단일 이진 | 다국적 차별 광학 제거 + PRT 지배신호 보존 + **A-2 누수 소멸** |

- 지표: **PR-AUC**(메인) + Bootstrap 95% CI(n_boot=2000) / 보조 Brier·F1@0.65
- test: 40,687행, 취소율 38.7% | 고정·시간기반(누수 없음)
- 모델: LightGBM(주력) + Logistic Regression(보조). run_all_models.py 와 동일 전처리(OHE+reindex, LR만 스케일).

## 결과

| 모델 | 안 | PR-AUC | 95% CI | ΔPR-AUC(vs WITH) | Brier | F1@0.65 | n_feat |
|------|----|--------|--------|------------------|-------|---------|--------|
| LightGBM | (a) WITH country_grouped (현행) | **0.8189** | [0.8134, 0.8240] | 기준 | 0.1504 | 0.6475 | 70 |
| LightGBM | (b) DROP 국적 전부 제외 | **0.7783** | [0.7723, 0.7840] | -0.0406 | 0.1644 | 0.5931 | 59 |
| LightGBM | (c) is_domestic (PRT=1 vs 그 외=0) | **0.8107** | [0.8055, 0.8161] | -0.0082 | 0.1540 | 0.6398 | 60 |
| Logistic Regression | (a) WITH country_grouped (현행) | **0.7818** | [0.7751, 0.7889] | 기준 | 0.1583 | 0.6695 | 70 |
| Logistic Regression | (b) DROP 국적 전부 제외 | **0.7389** | [0.7319, 0.7460] | -0.0429 | 0.1741 | 0.5684 | 59 |
| Logistic Regression | (c) is_domestic (PRT=1 vs 그 외=0) | **0.7756** | [0.7688, 0.7822] | -0.0062 | 0.1619 | 0.6710 | 60 |

## 해석

**주력 모델 = LightGBM** (현 DSS 동결 모델 계열).

- (b) DROP: PR-AUC 0.8189 → 0.7783 (**-0.0406, 상대 5.0%**). 95% CI는 WITH와 겹치지 않음 → 유의한 하락.
- (c) is_domestic: PR-AUC 0.8189 → 0.8107 (**-0.0082, 상대 1.0%**). 95% CI는 WITH와 겹침 → 구분 불가. 국적 OHE(다국적) 대신 이진 1개로 대체하면서 다국적 차별 광학·top10 누수(A-2)를 동시에 제거.

## 권고

**(c) is_domestic 절충 권고.** DROP은 성능 손실이 측정되지만, is_domestic 으로 대체하면 하락폭이 1.0%로 줄고 다국적 차별 광학과 top10 누수(A-2)를 함께 제거한다. '내국인 vs 외국인'은 체류 패턴 차이로 운영상 정당화 가능.

> 정직한 한계: 국적을 빼도 ADR·market_segment·distribution_channel 등 상관 피처로 **간접 차별**이 잔존할 수 있다. 완전한 공정성은 disparate impact 측정이 필요하나 6일 범위를 초과 → '한계'로 명시.

## 발표 방어 문장 (S11 윤리·법률 집중블록용)

1. "국적은 SHAP 1순위라 '그냥 빼면 된다'고 말하고 싶지만, 정직하게 측정하니 완전 제거 시 PR-AUC가 0.819→0.778로 5.0%(0.0406) 떨어졌고 95% 신뢰구간도 분리됐습니다 — 이 데이터에서 국적은 실제로 유의한 신호입니다. 그래서 '완전 삭제'가 아니라 차별 광학을 제거하면서 신호를 보존하는 절충을 택합니다."

2. "그 절충이 '내국인(PRT) 여부' 이진 피처 하나로의 대체입니다 (PR-AUC 0.811, WITH 대비 1.0%·CI 겹침으로 사실상 무손실). 국적별 OHE가 만드는 '다국적 차별' 광학을 없애고, 동시에 'top10을 전기간으로 정한' 누수(A-2)까지 소멸시킵니다 — 성능·윤리·누수를 한 수로 정리합니다."

---
_생성: src/country_ablation.py (boot=2000, seed=42) | results/country_ablation.csv 동반_
