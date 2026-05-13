"""
make_seasonal_weather.py  ← 김나리 담당

train.csv의 날씨 데이터로 호텔×월별 계절 평균값을 계산해 저장.
탭2 신규 예약 입력 시 자동으로 이 값이 채워짐 (미결 #10 해소).

실행:
    python src/make_seasonal_weather.py

출력:
    data/seasonal_weather.csv
    (hotel, arrival_date_month, 날씨 7개 컬럼)
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

WEATHER_COLS = [
    "precipitation_sum",
    "temperature_2m_max",
    "temperature_2m_min",
    "wind_speed_10m_max",
    "precipitation_hours",
    "relative_humidity_2m_mean",
    "cloud_cover_mean",
]

MONTH_MAP = {
    "January": 1,  "February": 2,  "March": 3,    "April": 4,
    "May": 5,      "June": 6,      "July": 7,      "August": 8,
    "September": 9,"October": 10,  "November": 11, "December": 12,
}


def main():
    train = pd.read_csv(ROOT / "data" / "train.csv")
    print(f"로드 완료: {train.shape}")

    # 월 숫자 변환
    train["month_num"] = train["arrival_date_month"].map(MONTH_MAP)

    # 날씨 컬럼 존재 확인
    missing = [c for c in WEATHER_COLS if c not in train.columns]
    if missing:
        print(f"[경고] 없는 컬럼: {missing}")
        WEATHER_COLS_USE = [c for c in WEATHER_COLS if c in train.columns]
    else:
        WEATHER_COLS_USE = WEATHER_COLS

    # hotel × month 평균
    seasonal = (
        train.groupby(["hotel", "month_num"])[WEATHER_COLS_USE]
             .mean()
             .round(2)
             .reset_index()
             .rename(columns={"month_num": "arrival_date_month"})
    )

    out_path = ROOT / "data" / "seasonal_weather.csv"
    seasonal.to_csv(out_path, index=False)
    print(f"\n저장 완료: {out_path}")
    print(f"행 수: {len(seasonal)} (호텔 2개 × 월 최대 12개 = 최대 24행)\n")
    print(seasonal.to_string(index=False))


if __name__ == "__main__":
    main()
