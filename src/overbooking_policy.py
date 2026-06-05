"""
src/overbooking_policy.py
마지막 퍼즐 — 세그먼트별 오버부킹 비율(실데이터 예측) + 보상 가격 삼각측량.

① 오버부킹 비율 예측: 실 취소모델 P(취소)로 도착일 코호트의 노쇼 분포 → newsvendor 최적 K
   → "최적 오버부킹 % ≈ 예측 노쇼율 (± 비용비 버퍼)" 를 실데이터로. (순수 실데이터·RM 표준)
② 세그먼트 정책: lead_time 구간별 평균 P(취소) → 권장 오버부킹 버퍼 (피처 기반 정책 테이블)
③ 보상 삼각측량: walk_sim(€46) / 업계(첫날 ADR) / 빈방 기회비용(ADR) 이 같은 범위로 수렴
   → 합성(LLM)을 유일 근거가 아니라 '3 증거 중 하나'로 강등 = 방어.

국적은 행동(오버부킹/보상) 차등에서 제외(윤리). 세그먼트 축 = lead_time.

산출물: results/overbooking_policy.png, overbooking_policy_cohorts.csv, overbooking_policy_segments.csv
실행: python src/overbooking_policy.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.stats import norm

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
CAT = ["hotel", "meal", "market_segment", "distribution_channel",
       "reserved_room_type", "customer_type", "country_grouped"]
COST_RATIOS = [0.5, 1.0, 2.0]   # r = C_walk/ADR (design_21: reputation 포함 시 walk↑ → 보수적)


def risk(df):
    """실 LightGBM 모델로 P(취소) 산출 (build_hub_stream와 동일 정렬)."""
    m = joblib.load(RESULTS / "model_final.pkl")
    X = pd.get_dummies(df, columns=CAT)
    feats = getattr(m, "feature_name_", None)
    if feats is None and hasattr(m, "booster_"):
        feats = list(m.booster_.feature_name())
    X = X.reindex(columns=feats, fill_value=0)
    return m.predict_proba(X)[:, 1]


def kstar(mu, sigma, r):
    """newsvendor 최적 K: P(D>=K) >= r/(1+r)  ⇒  K <= mu + sigma·Φ⁻¹(1/(1+r)). 정규 근사."""
    return mu + sigma * norm.ppf(1.0 / (1.0 + r))


def main():
    test = pd.read_csv(DATA / "test_processed.csv")
    p = risk(test.copy())
    test = test.assign(p=p)
    arr = pd.to_datetime(dict(year=test.arrival_date_year, month=test.arrival_date_month,
                              day=test.arrival_date_day_of_month), errors="coerce")
    test["arr"] = arr
    adr_med = float(test.adr.median())
    print(f"[로드] test {len(test):,} | 평균 P(취소) {p.mean():.3f} / 실제 취소율 {test.is_canceled.mean():.3f} "
          f"| ADR 중앙값 €{adr_med:.0f}")

    # ── ① 오버부킹 비율 — 도착일 코호트별 newsvendor ─────────────────────────
    rows = []
    for d, g in test.groupby("arr"):
        if len(g) < 10:
            continue
        mu = g.p.sum()
        sig = np.sqrt((g.p * (1 - g.p)).sum())
        n = len(g)
        rec = {"date": d, "n": n, "noshow_rate": float(g.p.mean())}
        for r in COST_RATIOS:
            rec[f"obk_pct_r{r}"] = max(0.0, kstar(mu, sig, r)) / n
        rows.append(rec)
    coh = pd.DataFrame(rows)
    coh.to_csv(RESULTS / "overbooking_policy_cohorts.csv", index=False)
    print(f"\n[① 오버부킹 비율] 도착일 코호트 {len(coh)}개 (평균 {coh.n.mean():.0f}건/일)")
    for r in COST_RATIOS:
        print(f"  비용비 r={r}: 최적 오버부킹 % 중앙값 {coh[f'obk_pct_r{r}'].median()*100:5.1f}%  "
              f"(노쇼율 따라 {coh[f'obk_pct_r{r}'].quantile(.1)*100:.0f}~{coh[f'obk_pct_r{r}'].quantile(.9)*100:.0f}% 변동)")

    # ── ② 세그먼트 정책 — lead_time 구간 ────────────────────────────────────
    bins = [-1, 7, 30, 90, 180, 99999]
    labels = ["<=7d", "8-30d", "31-90d", "91-180d", ">180d"]
    test["lt_band"] = pd.cut(test.lead_time, bins=bins, labels=labels)
    seg = (test.groupby("lt_band", observed=True)
           .agg(n=("p", "size"), pred_noshow=("p", "mean"),
                actual_cancel=("is_canceled", "mean"), adr=("adr", "median"))
           .reset_index())
    seg["overbook_buffer_pct"] = (seg.pred_noshow * 100).round(1)  # 중립 r=1 근사 ≈ 노쇼율
    seg.to_csv(RESULTS / "overbooking_policy_segments.csv", index=False)
    print("\n[② 세그먼트 정책 — lead_time band] (overbook_buffer ≈ 예측 노쇼율, r=1)")
    print(seg.to_string(index=False))

    # ── ③ 보상 삼각측량 ─────────────────────────────────────────────────────
    print(f"\n[③ 보상 삼각측량] ADR 중앙값 €{adr_med:.0f}")
    print(f"  (a) walk_sim 수락(D archetype)  €46   ≈ {46/adr_med*100:.0f}% ADR   [LLM 행동]")
    print(f"  (b) 업계 첫날 보상              €{adr_med:.0f}  ≈ 100% ADR (+교통)  [관행 grounding]")
    print(f"  (c) 빈방 기회비용(상한)         €{adr_med:.0f}  = 100% ADR          [실 ADR]")
    print(f"  → 보상 €46~€{adr_med:.0f} (≈0.4~1.0×ADR) 범위로 3 독립소스 수렴 = 삼각측량 방어")

    # ── plot: 오버부킹 % vs 예측 노쇼율 ─────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(coh.noshow_rate * 100, coh["obk_pct_r1.0"] * 100, s=9, alpha=.35, color="#1B3A8F")
    lo, hi = coh.noshow_rate.min() * 100, coh.noshow_rate.max() * 100
    ax.plot([lo, hi], [lo, hi], ls="--", color="#8A5A0F", lw=1, label="overbook % = predicted no-show %")
    ax.set_xlabel("Cohort predicted no-show rate (%)  [real cancellation model]")
    ax.set_ylabel("Optimal overbooking % (r=1)")
    ax.set_title("Overbooking RATIO prediction — overbook more when model predicts more no-shows")
    ax.legend(fontsize=8); ax.grid(alpha=.3)
    plt.tight_layout()
    fig.savefig(RESULTS / "overbooking_policy.png", dpi=120)
    print("\n[산출물] results/overbooking_policy.png, overbooking_policy_cohorts.csv, overbooking_policy_segments.csv")


if __name__ == "__main__":
    main()
