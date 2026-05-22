"""Walk 협상 시뮬레이션 결과 분석 스크립트.

Usage:
    python src/sim_walk_analyze.py
    python src/sim_walk_analyze.py --data results/walk_sim_results.jsonl
"""
import argparse
import json
import sys
from pathlib import Path
from collections import Counter

# Windows CP949 환경에서 유니코드 출력 지원
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats
from scipy.stats import fisher_exact, chi2_contingency

# ── 경로 설정 ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

ARCHETYPE_ORDER = ["A", "B", "C", "D", "E"]
ARCHETYPE_LABELS = {
    "A": "Business Solo",
    "B": "Leisure Couple",
    "C": "Family",
    "D": "Budget OTA",
    "E": "Group",
}
DIFFICULTY = {
    "A": "low",
    "B": "medium",
    "C": "high",
    "D": "low",
    "E": "very_high",
}
COLORS = {
    "A": "#2196F3",
    "B": "#4CAF50",
    "C": "#FF9800",
    "D": "#F44336",
    "E": "#9C27B0",
}


# ── 데이터 로드 ──────────────────────────────────────────────────────────────
def load_data(path: Path) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    df["accepted"] = df["final_decision"] == "ACCEPT"
    df["total_value"] = df["adr"] * df["nights"]
    return df


def wilson_ci(k: int, n: int, z: float = 1.96):
    """Wilson score 95% CI. Returns (lower, upper)."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denom
    margin = (z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2))) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


# ── 1. 기본 요약 ──────────────────────────────────────────────────────────────
def print_summary(df: pd.DataFrame):
    print("\n" + "=" * 70)
    print("Walk 협상 시뮬레이션 — 전체 요약")
    print("=" * 70)
    total = len(df)
    accepted = df["accepted"].sum()
    parse_ok = df["r1_parse_ok"].sum()
    print(f"  총 협상 수    : {total:,}건")
    print(f"  전체 수락률   : {accepted/total:.1%}  ({accepted}/{total})")
    print(f"  R1 파싱 성공  : {parse_ok/total:.1%}  ({int(parse_ok)}/{total})")

    print("\n── 아키타입별 수락률 (전체 offer 통합) ──")
    print(f"  {'아키타입':<6} {'레이블':<20} {'수락':<6} {'총합':<6} {'수락률':>7}  95% CI")
    print("  " + "-" * 60)
    for arch in ARCHETYPE_ORDER:
        sub = df[df["archetype"] == arch]
        k, n = int(sub["accepted"].sum()), len(sub)
        lo, hi = wilson_ci(k, n)
        label = ARCHETYPE_LABELS[arch]
        diff = DIFFICULTY[arch]
        print(f"  {arch:<6} {label:<20} {k:<6} {n:<6} {k/n:>6.1%}   [{lo:.1%}, {hi:.1%}]  ({diff})")


# ── 2. Claim 2 통계 검증 ─────────────────────────────────────────────────────
def claim2_test(df: pd.DataFrame):
    print("\n" + "=" * 70)
    print("Claim 2 검증: Family(C) 수락률 < Budget OTA(D) 수락률")
    print("=" * 70)

    c_df = df[df["archetype"] == "C"]
    d_df = df[df["archetype"] == "D"]
    c_k, c_n = int(c_df["accepted"].sum()), len(c_df)
    d_k, d_n = int(d_df["accepted"].sum()), len(d_df)

    c_lo, c_hi = wilson_ci(c_k, c_n)
    d_lo, d_hi = wilson_ci(d_k, d_n)
    print(f"\n  Family     (C): {c_k}/{c_n} = {c_k/c_n:.1%}  95% CI [{c_lo:.1%}, {c_hi:.1%}]")
    print(f"  Budget OTA (D): {d_k}/{d_n} = {d_k/d_n:.1%}  95% CI [{d_lo:.1%}, {d_hi:.1%}]")

    # Fisher exact test (단측: C < D)
    table = [[c_k, c_n - c_k], [d_k, d_n - d_k]]
    _, p_fisher = fisher_exact(table, alternative="less")
    print(f"\n  Fisher exact test (단측 C < D): p = {p_fisher:.4f}")

    # Chi-square (양측 참고용)
    if c_k + d_k > 0:
        _, p_chi2, _, _ = chi2_contingency(table)
        print(f"  Chi-square test (양측 참고):    p = {p_chi2:.4f}")

    verdict = "✅ CLAIM 2 지지" if p_fisher < 0.05 else "❌ CLAIM 2 기각"
    print(f"\n  결론: {verdict} (α=0.05, p={p_fisher:.4f})")
    if p_fisher < 0.05:
        print("  → LLM 페르소나가 walk_difficulty(high/low)를 유의미하게 반영함")

    return c_k, c_n, d_k, d_n


# ── 3. offer 구간별 수락률 (임계값 분석) ─────────────────────────────────────
def offer_threshold(df: pd.DataFrame):
    print("\n" + "=" * 70)
    print("Offer 구간별 수락률 — 임계값 분석")
    print("=" * 70)
    grp = (
        df.groupby(["archetype", "archetype_label", "initial_offer"])["accepted"]
        .agg(["sum", "count"])
        .reset_index()
        .rename(columns={"sum": "accepts", "count": "n"})
    )
    grp["rate"] = grp["accepts"] / grp["n"]

    for arch in ARCHETYPE_ORDER:
        sub = grp[grp["archetype"] == arch].sort_values("initial_offer")
        label = ARCHETYPE_LABELS[arch]
        print(f"\n  [{arch}] {label}  (walk_difficulty={DIFFICULTY[arch]})")
        for _, row in sub.iterrows():
            bar = "█" * int(row["rate"] * 20)
            print(f"    €{row['initial_offer']:>5.0f}  {bar:<20}  {row['rate']:.0%}  ({int(row['accepts'])}/{int(row['n'])})")

    # B의 비단조 패턴 분석
    b_sub = grp[grp["archetype"] == "B"].sort_values("initial_offer")
    print("\n  [주목] B (Leisure Couple) 비단조 패턴:")
    print("  offer 증가 → 수락률이 오히려 감소하는 역전 현상 감지")
    for _, row in b_sub.iterrows():
        print(f"    €{row['initial_offer']:>5.0f} → {row['rate']:.0%}")

    return grp


# ── 4. R2 협상 효과 ──────────────────────────────────────────────────────────
def r2_analysis(df: pd.DataFrame):
    print("\n" + "=" * 70)
    print("R2 협상 효과 분석")
    print("=" * 70)

    counter_df = df[df["r1_decision"] == "COUNTER"].copy()
    print(f"  R1=COUNTER 케이스 : {len(counter_df)}건  ({len(counter_df)/len(df):.1%})")

    if len(counter_df) == 0:
        print("  COUNTER 케이스 없음")
        return

    r2_accept = (counter_df["r2_decision"] == "ACCEPT").sum()
    print(f"  R2=ACCEPT 비율    : {r2_accept}/{len(counter_df)} = {r2_accept/len(counter_df):.1%}")

    counter_df["gap"] = counter_df["r1_counter"] - counter_df["r2_offer"]
    print(f"  Counter vs R2 offer 차이 (고객 요구 - 호텔 revised):")
    print(f"    평균 gap : €{counter_df['gap'].mean():.1f}  (양수 = 고객이 더 많이 요구)")
    print(f"    중앙값 gap: €{counter_df['gap'].median():.1f}")

    print(f"\n  아키타입별 R2 협상 성사율:")
    for arch in ARCHETYPE_ORDER:
        sub = counter_df[counter_df["archetype"] == arch]
        if len(sub) == 0:
            continue
        r2_ok = (sub["r2_decision"] == "ACCEPT").sum()
        print(f"    {arch} {ARCHETYPE_LABELS[arch]:<20}: {r2_ok}/{len(sub)} = {r2_ok/len(sub):.1%}")


# ── 5. Counter amount 분포 ────────────────────────────────────────────────────
def counter_distribution(df: pd.DataFrame):
    print("\n" + "=" * 70)
    print("Counter Amount 분포 (R1=COUNTER 케이스)")
    print("=" * 70)

    counter_df = df[df["r1_decision"] == "COUNTER"].dropna(subset=["r1_counter"])
    counter_df = counter_df.copy()
    counter_df["counter_ratio"] = counter_df["r1_counter"] / counter_df["total_value"]

    print(f"  {'아키타입':<6} {'레이블':<20} {'n':>4}  {'counter 평균':>12}  {'비율(counter/total)':>20}")
    print("  " + "-" * 68)
    for arch in ARCHETYPE_ORDER:
        sub = counter_df[counter_df["archetype"] == arch]
        if len(sub) == 0:
            print(f"  {arch:<6} {ARCHETYPE_LABELS[arch]:<20} {'0':>4}")
            continue
        mean_c = sub["r1_counter"].mean()
        mean_r = sub["counter_ratio"].mean()
        print(f"  {arch:<6} {ARCHETYPE_LABELS[arch]:<20} {len(sub):>4}  €{mean_c:>10.1f}  {mean_r:>19.1%}")


# ── 6. Reason 텍스트 정성 분석 ────────────────────────────────────────────────
def reason_analysis(df: pd.DataFrame):
    print("\n" + "=" * 70)
    print("Reason 텍스트 정성 분석")
    print("=" * 70)

    keywords = {
        "A": ["corporate", "business", "schedule", "efficient", "quick", "inconvenience"],
        "B": ["romantic", "leisure", "couple", "vacation", "holiday", "experience"],
        "C": ["children", "family", "kids", "disrupt", "stress", "relocation"],
        "D": ["budget", "price", "ota", "value", "money", "refund", "compensat"],
        "E": ["group", "colleagues", "coordin", "team", "logistic", "multiple"],
    }

    for arch in ARCHETYPE_ORDER:
        sub = df[df["archetype"] == arch]
        reasons = sub["r1_reason"].dropna().tolist()
        total_chars = sum(len(r) for r in reasons)
        print(f"\n  [{arch}] {ARCHETYPE_LABELS[arch]} — {len(reasons)}개 reason, 평균 {total_chars/max(len(reasons),1):.0f}자")

        # 키워드 빈도
        combined = " ".join(reasons).lower()
        kw_hits = {kw: combined.count(kw) for kw in keywords[arch]}
        top_kw = sorted(kw_hits.items(), key=lambda x: -x[1])[:4]
        print(f"    페르소나 키워드 빈도: {', '.join(f'{k}({v})' for k,v in top_kw)}")

        # 샘플 1개 (REJECT 우선, 없으면 COUNTER)
        reject_samples = sub[sub["final_decision"] == "REJECT"]["r1_reason"].dropna()
        sample = reject_samples.iloc[0] if len(reject_samples) > 0 else reasons[0] if reasons else ""
        if sample:
            short = (sample[:180] + "…") if len(sample) > 180 else sample
            decision = "REJECT" if len(reject_samples) > 0 else "ACCEPT/COUNTER"
            print(f"    예시 ({decision}): \"{short}\"")


# ── 시각화 1: Heatmap ────────────────────────────────────────────────────────
def plot_heatmap(df: pd.DataFrame, out: Path):
    grp = (
        df.groupby(["archetype", "initial_offer"])["accepted"]
        .mean()
        .reset_index()
        .rename(columns={"accepted": "rate"})
    )

    pivot = grp.pivot(index="archetype", columns="initial_offer", values="rate")
    pivot = pivot.reindex(ARCHETYPE_ORDER)

    fig, ax = plt.subplots(figsize=(12, 4))
    im = ax.imshow(pivot.values, aspect="auto", cmap="RdYlGn", vmin=0, vmax=1)

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([f"€{c:.0f}" for c in pivot.columns], rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(ARCHETYPE_ORDER)))
    ax.set_yticklabels(
        [f"{a} {ARCHETYPE_LABELS[a]}" for a in ARCHETYPE_ORDER], fontsize=9
    )

    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.values[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.0%}", ha="center", va="center",
                        fontsize=8, color="black" if 0.3 < val < 0.7 else "white")

    plt.colorbar(im, ax=ax, label="Accept Rate")
    ax.set_title("Walk Compensation Accept Rate by Archetype × Offer Level", fontsize=11, pad=10)
    ax.set_xlabel("Initial Offer (€)")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"\n  저장: {out}")


# ── 시각화 2: Accept Curves ──────────────────────────────────────────────────
def plot_accept_curves(df: pd.DataFrame, out: Path):
    grp = (
        df.groupby(["archetype", "initial_offer"])["accepted"]
        .mean()
        .reset_index()
        .rename(columns={"accepted": "rate"})
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    for arch in ARCHETYPE_ORDER:
        sub = grp[grp["archetype"] == arch].sort_values("initial_offer")
        label = f"{arch}: {ARCHETYPE_LABELS[arch]} ({DIFFICULTY[arch]})"
        ax.plot(sub["initial_offer"], sub["rate"], marker="o", linewidth=2,
                color=COLORS[arch], label=label)

    ax.axhline(0.5, color="gray", linestyle="--", linewidth=1, alpha=0.6, label="50% threshold")
    ax.set_xlabel("Initial Offer (€)", fontsize=11)
    ax.set_ylabel("Accept Rate", fontsize=11)
    ax.set_ylim(-0.05, 1.05)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.legend(fontsize=9, loc="upper left")
    ax.set_title("Walk Compensation Accept Rate Curves by Archetype", fontsize=12)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  저장: {out}")


# ── 시각화 3: Claim 2 barplot ────────────────────────────────────────────────
def plot_claim2(c_k, c_n, d_k, d_n, out: Path):
    archs = ["C\nFamily\n(high)", "D\nBudget OTA\n(low)"]
    rates = [c_k / c_n, d_k / d_n]
    ci_lo = [wilson_ci(c_k, c_n)[0], wilson_ci(d_k, d_n)[0]]
    ci_hi = [wilson_ci(c_k, c_n)[1], wilson_ci(d_k, d_n)[1]]
    colors_bar = [COLORS["C"], COLORS["D"]]

    yerr_lo = [r - lo for r, lo in zip(rates, ci_lo)]
    yerr_hi = [hi - r for r, hi in zip(rates, ci_hi)]

    fig, ax = plt.subplots(figsize=(6, 5))
    bars = ax.bar(archs, rates, color=colors_bar, width=0.4, alpha=0.85,
                  yerr=[yerr_lo, yerr_hi], capsize=8, error_kw={"linewidth": 2})

    for bar, rate, k, n in zip(bars, rates, [c_k, d_k], [c_n, d_n]):
        ax.text(bar.get_x() + bar.get_width() / 2, rate + 0.03,
                f"{rate:.1%}\n({k}/{n})", ha="center", va="bottom", fontsize=11, fontweight="bold")

    _, p_val = fisher_exact(
        [[c_k, c_n - c_k], [d_k, d_n - d_k]], alternative="less"
    )
    sig_text = f"Fisher exact p = {p_val:.4f}"
    verdict = "[SUPPORTED] C < D (p < 0.05)" if p_val < 0.05 else f"n.s. (p = {p_val:.4f})"
    ax.set_title(f"Claim 2: Family vs Budget OTA Accept Rate\n{verdict}", fontsize=11)
    ax.set_ylabel("Accept Rate (with 95% Wilson CI)", fontsize=10)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0%", "20%", "40%", "60%", "80%", "100%"])
    ax.text(0.98, 0.02, sig_text, transform=ax.transAxes,
            ha="right", va="bottom", fontsize=9, color="gray")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  저장: {out}")


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(RESULTS / "walk_sim_results.jsonl"))
    args = parser.parse_args()

    path = Path(args.data)
    if not path.exists():
        print(f"ERROR: {path} 없음")
        return

    df = load_data(path)

    print_summary(df)
    c_k, c_n, d_k, d_n = claim2_test(df)
    offer_grp = offer_threshold(df)
    r2_analysis(df)
    counter_distribution(df)
    reason_analysis(df)

    print("\n── 시각화 생성 ──")
    plot_heatmap(df, RESULTS / "walk_accept_heatmap.png")
    plot_accept_curves(df, RESULTS / "walk_accept_curves.png")
    plot_claim2(c_k, c_n, d_k, d_n, RESULTS / "walk_claim2_barplot.png")

    print("\n분석 완료.")


if __name__ == "__main__":
    main()
