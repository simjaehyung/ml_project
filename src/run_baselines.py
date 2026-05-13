"""
run_baselines.py
Dummy + LR + RF 한 번에 실행 → PR curve 통합 그래프 + results/baseline_results.md 갱신

실행: 프로젝트 루트에서
    python src/run_baselines.py
"""

import pandas as pd
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score, f1_score, precision_recall_curve
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

ROOT    = Path(__file__).parent.parent
DATA    = ROOT / "data"
RESULTS = ROOT / "results"

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

print(f"OHE 후  train {X_tr.shape}  test {X_te.shape}")

# ── 2. 스케일링 (LR용) ────────────────────────────────────────────────────────
scaler   = StandardScaler()
X_tr_s   = scaler.fit_transform(X_tr)
X_te_s   = scaler.transform(X_te)

# ── 3. 모델 학습 ──────────────────────────────────────────────────────────────
models = {
    "Dummy":              DummyClassifier(strategy="most_frequent"),
    "Logistic Regression": None,
    "Random Forest":       RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
}

results = {}

print("\n[Dummy]")
m = models["Dummy"]
m.fit(X_tr, y_tr)
p = m.predict_proba(X_te)[:, 1]
results["Dummy"] = {
    "proba": p,
    "pr_auc": average_precision_score(y_te, p),
    "f1": f1_score(y_te, p > 0.5),
    "color": "gray", "linestyle": "--",
}
print(f"  PR-AUC {results['Dummy']['pr_auc']:.4f}  F1@0.5 {results['Dummy']['f1']:.4f}")

print("[Logistic Regression]")
lr = LogisticRegression(C=1, max_iter=1000, random_state=42)
lr.fit(X_tr_s, y_tr)
p = lr.predict_proba(X_te_s)[:, 1]
results["Logistic Regression"] = {
    "proba": p,
    "pr_auc": average_precision_score(y_te, p),
    "f1": f1_score(y_te, p > 0.5),
    "color": "steelblue", "linestyle": "-",
}
print(f"  PR-AUC {results['Logistic Regression']['pr_auc']:.4f}  F1@0.5 {results['Logistic Regression']['f1']:.4f}")

print("[Random Forest]  (시간 소요 ~1~3분)")
rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
rf.fit(X_tr, y_tr)
p = rf.predict_proba(X_te)[:, 1]
results["Random Forest"] = {
    "proba": p,
    "pr_auc": average_precision_score(y_te, p),
    "f1": f1_score(y_te, p > 0.5),
    "color": "darkorange", "linestyle": "-",
}
print(f"  PR-AUC {results['Random Forest']['pr_auc']:.4f}  F1@0.5 {results['Random Forest']['f1']:.4f}")

# ── 4. 통합 PR curve 저장 ─────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 6))

for name, r in results.items():
    prec, rec, _ = precision_recall_curve(y_te, r["proba"])
    ax.plot(rec, prec, label=f"{name} (PR-AUC={r['pr_auc']:.4f})",
            color=r["color"], linestyle=r["linestyle"])

ax.axhline(y_te.mean(), color="red", linestyle=":", alpha=0.5,
           label=f"Random baseline ({y_te.mean():.3f})")
ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
ax.set_title("PR Curve — Baseline 비교 (processed pipeline 기준)")
ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout()
fig.savefig(RESULTS / "pr_curve_baseline.png", dpi=120)
print(f"\n통합 PR curve 저장 → results/pr_curve_baseline.png")

# ── 5. baseline_results.md 갱신 ───────────────────────────────────────────────
md = f"""# Baseline 모델 결과 비교

테스트셋: {len(y_te):,}행 (2017-01 ~ 2017-08) | 취소율 {y_te.mean():.1%}

| # | 모델 | PR-AUC | F1@0.5 | 비고 |
|---|------|--------|--------|------|
| 0 | Dummy (most_frequent) | **{results['Dummy']['pr_auc']:.4f}** | {results['Dummy']['f1']:.4f} | 기준선. 이 이상이어야 의미 있음 |
| 1 | Logistic Regression | **{results['Logistic Regression']['pr_auc']:.4f}** | {results['Logistic Regression']['f1']:.4f} | C=1, StandardScaler |
| 2 | Random Forest | **{results['Random Forest']['pr_auc']:.4f}** | {results['Random Forest']['f1']:.4f} | n_estimators=100 |
| 3 | XGBoost | — | — | Week 3 이고은 |
| 4 | LightGBM | — | — | Week 3 김나리 |

## 해석 메모

- Dummy PR-AUC = {results['Dummy']['pr_auc']:.4f} ≈ 테스트셋 취소율. 예상된 수치 (상수 예측기의 이론적 PR-AUC = 양성 비율)
- F1@0.5 = 0.000 : most_frequent → 전부 "취소 없음"으로 예측하므로 양성 클래스 TP 없음
- **실질 기준선: PR-AUC > {results['Dummy']['pr_auc'] + 0.01:.2f} 이상부터 모델이 Dummy를 이김**
- LR·RF 모두 Dummy 대비 큰 폭 개선
- RF PR-AUC {'>' if results['Random Forest']['pr_auc'] > results['Logistic Regression']['pr_auc'] else '<'} LR, RF F1@0.5 {'>' if results['Random Forest']['f1'] > results['Logistic Regression']['f1'] else '<'} LR

## 파이프라인 기준

이 결과는 `src/preprocessing_pipeline.py` 출력 기준.
deposit_type DROP + country Top10+Other OHE 적용됨.

## PR Curve

![PR Curve](pr_curve_baseline.png)

## 미결 #2 해소

precipitation_sum vs precipitation_hours 상관: **0.824** (0.9 미만)
→ 현재 단계에서 제거 불필요. Phase 2에서 변수 중요도 확인 후 판단.
"""

(RESULTS / "baseline_results.md").write_text(md, encoding="utf-8")
print("baseline_results.md 갱신 완료")

print("\n=== 최종 결과 ===")
for name, r in results.items():
    print(f"  {name:25s}  PR-AUC {r['pr_auc']:.4f}  F1@0.5 {r['f1']:.4f}")
