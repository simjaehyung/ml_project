"""
sim_analyze.py
시뮬레이션 결과 분석 + 시각화

입력:  results/sim_responses.jsonl
출력:  results/sim_threshold_sweep.png    — 임계값별 RevPAR / walk_rate
       results/sim_acceptance_breakdown.png — 세그먼트·국적별 수락률
       results/sim_sweep_results.csv        — 수치 테이블
       콘솔: 최적 임계값 권고

실행:
  python src/sim_analyze.py
  python src/sim_analyze.py --input results/sim_responses.jsonl
"""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

from sim_hotel import sweep_thresholds, find_optimal_threshold

ROOT    = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

THRESHOLDS = [0.50, 0.55, 0.60, 0.65, 0.70]


# ── 응답 로드 ─────────────────────────────────────────────────────────────────
def load_responses(path: str) -> pd.DataFrame:
    records = []
    with open(ROOT / path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    df = pd.DataFrame(records)
    df["cancel_prob"] = pd.to_numeric(df["cancel_prob"], errors="coerce")
    df["adr"]         = pd.to_numeric(df["adr"],         errors="coerce")
    df["discount"]    = pd.to_numeric(df["discount"],    errors="coerce")
    return df.dropna(subset=["cancel_prob", "adr", "discount"])


# ── Plot 1: 임계값 스윕 ───────────────────────────────────────────────────────
def plot_threshold_sweep(sweep_df: pd.DataFrame, optimal: dict | None):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Flexi 시스템 — 임계값별 성능 분석\n(LLM 에이전트 시뮬레이션)", fontsize=13)

    # RevPAR 개선율
    colors = ["seagreen" if v >= 0 else "crimson"
              for v in sweep_df["revpar_uplift_pct"]]
    bars = ax1.bar(sweep_df["threshold"].astype(str),
                   sweep_df["revpar_uplift_pct"],
                   color=colors, alpha=0.8, width=0.5)
    ax1.axhline(0, color="gray", linewidth=1, linestyle="--")
    ax1.set_xlabel("Flexi 임계값 (cancel_prob ≥ X → 오퍼 제시)")
    ax1.set_ylabel("RevPAR 개선율 (%)")
    ax1.set_title("임계값별 RevPAR 개선")
    ax1.grid(axis="y", alpha=0.3)
    for bar, val in zip(bars, sweep_df["revpar_uplift_pct"]):
        ax1.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + 0.05,
                 f"{val:+.2f}%", ha="center", va="bottom", fontsize=9)

    # Walk rate + 2% 제한선
    ax2.plot(sweep_df["threshold"], sweep_df["walk_rate_pct"],
             "o-", color="crimson", linewidth=2.5, markersize=9, zorder=3)
    ax2.axhline(2.0, color="orange", linestyle="--", linewidth=1.8,
                label="walk rate 한도 2%", zorder=2)
    ax2.fill_between(sweep_df["threshold"],
                     sweep_df["walk_rate_pct"], 2.0,
                     where=sweep_df["walk_rate_pct"] > 2.0,
                     alpha=0.15, color="crimson", label="위험 구간")
    ax2.set_xlabel("Flexi 임계값")
    ax2.set_ylabel("Walk Rate (%)")
    ax2.set_title("임계값별 Walk Rate")
    ax2.legend(fontsize=9)
    ax2.grid(alpha=0.3)
    for x, y in zip(sweep_df["threshold"], sweep_df["walk_rate_pct"]):
        ax2.text(x, y + 0.05, f"{y:.2f}%", ha="center", va="bottom", fontsize=9)

    # 최적 임계값 표시
    if optimal:
        t_opt = optimal["threshold"]
        for ax in (ax1, ax2):
            ax.axvline(str(t_opt) if ax is ax1 else t_opt,
                       color="gold", linewidth=2.5, linestyle=":",
                       label=f"최적 임계값 {t_opt}", zorder=4)
            ax.legend(fontsize=9)

    plt.tight_layout()
    out = RESULTS / "sim_threshold_sweep.png"
    fig.savefig(out, dpi=130)
    print(f"  → {out}")
    plt.close()


# ── Plot 2: 세그먼트·국적별 수락률 ───────────────────────────────────────────
def plot_acceptance_breakdown(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Flexi 오퍼 수락률 — 세그먼트 & 국적별\n(LLM 에이전트 시뮬레이션)", fontsize=13)

    palette = {
        "ACCEPT_FLEXI":  "#2ca02c",
        "DECLINE_FLEXI": "#1f77b4",
        "CANCEL":        "#d62728",
    }

    for ax, col, title in [
        (axes[0], "market_segment", "시장 세그먼트별"),
        (axes[1], "country",        "국적별 (Top 10)"),
    ]:
        if col not in df.columns:
            ax.set_visible(False)
            continue

        counts = (df.groupby(col)["decision"]
                    .value_counts()
                    .unstack(fill_value=0))

        if col == "country":
            total_by_group = counts.sum(axis=1)
            counts = counts.loc[total_by_group.nlargest(10).index]

        # 비율로 변환
        rates  = counts.div(counts.sum(axis=1), axis=0)
        # ACCEPT_FLEXI 기준 정렬
        if "ACCEPT_FLEXI" in rates.columns:
            rates = rates.sort_values("ACCEPT_FLEXI", ascending=True)

        bottom = np.zeros(len(rates))
        for decision in ("CANCEL", "DECLINE_FLEXI", "ACCEPT_FLEXI"):
            if decision not in rates.columns:
                continue
            vals = rates[decision].values
            ax.barh(range(len(rates)), vals, left=bottom,
                    color=palette[decision], alpha=0.85,
                    label=decision.replace("_", " "))
            bottom += vals

        ax.set_yticks(range(len(rates)))
        ax.set_yticklabels(rates.index, fontsize=9)
        ax.axvline(0.5, color="gray", linestyle="--", alpha=0.5)
        ax.set_xlabel("비율")
        ax.set_title(f"{title} 의사결정 분포")
        ax.set_xlim(0, 1)
        ax.grid(axis="x", alpha=0.3)

    handles = [mpatches.Patch(color=palette[k], label=k.replace("_", " "))
               for k in ("ACCEPT_FLEXI", "DECLINE_FLEXI", "CANCEL")]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=9,
               bbox_to_anchor=(0.5, -0.02))

    plt.tight_layout()
    out = RESULTS / "sim_acceptance_breakdown.png"
    fig.savefig(out, dpi=130, bbox_inches="tight")
    print(f"  → {out}")
    plt.close()


# ── Plot 3: cancel_prob 분포별 수락률 ─────────────────────────────────────────
def plot_prob_vs_acceptance(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 5))

    bins   = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 1.01]
    labels = ["0.50-0.55", "0.55-0.60", "0.60-0.65", "0.65-0.70",
              "0.70-0.75", "0.75-0.80", "0.80-0.85", "0.85-0.90", "0.90+"]
    df["prob_bin"] = pd.cut(df["cancel_prob"], bins=bins, labels=labels, right=False)

    grp = (df.groupby("prob_bin", observed=True)["decision"]
             .value_counts(normalize=True)
             .unstack(fill_value=0))

    palette = {"ACCEPT_FLEXI": "#2ca02c", "DECLINE_FLEXI": "#1f77b4", "CANCEL": "#d62728"}
    bottom  = np.zeros(len(grp))
    for decision in ("CANCEL", "DECLINE_FLEXI", "ACCEPT_FLEXI"):
        if decision not in grp.columns:
            continue
        ax.bar(range(len(grp)), grp[decision].values, bottom=bottom,
               color=palette[decision], alpha=0.85,
               label=decision.replace("_", " "))
        bottom += grp[decision].values

    ax.set_xticks(range(len(grp)))
    ax.set_xticklabels(grp.index, rotation=30, ha="right", fontsize=9)
    ax.set_xlabel("취소 확률 구간")
    ax.set_ylabel("비율")
    ax.set_title("취소 확률 구간별 LLM 에이전트 의사결정\n(할인율은 확률에 비례 — 높을수록 더 큰 할인)")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    ax.set_xlim(-0.5, len(grp) - 0.5)

    plt.tight_layout()
    out = RESULTS / "sim_prob_vs_acceptance.png"
    fig.savefig(out, dpi=130)
    print(f"  → {out}")
    plt.close()


# ── 콘솔 요약 ─────────────────────────────────────────────────────────────────
def print_summary(df: pd.DataFrame, sweep_df: pd.DataFrame, optimal: dict | None):
    print("\n" + "=" * 65)
    print("시뮬레이션 결과 요약")
    print("=" * 65)
    print(f"총 에이전트:   {len(df):,}건")
    print(f"cancel_prob:   {df['cancel_prob'].min():.3f} ~ {df['cancel_prob'].max():.3f}"
          f"  (평균 {df['cancel_prob'].mean():.3f})")
    print(f"할인율 범위:   {df['discount'].min():.1f}% ~ {df['discount'].max():.1f}%")

    print("\n[전체 에이전트 의사결정]")
    from collections import Counter
    cnt   = Counter(df["decision"])
    total = len(df)
    for k in ("ACCEPT_FLEXI", "DECLINE_FLEXI", "CANCEL"):
        v = cnt.get(k, 0)
        print(f"  {k:<20} {v:>5}건  ({v / total * 100:>5.1f}%)")

    print("\n[임계값별 시뮬레이션 결과]")
    print(f"  {'임계값':>6}  {'오퍼건수':>8}  {'수락률':>7}  "
          f"{'RevPAR개선':>10}  {'walk_rate':>10}")
    print(f"  {'-' * 55}")
    for _, row in sweep_df.iterrows():
        flag = " ★" if optimal and row["threshold"] == optimal["threshold"] else ""
        print(f"  {row['threshold']:>6.2f}  {int(row['n_offered']):>8}  "
              f"{row['accept_rate']:>6.1%}  "
              f"{row['revpar_uplift_pct']:>+9.2f}%  "
              f"{row['walk_rate_pct']:>9.3f}%{flag}")

    if optimal:
        print(f"\n★ 최적 임계값 (walk_rate ≤ 2%): {optimal['threshold']}")
        print(f"  RevPAR 개선: +{optimal['revpar_uplift_pct']:.2f}%")
        print(f"  오퍼 건수:   {int(optimal['n_offered'])}건 / {int(optimal['n_total'])}건")
        print(f"  수락률:      {optimal['accept_rate']:.1%}")
        print(f"  Walk Rate:   {optimal['walk_rate_pct']:.3f}%")
    else:
        print("\n모든 임계값에서 walk_rate > 2% → 오버부킹 버퍼 조정 필요")
    print("=" * 65)


# ── 메인 ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str,
                        default="results/sim_responses.jsonl")
    parser.add_argument("--thresholds", type=float, nargs="+",
                        default=THRESHOLDS)
    args = parser.parse_args()

    print("▶ 응답 로드...")
    df = load_responses(args.input)
    print(f"  {len(df):,}건 로드 완료")

    print("▶ 임계값 스윕...")
    sweep_df = sweep_thresholds(df, args.thresholds)
    optimal  = find_optimal_threshold(sweep_df)

    print("▶ 플롯 생성...")
    plot_threshold_sweep(sweep_df, optimal)
    plot_acceptance_breakdown(df)
    plot_prob_vs_acceptance(df)

    print_summary(df, sweep_df, optimal)

    out_csv = RESULTS / "sim_sweep_results.csv"
    sweep_df.to_csv(out_csv, index=False)
    print(f"\n  → {out_csv}")


if __name__ == "__main__":
    main()
