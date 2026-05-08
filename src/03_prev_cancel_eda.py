"""
18번 previous_cancellations EDA — Week 2 STEP 2 (Dev A)

목적:
1. PM 가이드 — 연도별(2015/2016) 분포 + ≥1 그룹 취소율 (기대값 90%+)
2. 미결 항목 C (design_04) — `is_repeated_guest=0`인데 `previous_cancellations≥1`인 행
   약 2,674건의 정의 어긋남 패턴 검증

실행:
  cd ml_project
  ../hotel-noshow/.venv/Scripts/python.exe src/03_prev_cancel_eda.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
import pandas as pd

# 데이터 로드 — train.csv는 시간 분할된 raw 데이터 (전처리 전, .gitignore 예외로 추적됨)
DATA = Path(__file__).parent.parent / "data" / "train.csv"
df = pd.read_csv(DATA)
print(f"train.csv shape: {df.shape}")
print(f"전체 취소율: {df['is_canceled'].mean():.2%}")
print()

# ─── [E1] 연도별 분포 (PM 가이드 (a)) ──────────────────────────────
print("=" * 60)
print("[E1] previous_cancellations — 연도별 분포")
print("=" * 60)
for yr in sorted(df["arrival_date_year"].unique()):
    sub = df[df["arrival_date_year"] == yr]
    print(f"\n[{yr}년] n = {len(sub):,}")
    print(f"  previous_cancellations 분포:")
    counts = sub["previous_cancellations"].value_counts().sort_index().head(5)
    for v, n in counts.items():
        print(f"    값 {v}: {n:>6,}건 ({n/len(sub):.1%})")
    print(f"  ≥1 비율: {(sub['previous_cancellations'] >= 1).mean():.2%}")

# ─── [E2] ≥1 그룹 연도별 취소율 (PM 가이드 (b)) ────────────────────
print()
print("=" * 60)
print("[E2] previous_cancellations ≥1 그룹의 취소율 (연도별)")
print("=" * 60)
print("기대값: 90%+. 낙으면 PM 보고")
print()
for yr in sorted(df["arrival_date_year"].unique()):
    sub = df[df["arrival_date_year"] == yr]
    high = sub[sub["previous_cancellations"] >= 1]
    if len(high) > 0:
        rate = high["is_canceled"].mean()
        flag = "✓" if rate >= 0.90 else "⚠ 90% 미만"
        print(f"  {yr}: ≥1 그룹 n={len(high):>5,} → 취소율 {rate:.2%}  {flag}")
    else:
        print(f"  {yr}: ≥1 그룹 0건")

# 전체 합산
high_all = df[df["previous_cancellations"] >= 1]
print(f"\n  전체: ≥1 그룹 n={len(high_all):,} → 취소율 {high_all['is_canceled'].mean():.2%}")

# ─── [E3] 정의 어긋남 검증 (미결 항목 C) ──────────────────────────
print()
print("=" * 60)
print("[E3] 미결 C — is_repeated_guest=0 인데 previous_cancellations≥1 인 행")
print("=" * 60)

mismatch = df[(df["is_repeated_guest"] == 0) & (df["previous_cancellations"] >= 1)]
n_mis = len(mismatch)
print(f"\n행 수: {n_mis:,} (전체의 {n_mis/len(df):.2%})")

if n_mis > 0:
    print(f"\n이 그룹의 특성:")
    print(f"  취소율: {mismatch['is_canceled'].mean():.2%}")
    print(f"  vs 전체 ≥1 그룹 취소율: {high_all['is_canceled'].mean():.2%}")

    print(f"\n  호텔 분포:")
    for h, n in mismatch["hotel"].value_counts().items():
        rate = mismatch[mismatch["hotel"] == h]["is_canceled"].mean()
        print(f"    {h}: {n:,}건 (취소율 {rate:.2%})")

    print(f"\n  lead_time 통계:")
    lt = mismatch["lead_time"]
    print(f"    mean {lt.mean():.0f} / median {lt.median():.0f} / max {lt.max()}")
    print(f"    vs 전체 lead_time mean: {df['lead_time'].mean():.0f}")

    print(f"\n  market_segment 분포 (Top 5):")
    for seg, n in mismatch["market_segment"].value_counts().head(5).items():
        print(f"    {seg}: {n:,}건 ({n/n_mis:.1%})")

    print(f"\n  previous_cancellations 값 분포 (Top 5):")
    for v, n in mismatch["previous_cancellations"].value_counts().head(5).items():
        print(f"    값 {v}: {n:,}건")

    print(f"\n  연도별:")
    for yr in sorted(mismatch["arrival_date_year"].unique()):
        sub = mismatch[mismatch["arrival_date_year"] == yr]
        rate = sub["is_canceled"].mean()
        print(f"    {yr}: {len(sub):,}건 (취소율 {rate:.2%})")

# ─── [E4] 비교군: is_repeated_guest=1 & ≥1 (정상 정의대로) ───────
print()
print("=" * 60)
print("[E4] 비교군: is_repeated_guest=1 & previous_cancellations≥1 (정의 정상)")
print("=" * 60)

normal = df[(df["is_repeated_guest"] == 1) & (df["previous_cancellations"] >= 1)]
print(f"\n행 수: {len(normal):,} (전체의 {len(normal)/len(df):.2%})")
if len(normal) > 0:
    print(f"  취소율: {normal['is_canceled'].mean():.2%}")
    print(f"  lead_time mean: {normal['lead_time'].mean():.0f}")

# ─── [E5] 전체 sanity ────────────────────────────────────────────
print()
print("=" * 60)
print("[E5] 전체 sanity — is_repeated_guest × previous_cancellations≥1 교차표")
print("=" * 60)
print()
ct = pd.crosstab(
    df["is_repeated_guest"],
    df["previous_cancellations"] >= 1,
    margins=True, margins_name="합계",
)
ct.columns = ["prev=0", "prev≥1", "합계"]
print(ct)

print()
print("=" * 60)
print("끝. 결과 해석은 docs/week2_eda_prev_cancel.md 에 정리.")
print("=" * 60)
