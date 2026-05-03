"""
time_split.py
bookings_weather_pm.csv 를 시간 기반으로 train / test 분리.

기준: 2016-12-31 이전 = train / 2017-01-01 이후 = test
결과: data/train.csv, data/test.csv
"""

import pandas as pd

df = pd.read_csv("../data/bookings_weather_pm.csv")
df["arrival_date"] = pd.to_datetime(df["arrival_date"])

cutoff = pd.Timestamp("2017-01-01")
train = df[df["arrival_date"] < cutoff].copy()
test  = df[df["arrival_date"] >= cutoff].copy()

train.to_csv("../data/train.csv", index=False)
test.to_csv("../data/test.csv",   index=False)

total = len(df)
print(f"train: {len(train):,}행  ({len(train)/total*100:.1f}%)  {train['arrival_date'].min().date()} ~ {train['arrival_date'].max().date()}")
print(f"test : {len(test):,}행  ({len(test)/total*100:.1f}%)  {test['arrival_date'].min().date()} ~ {test['arrival_date'].max().date()}")
print()
print(f"train 취소율: {train['is_canceled'].mean()*100:.2f}%")
print(f"test  취소율: {test['is_canceled'].mean()*100:.2f}%")
print()
print("저장 완료 -> data/train.csv, data/test.csv")
