"""
run_all_models.py
Dummy + LR + RF + XGBoost + LightGBM 한 번에 실행

산출물:
  results/pr_curve_all.png        - 5종 PR curve
  results/model_final.pkl         - 최종 선정 모델 (PR-AUC 기준)
  results/baseline_results.md     - 5종 비교표 갱신

실행:
  python src/run_all_models.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pickle
import time
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score, f1_score, precision_recall_curve

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("[경고] xgboost 미설치 - pip install xgboost")

try:
    from lightgbm import LGBMClassifier
    HAS_LGB = True
except ImportError:
    HAS_LGB = False
    print("[경고] lightgbm 미설치 - pip install lightgbm")

ROOT    = Path(__file__).parent.parent
DATA    = ROOT / "data"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

# ── 1. 로드 + OHE ─────────────────────────────────────────────────────────────
train = pd.read_csv(DATA / "train_processed.csv")
test  = pd.read_csv(DATA / "test_processed.csv")
print(f"로드  train {train.shape}  test {test.shape}")

cat_cols = ["hotel", "meal", "market_segment", "distribution_channel",
            "reserved_room_type", "customer_type", "country_grouped"]

train_e = pd.get_dummies(train, columns=cat_cols)
test_e  = pd.get_dummies(test,  columns=cat_cols)
test_e  = test_e.reindex(columns=train_e.columns, fill_value=0)

X_tr = train_e.drop("is_canceled", axis=1)
y_tr = train_e["is_canceled"]
X_te = test_e.drop("is_canceled", axis=1)
y_te = test_e["is_canceled"]

print(f"OHE 후  X_tr {X_tr.shape}  X_te {X_te.shape}\n")

# ── 2. 스케일링 (LR 전용) ─────────────────────────────────────────────────────
scaler  = StandardScaler()
X_tr_s  = scaler.fit_transform(X_tr)
X_te_s  = scaler.transform(X_te)

# ── 3. 헬퍼 ──────────────────────────────────────────────────────────────────
def evaluate(name, model, X_train, y_train, X_test, y_test):
    t0 = time.time()
    model.fit(X_train, y_train)
    elapsed = time.time() - t0
    proba = model.predict_proba(X_test)[:, 1]
    pr_auc = average_precision_score(y_test, proba)
    f1     = f1_score(y_test, proba >= 0.5)
    print(f"  [{name}]  PR-AUC {pr_auc:.4f}  F1@0.5 {f1:.4f}  ({elapsed:.1f}s)")
    return {"model": model, "proba": proba, "pr_auc": pr_auc, "f1": f1}

# ── 4. 학습 ───────────────────────────────────────────────────────────────────
results = {}

results["Dummy"] = evaluate(
    "Dummy", DummyClassifier(strategy="most_frequent"),
    X_tr, y_tr, X_te, y_te,
)
results["Logistic Regression"] = evaluate(
    "Logistic Regression", LogisticRegression(C=1, max_iter=1000, random_state=42),
    X_tr_s, y_tr, X_te_s, y_te,
)
results["Random Forest"] = evaluate(
    "Random Forest", RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
    X_tr, y_tr, X_te, y_te,
)
if HAS_XGB:
    results["XGBoost"] = evaluate(
        "XGBoost",
        XGBClassifier(n_estimators=100, random_state=42,
                      eval_metric="logloss", verbosity=0, n_jobs=-1),
        X_tr, y_tr, X_te, y_te,
    )
if HAS_LGB:
    results["LightGBM"] = evaluate(
        "LightGBM",
        LGBMClassifier(n_estimators=100, random_state=42, verbose=-1, n_jobs=-1),
        X_tr, y_tr, X_te, y_te,
    )

# ── 5. 최종 모델 선정 ─────────────────────────────────────────────────────────
TREE_MODELS = [k for k in ("XGBoost", "LightGBM") if k in results]

if len(TREE_MODELS) == 2:
    xgb_auc = results["XGBoost"]["pr_auc"]
    lgb_auc = results["LightGBM"]["pr_auc"]
    diff    = abs(xgb_auc - lgb_auc)
    if diff < 0.01:
        winner = "LightGBM"
        reason = f"PR-AUC 차이 {diff:.4f} < 0.01 → LightGBM (속도·메모리 우위)"
    else:
        winner = "XGBoost" if xgb_auc >= lgb_auc else "LightGBM"
        reason = f"PR-AUC 차이 {diff:.4f} ≥ 0.01 → 높은 쪽 선택"
elif len(TREE_MODELS) == 1:
    winner = TREE_MODELS[0]
    reason = "단독 트리 모델"
else:
    winner = "Logistic Regression"
    reason = "트리 모델 미설치 — LR 대체"

print(f"\n★ 최종 선정: {winner}  ({reason})")

# ── 6. model_final.pkl 저장 ───────────────────────────────────────────────────
final_model = results[winner]["model"]
pkl_path    = RESULTS / "model_final.pkl"
with open(pkl_path, "wb") as f:
    pickle.dump(final_model, f)
print(f"  → {pkl_path}")

# ── 7. PR curve 5종 저장 ──────────────────────────────────────────────────────
PALETTE = {
    "Dummy":               ("gray",       "--"),
    "Logistic Regression": ("steelblue",  "-"),
    "Random Forest":       ("darkorange", "-"),
    "XGBoost":             ("seagreen",   "-"),
    "LightGBM":            ("crimson",    "-"),
}

fig, ax = plt.subplots(figsize=(8, 6))
for name, r in results.items():
    color, ls = PALETTE.get(name, ("black", "-"))
    marker = " ★" if name == winner else ""
    prec, rec, _ = precision_recall_curve(y_te, r["proba"])
    ax.plot(rec, prec,
            label=f"{name}{marker} (PR-AUC={r['pr_auc']:.4f})",
            color=color, linestyle=ls,
            linewidth=2.5 if name == winner else 1.5)

ax.axhline(y_te.mean(), color="red", linestyle=":", alpha=0.5,
           label=f"Random baseline ({y_te.mean():.3f})")
ax.set_xlabel("Recall")
ax.set_ylabel("Precision")
ax.set_title("PR Curve — 전 모델 비교 (★ = 최종 선정)")
ax.legend(fontsize=9)
ax.grid(alpha=0.3)
plt.tight_layout()
out_png = RESULTS / "pr_curve_all.png"
fig.savefig(out_png, dpi=120)
print(f"  → {out_png}")

# ── 8. baseline_results.md 갱신 ───────────────────────────────────────────────
def fmt_row(idx, name, r, note):
    star = " ★" if name == winner else ""
    return (f"| {idx} | {name}{star} "
            f"| **{r['pr_auc']:.4f}** | {r['f1']:.4f} | {note} |")

rows = []
notes = {
    "Dummy":               "기준선",
    "Logistic Regression": "C=1, StandardScaler",
    "Random Forest":       "n_estimators=100",
    "XGBoost":             "n_estimators=100, eval_metric=logloss",
    "LightGBM":            "n_estimators=100, verbose=-1",
}
for i, (name, note) in enumerate(notes.items()):
    if name in results:
        rows.append(fmt_row(i, name, results[name], note))
    else:
        rows.append(f"| {i} | {name} | — | — | 미실행 |")

md = f"""# Baseline 모델 결과 비교

테스트셋: {len(y_te):,}행 (2017-01 ~ 2017-08) | 취소율 {y_te.mean():.1%}

| # | 모델 | PR-AUC | F1@0.5 | 비고 |
|---|------|--------|--------|------|
{chr(10).join(rows)}

## 최종 선정

**{winner}** — {reason}

## 해석 메모

- Dummy PR-AUC ≈ 테스트셋 취소율 (상수 예측기의 이론적 PR-AUC = 양성 비율)
- F1@0.5 = 0.000 : most_frequent → 양성 클래스 TP 없음
- LR·RF·XGBoost·LightGBM 모두 Dummy 대비 큰 폭 개선
- ★ 표시 모델이 `results/model_final.pkl`로 저장됨

## 파이프라인 기준

`src/preprocessing_pipeline.py` 출력 기준.
deposit_type DROP + country Top10+Other OHE + OHE 후 컬럼 수 {X_tr.shape[1]}개.

## PR Curve

![PR Curve](pr_curve_all.png)

## 미결 #2 해소

precipitation_sum vs precipitation_hours 상관: **0.824** (0.9 미만)
→ 현재 단계에서 제거 불필요. Phase 2에서 변수 중요도 확인 후 판단.
"""

(RESULTS / "baseline_results.md").write_text(md, encoding="utf-8")
print(f"  → results/baseline_results.md")

# ── 9. 최종 요약 ──────────────────────────────────────────────────────────────
print("\n" + "=" * 55)
print("모델          PR-AUC    F1@0.5")
print("-" * 55)
for name, r in results.items():
    star = " ★" if name == winner else ""
    print(f"  {name+star:<28s}  {r['pr_auc']:.4f}    {r['f1']:.4f}")
print("=" * 55)
print(f"\n산출물:")
print(f"  results/pr_curve_all.png")
print(f"  results/model_final.pkl  ({winner})")
print(f"  results/baseline_results.md")
