# Baseline 모델 결과 비교

테스트셋: 40,687행 (2017-01 ~ 2017-08) | 취소율 38.7%

| # | 모델 | PR-AUC | F1@0.5 | 비고 |
|---|------|--------|--------|------|
| 0 | Dummy (most_frequent) | **0.3870** | 0.0000 | 기준선. 이 이상이어야 의미 있음 |
| 1 | Logistic Regression | — | — | 김나리 작업 중 |
| 2 | Random Forest | — | — | 김나리 작업 중 |
| 3 | XGBoost | — | — | Week 3 이고은 |
| 4 | LightGBM | — | — | Week 3 김나리 |

## 해석 메모

- Dummy PR-AUC = 0.387 ≈ 테스트셋 취소율. 예상된 수치 (상수 예측기의 이론적 PR-AUC = 양성 비율)
- F1@0.5 = 0.000 : most_frequent → 전부 "취소 없음"으로 예측하므로 양성 클래스 TP 없음
- **실질 기준선: PR-AUC > 0.39 이상부터 모델이 Dummy를 이김**

## PR Curve

![PR Curve](pr_curve_baseline.png)
