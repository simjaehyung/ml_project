"""
dummy_classifier.py
Baseline 0 — DummyClassifier(strategy="most_frequent")
PR-AUC 기준선 확인용. 이 점수 이상이어야 모델이 의미 있다.

실행: 프로젝트 루트에서
    python src/dummy_classifier.py
전제: data/train_processed.csv, data/test_processed.csv 존재
"""

import pandas as pd
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.metrics import average_precision_score, f1_score, precision_recall_curve
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"

# ── 로드 + OHE ────────────────────────────────────────────────────────────────
train = pd.read_csv(DATA / "train_processed.csv")
test  = pd.read_csv(DATA / "test_processed.csv")

cat_cols = ["hotel", "meal", "market_segment", "distribution_channel",
            "reserved_room_type", "deposit_type", "customer_type", "country_grouped"]

train_e = pd.get_dummies(train, columns=cat_cols)
test_e  = pd.get_dummies(test,  columns=cat_cols)
test_e  = test_e.reindex(columns=train_e.columns, fill_value=0)

X_tr = train_e.drop("is_canceled", axis=1)
y_tr = train_e["is_canceled"]
X_te = test_e.drop("is_canceled", axis=1)
y_te = test_e["is_canceled"]

# ── Dummy 학습 ────────────────────────────────────────────────────────────────
dummy = DummyClassifier(strategy="most_frequent")
dummy.fit(X_tr, y_tr)
proba = dummy.predict_proba(X_te)[:, 1]

pr_auc = average_precision_score(y_te, proba)
f1     = f1_score(y_te, proba > 0.5)

print(f"Dummy PR-AUC : {pr_auc:.4f}")
print(f"Dummy F1@0.5 : {f1:.4f}")
print(f"(취소율 baseline: train {y_tr.mean():.3f} / test {y_te.mean():.3f})")

# ── PR curve 저장 ─────────────────────────────────────────────────────────────
precision, recall, _ = precision_recall_curve(y_te, proba)
fig, ax = plt.subplots(figsize=(7, 5))
ax.plot(recall, precision, label=f"Dummy (PR-AUC={pr_auc:.4f})", color="gray", linestyle="--")
ax.axhline(y_te.mean(), color="red", linestyle=":", alpha=0.5, label=f"Random baseline ({y_te.mean():.3f})")
ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
ax.set_title("PR Curve — Baseline 비교")
ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout()
fig.savefig(RESULTS / "pr_curve_baseline.png", dpi=120)
print(f"\nPR curve 저장 → results/pr_curve_baseline.png")
