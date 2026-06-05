"""
src/country_ablation.py
국적(country) 피처 — 성능-윤리 트레이드오프 정량화

배경: docs/preprocessing_reexamination_2026-06-04.md A-3
  - country_grouped 가 SHAP 1순위 → "위험도를 국적이 좌우" = 차별 리스크(GDPR·반차별)
  - 더불어 top10이 train 전기간으로 결정된 누수(A-2)도 동반.
  - 권고: (c) ablation 으로 '성능 비용' 먼저 측정 → 거의 안 떨어지면 drop,
          떨어지면 (b) is_domestic 로 절충.

이 스크립트가 측정하는 3안 (고정 시간기반 test = 2017-01~08, 마지막 6개월):
  (a) WITH        country_grouped 포함 (현행 — PRT+Top10+Other OHE)
  (b) DROP        country 계열 전부 제외
  (c) is_domestic PRT=1 vs 그 외=0 단일 이진 피처로 대체

모델: LightGBM(주력) + Logistic Regression(보조).
지표: PR-AUC (메인) + Bootstrap 95% CI (n=2000). 보조로 Brier, F1@0.65.

전처리·모델 패턴은 src/run_all_models.py / src/growth_curve.py 와 동일:
  - get_dummies(OHE) + test reindex(컬럼 정렬, fill 0)
  - LR 전용 StandardScaler
  - 고정 test, 시간기반 split 그대로(이미 train_processed/test_processed 로 분리됨)

실행:
  python src/country_ablation.py            # full (boot 2000)
  python src/country_ablation.py --quick    # 스모크 (boot 200)

산출물:
  results/country_ablation.csv
  docs/country_ablation_result.md
"""
import sys, io, time, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score, brier_score_loss, f1_score

try:
    from lightgbm import LGBMClassifier
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

ROOT    = Path(__file__).parent.parent
DATA    = ROOT / "data"
RESULTS = ROOT / "results"
DOCS    = ROOT / "docs"
RESULTS.mkdir(exist_ok=True)

# run_all_models.py 와 동일한 카테고리 집합 (country 포함)
CAT_COLS_FULL = ["hotel", "meal", "market_segment", "distribution_channel",
                 "reserved_room_type", "customer_type", "country_grouped"]
CAT_COLS_NOCTRY = [c for c in CAT_COLS_FULL if c != "country_grouped"]

THRESH = 0.65     # 운영 임계값(현 DSS 기본) — F1·cost 보조 지표용
SEED   = 42


def build_variant(train, test, variant):
    """variant ∈ {with, drop, is_domestic} 에 따라 (X_tr,y_tr,X_te,y_te) 구성.
    OHE 후 test 를 train 컬럼으로 reindex(run_all_models.py 와 동일 규약)."""
    tr, te = train.copy(), test.copy()

    if variant == "with":
        cat = CAT_COLS_FULL
    elif variant == "drop":
        tr = tr.drop(columns=["country_grouped"])
        te = te.drop(columns=["country_grouped"])
        cat = CAT_COLS_NOCTRY
    elif variant == "is_domestic":
        # PRT(내국인) = 1, 그 외 = 0. country_grouped 는 OHE 대상에서 제거.
        tr["is_domestic"] = (tr["country_grouped"] == "PRT").astype(int)
        te["is_domestic"] = (te["country_grouped"] == "PRT").astype(int)
        tr = tr.drop(columns=["country_grouped"])
        te = te.drop(columns=["country_grouped"])
        cat = CAT_COLS_NOCTRY
    else:
        raise ValueError(variant)

    tr_e = pd.get_dummies(tr, columns=cat)
    te_e = pd.get_dummies(te, columns=cat)
    te_e = te_e.reindex(columns=tr_e.columns, fill_value=0)

    X_tr = tr_e.drop("is_canceled", axis=1); y_tr = tr_e["is_canceled"]
    X_te = te_e.drop("is_canceled", axis=1); y_te = te_e["is_canceled"]
    return X_tr, y_tr, X_te, y_te


def bootstrap_ci(y_true, proba, n_boot, rng):
    yv = y_true.values if hasattr(y_true, "values") else np.asarray(y_true)
    n  = len(yv)
    aps = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        aps[b] = average_precision_score(yv[idx], proba[idx])
    return float(np.percentile(aps, 2.5)), float(np.percentile(aps, 97.5))


def fit_eval(model_name, variant, train, test, n_boot, rng):
    X_tr, y_tr, X_te, y_te = build_variant(train, test, variant)

    if model_name == "Logistic Regression":
        scaler = StandardScaler()
        X_tr_u = scaler.fit_transform(X_tr)
        X_te_u = scaler.transform(X_te)
        mdl = LogisticRegression(C=1, max_iter=1000, random_state=SEED)
    elif model_name == "LightGBM":
        X_tr_u, X_te_u = X_tr, X_te
        mdl = LGBMClassifier(n_estimators=100, random_state=SEED, verbose=-1, n_jobs=-1)
    else:
        raise ValueError(model_name)

    t0 = time.time()
    mdl.fit(X_tr_u, y_tr)
    proba = mdl.predict_proba(X_te_u)[:, 1]
    pr_auc = average_precision_score(y_te, proba)
    lo, hi = bootstrap_ci(y_te, proba, n_boot, rng)
    brier  = brier_score_loss(y_te, proba)
    f1     = f1_score(y_te, proba >= THRESH)
    elapsed = time.time() - t0
    print(f"  [{model_name:>19} | {variant:>11}]  "
          f"PR-AUC {pr_auc:.4f}  CI[{lo:.4f},{hi:.4f}]  "
          f"Brier {brier:.4f}  F1@{THRESH} {f1:.4f}  n_feat={X_tr.shape[1]}  ({elapsed:.1f}s)")
    return {"model": model_name, "variant": variant, "n_features": X_tr.shape[1],
            "pr_auc": pr_auc, "ci_low": lo, "ci_high": hi,
            "brier": brier, "f1@0.65": f1}


VARIANT_LABEL = {
    "with":        "(a) WITH country_grouped (현행)",
    "drop":        "(b) DROP 국적 전부 제외",
    "is_domestic": "(c) is_domestic (PRT=1 vs 그 외=0)",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="스모크: boot 200")
    ap.add_argument("--boot", type=int, default=2000)
    args = ap.parse_args()
    n_boot = 200 if args.quick else args.boot

    train = pd.read_csv(DATA / "train_processed.csv")
    test  = pd.read_csv(DATA / "test_processed.csv")
    print(f"[로드] train {train.shape}  test {test.shape}  "
          f"| test 취소율 {test['is_canceled'].mean():.1%}  boot={n_boot}")
    print(f"[고정 test] 2017-01~08 (마지막 6개월, 시간기반 split)\n")

    models = ["LightGBM", "Logistic Regression"] if HAS_LGB else ["Logistic Regression"]
    variants = ["with", "drop", "is_domestic"]
    rng = np.random.default_rng(0)

    rows = []
    for model_name in models:
        for variant in variants:
            rows.append(fit_eval(model_name, variant, train, test, n_boot, rng))

    df = pd.DataFrame(rows)
    out_csv = RESULTS / "country_ablation.csv"
    df.to_csv(out_csv, index=False)
    print(f"\n[산출물] {out_csv}")

    # ── delta 계산 (WITH 대비 하락폭) ────────────────────────────────────────
    summary = {}
    for model_name in models:
        sub = df[df["model"] == model_name].set_index("variant")
        base = sub.loc["with", "pr_auc"]
        deltas = {v: sub.loc[v, "pr_auc"] - base for v in variants}
        # CI 겹침 판정: drop/is_domestic 의 CI상한 vs with CI하한
        with_lo = sub.loc["with", "ci_low"]
        overlap = {v: sub.loc[v, "ci_high"] >= with_lo for v in ["drop", "is_domestic"]}
        summary[model_name] = {"base": base, "deltas": deltas, "overlap": overlap, "sub": sub}

    # ── 마크다운 리포트 ─────────────────────────────────────────────────────
    lines = []
    lines.append("# 국적(country) 피처 — 성능-윤리 트레이드오프 ablation 결과")
    lines.append("")
    lines.append("> 작성: PM 자율작업 (country ablation) | 성격: **정량 측정 + 발표 방어 카드**")
    lines.append("> 계기: `docs/preprocessing_reexamination_2026-06-04.md` A-3 (국적 SHAP 1위 → 차별 리스크) + A-2 (top10 누수)")
    lines.append("> 스크립트: `src/country_ablation.py` | 데이터: `data/{train,test}_processed.csv` (고정 시간기반 test, 2017-01~08)")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 측정 설계")
    lines.append("")
    lines.append("| 안 | 처리 | 의미 |")
    lines.append("|---|------|------|")
    lines.append("| (a) WITH | `country_grouped` OHE 포함 (현행) | 국적을 위험 동인으로 그대로 사용 |")
    lines.append("| (b) DROP | 국적 계열 전부 제거 | 윤리 부채 0, 국적 신호 완전 포기 |")
    lines.append("| (c) is_domestic | PRT=1 vs 그 외=0 단일 이진 | 다국적 차별 광학 제거 + PRT 지배신호 보존 + **A-2 누수 소멸** |")
    lines.append("")
    lines.append(f"- 지표: **PR-AUC**(메인) + Bootstrap 95% CI(n_boot={n_boot}) / 보조 Brier·F1@{THRESH}")
    lines.append(f"- test: {len(test):,}행, 취소율 {test['is_canceled'].mean():.1%} | 고정·시간기반(누수 없음)")
    lines.append("- 모델: LightGBM(주력) + Logistic Regression(보조). run_all_models.py 와 동일 전처리(OHE+reindex, LR만 스케일).")
    lines.append("")
    lines.append("## 결과")
    lines.append("")
    lines.append("| 모델 | 안 | PR-AUC | 95% CI | ΔPR-AUC(vs WITH) | Brier | F1@0.65 | n_feat |")
    lines.append("|------|----|--------|--------|------------------|-------|---------|--------|")
    for model_name in models:
        sub = summary[model_name]["sub"]
        for v in variants:
            r = sub.loc[v]
            d = summary[model_name]["deltas"][v]
            dstr = "기준" if v == "with" else f"{d:+.4f}"
            lines.append(f"| {model_name} | {VARIANT_LABEL[v]} | "
                         f"**{r['pr_auc']:.4f}** | [{r['ci_low']:.4f}, {r['ci_high']:.4f}] | "
                         f"{dstr} | {r['brier']:.4f} | {r['f1@0.65']:.4f} | {int(r['n_features'])} |")
    lines.append("")

    # ── 해석 + 방어 문장 (실제 수치로 자동 생성) ──────────────────────────────
    lines.append("## 해석")
    lines.append("")
    main_model = "LightGBM" if "LightGBM" in summary else "Logistic Regression"
    s = summary[main_model]
    d_drop = s["deltas"]["drop"]
    d_dom  = s["deltas"]["is_domestic"]
    base   = s["base"]
    pct_drop = abs(d_drop) / base * 100
    pct_dom  = abs(d_dom) / base * 100
    ovl_drop = s["overlap"]["drop"]
    ovl_dom  = s["overlap"]["is_domestic"]

    lines.append(f"**주력 모델 = {main_model}** (현 DSS 동결 모델 계열).")
    lines.append("")
    lines.append(f"- (b) DROP: PR-AUC {base:.4f} → {s['sub'].loc['drop','pr_auc']:.4f} "
                 f"(**{d_drop:+.4f}, 상대 {pct_drop:.1f}%**). "
                 f"95% CI는 WITH와 {'겹침 → 통계적으로 구분 불가' if ovl_drop else '겹치지 않음 → 유의한 하락'}.")
    lines.append(f"- (c) is_domestic: PR-AUC {base:.4f} → {s['sub'].loc['is_domestic','pr_auc']:.4f} "
                 f"(**{d_dom:+.4f}, 상대 {pct_dom:.1f}%**). "
                 f"95% CI는 WITH와 {'겹침 → 구분 불가' if ovl_dom else '겹치지 않음 → 유의한 하락'}. "
                 f"국적 OHE(다국적) 대신 이진 1개로 대체하면서 다국적 차별 광학·top10 누수(A-2)를 동시에 제거.")
    lines.append("")

    # 권고 결정 (수치 기반 분기)
    if ovl_drop and pct_drop < 2.0:
        rec = ("**(b) DROP 권고.** 국적을 완전히 빼도 PR-AUC 하락이 통계적으로 구분 불가(CI 겹침)하고 "
               f"절대 하락 {abs(d_drop):.4f}({pct_drop:.1f}%)에 그친다. 윤리 부채를 0으로 만들면서 성능 손실은 무시할 수준 "
               "→ 윤리적으로 안전하게 제거 가능.")
    elif pct_dom < pct_drop and (ovl_dom or pct_dom < 2.0):
        rec = ("**(c) is_domestic 절충 권고.** DROP은 성능 손실이 측정되지만, is_domestic 으로 대체하면 "
               f"하락폭이 {pct_dom:.1f}%로 줄고 다국적 차별 광학과 top10 누수(A-2)를 함께 제거한다. "
               "'내국인 vs 외국인'은 체류 패턴 차이로 운영상 정당화 가능.")
    else:
        rec = ("**판단 보류 — 수치 확인 필요.** 국적 제거 시 성능 손실이 측정되므로, "
               "성능-윤리 트레이드오프를 발표에서 정직하게 제시하고 거버넌스(행동 차등에 국적 직접 사용 금지)와 병행 검토.")
    lines.append("## 권고")
    lines.append("")
    lines.append(rec)
    lines.append("")
    lines.append("> 정직한 한계: 국적을 빼도 ADR·market_segment·distribution_channel 등 상관 피처로 **간접 차별**이 잔존할 수 있다. "
                 "완전한 공정성은 disparate impact 측정이 필요하나 6일 범위를 초과 → '한계'로 명시.")
    lines.append("")

    # ── 발표 방어 문장 ──────────────────────────────────────────────────────
    lines.append("## 발표 방어 문장 (S11 윤리·법률 집중블록용)")
    lines.append("")
    if ovl_drop:
        # DROP 이 통계적으로 공짜인 경우 — "거의 비용 없이 제거" 서사
        lines.append(f'1. "국적은 SHAP 1순위였지만, 모델에서 완전히 제거해도 PR-AUC는 {base:.3f}→{s["sub"].loc["drop","pr_auc"]:.3f}, '
                     f'단 {pct_drop:.1f}%({abs(d_drop):.4f}) 하락이고 95% 신뢰구간이 겹쳐 통계적으로 구분되지 않습니다. '
                     f'국적 기반 차등 대우라는 차별 리스크를 사실상 비용 없이 제거할 수 있습니다."')
        lines.append("")
        lines.append(f'2. "굳이 신호를 더 보존하고 싶다면 \'내국인(PRT) 여부\' 이진 피처 하나만 남기는 절충안도 있습니다 '
                     f'(PR-AUC {s["sub"].loc["is_domestic","pr_auc"]:.3f}). '
                     f'다국적 차별 광학을 없애고 \'top10을 전기간으로 정한\' 누수(A-2)까지 동시에 소멸시킵니다."')
    else:
        # DROP 이 유의하게 손실 — 정직하게 트레이드오프 제시, is_domestic 으로 착지
        lines.append(f'1. "국적은 SHAP 1순위라 \'그냥 빼면 된다\'고 말하고 싶지만, 정직하게 측정하니 완전 제거 시 '
                     f'PR-AUC가 {base:.3f}→{s["sub"].loc["drop","pr_auc"]:.3f}로 {pct_drop:.1f}%({abs(d_drop):.4f}) 떨어졌고 '
                     f'95% 신뢰구간도 분리됐습니다 — 이 데이터에서 국적은 실제로 유의한 신호입니다. '
                     f'그래서 \'완전 삭제\'가 아니라 차별 광학을 제거하면서 신호를 보존하는 절충을 택합니다."')
        lines.append("")
        lines.append(f'2. "그 절충이 \'내국인(PRT) 여부\' 이진 피처 하나로의 대체입니다 '
                     f'(PR-AUC {s["sub"].loc["is_domestic","pr_auc"]:.3f}, WITH 대비 {pct_dom:.1f}%·CI 겹침으로 사실상 무손실). '
                     f'국적별 OHE가 만드는 \'다국적 차별\' 광학을 없애고, 동시에 \'top10을 전기간으로 정한\' 누수(A-2)까지 '
                     f'소멸시킵니다 — 성능·윤리·누수를 한 수로 정리합니다."')
    lines.append("")
    lines.append("---")
    lines.append(f"_생성: src/country_ablation.py (boot={n_boot}, seed={SEED}) | results/country_ablation.csv 동반_")
    lines.append("")

    report = "\n".join(lines)
    out_md = DOCS / "country_ablation_result.md"
    out_md.write_text(report, encoding="utf-8")
    print(f"[산출물] {out_md}")

    # ── 콘솔 핵심 요약 ──────────────────────────────────────────────────────
    print("\n" + "=" * 64)
    print("핵심 요약")
    print("=" * 64)
    for model_name in models:
        s2 = summary[model_name]
        print(f"[{model_name}]  WITH={s2['base']:.4f}  "
              f"DROP={s2['sub'].loc['drop','pr_auc']:.4f}({s2['deltas']['drop']:+.4f})  "
              f"is_domestic={s2['sub'].loc['is_domestic','pr_auc']:.4f}({s2['deltas']['is_domestic']:+.4f})")
    print("=" * 64)


if __name__ == "__main__":
    main()
