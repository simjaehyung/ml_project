"""
src/growth_curve.py
트랙 I — 주 단위 성장 곡선 & 구간별 모델 선정
설계: design_18 + 2026-06-04 모델 토론 합의

합의 반영:
  - 시간축    : 누적창(expanding, 주력) + 슬라이딩창(sliding, robustness 오버레이)
  - 라벨 규칙 : point-in-time — 도착일이 관측주차(t)를 지난 예약만 학습(look-ahead 차단)
                arrival_week <= t  ⇒  booking_week <= arrival_week <= t 자동 함의
  - 모델      : Dummy, LR(스케일), RF, XGBoost, LightGBM
  - HP 정책   : 구간별 경량 재튜닝(규제축 1개). train 내부 '시간순 holdout(마지막 20%)'로 선택
                → 평가셋(test) 누수 없음. 최종은 train_sub 전체로 재학습.
  - KPI 3층   : PR-AUC + Bootstrap 95% CI (선정) / Brier (배포 준비도) / expected cost (보조·비용비 sweep)
  - 핵심 산출물: 전환 주차 W = LightGBM CI하한 > LR CI상한이 되는 첫 누적 주차

실행:
  python src/growth_curve.py             # full (학교서버/백그라운드 권장, 1~2h)
  python src/growth_curve.py --quick     # 스모크 (구간 5개, 시드 1, boot 100) — 정상동작 확인용

산출물:
  results/growth_curve_raw.csv   - (window, cutoff_week, n_train, model, seed) 별 PR-AUC/Brier/cost
  results/growth_curve_agg.csv   - 시드 평균 + Bootstrap CI(LR·LGB) + 전환주차
  results/growth_curve.png       - 5곡선 + CI 밴드(누적) + 슬라이딩 오버레이
"""
import sys, io, time, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score, brier_score_loss

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
try:
    from lightgbm import LGBMClassifier
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

ROOT    = Path(__file__).parent.parent
DATA    = ROOT / "data"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

CAT_COLS = ["hotel", "meal", "market_segment", "distribution_channel",
            "reserved_room_type", "customer_type", "country_grouped"]
SEEDS_DEFAULT = [42, 7, 123]
SLIDE_WEEKS   = 26          # 슬라이딩창 폭(주)
MIN_N         = 400         # 구간 최소 학습 표본(콜드스타트 노이즈 컷오프)
THRESH        = 0.65        # 운영 임계값(현 DSS 기본) — expected cost용
COST_RATIOS   = [2, 5, 10]  # c_fn / c_fp (빈방손실 / 오버부킹보상) sweep
CI_MODELS     = ["Logistic Regression", "LightGBM"]  # 전환주차 판정 핵심쌍만 Bootstrap


# ── 절대 주차 인덱스 ──────────────────────────────────────────────────────────
def abs_week(df):
    y0 = df["arrival_date_year"].min()
    return (df["arrival_date_year"] - y0) * 53 + df["arrival_date_week_number"]


# ── 모델 + 경량 HP 그리드(규제 축 1개) ────────────────────────────────────────
def model_grid(seed):
    grid = {
        "Dummy":               [("const", DummyClassifier(strategy="most_frequent"))],
        "Logistic Regression": [(f"C={c}", LogisticRegression(C=c, max_iter=1000, random_state=seed))
                                 for c in (0.1, 1.0, 10.0)],
        "Random Forest":       [(f"depth={d}", RandomForestClassifier(
                                    n_estimators=100, max_depth=d, random_state=seed, n_jobs=-1))
                                 for d in (None, 10, 20)],
    }
    if HAS_XGB:
        grid["XGBoost"] = [(f"depth={d}", XGBClassifier(
            n_estimators=100, max_depth=d, random_state=seed,
            eval_metric="logloss", verbosity=0, n_jobs=-1)) for d in (3, 6, 9)]
    if HAS_LGB:
        grid["LightGBM"] = [(f"leaves={l}", LGBMClassifier(
            n_estimators=100, num_leaves=l, random_state=seed,
            verbose=-1, n_jobs=-1)) for l in (15, 31, 63)]
    return grid


NEEDS_SCALE = {"Logistic Regression"}


def fit_select(name, candidates, Xtr, ytr, wk_tr):
    """train 내부 시간순 holdout(마지막 20%)로 규제축 1개 선택 → train 전체로 재학습."""
    if len(candidates) == 1:
        m = candidates[0][1]; m.fit(Xtr, ytr); return m, candidates[0][0]
    order = np.argsort(wk_tr.values)
    cut   = int(len(order) * 0.8)
    tr_idx, va_idx = order[:cut], order[cut:]
    # holdout이 너무 작거나 한 클래스뿐이면 튜닝 생략(첫 후보=기본값)
    if len(va_idx) < 50 or ytr.iloc[va_idx].nunique() < 2:
        m = candidates[0][1]; m.fit(Xtr, ytr); return m, candidates[0][0] + "(default)"
    best, best_ap = None, -1
    for tag, mdl in candidates:
        mdl.fit(Xtr.iloc[tr_idx], ytr.iloc[tr_idx])
        ap = average_precision_score(ytr.iloc[va_idx], mdl.predict_proba(Xtr.iloc[va_idx])[:, 1])
        if ap > best_ap:
            best_ap, best = ap, (tag, mdl)
    best[1].fit(Xtr, ytr)        # 전체 재학습
    return best[1], best[0]


def expected_costs(y_true, proba, thresh=THRESH):
    pred = proba >= thresh
    fn = int(((y_true == 1) & (~pred)).sum())   # 취소인데 놓침 → 빈 방 손실
    fp = int(((y_true == 0) & (pred)).sum())    # 취소 아닌데 Flexi → 오버부킹 보상
    return {f"cost_r{r}": (r * fn + fp) / len(y_true) for r in COST_RATIOS}


def bootstrap_ci(y_true, proba, n_boot, rng):
    yv = y_true.values if hasattr(y_true, "values") else y_true
    n  = len(yv)
    aps = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        aps[b] = average_precision_score(yv[idx], proba[idx])
    return float(np.percentile(aps, 2.5)), float(np.percentile(aps, 97.5))


PALETTE = {"Dummy": "gray", "Logistic Regression": "steelblue",
           "Random Forest": "darkorange", "XGBoost": "seagreen", "LightGBM": "crimson"}


def compute_robust_W(agg):
    """robust 전환주차 = 누적창에서 LGB CI하한 > LR CI상한이 '이후 끝까지 지속'되는 첫 주차.
    소표본 1회성 노이즈 분리를 배제한다(발표 방어용). 그런 주차가 없으면 None."""
    cum = agg[agg["window"] == "cumulative"]
    if not {"ci_low", "ci_high"}.issubset(cum.columns):
        return None
    sub = cum[cum["model"].isin(["Logistic Regression", "LightGBM"])]
    if sub.empty:
        return None
    piv = sub.pivot(index="cutoff_week", columns="model", values=["ci_low", "ci_high"])
    wks = sorted(piv.index)

    def lgb_over_lr(w):
        try:
            lg = piv.loc[w, ("ci_low", "LightGBM")]
            lr = piv.loc[w, ("ci_high", "Logistic Regression")]
            return pd.notna(lg) and pd.notna(lr) and lg > lr
        except KeyError:
            return False

    for i, wk in enumerate(wks):
        if all(lgb_over_lr(w) for w in wks[i:]):
            return int(wk)
    return None


def finalize(agg, t_start=None):
    """W 계산 + 곡선 플롯 + 저장. 학습 결과(agg)와 --replot(csv 로드) 양쪽에서 재사용."""
    W = compute_robust_W(agg)
    print(f"\n★ robust 전환주차 W = {W}  (LGB CI하한 > LR CI상한이 끝까지 지속되는 첫 누적주차)")

    fig, axA = plt.subplots(figsize=(10, 6))
    cum = agg[agg["window"] == "cumulative"]
    for name, g in cum.groupby("model"):
        g = g.sort_values("cutoff_week")
        c = PALETTE.get(name, "black")
        axA.plot(g["cutoff_week"], g["pr_auc"], "-", color=c, lw=2, label=f"{name} (cumulative)")
        if {"ci_low", "ci_high"}.issubset(g.columns) and g["ci_low"].notna().any():
            axA.fill_between(g["cutoff_week"], g["ci_low"], g["ci_high"], color=c, alpha=0.15)
    sld = agg[agg["window"] == "sliding"]
    for name, g in sld.groupby("model"):
        g = g.sort_values("cutoff_week")
        axA.plot(g["cutoff_week"], g["pr_auc"], "--", color=PALETTE.get(name, "black"),
                 lw=1, alpha=0.6)
    if W is not None:
        axA.axvline(W, color="black", ls=":", alpha=0.7)
        axA.text(W, axA.get_ylim()[0], f" W={W} (robust)", fontsize=10)
    axA.set_xlabel("cumulative week (arrival, point-in-time)")
    axA.set_ylabel("PR-AUC (fixed summer test)")
    axA.set_title("Growth curve — solid=cumulative(+95% CI), dashed=sliding robustness")
    axA.legend(fontsize=8, ncol=2); axA.grid(alpha=0.3)
    plt.tight_layout()
    fig.savefig(RESULTS / "growth_curve.png", dpi=120)
    print(f"\n[산출물]\n  results/growth_curve_raw.csv\n  results/growth_curve_agg.csv\n  results/growth_curve.png")
    if t_start is not None:
        print(f"[완료] {time.time()-t_start:.0f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="스모크: 구간 5개 + 시드 1 + boot 100")
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--seeds", type=int, default=len(SEEDS_DEFAULT))
    ap.add_argument("--windows", choices=["cumulative", "sliding", "both"], default="both")
    ap.add_argument("--stride", type=int, default=1, help="누적 컷오프 N개마다 1개만 (곡선 점 수 축소·속도↑)")
    ap.add_argument("--replot", action="store_true", help="학습 생략, 기존 agg.csv로 곡선·W만 재생성")
    args = ap.parse_args()

    if args.replot:
        print("[replot] 기존 results/growth_curve_agg.csv 로 곡선·W 재생성 (학습 생략)")
        finalize(pd.read_csv(RESULTS / "growth_curve_agg.csv"))
        return

    seeds = SEEDS_DEFAULT[:args.seeds]
    n_boot = args.boot
    if args.quick:
        seeds, n_boot = [42], 100

    print(f"[설정] quick={args.quick} seeds={seeds} boot={n_boot} windows={args.windows}")
    t_start = time.time()

    tr_path, te_path = DATA / "train_processed.csv", DATA / "test_processed.csv"
    if not tr_path.exists():
        print(f"✗ {tr_path} 없음 — 먼저 'python src/preprocessing_pipeline.py' 실행")
        sys.exit(1)
    train = pd.read_csv(tr_path)
    test  = pd.read_csv(te_path)
    train["_wk"] = abs_week(train)
    print(f"[로드] train {train.shape} test {test.shape} | 주차 {train['_wk'].min()}~{train['_wk'].max()}")

    # 고정 평가셋 인코딩(전 구간 공통 기준 컬럼은 각 구간 train_sub에 맞춰 reindex)
    test_e = pd.get_dummies(test, columns=CAT_COLS)
    y_te   = test_e["is_canceled"]
    test_feat = test_e.drop("is_canceled", axis=1)

    weeks = sorted(train["_wk"].unique())
    windows = ["cumulative", "sliding"] if args.windows == "both" else [args.windows]

    # 구간(누적 컷오프) 목록 — n>=MIN_N 보장되는 주차부터
    cutoffs = []
    for t in weeks:
        if (train["_wk"] <= t).sum() >= MIN_N:
            cutoffs.append(t)
    if args.quick:
        cutoffs = cutoffs[:: max(1, len(cutoffs) // 5)][:5]
    elif args.stride > 1:
        cutoffs = cutoffs[::args.stride]
    print(f"[구간] 누적 컷오프 {len(cutoffs)}개: {cutoffs[0]}~{cutoffs[-1]}")

    rng = np.random.default_rng(0)
    rows = []      # raw per (window,cutoff,model,seed)
    ci_rows = []   # bootstrap CI per (window,cutoff,model)

    for win in windows:
        for t in cutoffs:
            if win == "cumulative":
                sub = train[train["_wk"] <= t]
            else:  # sliding: 최근 SLIDE_WEEKS
                sub = train[(train["_wk"] > t - SLIDE_WEEKS) & (train["_wk"] <= t)]
            if len(sub) < MIN_N or sub["is_canceled"].nunique() < 2:
                continue

            sub_e = pd.get_dummies(sub, columns=CAT_COLS)
            ytr   = sub_e["is_canceled"]
            Xtr   = sub_e.drop(["is_canceled", "_wk"], axis=1, errors="ignore")
            wk_tr = sub["_wk"].reset_index(drop=True)
            Xtr   = Xtr.reset_index(drop=True); ytr = ytr.reset_index(drop=True)
            Xte   = test_feat.reindex(columns=Xtr.columns, fill_value=0)

            # 스케일(LR 전용)
            scaler = StandardScaler()
            Xtr_s  = pd.DataFrame(scaler.fit_transform(Xtr), columns=Xtr.columns)
            Xte_s  = pd.DataFrame(scaler.transform(Xte),    columns=Xtr.columns)

            proba_for_ci = {}   # model -> proba(seed0) for bootstrap
            for seed in seeds:
                grid = model_grid(seed)
                for name, cands in grid.items():
                    X_tr_use = Xtr_s if name in NEEDS_SCALE else Xtr
                    X_te_use = Xte_s if name in NEEDS_SCALE else Xte
                    mdl, hp = fit_select(name, cands, X_tr_use, ytr, wk_tr)
                    proba = mdl.predict_proba(X_te_use)[:, 1]
                    rec = {"window": win, "cutoff_week": int(t), "n_train": int(len(sub)),
                           "model": name, "seed": seed, "hp": hp,
                           "pr_auc": average_precision_score(y_te, proba),
                           "brier":  brier_score_loss(y_te, proba)}
                    rec.update(expected_costs(y_te, proba))
                    rows.append(rec)
                    if seed == seeds[0]:
                        proba_for_ci[name] = proba

            # Bootstrap CI (누적창 × 핵심쌍만)
            if win == "cumulative":
                for name in CI_MODELS:
                    if name in proba_for_ci:
                        lo, hi = bootstrap_ci(y_te, proba_for_ci[name], n_boot, rng)
                        ci_rows.append({"cutoff_week": int(t), "model": name,
                                        "ci_low": lo, "ci_high": hi})
            print(f"  [{win}] week {t:>3}  n={len(sub):>6}  done  ({time.time()-t_start:.0f}s)")

    raw = pd.DataFrame(rows)
    raw.to_csv(RESULTS / "growth_curve_raw.csv", index=False)

    # 시드 평균 집계
    agg = (raw.groupby(["window", "cutoff_week", "n_train", "model"])
              .agg(pr_auc=("pr_auc", "mean"), pr_auc_sd=("pr_auc", "std"),
                   brier=("brier", "mean"))
              .reset_index())
    ci = pd.DataFrame(ci_rows)
    if not ci.empty:
        agg = agg.merge(ci, on=["cutoff_week", "model"], how="left")
    agg.to_csv(RESULTS / "growth_curve_agg.csv", index=False)

    finalize(agg, t_start)


if __name__ == "__main__":
    main()
