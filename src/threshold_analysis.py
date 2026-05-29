# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pickle, pandas as pd, numpy as np
from pathlib import Path
from sklearn.metrics import f1_score, average_precision_score

ROOT    = Path("c:/Users/jhsim/Erica261/M.L/projects/07_Hotel_DSS")
DATA    = ROOT / "data"
RESULTS = ROOT / "results"

with open(RESULTS / "model_lgbm.pkl", "rb") as f:
    model = pickle.load(f)

train_proc = pd.read_csv(DATA / "train_processed.csv")
test_proc  = pd.read_csv(DATA / "test_processed.csv")

cat_cols = ["hotel","meal","market_segment","distribution_channel",
            "reserved_room_type","customer_type","country_grouped"]
train_e = pd.get_dummies(train_proc, columns=cat_cols)
test_e  = pd.get_dummies(test_proc,  columns=cat_cols)
test_e  = test_e.reindex(columns=train_e.columns, fill_value=0)

X_te = test_e.drop("is_canceled", axis=1)
y_te = test_e["is_canceled"].values
proba = model.predict_proba(X_te)[:, 1]

full_prauc = average_precision_score(y_te, proba)
print(f"전체 PR-AUC      : {full_prauc:.4f}")
print(f"테스트셋 크기     : {len(y_te):,}행")
print(f"실제 취소율       : {y_te.mean():.1%}")
print(f"실제 취소 건수    : {y_te.sum():,}건")
print()

print(f"{'임계값':>8}  {'해당건수':>9}  {'전체비율':>8}  {'Precision(실제취소율)':>22}  {'Recall':>8}  {'F1':>8}")
print("-" * 80)
for thr in [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.99]:
    mask  = proba >= thr
    n     = mask.sum()
    if n == 0:
        print(f"  >={thr:.0%}  {n:>9,}  (해당없음)")
        continue
    prec   = y_te[mask].mean()
    recall = y_te[mask].sum() / y_te.sum()
    pred_y = mask.astype(int)
    f1     = f1_score(y_te, pred_y)
    print(f"  >={thr:.0%}  {n:>9,}  {n/len(y_te):>8.1%}  {prec:>22.1%}  {recall:>8.1%}  {f1:>8.4f}")

print()
total_cancel = y_te.sum()
for thr in [0.70, 0.80, 0.85, 0.90]:
    mask  = proba >= thr
    n     = mask.sum()
    hit   = y_te[mask].sum()
    miss  = n - hit
    print(f"=== {thr:.0%}+ 상세 ===")
    print(f"  예측 건수     : {n:,}건  (전체의 {n/len(y_te):.1%})")
    print(f"  실제 취소     : {hit:,}건  (그룹 내 취소율 {hit/n:.1%})")
    print(f"  오경보(FP)    : {miss:,}건  (취소 안 했는데 {thr:.0%}+ 예측)")
    print(f"  전체 취소 커버 : {hit}/{total_cancel:,}  = {hit/total_cancel:.1%}")
    print()
