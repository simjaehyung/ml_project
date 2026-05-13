# Baseline 모델 결과 비교

테스트셋: 40,687행 (2017-01 ~ 2017-08) | 취소율 38.7%

| # | 모델 | PR-AUC | F1@0.5 | 비고 |
|---|------|--------|--------|------|
| 0 | Dummy | **0.3870** | 0.0000 | 기준선 |
| 1 | Logistic Regression | **0.7818** | 0.7073 | C=1, StandardScaler |
| 2 | Random Forest | **0.7785** | 0.6482 | n_estimators=100 |
| 3 | XGBoost | **0.8053** | 0.6863 | n_estimators=100, eval_metric=logloss |
| 4 | LightGBM ★ | **0.8189** | 0.6872 | n_estimators=100, verbose=-1 |

## 최종 선정

**LightGBM** — PR-AUC 차이 0.0136 ≥ 0.01 → 높은 쪽 선택

## 해석 메모

- Dummy PR-AUC ≈ 테스트셋 취소율 (상수 예측기의 이론적 PR-AUC = 양성 비율)
- F1@0.5 = 0.000 : most_frequent → 양성 클래스 TP 없음
- LR·RF·XGBoost·LightGBM 모두 Dummy 대비 큰 폭 개선
- ★ 표시 모델이 `results/model_final.pkl`로 저장됨

## 파이프라인 기준

`src/preprocessing_pipeline.py` 출력 기준.
deposit_type DROP + country Top10+Other OHE + OHE 후 컬럼 수 70개.

## PR Curve

![PR Curve](pr_curve_all.png)

## 미결 #2 해소

precipitation_sum vs precipitation_hours 상관: **0.824** (0.9 미만)
→ 현재 단계에서 제거 불필요. Phase 2에서 변수 중요도 확인 후 판단.
