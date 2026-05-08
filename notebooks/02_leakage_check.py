"""
02_leakage_check.py
누수 후보 분류표(docs/leakage_candidates.md)의 근거를 데이터로 직접 확인.

이 스크립트의 역할은 "분류표에 기록된 수치/사실이 실제 데이터와 일치하는지"
재현 가능한 형태로 출력하는 것. 분류표의 '검증 방법' 칸에 적힌 명령들이
이 스크립트의 각 섹션과 1:1 대응됨.

사용법:
    python 02_leakage_check.py
"""

import sys

import pandas as pd

# Windows 한국어 콘솔(cp949)에서 이모지(🔴 등)가 인코딩 안 되는 걸 회피.
# 매번 PYTHONUTF8=1 안 붙여도 되도록 스크립트 자체에서 stdout을 utf-8로 재설정.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

CSV_PATH = "../data/hotel_bookings.csv"   # 본인 경로에 맞게 수정
df = pd.read_csv(CSV_PATH)

# 도착일 datetime 컬럼을 한 번만 만들어 두고 재사용
# (원본 컬럼은 건드리지 않음 — 가설 주입 순환 회피)
df["_arrival_date"] = pd.to_datetime(
    df["arrival_date_year"].astype(str)
    + "-"
    + df["arrival_date_month"]
    + "-"
    + df["arrival_date_day_of_month"].astype(str),
    format="%Y-%B-%d",
)
df["_reservation_status_date"] = pd.to_datetime(df["reservation_status_date"])

print("=" * 70)
print("🔴 명백 누수 컬럼 (Leak: confirmed) — drop 확정 후보")
print("=" * 70)

# ---------------------------------------------------------------------------
# [L1] reservation_status — 타깃과 정의상 동치인지 확인
# ---------------------------------------------------------------------------
print("\n[L1] reservation_status × is_canceled 교차표")
ct = pd.crosstab(df["is_canceled"], df["reservation_status"])
print(ct)

# Check-Out 은 is_canceled=0 으로만, Canceled/No-Show 는 is_canceled=1 로만 가야 함
checkout_leak = ct.loc[1, "Check-Out"] if "Check-Out" in ct.columns else 0
canceled_clean = ct.loc[0, "Canceled"] if "Canceled" in ct.columns else 0
noshow_clean = ct.loc[0, "No-Show"] if "No-Show" in ct.columns else 0
violations = checkout_leak + canceled_clean + noshow_clean
print(
    f"\n  → 정의상 동치 위반 행 수: {violations:,} / {len(df):,}  "
    f"({violations / len(df) * 100:.4f}%)"
)
print("  → 위반 0이면 reservation_status 는 is_canceled 의 별칭. drop 확정.")

# ---------------------------------------------------------------------------
# [L2] reservation_status_date — 도착일 이후에도 값이 갱신되는지 확인
# ---------------------------------------------------------------------------
print("\n[L2] reservation_status_date 가 도착일을 지난 후 갱신되는가?")
delta_days = (df["_reservation_status_date"] - df["_arrival_date"]).dt.days

# 그룹별로 분포 보기 (취소건 / 정상건)
for label, sub in df.groupby("is_canceled"):
    d = (sub["_reservation_status_date"] - sub["_arrival_date"]).dt.days
    name = "정상 체크인 (is_canceled=0)" if label == 0 else "취소·노쇼 (is_canceled=1)"
    print(f"\n  · {name}: n={len(sub):,}")
    print(f"    delta(일) 분포  min={d.min()}, median={d.median()}, max={d.max()}")
    print(f"    도착일 이후(>=0)인 비율: {(d >= 0).mean() * 100:.2f}%")
    print(f"    도착일 이전(<0)인 비율 : {(d < 0).mean() * 100:.2f}%")

print(
    "\n  → 정상건은 status_date 가 도착일 이후(체크아웃 시점)로 갱신되고,"
    "\n    취소건은 도착 전이라도 '취소 처리한 날짜'로 갱신됨."
    "\n    어느 쪽이든 '예약 시점에 알 수 없는 미래 정보' → drop 확정."
)

# ---------------------------------------------------------------------------
# 정리 출력
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("요약")
print("=" * 70)
print("L1. reservation_status      → 🔴 누수 확정 (타깃과 정의상 동치)")
print("L2. reservation_status_date → 🔴 누수 확정 (도착일 이후 갱신되는 시점값)")


print("\n" + "=" * 70)
print("🟡 보류 컬럼 (회의 안건)")
print("=" * 70)

# ---------------------------------------------------------------------------
# [Y1] assigned_room_type — 체크인 시점 배정값인가, 예약 시점 디폴트인가?
# ---------------------------------------------------------------------------
# 핵심 가설: assigned 가 '체크인 시점에 배정' 이라면, 취소건(체크인 안 함)은
# assigned 값이 reserved 와 같게 디폴트로 채워졌을 가능성이 큼.
# 정상건만 불일치가 많다면 → assigned 는 체크인 시점에 갱신되는 값 → 누수.
print("\n[Y1] assigned_room_type — 체크인 시점 갱신 여부")

mask = df["reserved_room_type"] != df["assigned_room_type"]
print(f"\n  · 전체 reserved≠assigned 불일치: {mask.mean() * 100:.2f}%  ({mask.sum():,}건)")

# is_canceled 별 불일치 비율
print("\n  · 그룹별 불일치 비율:")
for label, sub in df.groupby("is_canceled"):
    m = (sub["reserved_room_type"] != sub["assigned_room_type"]).mean()
    name = "정상 체크인 (is_canceled=0)" if label == 0 else "취소·노쇼 (is_canceled=1)"
    print(f"    {name}: n={len(sub):,}, 불일치 {m * 100:.2f}%")

# reserved=A, assigned=A 같은 가장 흔한 케이스 대신 '실제 배정이 일어난' 케이스에
# 집중하기 위해 불일치 행만 모아 is_canceled 분포 확인
mismatch_only = df.loc[mask, "is_canceled"]
print(
    f"\n  · 불일치 {mask.sum():,}건 중 is_canceled=1 비율: "
    f"{mismatch_only.mean() * 100:.2f}%  "
    f"(전체 평균 {df['is_canceled'].mean() * 100:.2f}% 와 비교)"
)

print(
    "\n  → 해석:"
    "\n    · 만약 정상건의 불일치가 압도적이면 → 'assigned 는 체크인 후 갱신' 가설 지지 → 🔴"
    "\n    · 두 그룹 비슷하면 → 예약 시점 또는 그 직후에 채워지는 값일 수 있음 → 🟡 유지"
    "\n    · 회의에서 결정 (Dev A·B + PM)"
)

# ---------------------------------------------------------------------------
# [Y2] booking_changes — 변경이 언제 일어났는지 시점이 데이터에 없음.
# 간접 신호 3가지로 누수성 추론.
# ---------------------------------------------------------------------------
# 가설: 변경이 도착 임박해서 일어났다면 누수, 예약 직후 일어났다면 안전.
# 단서가 없으므로 (a) 분포 차이, (b) 값별 취소율, (c) 0 vs 1+ 비교 로 추론.
print("\n[Y2] booking_changes — 시점 미기록 → 간접 신호로 추론")

# (a) is_canceled 별 booking_changes 분포
print("\n  (a) is_canceled 별 booking_changes 통계")
stat = df.groupby("is_canceled")["booking_changes"].agg(
    ["mean", "median", "max", lambda s: (s == 0).mean()]
)
stat.columns = ["mean", "median", "max", "pct_zero"]
print(stat.round(4))

# (b) booking_changes 값별 취소율 (값이 큰 쪽은 표본이 작아 따로 묶음)
print("\n  (b) booking_changes 값별 취소율 (n과 함께)")
g = df.groupby("booking_changes")["is_canceled"].agg(["count", "mean"]).round(4)
g.columns = ["n", "cancel_rate"]
# 0~5 까지 따로, 6+ 묶기
small = g.loc[g.index <= 5]
big_idx = g.index > 5
big = pd.DataFrame(
    {
        "n": [g.loc[big_idx, "n"].sum()],
        "cancel_rate": [
            (
                df.loc[df["booking_changes"] > 5, "is_canceled"].mean()
                if (df["booking_changes"] > 5).any()
                else float("nan")
            )
        ],
    },
    index=["6+"],
)
print(pd.concat([small, big]))

# (c) 0 vs 1+ 그룹 취소율
zero_rate = df.loc[df["booking_changes"] == 0, "is_canceled"].mean()
nonzero_rate = df.loc[df["booking_changes"] >= 1, "is_canceled"].mean()
print(
    f"\n  (c) 변경 없음(=0) vs 변경 있음(>=1) 취소율"
    f"\n      = 0  : {zero_rate * 100:.2f}%  (n={(df['booking_changes'] == 0).sum():,})"
    f"\n      ≥ 1  : {nonzero_rate * 100:.2f}%  (n={(df['booking_changes'] >= 1).sum():,})"
    f"\n      차이 : {(zero_rate - nonzero_rate) * 100:+.2f}%p"
)

print(
    "\n  → 해석 가이드:"
    "\n    · 변경 있음 그룹의 취소율이 *유의하게 낮다* → 도착 임박 변경 가능성 → 🔴 의심"
    "\n      (변경한 사람은 결국 옴 = 변경 자체가 미래 정보)"
    "\n    · 두 그룹 취소율이 비슷 → 변경 시점 분산 → 누수성 약함 → 🟡 유지/keep"
)

# ---------------------------------------------------------------------------
# [Y3] previous_cancellations / previous_bookings_not_canceled
# 데이터 한계: 손님 ID 컬럼이 없어 '같은 손님 행 단위 누적' 검증 불가.
# 빠른 사실만 (1) 분포, (2) 재방문 손님 필터, (3) 값별 취소율 — 이걸로 회의에 가져감.
# ---------------------------------------------------------------------------
PREV_COLS = ["previous_cancellations", "previous_bookings_not_canceled"]
print("\n[Y3] previous_cancellations / previous_bookings_not_canceled")

# (1) 두 컬럼 전체 분포 — pct_zero 가 압도적이면 대부분 신규 손님
print("\n  (1) 두 컬럼 분포")
desc = df[PREV_COLS].agg(
    {
        "previous_cancellations": ["mean", "median", "max"],
        "previous_bookings_not_canceled": ["mean", "median", "max"],
    }
)
print(desc.round(4))
for c in PREV_COLS:
    pct_zero = (df[c] == 0).mean()
    print(f"    {c}: ==0 비율 {pct_zero * 100:.2f}%")

# (2) is_repeated_guest=1 만 필터해 동일 통계
print("\n  (2) is_repeated_guest == 1 필터 (재방문 손님만)")
rep = df[df["is_repeated_guest"] == 1]
print(f"    재방문 행 수: {len(rep):,}  ({len(rep) / len(df) * 100:.2f}%)")
for c in PREV_COLS:
    pct_zero = (rep[c] == 0).mean()
    print(
        f"    {c}: mean={rep[c].mean():.4f}, "
        f"max={rep[c].max()}, ==0 비율 {pct_zero * 100:.2f}%"
    )

# (4) 값별 취소율 — 0 vs 1+ 단순 비교
print("\n  (4) 0 vs 1+ 그룹 취소율")
for c in PREV_COLS:
    zero_rate = df.loc[df[c] == 0, "is_canceled"].mean()
    nonzero_rate = df.loc[df[c] >= 1, "is_canceled"].mean()
    n_zero = (df[c] == 0).sum()
    n_nonzero = (df[c] >= 1).sum()
    print(
        f"\n    [{c}]"
        f"\n      = 0 : 취소율 {zero_rate * 100:.2f}%  (n={n_zero:,})"
        f"\n      ≥ 1 : 취소율 {nonzero_rate * 100:.2f}%  (n={n_nonzero:,})"
        f"\n      차이 : {(zero_rate - nonzero_rate) * 100:+.2f}%p"
    )

print(
    "\n  → 해석:"
    "\n    · 빠른 검증은 위 (1)(2)(4)뿐. (3) 대리키 누적 검증은 손님 ID가 없어 불가능."
    "\n    · 회의 안건: 행 단위 시간 누수 가능성 자체를 어떻게 다룰지 정책 결정 필요."
)

# ---------------------------------------------------------------------------
# [Y4] agent / company — 누수보다는 결측 처리 정책 안건.
# 결측 자체가 "에이전시 미경유 / 법인 아님" 신호일 가능성 → 결측/비결측 취소율 비교만.
# ---------------------------------------------------------------------------
print("\n[Y4] agent / company — 결측의 의미")
for c in ["agent", "company"]:
    miss = df[c].isna()
    miss_rate = miss.mean()
    cancel_miss = df.loc[miss, "is_canceled"].mean()
    cancel_present = df.loc[~miss, "is_canceled"].mean()
    print(
        f"\n  [{c}] 결측률 {miss_rate * 100:.2f}%"
        f"\n    결측 행 취소율  : {cancel_miss * 100:.2f}%  (n={miss.sum():,})"
        f"\n    비결측 행 취소율: {cancel_present * 100:.2f}%  (n={(~miss).sum():,})"
        f"\n    차이            : {(cancel_miss - cancel_present) * 100:+.2f}%p"
    )

print(
    "\n  → 두 컬럼 모두 결측 자체가 신호일 가능성. 처리 옵션:"
    "\n    (a) drop, (b) 결측 인디케이터(0/1)로 변환, (c) ID 카디널리티 처리(타깃 인코딩 등)."
    "\n    회의에서 결정."
)
