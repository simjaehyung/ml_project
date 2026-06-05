"""
src/overbooking_ev.py
슬라이드7 — 오버부킹 K vs 기대 순이익 곡선 (실데이터 기대값)

설계 근거:
  - design_21_overbooking_compensation_grounding.md
      · 2.1  최적 오버부킹 = 한계비용 = 한계수익 (호텔 RM 표준 결정법)
      · 4절  ⚠️ 비용비(빈방:walk)는 미지수 → reputation 포함 시 walk가 더 비쌀 수 있음
              → 비용비를 sweep, ≤1 구간 포함, "보수적 오버부킹"이 정답일 수 있음
      · 1.3  walk 보상 ≈ 첫날 ADR(+교통+굿윌). 풀보상 ~100% ADR. reputation 추가 시 1~3×ADR
  - hub_stream.json : 예약별 risk(=취소확률, LightGBM), adr, canceled, split

모델 (정직한 근사):
  고위험 풀(risk>=THRESH)의 예약 R건에 대해 호텔이 K실 오버부킹(=초과 수락)한다고 하자.
  각 고위험 예약 i는 확률 p_i=risk_i 로 취소(=노쇼), 1-p_i 로 도착(show).
  '오버부킹된 K실'을 메우는 것은 이 풀에서 추가로 도착하는 손님이다.

  show 수 S ~ Poisson-binomial( {1-p_i} ).  (각 예약 독립 베르누이, 확률 1-p_i)
  K실을 오버부킹하면:
    - 실제 도착이 K 이하  → 모두 수용, 빈 방 손실 없이 채움 (이익)
    - 실제 도착이 K 초과  → 초과분(S-K)만큼 walk 발생 (보상+평판 비용)

  하지만 발표 곡선의 직관은 "한계수익(채운 방 ADR) vs 한계비용(walk)".
  K번째 방을 추가로 오버부킹할 때:
    기대 한계수익  = ADR * P(S >= K)        # K번째 방이 실제로 채워질 확률
    기대 한계비용  = C_walk * P(S >= K)      # 동시에 그 방이 walk를 유발할 확률
       (둘 다 P(S>=K): K번째 오버부킹분은 'S>=K일 때만' 실현됨. show면 채워서 수익,
        그러나 capacity 초과라 walk 비용도 그 사건에서 발생.)
  → 순 한계이익(K) = (ADR - C_walk) * P(S >= K)
       단순화하면 C_walk<ADR이면 항상 +, C_walk>ADR이면 항상 - 가 되어 곡선이 단조롭다.

  그래서 'capacity가 고정'이라는 더 현실적인 가정으로 곡선을 만든다:
  호텔 free capacity(빈 방으로 비는 방 수)가 있고, 그걸 채우려 K실 오버부킹한다.
  빈 방 수 V = 풀에서 취소될 기대 건수 ≈ Σ p_i (= 노쇼로 비는 방).
  K실 오버부킹의 기대 순이익:
    E[Profit(K)] = ADR * E[min(S, K)]            # 도착자로 채운 방 (capacity까지)
                   - C_walk * E[max(S - V, 0) | overbook K]
  를 쓰면 복잡하고 V 추정이 또 가정이 된다.

  ⇒ 발표 슬라이드용으로는 가장 방어 가능한 '교과서 newsvendor' 형태를 채택한다(아래 EV_overbook).

핵심 채택 모델 (newsvendor / 한계분석, design_21 §2.1):
  빈 방(노쇼로 생기는 공실)을 메우려 K실을 추가 판매(오버부킹)한다.
  D = 노쇼 수 = 고위험 풀에서 취소되는 예약 수 ~ PoissonBinomial({p_i=risk_i}).
  (노쇼 1건당 빈 방 1개가 생기므로 '메울 수 있는 방 = D'.)
  K실 오버부킹 시:
    - K <= D : 오버부킹분 전원 수용 → K*ADR 수익, walk 0
    - K >  D : D개는 빈 방에 수용(D*ADR), 나머지 (K-D)는 walk → (K-D)*C_walk 비용
  E[Profit(K)] = ADR * E[min(K, D)] - C_walk * E[max(K - D, 0)]

  한계분석: K→K+1 의 기대 증분
    ΔE = ADR * P(D >= K+1) - C_walk * P(D <= K)
  최적 K* : ΔE >= 0 인 마지막 K  ⇔  P(D >= K) >= C_walk/(ADR+C_walk)
  = 고전 overbooking critical-ratio. 비용비 r=C_walk/ADR 로 self-contained.

출력:
  results/overbooking_ev.csv  — (cost_ratio, K, E_profit, P_walk, marginal) 곡선
  results/overbooking_ev.png  — 비용비별 곡선 + 각 최적 K* 표시

실행:
  python src/overbooking_ev.py
  python src/overbooking_ev.py --threshold 0.65 --split test
"""
import sys, io, argparse, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
HUB     = ROOT / "hotel-dss-app" / "public" / "hub_stream.json"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

# ── design_21 §4 / §1.3 근거 비용비 ──────────────────────────────────────────
#   r = C_walk / ADR  (walk 1건 비용을 ADR 배수로)
#   §1.3: walk 풀보상 ≈ 1×ADR(첫날) + 교통 → 0.4~1.0×ADR (협상 하단~풀보상)
#   §4  : reputation 포함 시 walk ≥ 1~3×ADR  → 빈방보다 walk가 비쌈(비용비 거꾸로)
#   → 보수(저)·중립·평판포함(고) 3개 시나리오로 sweep.
COST_RATIOS = {
    "낙관(walk 0.5×ADR, 협상 굿윌 하단)":      0.5,
    "중립(walk 1.0×ADR, 첫날 풀보상)":         1.0,
    "평판포함(walk 2.0×ADR, 보수적·design_21§4)": 2.0,
}


def load_cohort(split: str, highrisk_threshold: float | None):
    """대상 분할의 예약에서 취소확률(risk)·ADR 추출.
    highrisk_threshold 가 주어지면 risk>=threshold 풀만(=고위험만), 아니면 전체(=property 일일 코호트)."""
    with open(HUB, encoding="utf-8") as f:
        data = json.load(f)
    stream = data["stream"]
    if split != "all":
        stream = [r for r in stream if r.get("split") == split]
    n_split = len(stream)
    if highrisk_threshold is not None:
        stream = [r for r in stream if r.get("risk", 0.0) >= highrisk_threshold]
    p = np.array([float(r["risk"]) for r in stream], dtype=float)         # 취소확률
    adr_vals = np.array([float(r["adr"]) for r in stream], dtype=float)
    adr_pos = adr_vals[adr_vals > 0]
    adr = float(np.median(adr_pos)) if adr_pos.size else 100.0           # 대표 ADR
    actual_cancel = np.array([int(r["canceled"]) for r in stream], dtype=int)
    return p, adr, actual_cancel, n_split


def poisson_binomial_pmf(probs: np.ndarray) -> np.ndarray:
    """성공확률이 제각각인 베르누이 합의 PMF (DP). probs=취소확률 p_i.
    반환 pmf[k] = P(노쇼 수 D = k), k=0..n."""
    pmf = np.zeros(1, dtype=float)
    pmf[0] = 1.0
    for p in probs:
        # convolve [1-p, p]
        new = np.zeros(len(pmf) + 1, dtype=float)
        new[:-1] += pmf * (1.0 - p)
        new[1:]  += pmf * p
        pmf = new
    return pmf


def ev_curve(pmf: np.ndarray, adr: float, cost_ratio: float, k_max: int):
    """E[Profit(K)] = ADR*E[min(K,D)] - C_walk*E[max(K-D,0)],  C_walk=cost_ratio*ADR.
    한계증분 ΔE(K) = ADR*P(D>=K) - C_walk*P(D<=K-1) (K번째 방 추가)."""
    c_walk = cost_ratio * adr
    n = len(pmf) - 1
    ks = np.arange(0, k_max + 1)
    # 분포 함수
    cdf = np.cumsum(pmf)                       # cdf[d]=P(D<=d)
    sf  = np.concatenate([[1.0], 1.0 - cdf])   # sf[k]=P(D>=k); sf[0]=1
    sf = sf[:n + 2]
    def P_ge(k):                               # P(D >= k)
        return sf[k] if k <= n + 1 else 0.0
    def P_le(k):                               # P(D <= k)
        if k < 0: return 0.0
        return cdf[k] if k <= n else 1.0

    e_profit, p_walk, marg = [], [], []
    prof = 0.0
    for k in ks:
        if k == 0:
            e_profit.append(0.0); p_walk.append(0.0); marg.append(np.nan)
            continue
        # 한계증분으로 누적 (수치 안정)
        dE = adr * P_ge(k) - c_walk * P_le(k - 1)
        prof += dE
        e_profit.append(prof)
        marg.append(dE)
        # K실 오버부킹 시 walk 발생 확률 = P(D < K) = P(D <= K-1)
        p_walk.append(P_le(k - 1))
    return ks, np.array(e_profit), np.array(p_walk), np.array(marg)


def optimal_k(ks, e_profit):
    idx = int(np.argmax(e_profit))
    return int(ks[idx]), float(e_profit[idx])


def critical_ratio_k(pmf, cost_ratio):
    """이론적 최적: 가장 큰 K s.t. P(D>=K) >= r/(1+r),  r=cost_ratio."""
    cdf = np.cumsum(pmf); n = len(pmf) - 1
    target = cost_ratio / (1.0 + cost_ratio)
    best = 0
    for k in range(1, n + 1):
        p_ge = 1.0 - (cdf[k - 1] if k - 1 <= n else 1.0)
        if p_ge >= target:
            best = k
    return best, target


def main():
    ap = argparse.ArgumentParser(description="오버부킹 K vs 기대순이익 곡선")
    ap.add_argument("--split", type=str, default="test",
                    choices=["test", "train", "all"],
                    help="대상 분할 (기본 test = 평가셋)")
    ap.add_argument("--cohort", type=int, default=162,
                    help="하루 도착 코호트 크기 (기본 162 = test 일일 도착 중앙값)")
    ap.add_argument("--highrisk-only", action="store_true",
                    help="전체 코호트 대신 고위험 풀(risk>=threshold)만 사용")
    ap.add_argument("--threshold", type=float, default=0.65,
                    help="--highrisk-only 시 고위험 임계 (운영 임계 0.65)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    print("=" * 68)
    print("오버부킹 K vs 기대 순이익 곡선  (design_21 §2.1 newsvendor)")
    print("=" * 68)

    hr = args.threshold if args.highrisk_only else None
    p_all, adr, actual, n_split = load_cohort(args.split, hr)
    mode = (f"고위험 풀 risk>={args.threshold}" if args.highrisk_only
            else "property 일일 도착 코호트(전체 risk 분포)")
    print(f"[데이터] hub_stream.json  split={args.split}  (n={n_split:,})")
    print(f"  대상 모집단 : {mode}  → {len(p_all):,}건")
    if len(p_all) == 0:
        print("  비었습니다. 옵션을 확인하세요."); return
    print(f"  모집단 평균 취소확률(risk) : {p_all.mean():.3f}")
    print(f"  모집단 실제 취소율(검증)   : {actual.mean():.3f}")
    print(f"  대표 ADR(중앙값,>0)        : €{adr:.0f}")

    # ── 하루 도착 코호트 표본 ─────────────────────────────────────────────────
    # test는 6개월 누적이므로 그대로 쓰면 노쇼 수가 수천 단위 → '하루 K실 결정' 직관과 안 맞음.
    # test 일일 도착 중앙값(162건)을 한 '운영 단위'로 보고 그만큼 무작위 표본 → 하루 분포 재현.
    rng = np.random.default_rng(args.seed)
    scale = min(args.cohort, len(p_all))
    idx = rng.choice(len(p_all), size=scale, replace=False)
    p = p_all[idx]
    exp_noshow = p.sum()
    print(f"\n[운영규모 정규화] 모집단에서 {scale}건 표본 → 하루 오버부킹 결정 단위")
    print(f"  기대 노쇼 수 E[D] = Σ risk = {exp_noshow:.1f}건  (= 노쇼로 비는 방 기대치 = 메울 여지)")

    pmf = poisson_binomial_pmf(p)
    d_mode = int(np.argmax(pmf))
    print(f"  노쇼 분포 최빈값 D* = {d_mode}건,  표준편차 ≈ {np.sqrt((p*(1-p)).sum()):.1f}")

    k_max = int(min(scale, exp_noshow * 2 + 10))

    # ── 비용비별 곡선 ─────────────────────────────────────────────────────────
    rows = []
    curves = {}
    print(f"\n{'시나리오':<38} {'비용비r':>7} {'최적K*(곡선)':>11} {'이론K*':>7} {'E[순이익]':>11}")
    print("-" * 84)
    for label, r in COST_RATIOS.items():
        ks, eprof, pwalk, marg = ev_curve(pmf, adr, r, k_max)
        k_star, prof_star = optimal_k(ks, eprof)
        k_theory, target = critical_ratio_k(pmf, r)
        curves[label] = (ks, eprof, pwalk, k_star, r)
        print(f"{label:<38} {r:>7.2f} {k_star:>11} {k_theory:>7} €{prof_star:>9.0f}")
        for k in ks:
            rows.append({
                "scenario": label, "cost_ratio": r, "K": int(k),
                "E_profit": round(float(eprof[k]), 2),
                "P_walk": round(float(pwalk[k]), 4),
                "marginal": round(float(marg[k]), 2) if not np.isnan(marg[k]) else "",
                "k_star_curve": k_star, "k_star_theory": k_theory,
                "adr": round(adr, 1), "exp_noshow": round(float(exp_noshow), 2),
                "cohort_size": scale, "mode": ("highrisk" if args.highrisk_only else "daily_cohort"),
                "split": args.split,
            })

    # ── CSV ───────────────────────────────────────────────────────────────────
    import csv
    csv_path = RESULTS / "overbooking_ev.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"\n> CSV 저장 : {csv_path}  ({len(rows)}행)")

    # ── 그래프 ────────────────────────────────────────────────────────────────
    plt.rcParams["font.family"] = ["Malgun Gothic", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    colors = ["#2ECC71", "#3498DB", "#E74C3C"]
    # K* 라벨을 정점 우하단(곡선 하강부 쪽 빈 공간)에 계단식으로 — 제목과 충돌 방지
    label_dxy = [(14, -20), (14, -40), (14, -60)]
    for (label, (ks, eprof, pwalk, k_star, r)), c, (dx, dy) in zip(curves.items(), colors, label_dxy):
        ax.plot(ks, eprof, lw=2.4, color=c, label=label)
        # 최적 K* 마커
        ax.scatter([k_star], [eprof[k_star]], color=c, s=55, zorder=5,
                   edgecolor="white", linewidth=1.2)
        ax.annotate(f"K*={k_star}", (k_star, eprof[k_star]),
                    textcoords="offset points", xytext=(dx, dy),
                    fontsize=9.5, color=c, fontweight="bold",
                    arrowprops=dict(arrowstyle="-", color=c, lw=0.7, alpha=0.6))
    ax.axvline(exp_noshow, color="#999", ls="--", lw=1, alpha=0.7)
    ax.annotate(f"E[노쇼]={exp_noshow:.0f}", (exp_noshow, eprof.min()),
                textcoords="offset points", xytext=(6, 30), fontsize=8.5, color="#666")
    ax.axhline(0, color="#bbb", lw=0.8)
    ax.set_xlabel("오버부킹 객실 수 K", fontsize=11)
    ax.set_ylabel("기대 순이익 (€)", fontsize=11)
    ax.set_title(f"오버부킹 K vs 기대 순이익 — 비용비 sweep\n"
                 f"{mode} (split={args.split}, 코호트 {scale}건, ADR €{adr:.0f})", fontsize=10.5)
    ax.legend(fontsize=8.6, loc="lower left", title="비용비 r = walk비용 / ADR", title_fontsize=8.6)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    png_path = RESULTS / "overbooking_ev.png"
    fig.savefig(png_path, dpi=150)
    print(f"> 그래프 저장 : {png_path}")

    # ── 해석 ──────────────────────────────────────────────────────────────────
    print("\n" + "=" * 68)
    print("해석 (design_21 §4 정직 프레임)")
    print("=" * 68)
    k_lo = curves["낙관(walk 0.5×ADR, 협상 굿윌 하단)"][3]
    k_hi = curves["평판포함(walk 2.0×ADR, 보수적·design_21§4)"][3]
    print(f"  · 비용비가 낮을수록(walk 쌈) 공격적 → 최적 K* {k_lo} (낙관)")
    print(f"  · 평판 포함해 walk가 ADR의 2배면 보수적 → 최적 K* {k_hi} (보수)")
    print(f"  · E[노쇼]={exp_noshow:.0f} 근처에서 곡선이 꺾인다 = '노쇼로 비는 만큼만 메운다'는 직관")
    print(f"  · 비용비는 미지수 → 점추정 금지, 위 범위로 제시. 평판 포함 시 보수적 K가 정답(§4).")
    print("=" * 68)


if __name__ == "__main__":
    main()
