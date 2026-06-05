"""
src/domain2_upsell.py
확장성 증거 — "같은 수집 인프라 → 두 번째 도메인".

취소(domain 1) 파이프라인을 **그대로 재사용**해, 동일한 예약 피처로 '업셀 성향'
(특별요청 ≥ 1건 발생)을 예측한다. 핵심 트릭: growth_curve.py의 머신러리
(model_grid·eval_cutoff·성장곡선)를 import 하고 **타깃 컬럼(is_canceled 슬롯)만 교체**.
→ "같은 코드, 새 도메인"을 문자 그대로 증명. + 새 도메인은 콜드스타트(0)에서 자란다.

왜 업셀인가: 수익(ancillary revenue) 도메인 / 취소와 같은 per-booking 분류 /
total_of_special_requests 를 피처에서 제거해 비순환. is_canceled(미래값)도 피처 제외.

산출물:
  results/domain2_upsell_compare.csv     - full-data 5모델 PR-AUC (업셀)
  results/domain2_upsell_growth.{csv,png} - 미니 성장곡선 (새 도메인이 데이터 쌓이며 자람)

실행: python src/domain2_upsell.py [--stride N]
"""
import sys, io, time, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

import growth_curve as gc   # ★ 같은 인프라 재사용 (model_grid·eval_cutoff·성장곡선·PALETTE)

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"


def relabel(df):
    """is_canceled 컬럼을 '업셀(특별요청>=1)' 타깃으로 교체 + 특별요청 피처 제거.
    → 라벨 슬롯만 바꾸면 growth_curve의 eval_cutoff 가 그대로 새 도메인을 학습한다."""
    d = df.copy()
    d["is_canceled"] = (d["total_of_special_requests"] >= 1).astype(int)  # 새 타깃을 라벨 슬롯에
    d = d.drop(columns=["total_of_special_requests"])                     # 타깃 원천 피처 제거(비순환)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stride", type=int, default=8, help="성장곡선 컷오프 stride(속도)")
    args = ap.parse_args()
    t0 = time.time()

    train = relabel(pd.read_csv(DATA / "train_processed.csv"))
    test  = relabel(pd.read_csv(DATA / "test_processed.csv"))
    train["_wk"] = gc.abs_week(train)
    base_tr, base_te = train["is_canceled"].mean(), test["is_canceled"].mean()
    print(f"[로드] train {train.shape} test {test.shape} | 업셀(특별요청>=1) 비율 "
          f"train {base_tr:.3f} / test {base_te:.3f}")

    # 고정 평가셋 인코딩
    te = pd.get_dummies(test, columns=gc.CAT_COLS)
    y_te = te["is_canceled"].reset_index(drop=True)
    test_feat = te.drop("is_canceled", axis=1).reset_index(drop=True)
    rng = np.random.default_rng(0)

    # ── 1) full-data 5모델 비교 (같은 인프라가 새 도메인 모델을 만든다) ───────────
    rows, _ = gc.eval_cutoff(train, test_feat, y_te, [42], 0, rng,
                             "full", int(train["_wk"].max()), do_ci=False)
    cmp = (pd.DataFrame(rows)[["model", "pr_auc", "brier"]]
           .sort_values("pr_auc", ascending=False).reset_index(drop=True))
    RESULTS.mkdir(exist_ok=True)
    cmp.to_csv(RESULTS / "domain2_upsell_compare.csv", index=False)
    print(f"\n[업셀 도메인 — full-data PR-AUC] (base rate {base_te:.3f})")
    print(cmp.to_string(index=False))
    print(f"  → 최고 {cmp.iloc[0]['model']} {cmp.iloc[0]['pr_auc']:.3f} "
          f"(base 대비 {cmp.iloc[0]['pr_auc']/base_te:.2f}배)")

    # ── 2) 미니 성장곡선 (새 도메인도 0에서 자란다 = '모든 새 도메인은 콜드스타트') ─
    weeks = sorted(train["_wk"].unique())
    cutoffs = [t for t in weeks if (train["_wk"] <= t).sum() >= gc.MIN_N][::args.stride]
    print(f"\n[성장곡선] 컷오프 {len(cutoffs)}개 (stride={args.stride})")
    grows = []
    for t in cutoffs:
        sub = train[train["_wk"] <= t]
        if sub["is_canceled"].nunique() < 2:
            continue
        r, _ = gc.eval_cutoff(sub, test_feat, y_te, [42], 0, rng, "cumulative", t, do_ci=False)
        grows += r
        print(f"  week {t:>3}  n={len(sub):>6}  done  ({time.time()-t0:.0f}s)")
    agg = (pd.DataFrame(grows).groupby(["cutoff_week", "n_train", "model"])
           .agg(pr_auc=("pr_auc", "mean")).reset_index())
    agg.to_csv(RESULTS / "domain2_upsell_growth.csv", index=False)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    for name, gg in agg.groupby("model"):
        gg = gg.sort_values("n_train")
        ax.plot(gg["n_train"], gg["pr_auc"], "-", color=gc.PALETTE.get(name, "black"), lw=2, label=name)
    ax.axhline(base_te, ls=":", color="gray", alpha=.7)
    ax.text(agg["n_train"].max(), base_te, " base rate", fontsize=8, va="bottom", ha="right")
    ax.set_xlabel("cumulative training data (bookings)")
    ax.set_ylabel("PR-AUC (upsell = special_requests >= 1)")
    ax.set_title("Domain 2 (Upsell) — same infra, a NEW domain grows from zero")
    ax.legend(fontsize=8); ax.grid(alpha=.3); plt.tight_layout()
    fig.savefig(RESULTS / "domain2_upsell_growth.png", dpi=120)

    print(f"\n[산출물]\n  results/domain2_upsell_compare.csv"
          f"\n  results/domain2_upsell_growth.csv\n  results/domain2_upsell_growth.png")
    print(f"[완료] {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
