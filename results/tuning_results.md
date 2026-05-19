# LightGBM Hyperparameter Tuning 결과

실행일: 2026-05-19 13:25

## 성능 비교

| 모델 | PR-AUC | F1@0.5 |
|------|--------|--------|
| LightGBM default (baseline) | 0.8189 | 0.6872 |
| **LightGBM tuned (이번 결과)** | **0.8103** | 0.6851 |
| 개선 | -0.0086 | — |

## Best Params (trial #49)

Val PR-AUC: 0.8456

```python
{'n_estimators': 1488, 'learning_rate': 0.04441634180912145, 'num_leaves': 74, 'min_child_samples': 58, 'feature_fraction': 0.641147064894889, 'bagging_fraction': 0.8446721394755452, 'bagging_freq': 5, 'lambda_l1': 0.0009756741601451628, 'lambda_l2': 0.023371079727345936}
```

## Validation 전략

- Val : train에서 2016-11 ~ 2016-12 시간 기반 holdout (8,314행)
- Train : 나머지 70,389행으로 탐색
- 최종 모델 : train 전체 (78,703행) 재학습

## 탐색 범위

| 파라미터 | 범위 |
|---------|------|
| n_estimators | 300 ~ 1500 |
| learning_rate | 0.01 ~ 0.2 (log) |
| num_leaves | 20 ~ 200 |
| min_child_samples | 10 ~ 100 |
| feature_fraction | 0.5 ~ 1.0 |
| bagging_fraction | 0.5 ~ 1.0 |
| bagging_freq | 1 ~ 7 |
| lambda_l1 | 1e-4 ~ 10.0 (log) |
| lambda_l2 | 1e-4 ~ 10.0 (log) |

n_trials = 50 | early_stopping = 50rounds
