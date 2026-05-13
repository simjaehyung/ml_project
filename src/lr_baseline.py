"""
lr_baseline.py
Baseline 1 — Logistic Regression (C=1, StandardScaler)
입력: data/train_processed.csv, data/test_processed.csv  (preprocessing_pipeline.py 출력)
     deposit_type 제거 + country Top10+Other 기준 데이터

실행: 프로젝트 루트에서
    python src/lr_baseline.py
"""

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score, f1_score, precision_recall_curve
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

ROOT    = Path(__file__).parent.parent
DATA    = ROOT / "data"
RESULTS = ROOT / "results"

# ── 1. 로드 ───────────────────────────────────────────────────────────────────
train = pd.read_csv(DATA / "train_processed.csv")
test  = pd.read_csv(DATA / "test_processed.csv")
print(f"로드  train {train.shape}  test {test.shape}")

# ── 2. OHE ────────────────────────────────────────────────────────────────────
cat_cols = ["hotel", "meal", "market_segment", "distribution_channel",
            "reserved_room_type", "customer_type", "country_grouped"]

train_e = pd.get_dummies(train, columns=cat_cols)
test_e  = pd.get_dummies(test,  columns=cat_cols)
test_e  = test_e.reindex(columns=train_e.columns, fill_value=0)

X_tr = train_e.drop("is_canceled", axis=1)
y_tr = train_e["is_canceled"]
X_te = test_e.drop("is_canceled", axis=1)
y_te = test_e["is_canceled"]

print(f"OHE 후  train {X_tr.shape}  test {X_te.shape}")

# ── 3. 스케일링 (LR 필수) ──────────────────────────────────────────────────────
scaler = StandardScaler()
X_tr_s = scaler.fit_transform(X_tr)
X_te_s = scaler.transform(X_te)

# ── 4. 학습 ───────────────────────────────────────────────────────────────────
lr = LogisticRegression(C=1, max_iter=1000, random_state=42)
lr.fit(X_tr_s, y_tr)
proba = lr.predict_proba(X_te_s)[:, 1]

# ── 5. 평가 ───────────────────────────────────────────────────────────────────
pr_auc = average_precision_score(y_te, proba)
f1     = f1_score(y_te, proba > 0.5)

print(f"\nLR PR-AUC : {pr_auc:.4f}")
print(f"LR F1@0.5 : {f1:.4f}")
print(f"(취소율 train {y_tr.mean():.3f} / test {y_te.mean():.3f})")

# ── 6. PR curve 저장 ──────────────────────────────────────────────────────────
precision, recall, _ = precision_recall_curve(y_te, proba)

fig, ax = plt.subplots(figsize=(7, 5))
ax.plot(recall, precision,
        label=f"Logistic Regression (PR-AUC={pr_auc:.4f})", color="steelblue")
ax.axhline(y_te.mean(), color="red", linestyle=":", alpha=0.5,
           label=f"Random baseline ({y_te.mean():.3f})")
ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
ax.set_title("PR Curve — LR Baseline (processed pipeline)")
ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout()
fig.savefig(RESULTS / "pr_curve_lr.png", dpi=120)
print(f"\nPR curve 저장 → results/pr_curve_lr.png")
