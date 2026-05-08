"""
01_columns_dictionary.py
호텔 예약 데이터의 32개 컬럼 통계를 추출해 표로 출력한다.
사전 문서(01_columns_dictionary.md)의 dtype/결측%/고유값/예시값 컬럼이
실제 데이터와 일치하는지 다시 확인할 때 사용.

사용법:
    python 01_columns_dictionary.py
"""

import pandas as pd

# 데이터 로드
CSV_PATH = "../data/hotel_bookings.csv"   # 본인 경로에 맞게 수정
df = pd.read_csv(CSV_PATH)

# 1. 한눈에 보기
print("=" * 60)
print("📌 데이터 한눈에")
print("=" * 60)
print(f"전체 행 수    : {len(df):,}")
print(f"전체 컬럼 수  : {len(df.columns)}")
print(f"전체 취소율   : {df['is_canceled'].mean() * 100:.2f}%")
print()
print("호텔별 분포 / 취소율:")
print(df.groupby("hotel")["is_canceled"].agg(["count", "mean"]).round(4))
print()
print("도착 연도별 분포:")
print(df["arrival_date_year"].value_counts().sort_index())
print()

# 2. 컬럼별 통계 표
print("=" * 60)
print("📋 컬럼별 통계")
print("=" * 60)
header = f"{'#':>3} | {'컬럼명':<35} | {'타입':<8} | {'결측%':>7} | {'고유값':>7} | 예시값(빈도순 Top3)"
print(header)
print("-" * len(header))

for i, col in enumerate(df.columns, start=1):
    s = df[col]
    null_pct = s.isna().mean() * 100
    nunique = s.nunique(dropna=True)
    # 빈도 높은 값 3개를 예시로
    top3 = s.dropna().value_counts().head(3).index.tolist()
    examples = ", ".join(repr(v) if isinstance(v, str) else str(v) for v in top3)
    print(
        f"{i:>3} | {col:<35} | {str(s.dtype):<8} | "
        f"{null_pct:>6.2f}% | {nunique:>7,} | {examples}"
    )

# 3. 사전 문서에서 언급한 두 가지 사실 검증
print()
print("=" * 60)
print("🔎 사전 문서의 핵심 관찰 검증")
print("=" * 60)

# (1) reservation_status 와 is_canceled 의 관계
print("\n[1] reservation_status vs is_canceled 교차표")
print(pd.crosstab(df["is_canceled"], df["reservation_status"]))

# (2) reserved_room_type 과 assigned_room_type 의 불일치 비율
mismatch = (df["reserved_room_type"] != df["assigned_room_type"]).mean()
print(f"\n[2] 예약 객실 vs 배정 객실 불일치 비율: {mismatch * 100:.2f}%")

# (3) 결측이 있는 컬럼만 정리
print("\n[3] 결측 발견 컬럼")
nulls = df.isna().sum().sort_values(ascending=False)
print(nulls[nulls > 0])
