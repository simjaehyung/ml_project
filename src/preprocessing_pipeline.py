"""
preprocessing_pipeline.py
데이터 확인 결과 (2026-05-07):
  - reservation_status 등 확정 DROP 5개: bookings_weather_pm 단계에서 이미 제거됨
  - agent / company: 이미 0/1 인디케이터로 변환됨
  - 이 스크립트에서 처리할 것: 날씨 3개 DROP, deposit_type DROP, country 그룹핑, children NaN, month 숫자, arrival_date 제거

실행: 프로젝트 루트에서
    python src/preprocessing_pipeline.py
출력: data/train_processed.csv, data/test_processed.csv
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

# ── 1. 로드 ───────────────────────────────────────────────────────────────────
train = pd.read_csv(DATA / "train.csv")
test  = pd.read_csv(DATA / "test.csv")
print(f"로드 완료  train {train.shape}  test {test.shape}")

# ── 2. 날씨 다중공선성 DROP (3개) ──────────────────────────────────────────────
weather_drop = ["temperature_2m_mean", "wind_speed_10m_mean", "rain_sum"]
train = train.drop(columns=weather_drop)
test  = test.drop(columns=weather_drop)

# ── 3. deposit_type DROP (Non Refund 99.2% 취소율 — 사후 기록 오염 가능성, 2026-05-08 확정)
train = train.drop(columns=["deposit_type"])
test  = test.drop(columns=["deposit_type"])

# ── 4. arrival_date 제거 (time_split 용도로만 사용된 임시 컬럼) ──────────────────
train = train.drop(columns=["arrival_date"])
test  = test.drop(columns=["arrival_date"])

# ── 5. children NaN → 0 ───────────────────────────────────────────────────────
train["children"] = train["children"].fillna(0)
test["children"]  = test["children"].fillna(0)

# ── 6. arrival_date_month 숫자 변환 ───────────────────────────────────────────
month_map = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}
train["arrival_date_month"] = train["arrival_date_month"].map(month_map)
test["arrival_date_month"]  = test["arrival_date_month"].map(month_map)

# ── 7. country → Top10 + Other (train 기준으로 top10 결정, leakage 방지) ────────
top10_countries = train["country"].value_counts().nlargest(10).index.tolist()
print(f"Top10 국가: {top10_countries}")

train["country_grouped"] = train["country"].where(train["country"].isin(top10_countries), other="Other")
test["country_grouped"]  = test["country"].where(test["country"].isin(top10_countries), other="Other")
train = train.drop(columns=["country"])
test  = test.drop(columns=["country"])

# ── 8. 저장 ───────────────────────────────────────────────────────────────────
train.to_csv(DATA / "train_processed.csv", index=False)
test.to_csv(DATA / "test_processed.csv",   index=False)

# ── 9. 결과 요약 ──────────────────────────────────────────────────────────────
print(f"\n처리 완료")
print(f"  train_processed: {train.shape}  취소율 {train['is_canceled'].mean():.3f}")
print(f"  test_processed:  {test.shape}   취소율 {test['is_canceled'].mean():.3f}")
print(f"\n컬럼 ({train.shape[1]}개): {list(train.columns)}")
print(f"\nNaN 합계 (train): {train.isnull().sum().sum()}")
print(f"\ncountry_grouped 분포:\n{train['country_grouped'].value_counts()}")
