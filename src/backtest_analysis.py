"""
backtest_analysis.py
오버부킹 최적화 + 음식 커버 예측 백테스트
Naive / Historical Rate / LightGBM 모델 3방향 비교
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pickle
import pandas as pd
import numpy as np
from pathlib import Path

ROOT    = Path(__file__).parent.parent
DATA    = ROOT / "data"
RESULTS = ROOT / "results"

# ── 1. 로드 ────────────────────────────────────────────────────────────────────
with open(RESULTS / "model_lgbm.pkl", "rb") as f:
    model = pickle.load(f)

train_proc = pd.read_csv(DATA / "train_processed.csv")
test_proc  = pd.read_csv(DATA / "test_processed.csv")
test_raw   = pd.read_csv(DATA / "test.csv")
train_raw  = pd.read_csv(DATA / "train.csv")

cat_cols = ["hotel", "meal", "market_segment", "distribution_channel",
            "reserved_room_type", "customer_type", "country_grouped"]
train_e = pd.get_dummies(train_proc, columns=cat_cols)
test_e  = pd.get_dummies(test_proc,  columns=cat_cols)
test_e  = test_e.reindex(columns=train_e.columns, fill_value=0)

X_te = test_e.drop("is_canceled", axis=1)
cancel_prob = model.predict_proba(X_te)[:, 1]

test_raw = test_raw.reset_index(drop=True)
test_raw["cancel_prob"]    = cancel_prob
test_raw["total_guests"]   = test_raw["adults"] + test_raw["children"].fillna(0)
test_raw["actual_arrived"] = 1 - test_raw["is_canceled"]

# ── 2. Historical 취소율 (train 기준, 호텔별) ──────────────────────────────────
hist_rate = train_raw.groupby("hotel")["is_canceled"].mean()
print("=== Train 기준 Historical 취소율 ===")
print(hist_rate.round(3).to_string())
print(f"전체: {train_raw['is_canceled'].mean():.3f}\n")

test_raw["hist_rate"] = test_raw["hotel"].map(hist_rate)

# ── 3. 날짜별 취소 예측 3방향 비교 ────────────────────────────────────────────
def rmse(a, p): return np.sqrt(((a - p) ** 2).mean())
def mae(a, p):  return (a - p).abs().mean()

daily = test_raw.groupby("arrival_date").agg(
    n=("is_canceled", "count"),
    actual_cancels=("is_canceled", "sum"),
    model_pred=("cancel_prob", "sum"),
    hist_pred=("hist_rate", lambda x: x.sum()),  # sum of hist_rates = expected cancels
).reset_index()
# hist_pred 보정: 각 예약의 hist_rate를 합산하면 expected cancels
daily["naive_pred"] = 0

print("=== [오버부킹] 날짜별 취소 예측 정확도 ===")
print(f"{'방법':<22} {'RMSE':>8} {'MAE':>8} {'vs Historical':>14}")
print("-" * 56)
r_naive = rmse(daily["actual_cancels"], daily["naive_pred"])
r_hist  = rmse(daily["actual_cancels"], daily["hist_pred"])
r_model = rmse(daily["actual_cancels"], daily["model_pred"])
m_naive = mae(daily["actual_cancels"],  daily["naive_pred"])
m_hist  = mae(daily["actual_cancels"],  daily["hist_pred"])
m_model = mae(daily["actual_cancels"],  daily["model_pred"])

print(f"  Naive (0명 취소 가정)    {r_naive:>8.2f} {m_naive:>8.2f}  --")
print(f"  Historical Rate         {r_hist:>8.2f} {m_hist:>8.2f}  --")
print(f"  LightGBM 모델           {r_model:>8.2f} {m_model:>8.2f}  {(1-r_model/r_hist)*100:>+.1f}%")
print()
print(f"  일평균 실제 취소: {daily['actual_cancels'].mean():.1f}건")
print(f"  일평균 hist 예측: {daily['hist_pred'].mean():.1f}건")
print(f"  일평균 모델 예측: {daily['model_pred'].mean():.1f}건")
print(f"  분석 기간: {daily['arrival_date'].min()} ~ {daily['arrival_date'].max()}")

# ── 4. 조식 커버 예측 3방향 비교 ──────────────────────────────────────────────
print("\n=== [식재료 발주] 조식 커버 예측 정확도 (BB+HB+FB) ===")

bf = test_raw[test_raw["meal"].isin(["BB", "HB", "FB"])].copy()

def daily_cover_stats(df):
    return df.groupby("arrival_date").apply(
        lambda g: pd.Series({
            "actual": (g["total_guests"] * g["actual_arrived"]).sum(),
            "naive":   g["total_guests"].sum(),
            "hist":   (g["total_guests"] * (1 - g["hist_rate"])).sum(),
            "model":  (g["total_guests"] * (1 - g["cancel_prob"])).sum(),
        }),
        include_groups=False
    ).reset_index()

bf_daily = daily_cover_stats(bf)

print(f"{'방법':<22} {'RMSE':>8} {'MAE':>8} {'초과발주 합계':>14} {'vs Historical':>14}")
print("-" * 70)
for col, label in [("naive", "Naive"), ("hist", "Historical Rate"), ("model", "LightGBM 모델")]:
    r = rmse(bf_daily["actual"], bf_daily[col])
    m = mae(bf_daily["actual"],  bf_daily[col])
    waste = (bf_daily[col] - bf_daily["actual"]).clip(lower=0).sum()
    if col == "hist":
        imp = "--"
    else:
        imp = f"{(1-r/rmse(bf_daily['actual'], bf_daily['hist']))*100:+.1f}%"
    print(f"  {label:<20} {r:>8.2f} {m:>8.2f} {waste:>14,.0f}커버 {imp:>14}")

# ── 5. Resort Hotel 석식 (HB+FB) ──────────────────────────────────────────────
print("\n=== [Resort Hotel] 석식 커버 예측 (HB+FB) ===")
rd = test_raw[(test_raw["hotel"] == "Resort Hotel") &
              (test_raw["meal"].isin(["HB", "FB"]))].copy()
rd_daily = daily_cover_stats(rd)

for col, label in [("naive", "Naive"), ("hist", "Historical Rate"), ("model", "LightGBM 모델")]:
    r = rmse(rd_daily["actual"], rd_daily[col])
    m = mae(rd_daily["actual"],  rd_daily[col])
    waste = (rd_daily[col] - rd_daily["actual"]).clip(lower=0).sum()
    if col == "hist":
        imp = "--"
    else:
        imp = f"{(1-r/rmse(rd_daily['actual'], rd_daily['hist']))*100:+.1f}%"
    print(f"  {label:<20} {r:>8.2f} {m:>8.2f} {waste:>14,.0f}커버 {imp:>14}")

# ── 6. 비용 추정 ──────────────────────────────────────────────────────────────
print("\n=== 비용 절감 추정 (Historical Rate 대비) ===")
hist_bf_waste  = (bf_daily["hist"]  - bf_daily["actual"]).clip(lower=0).sum()
model_bf_waste = (bf_daily["model"] - bf_daily["actual"]).clip(lower=0).sum()
saved_covers   = hist_bf_waste - model_bf_waste
cost_per_cover = 10  # EUR, 업계 평균

print(f"조식 기준 6개월 절감: {saved_covers:,.0f} 커버")
print(f"EUR {cost_per_cover}/커버 기준: EUR {saved_covers*cost_per_cover:,.0f}")
print(f"연환산 추정: EUR {saved_covers*cost_per_cover*2:,.0f}")
print()
print("* 한계: 취소 타이밍 데이터 없음 — 발주 조정 가능한 취소(도착 3일+ 전)만 실제 절감")
print("* 실제 절감액은 위 수치의 50~70% 수준으로 보수적으로 봐야 함")
print("* EUR 10/커버는 업계 평균 추정값 (실제 원가에 따라 달라짐)")

# ── 7. 캘리브레이션 요약 ──────────────────────────────────────────────────────
print("\n=== 캘리브레이션 요약 (예측 확률 신뢰도) ===")
bins   = [0, 0.2, 0.4, 0.6, 0.8, 1.01]
labels = ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"]
cal_df = pd.DataFrame({"prob": cancel_prob, "actual": test_e["is_canceled"].values})
cal_df["bucket"] = pd.cut(cal_df["prob"], bins=bins, labels=labels, right=False)
calib = cal_df.groupby("bucket", observed=True).agg(
    n=("actual", "count"),
    mean_pred=("prob", "mean"),
    actual_rate=("actual", "mean"),
).round(3)
calib["gap"] = (calib["mean_pred"] - calib["actual_rate"]).abs().round(3)
print(calib.to_string())
print(f"\n평균 캘리브레이션 gap: {calib['gap'].mean():.3f}")
print("(0에 가까울수록 '예측 확률 = 실제 취소율'에 근접)")
