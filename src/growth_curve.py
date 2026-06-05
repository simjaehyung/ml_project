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

평가 방식 (--eval):
  fixed       : (기본) 고정된 마지막 6개월(test split)을 매 cutoff에서 예측. 통제 벤치마크.
  walkforward : 매 cutoff t에서 '다음 H주(arrival_week ∈ (t, t+H])'만 예측. 배포 현실(월간 재학습→다음달).
                → 고정-test의 'train↔test 간격 축소(recency) confound'를 제거. 단 평가창이 움직여 더 노이즈.
                fixed 산출물과 분리: results/growth_curve_wf_*.{csv,png} (기존 덮어쓰지 않음).

실행:
  python src/growth_curve.py                              # fixed full (학교서버/백그라운드 권장)
  python src/growth_curve.py --quick                      # fixed 스모크
  python src/growth_curve.py --eval walkforward --horizon 4          # walk-forward full
  python src/growth_curve.py --eval walkforward --horizon 4 --quick  # walk-forward 스모크
  python src/growth_curve.py --eval walkforward --strict             # 평가창을 'booking_week<=t'로 제한(현실)

산출물:
  results/growth_curve_raw.csv / _agg.csv / .png         - fixed
  results/growth_curve_wf_raw.csv / _wf_agg.csv / _wf.png - walkforward
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
MIN_TEST      = 100         # walk-forward 평가창 최소 표본
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


# ── 한 cutoff 평가 블록 (walk-forward 전용 재사용 함수) ────────────────────────
def eval_cutoff(sub, test_feat, y_te, seeds, n_boot, rng, win_label, t, do_ci):
    """sub(학습셋) → test_feat/y_te(평가셋) 에 대해 5모델 평가. (rows, ci_rows) 반환.
    test_feat 은 이미 get_dummies/ is_canceled 제거된 상태(컬럼은 Xtr 기준으로 reindex됨)."""
    sub_e = pd.get_dummies(sub, columns=CAT_COLS)
    ytr   = sub_e["is_canceled"]
    Xtr   = sub_e.drop(["is_canceled", "_wk"], axis=1, errors="ignore")
    wk_tr = sub["_wk"].reset_index(drop=True)
    Xtr   = Xtr.reset_index(drop=True); ytr = ytr.reset_index(drop=True)
    Xte   = test_feat.reindex(columns=Xtr.columns, fill_value=0)

    scaler = StandardScaler()
    Xtr_s  = pd.DataFrame(scaler.fit_transform(Xtr), columns=Xtr.columns)
    Xte_s  = pd.DataFrame(scaler.transform(Xte),    columns=Xtr.columns)

    rows, ci_rows, proba_for_ci = [], [], {}
    for seed in seeds:
        grid = model_grid(seed)
        for name, cands in grid.items():
            X_tr_use = Xtr_s if name in NEEDS_SCALE else Xtr
            X_te_use = Xte_s if name in NEEDS_SCALE else Xte
            mdl, hp = fit_select(name, cands, X_tr_use, ytr, wk_tr)
            proba = mdl.predict_proba(X_te_use)[:, 1]
            rec = {"window": win_label, "cutoff_week": int(t), "n_train": int(len(sub)),
                   "n_test": int(len(y_te)), "model": name, "seed": seed, "hp": hp,
                   "pr_auc": average_precision_score(y_te, proba),
                   "brier":  brier_score_loss(y_te, proba)}
            rec.update(expected_costs(y_te, proba))
            rows.append(rec)
            if seed == seeds[0]:
                proba_for_ci[name] = proba
    if do_ci:
        for name in CI_MODELS:
            if name in proba_for_ci:
                lo, hi = bootstrap_ci(y_te, proba_for_ci[name], n_boot, rng)
                ci_rows.append({"cutoff_week": int(t), "model": name, "ci_low": lo, "ci_high": hi})
    return rows, ci_rows


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


def finalize(agg, t_start=None, mode="fixed", horizon=None):
    """W 계산 + 곡선 플롯 + 저장. fixed / walkforward 양쪽 + --replot 에서 재사용."""
    wf = (mode == "walkforward")
    W = compute_robust_W(agg)
    print(f"\n★ [{mode}] robust 전환주차 W = {W}  (LGB CI하한 > LR CI상한이 끝까지 지속되는 첫 누적주차)")

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
    ylab = f"PR-AUC (walk-forward, next {horizon}w)" if wf else "PR-AUC (fixed summer test)"
    axA.set_ylabel(ylab)
    title = (f"Growth curve [walk-forward, horizon={horizon}w] — solid=cumulative(+95% CI)"
             if wf else "Growth curve [fixed test] — solid=cumulative(+95% CI), dashed=sliding robustness")
    axA.set_title(title)
    axA.legend(fontsize=8, ncol=2); axA.grid(alpha=0.3)
    plt.tight_layout()
    png = "growth_curve_wf.png" if wf else "growth_curve.png"
    raw_name = "growth_curve_wf_raw.csv" if wf else "growth_curve_raw.csv"
    agg_name = "growth_curve_wf_agg.csv" if wf else "growth_curve_agg.csv"
    fig.savefig(RESULTS / png, dpi=120)
    print(f"\n[산출물]\n  results/{raw_name}\n  results/{agg_name}\n  results/{png}")
    if t_start is not None:
        print(f"[완료] {time.time()-t_start:.0f}s")


# ── walk-forward 평가 (다음 H주 예측) ─────────────────────────────────────────
def run_walkforward(train, test, seeds, n_boot, horizon, strict, quick, stride, t_start):
    # 전체 타임라인(train+test) 합쳐 abs_week 재계산 (평가창이 test 구간까지 전진)
    full = pd.concat([train.drop(columns=["_wk"], errors="ignore"), test], ignore_index=True)
    full["_wk"] = abs_week(full)
    bwk = full["_wk"] - (full["lead_time"] / 7.0) if strict else None  # 근사 예약주차(컬럼 미추가→누수 방지)

    weeks  = sorted(full["_wk"].unique())
    max_wk = max(weeks)
    cutoffs = []
    for t in weeks:
        if t + horizon > max_wk:        # 평가창(다음 H주) 확보 못하면 종료
            break
        if (full["_wk"] <= t).sum() >= MIN_N:
            cutoffs.append(t)
    if quick:
        cutoffs = cutoffs[:: max(1, len(cutoffs) // 5)][:5]
    elif stride > 1:
        cutoffs = cutoffs[::stride]
    print(f"[walk-forward] horizon={horizon}주{' strict' if strict else ''} | "
          f"전체 {full.shape} | 컷오프 {len(cutoffs)}개: {cutoffs[0]}~{cutoffs[-1]}")

    rng = np.random.default_rng(0)
    rows, ci_rows = [], []
    for t in cutoffs:
        sub = full[full["_wk"] <= t]
        mask = (full["_wk"] > t) & (full["_wk"] <= t + horizon)
        if strict:
            mask = mask & (bwk <= t)
        test_win = full[mask]
        if len(sub) < MIN_N or sub["is_canceled"].nunique() < 2:
            continue
        if len(test_win) < MIN_TEST or test_win["is_canceled"].nunique() < 2:
            print(f"  [wf] week {t:>3}  skip (n_test={len(test_win)})")
            continue

        twe = pd.get_dummies(test_win, columns=CAT_COLS)
        y_te = twe["is_canceled"].reset_index(drop=True)
        test_feat = twe.drop(["is_canceled", "_wk"], axis=1, errors="ignore").reset_index(drop=True)

        r, c = eval_cutoff(sub, test_feat, y_te, seeds, n_boot, rng, "cumulative", t, do_ci=True)
        rows += r; ci_rows += c
        print(f"  [wf] week {t:>3}  n_train={len(sub):>6} n_test={len(test_win):>5}  done  ({time.time()-t_start:.0f}s)")

    raw = pd.DataFrame(rows)
    raw.to_csv(RESULTS / "growth_curve_wf_raw.csv", index=False)
    agg = (raw.groupby(["window", "cutoff_week", "n_train", "model"])
              .agg(pr_auc=("pr_auc", "mean"), pr_auc_sd=("pr_auc", "std"),
                   brier=("brier", "mean"), n_test=("n_test", "first"))
              .reset_index())
    ci = pd.DataFrame(ci_rows)
    if not ci.empty:
        agg = agg.merge(ci, on=["cutoff_week", "model"], how="left")
    agg.to_csv(RESULTS / "growth_curve_wf_agg.csv", index=False)
    finalize(agg, t_start, mode="walkforward", horizon=horizon)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="스모크: 구간 5개 + 시드 1 + boot 100")
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--seeds", type=int, default=len(SEEDS_DEFAULT))
    ap.add_argument("--windows", choices=["cumulative", "sliding", "both"], default="both")
    ap.add_argument("--stride", type=int, default=1, help="누적 컷오프 N개마다 1개만 (곡선 점 수 축소·속도↑)")
    ap.add_argument("--replot", action="store_true", help="학습 생략, 기존 agg.csv로 곡선·W만 재생성")
    ap.add_argument("--eval", choices=["fixed", "walkforward"], default="fixed",
                    help="fixed(기본): 고정 마지막6개월 / walkforward: 다음 H주 예측")
    ap.add_argument("--horizon", type=int, default=4, help="walk-forward 평가창 폭(주). 업데이트 주기. 기본 4주(≈1달)")
    ap.add_argument("--strict", action="store_true",
                    help="walk-forward 평가창을 booking_week<=t 로 제한(지금 장부에 있는 다음달 예약만)")
    args = ap.parse_args()

    if args.replot:
        wf = (args.eval == "walkforward")
        src = "growth_curve_wf_agg.csv" if wf else "growth_curve_agg.csv"
        print(f"[replot] 기존 results/{src} 로 곡선·W 재생성 (학습 생략)")
        finalize(pd.read_csv(RESULTS / src), mode=args.eval, horizon=args.horizon)
        return

    seeds = SEEDS_DEFAULT[:args.seeds]
    n_boot = args.boot
    if args.quick:
        seeds, n_boot = [42], 100

    print(f"[설정] eval={args.eval} quick={args.quick} seeds={seeds} boot={n_boot} "
          f"windows={args.windows} horizon={args.horizon}")
    t_start = time.time()

    tr_path, te_path = DATA / "train_processed.csv", DATA / "test_processed.csv"
    if not tr_path.exists():
        print(f"✗ {tr_path} 없음 — 먼저 'python src/preprocessing_pipeline.py' 실행")
        sys.exit(1)
    train = pd.read_csv(tr_path)
    test  = pd.read_csv(te_path)
    train["_wk"] = abs_week(train)
    print(f"[로드] train {train.shape} test {test.shape} | 주차 {train['_wk'].min()}~{train['_wk'].max()}")

    # ── walk-forward 분기 (fixed 경로는 아래로 그대로) ───────────────────────
    if args.eval == "walkforward":
        run_walkforward(train, test, seeds, n_boot, args.horizon, args.strict,
                        args.quick, args.stride, t_start)
        return

    # ── fixed (기존 동작 — 변경 없음) ────────────────────────────────────────
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
