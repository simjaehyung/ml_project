"""
src/tune_lgbm.py
LightGBM Optuna 하이퍼파라미터 튜닝

실행:
  C:\\Users\\jhsim\\miniconda3\\python.exe src/tune_lgbm.py

산출물:
  results/model_lgbm_tuned.pkl   — 튜닝 완료 모델
  results/model_final.pkl        — 동일 파일 (앱 연동용 경로)
  results/tuning_results.md      — 파라미터 + 성능 기록

Validation 전략:
  train에서 마지막 2개월(2016-11, 2016-12)을 시간 기반 holdout으로 사용.
  test set은 튜닝 과정에서 일절 사용하지 않음 (최종 평가 전용).
"""

import pickle
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import optuna
import wandb
import lightgbm as lgb
from lightgbm import LGBMClassifier, early_stopping, log_evaluation
from pathlib import Path
from sklearn.metrics import average_precision_score, f1_score

optuna.logging.set_verbosity(optuna.logging.WARNING)

ROOT    = Path(__file__).parent.parent
DATA    = ROOT / "data"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

N_TRIALS    = 50
EARLY_STOP  = 50      # early stopping rounds
VAL_MONTHS  = [11, 12]  # 2016-11, 2016-12 → validation holdout
VAL_YEAR    = 2016
RANDOM_SEED = 42

# ── 1. 데이터 로드 + OHE ──────────────────────────────────────────────────────
print("=" * 55)
print("LightGBM Hyperparameter Tuning (Optuna)")
print("=" * 55)

train_raw = pd.read_csv(DATA / "train_processed.csv")
test_raw  = pd.read_csv(DATA / "test_processed.csv")

CAT_COLS = [
    "hotel", "meal", "market_segment", "distribution_channel",
    "reserved_room_type", "customer_type", "country_grouped",
]

train_e = pd.get_dummies(train_raw, columns=CAT_COLS)
test_e  = pd.get_dummies(test_raw,  columns=CAT_COLS)
test_e  = test_e.reindex(columns=train_e.columns, fill_value=0)

# ── 2. 시간 기반 validation split ─────────────────────────────────────────────
val_mask = (
    (train_raw["arrival_date_year"]  == VAL_YEAR) &
    (train_raw["arrival_date_month"].isin(VAL_MONTHS))
)
tr_mask = ~val_mask

X_tr = train_e[tr_mask].drop("is_canceled", axis=1)
y_tr = train_e[tr_mask]["is_canceled"]
X_val = train_e[val_mask].drop("is_canceled", axis=1)
y_val = train_e[val_mask]["is_canceled"]

X_te  = test_e.drop("is_canceled", axis=1)
y_te  = test_e["is_canceled"]

print(f"Train : {X_tr.shape[0]:,}행  Val : {X_val.shape[0]:,}행  Test : {X_te.shape[0]:,}행")
print(f"Val 기간 : {VAL_YEAR}-{min(VAL_MONTHS):02d} ~ {VAL_YEAR}-{max(VAL_MONTHS):02d}")
print(f"Val 취소율 : {y_val.mean():.1%}  |  Train 취소율 : {y_tr.mean():.1%}\n")

# ── 3. wandb 초기화 ───────────────────────────────────────────────────────────
wandb.init(
    project="hotel-dss",
    entity="tokyojj33-hanyang-university",
    name="lgbm-optuna-tuning",
    config={
        "n_trials":   N_TRIALS,
        "early_stop": EARLY_STOP,
        "val_months": VAL_MONTHS,
        "val_year":   VAL_YEAR,
    },
    tags=["tuning", "lightgbm", "optuna"],
)

# ── 4. Optuna objective ───────────────────────────────────────────────────────
def objective(trial: optuna.Trial) -> float:
    params = {
        "n_estimators":      trial.suggest_int("n_estimators", 300, 1500),
        "learning_rate":     trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "num_leaves":        trial.suggest_int("num_leaves", 20, 200),
        "min_child_samples": trial.suggest_int("min_child_samples", 10, 100),
        "feature_fraction":  trial.suggest_float("feature_fraction", 0.5, 1.0),
        "bagging_fraction":  trial.suggest_float("bagging_fraction", 0.5, 1.0),
        "bagging_freq":      trial.suggest_int("bagging_freq", 1, 7),
        "lambda_l1":         trial.suggest_float("lambda_l1", 1e-4, 10.0, log=True),
        "lambda_l2":         trial.suggest_float("lambda_l2", 1e-4, 10.0, log=True),
        "random_state":      RANDOM_SEED,
        "verbose":           -1,
        "n_jobs":            -1,
    }

    model = LGBMClassifier(**params)
    model.fit(
        X_tr, y_tr,
        eval_set=[(X_val, y_val)],
        callbacks=[
            early_stopping(EARLY_STOP, verbose=False),
            log_evaluation(period=-1),
        ],
    )

    proba   = model.predict_proba(X_val)[:, 1]
    pr_auc  = average_precision_score(y_val, proba)

    # wandb에 trial 결과 로그
    wandb.log({
        "trial":      trial.number,
        "val_pr_auc": pr_auc,
        **{f"param/{k}": v for k, v in params.items() if k not in ("random_state", "verbose", "n_jobs")},
    })

    return pr_auc


# ── 5. 튜닝 실행 ──────────────────────────────────────────────────────────────
print(f"Optuna 탐색 시작 — {N_TRIALS}회 trial\n")
study = optuna.create_study(
    direction="maximize",
    sampler=optuna.samplers.TPESampler(seed=RANDOM_SEED),
)
study.optimize(objective, n_trials=N_TRIALS, show_progress_bar=True)

best_params = study.best_params
best_val_auc = study.best_value

print(f"\n★ Best Val PR-AUC : {best_val_auc:.4f}  (trial #{study.best_trial.number})")
print("  Best params:")
for k, v in best_params.items():
    print(f"    {k}: {v}")

# ── 6. 최종 모델 — train 전체로 재학습 ────────────────────────────────────────
print("\n최종 모델 — train 전체로 재학습 중...")

# train 전체 (val 포함) 로 재학습, n_estimators는 best + 10% 여유
final_params = {**best_params, "random_state": RANDOM_SEED, "verbose": -1, "n_jobs": -1}
final_model  = LGBMClassifier(**final_params)

X_tr_full = train_e.drop("is_canceled", axis=1)
y_tr_full = train_e["is_canceled"]
final_model.fit(X_tr_full, y_tr_full)

# test set 최종 평가
proba_te    = final_model.predict_proba(X_te)[:, 1]
test_pr_auc = average_precision_score(y_te, proba_te)
test_f1     = f1_score(y_te, proba_te >= 0.5)

print(f"\n★ Test PR-AUC : {test_pr_auc:.4f}  (baseline: 0.8189)")
print(f"  Test F1@0.5 : {test_f1:.4f}")

# wandb 최종 기록
wandb.log({
    "best_val_pr_auc":  best_val_auc,
    "final_test_pr_auc": test_pr_auc,
    "final_test_f1":     test_f1,
    "improvement":       test_pr_auc - 0.8189,
})

# ── 7. 모델 저장 ──────────────────────────────────────────────────────────────
tuned_path = RESULTS / "model_lgbm_tuned.pkl"
final_path = RESULTS / "model_final.pkl"

with open(tuned_path, "wb") as f:
    pickle.dump(final_model, f)
with open(final_path, "wb") as f:
    pickle.dump(final_model, f)

print(f"\n모델 저장:")
print(f"  → {tuned_path}")
print(f"  → {final_path}")

# ── 8. wandb artifact 업로드 ──────────────────────────────────────────────────
artifact = wandb.Artifact("model-lgbm", type="model")
artifact.add_file(str(final_path))
wandb.log_artifact(artifact)
print("  → wandb artifact 업로드 완료")

# ── 9. tuning_results.md 저장 ─────────────────────────────────────────────────
md = f"""# LightGBM Hyperparameter Tuning 결과

실행일: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

## 성능 비교

| 모델 | PR-AUC | F1@0.5 |
|------|--------|--------|
| LightGBM default (baseline) | 0.8189 | 0.6872 |
| **LightGBM tuned (이번 결과)** | **{test_pr_auc:.4f}** | {test_f1:.4f} |
| 개선 | {test_pr_auc - 0.8189:+.4f} | — |

## Best Params (trial #{study.best_trial.number})

Val PR-AUC: {best_val_auc:.4f}

```python
{best_params}
```

## Validation 전략

- Val : train에서 2016-11 ~ 2016-12 시간 기반 holdout ({X_val.shape[0]:,}행)
- Train : 나머지 {X_tr.shape[0]:,}행으로 탐색
- 최종 모델 : train 전체 ({X_tr_full.shape[0]:,}행) 재학습

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

n_trials = {N_TRIALS} | early_stopping = {EARLY_STOP}rounds
"""

(RESULTS / "tuning_results.md").write_text(md, encoding="utf-8")
print(f"  → results/tuning_results.md")

# ── 10. 마무리 ────────────────────────────────────────────────────────────────
wandb.finish()

print("\n" + "=" * 55)
print(f"완료  Test PR-AUC {test_pr_auc:.4f}  (baseline 0.8189, {test_pr_auc - 0.8189:+.4f})")
print("=" * 55)
