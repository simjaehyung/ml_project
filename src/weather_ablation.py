"""
weather_ablation.py
LightGBM PR-AUC: with vs without weather features
+ Bootstrap 95% CI for best model
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import average_precision_score, precision_recall_curve
from sklearn.utils import resample
from lightgbm import LGBMClassifier

ROOT    = Path(__file__).parent.parent
DATA    = ROOT / "data"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

# ── 1. Load ───────────────────────────────────────────────────────────────────
train = pd.read_csv(DATA / "train_processed.csv")
test  = pd.read_csv(DATA / "test_processed.csv")
print(f"Loaded: train {train.shape}  test {test.shape}")
print(f"\nAll columns ({len(train.columns)}):\n{list(train.columns)}")

# ── 2. Identify weather columns ───────────────────────────────────────────────
# Weather variables kept after multicollinearity drop in preprocessing:
# precipitation_sum, precipitation_hours, temperature_2m_max,
# temperature_2m_min, wind_speed_10m_max, daylight_duration, sunshine_duration
WEATHER_CANDIDATES = [
    "precipitation_sum", "precipitation_hours",
    "temperature_2m_max", "temperature_2m_min",
    "wind_speed_10m_max", "daylight_duration", "sunshine_duration",
    # Include dropped ones in case they remain in CSVs
    "temperature_2m_mean", "wind_speed_10m_mean", "rain_sum",
]
weather_cols = [c for c in WEATHER_CANDIDATES if c in train.columns]
print(f"\nWeather columns found ({len(weather_cols)}): {weather_cols}")

# ── 3. OHE (same as run_all_models.py) ───────────────────────────────────────
cat_cols = ["hotel", "meal", "market_segment", "distribution_channel",
            "reserved_room_type", "customer_type", "country_grouped"]

train_e = pd.get_dummies(train, columns=cat_cols)
test_e  = pd.get_dummies(test,  columns=cat_cols)
test_e  = test_e.reindex(columns=train_e.columns, fill_value=0)

TARGET = "is_canceled"
X_tr = train_e.drop(TARGET, axis=1)
y_tr = train_e[TARGET]
X_te = test_e.drop(TARGET, axis=1)
y_te = test_e[TARGET]

print(f"\nOHE done: X_tr {X_tr.shape}  X_te {X_te.shape}")
print(f"Test cancel rate: {y_te.mean():.3f}  ({y_te.sum():,}/{len(y_te):,})")

# ── 4. Identify weather cols in OHE feature space ────────────────────────────
weather_feat_cols = [c for c in weather_cols if c in X_tr.columns]
non_weather_cols  = [c for c in X_tr.columns if c not in weather_feat_cols]

print(f"\nWeather feature cols in OHE space: {weather_feat_cols}")
print(f"Non-weather feature count: {len(non_weather_cols)}")

# ── 5a. LightGBM WITH weather ─────────────────────────────────────────────────
print("\n" + "="*60)
print("Training LightGBM WITH weather features...")
lgb_with = LGBMClassifier(n_estimators=100, random_state=42, verbose=-1, n_jobs=-1)
lgb_with.fit(X_tr, y_tr)
proba_with = lgb_with.predict_proba(X_te)[:, 1]
pr_auc_with = average_precision_score(y_te, proba_with)
print(f"  PR-AUC WITH weather: {pr_auc_with:.4f}")

# ── 5b. LightGBM WITHOUT weather ─────────────────────────────────────────────
print("\nTraining LightGBM WITHOUT weather features...")
lgb_no = LGBMClassifier(n_estimators=100, random_state=42, verbose=-1, n_jobs=-1)
lgb_no.fit(X_tr[non_weather_cols], y_tr)
proba_no = lgb_no.predict_proba(X_te[non_weather_cols])[:, 1]
pr_auc_no = average_precision_score(y_te, proba_no)
print(f"  PR-AUC WITHOUT weather: {pr_auc_no:.4f}")

# ── 6. Delta ──────────────────────────────────────────────────────────────────
delta = pr_auc_with - pr_auc_no
print(f"\n  Delta (with - without): {delta:+.4f}  "
      f"({'weather helps' if delta > 0 else 'weather hurts' if delta < 0 else 'no change'})")

# ── 7. Feature importance (gain) for WITH-weather model ──────────────────────
print("\n" + "="*60)
print("Feature importances (gain) - WITH weather model:")
feat_names = X_tr.columns.tolist()
importances = lgb_with.booster_.feature_importance(importance_type="gain")
fi = pd.Series(importances, index=feat_names).sort_values(ascending=False)

print("\nTop 20 features (gain):")
for i, (feat, val) in enumerate(fi.head(20).items(), 1):
    is_weather = "(WEATHER)" if feat in weather_feat_cols else ""
    print(f"  {i:2d}. {feat:<40s}  {val:12.2f}  {is_weather}")

print("\nTop 5 only:")
for i, (feat, val) in enumerate(fi.head(5).items(), 1):
    is_weather = "(WEATHER)" if feat in weather_feat_cols else ""
    print(f"  {i}. {feat}  {val:.2f}  {is_weather}")

# Weather cols in top-20?
top20 = fi.head(20).index.tolist()
weather_in_top20 = [c for c in weather_feat_cols if c in top20]
print(f"\nWeather features in top-20: {weather_in_top20 if weather_in_top20 else 'None'}")

# ── 8. Bootstrap 95% CI (WITH-weather model) ─────────────────────────────────
print("\n" + "="*60)
print("Bootstrap 95% CI (200 iterations, WITH-weather model)...")

np.random.seed(42)
n_boot = 200
boot_scores = []
y_te_arr    = y_te.values
proba_arr   = proba_with

for i in range(n_boot):
    idx = resample(np.arange(len(y_te_arr)), random_state=i)
    score = average_precision_score(y_te_arr[idx], proba_arr[idx])
    boot_scores.append(score)

boot_scores = np.array(boot_scores)
ci_lo = np.percentile(boot_scores, 2.5)
ci_hi = np.percentile(boot_scores, 97.5)
ci_mean = boot_scores.mean()
ci_std  = boot_scores.std()

print(f"  Bootstrap mean  PR-AUC: {ci_mean:.4f}")
print(f"  Bootstrap std:          {ci_std:.4f}")
print(f"  95% CI: [{ci_lo:.4f}, {ci_hi:.4f}]")

# ── 9. Also compute bootstrap for NO-weather model ───────────────────────────
print("\nBootstrap 95% CI (WITHOUT-weather model)...")
boot_no = []
proba_no_arr = proba_no
for i in range(n_boot):
    idx = resample(np.arange(len(y_te_arr)), random_state=i)
    score = average_precision_score(y_te_arr[idx], proba_no_arr[idx])
    boot_no.append(score)
boot_no = np.array(boot_no)
ci_lo_no = np.percentile(boot_no, 2.5)
ci_hi_no = np.percentile(boot_no, 97.5)
print(f"  95% CI (no weather): [{ci_lo_no:.4f}, {ci_hi_no:.4f}]")

# ── 10. Final summary ─────────────────────────────────────────────────────────
print("\n" + "="*60)
print("ABLATION STUDY SUMMARY")
print("="*60)
print(f"Weather columns found ({len(weather_feat_cols)}): {weather_feat_cols}")
print(f"\nPR-AUC WITH weather:    {pr_auc_with:.4f}   95% CI [{ci_lo:.4f}, {ci_hi:.4f}]")
print(f"PR-AUC WITHOUT weather: {pr_auc_no:.4f}   95% CI [{ci_lo_no:.4f}, {ci_hi_no:.4f}]")
print(f"Delta (with - without): {delta:+.4f}  "
      f"({'weather helps' if delta > 0 else 'weather hurts' if delta < 0 else 'no change'})")
print(f"\nTop 5 feature importances (gain) [WITH weather]:")
for i, (feat, val) in enumerate(fi.head(5).items(), 1):
    tag = " <-- WEATHER" if feat in weather_feat_cols else ""
    print(f"  {i}. {feat}: {val:.2f}{tag}")
print(f"\nWeather in top-20: {weather_in_top20 if weather_in_top20 else 'None'}")

# Save summary to results
summary_lines = [
    "# Weather Ablation Study — LightGBM",
    "",
    f"Weather columns found ({len(weather_feat_cols)}): {weather_feat_cols}",
    "",
    f"| Model | PR-AUC | 95% CI (bootstrap n=200) |",
    f"|-------|--------|--------------------------|",
    f"| WITH weather | {pr_auc_with:.4f} | [{ci_lo:.4f}, {ci_hi:.4f}] |",
    f"| WITHOUT weather | {pr_auc_no:.4f} | [{ci_lo_no:.4f}, {ci_hi_no:.4f}] |",
    f"| Delta | {delta:+.4f} | — |",
    "",
    "Top 5 feature importances (gain, WITH weather):",
]
for i, (feat, val) in enumerate(fi.head(5).items(), 1):
    tag = " <-- WEATHER" if feat in weather_feat_cols else ""
    summary_lines.append(f"  {i}. {feat}: {val:.2f}{tag}")
summary_lines += [
    "",
    f"Weather features in top-20: {weather_in_top20 if weather_in_top20 else 'None'}",
]
(RESULTS / "weather_ablation.md").write_text("\n".join(summary_lines), encoding="utf-8")
print(f"\nSaved: results/weather_ablation.md")
