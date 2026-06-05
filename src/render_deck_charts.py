# -*- coding: utf-8 -*-
"""
render_deck_charts.py — 최종발표 덱용 차트 6종 재렌더 (Editorial Instrument 스타일)

design_23 "Editorial Instrument" 디자인 토큰을 matplotlib에 이식한다.
웜페이퍼 배경 + 잉크 텍스트 + 시그니처 인디고/데이터 앰버 + 위험 3색.
hairline 그리드, mono tabular 숫자, 빔프로젝터 가독성(큰 폰트·높은 대비).

출력: presentations/charts/*.png
  c_models.png       5모델 PR-AUC (0.820 vs Dummy 0.387, 2.1배)
  c_growth.png       fixed vs walk-forward (rigor·드리프트, 전환=아티팩트)
  c_shap.png         상위 피처 (country 1위)
  c_overbooking.png  세그먼트 오버부킹 % by lead_time (8~30%)
  c_negotiation.png  walk_sim D €46 step + B 앵커링 역설
  c_ablation.png     country WITH/DROP/is_domestic (-5%/-1%)

데이터 정전: results/*.csv, baseline_results.md, shap_report.md
수치 lock: design_23 §G / design_24
"""
import sys, io, csv, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Rectangle, FancyArrowPatch
from matplotlib.lines import Line2D

# ---- UTF-8 stdout ----
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
OUTDIR = os.path.join(ROOT, "presentations", "charts")
os.makedirs(OUTDIR, exist_ok=True)

# ============================================================
# Editorial Instrument 디자인 토큰
# ============================================================
PAPER      = "#F4F2EC"   # 슬라이드 바닥
PAPER_DEEP = "#ECE9E1"
SURFACE    = "#FBFAF6"   # 차트 플레이트(near-white)
INK        = "#16151A"   # 1차 텍스트
INK2       = "#4B4A52"   # 2차 텍스트
INK3       = "#8B8A90"   # 캡션·축 라벨
FAINT      = "#B7B3A8"
RULE       = "#D8D4C8"   # 1px 헤어라인
RULE_SOFT  = "#E6E2D8"   # 가장 약한 디바이더 / 마이너 그리드
RULE_HARD  = "#C9C4B7"   # 축 프레임
SIGNATURE  = "#1B3A8F"   # editorial indigo (유일 주액센트)
SIG2       = "#2E55C2"
AMBER      = "#C8821E"   # signal amber (데이터 강조)
AMBER_INK  = "#8A5A0F"
RISK_HI    = "#B23A2E"   # brick — 고위험/취소
RISK_MID   = "#B8862B"   # ochre — 중
RISK_LO    = "#3F7A52"   # forest — 저/정상
LR_COL     = "#6F6E74"   # graphite — 지는 모델
DUMMY_COL  = "#B8B3A6"   # neutral

# ---- 폰트: 한글 Malgun Gothic, 숫자 mono(Consolas) ----
def _has(name):
    try:
        return any(f.name == name for f in fm.fontManager.ttflist)
    except Exception:
        return False

KO = "Malgun Gothic" if _has("Malgun Gothic") else "DejaVu Sans"
MONO = "Consolas" if _has("Consolas") else "DejaVu Sans Mono"
USE_KO = _has("Malgun Gothic")  # 한글 폰트 실패 시 영문 라벨로 통일

plt.rcParams.update({
    "font.family": KO,
    "font.size": 16,
    "axes.unicode_minus": False,
    "figure.facecolor": PAPER,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": PAPER,
    "text.color": INK,
    "axes.edgecolor": RULE_HARD,
    "axes.labelcolor": INK2,
    "xtick.color": INK2,
    "ytick.color": INK2,
})

def L(ko, en):
    """한글폰트 사용 가능하면 ko, 아니면 en."""
    return ko if USE_KO else en

def mono(ax_or_txt):
    pass

def style_axes(ax, hide_spines=("top", "right")):
    """Editorial Instrument 축 규율: hairline 그리드, 위/오른쪽 spine 제거."""
    for s in hide_spines:
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(RULE_HARD)
        ax.spines[s].set_linewidth(1.4)
    ax.tick_params(length=4, width=1.0, colors=INK2, labelsize=15)
    ax.set_axisbelow(True)
    ax.grid(axis="y", color=RULE_SOFT, linewidth=1.0, zorder=0)
    ax.set_facecolor(SURFACE)

def src_caption(fig, text):
    # footnote 분리 배치 (bottom 여백은 각 차트에서 subplots_adjust로 확보)
    fig.text(0.012, 0.012, text, fontsize=11, color=INK3, ha="left", va="bottom")

def save(fig, name):
    path = os.path.join(OUTDIR, name)
    # bbox_inches tight 사용 안 함 — figure 좌표 footnote와 축라벨 겹침 방지
    fig.savefig(path, dpi=160, facecolor=PAPER)
    plt.close(fig)
    return path

paths = {}

# ============================================================
# 1. c_models.png — 5모델 PR-AUC (0.820 vs Dummy 0.387, 2.1배)
# ============================================================
def chart_models():
    # baseline_results.md 값 + 성장곡선 full LightGBM 0.820 lock
    models = ["Dummy", "Logistic\nRegression", "Random\nForest", "XGBoost", "LightGBM"]
    vals   = [0.387, 0.7818, 0.7785, 0.8053, 0.820]
    cols   = [DUMMY_COL, LR_COL, "#9A9890", "#7A8AAE", SIGNATURE]

    fig, ax = plt.subplots(figsize=(11.0, 6.8))
    fig.subplots_adjust(top=0.84, bottom=0.16, left=0.085, right=0.97)
    x = np.arange(len(models))
    bars = ax.bar(x, vals, width=0.62, color=cols, zorder=3,
                  edgecolor="none")
    # 끝점 값 라벨 (mono tabular)
    for xi, v in zip(x, vals):
        ax.text(xi, v + 0.012, f"{v:.3f}", ha="center", va="bottom",
                fontfamily=MONO, fontsize=17,
                color=SIGNATURE if v == 0.820 else INK,
                fontweight="bold" if v == 0.820 else "normal")

    # Dummy 기준선 점선
    ax.axhline(0.387, color=DUMMY_COL, linewidth=1.4, linestyle=(0, (2, 4)), zorder=2)

    style_axes(ax)
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=14.5, color=INK2)
    ax.set_ylim(0, 0.92)
    ax.set_yticks(np.arange(0, 0.91, 0.2))
    ax.set_yticklabels([f"{t:.1f}" for t in np.arange(0, 0.91, 0.2)], fontfamily=MONO, fontsize=14)
    ax.set_ylabel("PR-AUC", fontsize=17, color=INK2)

    # 2.1배 콜아웃 (앵커=LightGBM)
    ax.annotate(
        L("Dummy 대비 2.1배", "2.1x over Dummy"),
        xy=(4, 0.820), xytext=(2.55, 0.895),
        fontsize=15.5, color=AMBER_INK, fontfamily=KO,
        fontweight="bold", ha="left", va="center",
        arrowprops=dict(arrowstyle="-", color=AMBER, lw=1.6,
                        connectionstyle="arc3,rad=-0.15")
    )
    # serif italic 시그니처 1개
    ax.set_title(L("취소 예측 — 5모델 비교", "Cancellation model — five baselines"),
                 fontsize=21, color=INK, fontweight="bold", loc="left", pad=14)
    ax.text(0.0, 1.005, "LightGBM", transform=ax.transAxes, fontsize=15,
            color=SIGNATURE, fontstyle="italic", fontfamily="Georgia",
            ha="left", va="bottom")

    src_caption(fig, L(
        "실데이터 — Kaggle 호텔 예약 2년(City 리스본·Resort 알가르브) · test 40,687행 · PR-AUC(메인) · baseline_results.md / 성장곡선 full",
        "Real data — Kaggle hotel bookings, 2yr (City Lisbon / Resort Algarve) · test n=40,687 · PR-AUC · baseline_results.md"))
    paths["c_models.png"] = save(fig, "c_models.png")

# ============================================================
# 2. c_growth.png — fixed vs walk-forward (rigor·드리프트)
#    전환은 fixed-test 아티팩트로 demote 표기
# ============================================================
def read_growth_fixed():
    rows = list(csv.DictReader(open(os.path.join(RESULTS, "growth_curve_agg.csv"))))
    cum = [r for r in rows if r["window"] == "cumulative"]
    out = {}
    for r in cum:
        m = r["model"]
        if m not in ("LightGBM", "Logistic Regression", "Dummy"):
            continue
        out.setdefault(m, []).append((int(r["n_train"]), float(r["pr_auc"]),
                                      r["ci_low"], r["ci_high"]))
    for m in out:
        out[m].sort()
    return out

def read_growth_wf():
    rows = list(csv.DictReader(open(os.path.join(RESULTS, "growth_curve_wf_agg.csv"))))
    out = {}
    for r in rows:
        m = r["model"]
        if m not in ("LightGBM", "Logistic Regression"):
            continue
        out.setdefault(m, []).append((int(r["n_train"]), float(r["pr_auc"]),
                                      r["ci_low"], r["ci_high"]))
    for m in out:
        out[m].sort()
    return out

def chart_growth():
    fixed = read_growth_fixed()
    wf = read_growth_wf()

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.6, 6.8), sharey=True,
                                   gridspec_kw=dict(wspace=0.06))
    fig.subplots_adjust(top=0.86, bottom=0.16, left=0.07, right=0.985)

    # ---- 좌: fixed-test 성장곡선 ----
    def plot_fixed(ax):
        lgb = fixed["LightGBM"]; lr = fixed["Logistic Regression"]
        nx_lgb = np.array([a for a, *_ in lgb]); vy_lgb = np.array([b for _, b, *_ in lgb])
        nx_lr  = np.array([a for a, *_ in lr]);  vy_lr  = np.array([b for _, b, *_ in lr])
        # CI 밴드 (LightGBM)
        lo = np.array([float(c) if c else np.nan for *_, c, _ in lgb])
        hi = np.array([float(c) if c else np.nan for *_2, c in lgb])
        ax.fill_between(nx_lgb, lo, hi, color=SIGNATURE, alpha=0.13, zorder=2, lw=0)
        ax.plot(nx_lr, vy_lr, color=LR_COL, lw=3.0, zorder=3,
                label=L("Logistic Regression", "Logistic Regression"))
        ax.plot(nx_lgb, vy_lgb, color=SIGNATURE, lw=4.0, zorder=4,
                label="LightGBM")
        ax.axhline(0.387, color=DUMMY_COL, lw=1.6, linestyle=(0, (2, 5)), zorder=2)
        # 전환점 W (아티팩트 표기) — n~53,615
        ax.axvline(53615, color=INK3, lw=1.4, linestyle=(0, (1, 4)), zorder=2)
        ax.scatter([53615], [0.799], s=70, facecolor="white",
                   edgecolor=INK3, linewidth=2.2, zorder=6)
        ax.text(53615, 0.452, L("W ~ 5.4만 건\n(전환 - fixed-test 아티팩트)",
                                 "W ~ 53,615\n(crossover - fixed-test artifact)"),
                fontsize=11.5, color=INK3, ha="center", va="bottom", fontstyle="italic")
        # 끝점 라벨
        ax.text(nx_lgb[-1], vy_lgb[-1] + 0.013, "LightGBM · 0.820",
                fontfamily=MONO, fontsize=13.5, color=SIGNATURE, ha="right", va="bottom")
        ax.text(nx_lr[-1], vy_lr[-1] - 0.028, "LR · 0.78",
                fontfamily=MONO, fontsize=13, color=LR_COL, ha="right", va="top")
        style_axes(ax)
        ax.set_title(L("① 고정 test (rigor)", "(1) Fixed test (rigor)"),
                     fontsize=16, color=INK, fontweight="bold", loc="left", pad=8)
        ax.set_xlabel(L("누적 학습량 (건)", "Cumulative training size"), fontsize=14, color=INK2)
        ax.set_xlim(0, 82000)
        ax.set_xticks([0, 20000, 40000, 60000, 80000])
        ax.set_xticklabels(["0", "20k", "40k", "60k", "80k"], fontfamily=MONO, fontsize=13)

    # ---- 우: walk-forward (드리프트) ----
    def plot_wf(ax):
        lgb = wf["LightGBM"]; lr = wf["Logistic Regression"]
        nx_lgb = np.array([a for a, *_ in lgb]); vy_lgb = np.array([b for _, b, *_ in lgb])
        nx_lr  = np.array([a for a, *_ in lr]);  vy_lr  = np.array([b for _, b, *_ in lr])
        lo = np.array([float(c) for *_, c, _ in lgb]); hi = np.array([float(c) for *_2, c in lgb])
        ax.fill_between(nx_lgb, lo, hi, color=SIGNATURE, alpha=0.13, zorder=2, lw=0)
        ax.plot(nx_lr, vy_lr, color=LR_COL, lw=3.0, marker="o", ms=6,
                mfc="white", mec=LR_COL, mew=1.8, zorder=3)
        ax.plot(nx_lgb, vy_lgb, color=SIGNATURE, lw=4.0, marker="o", ms=6,
                mfc="white", mec=SIGNATURE, mew=2.0, zorder=4)
        # LGB 강건 콜아웃 (곡선 중앙 아래 빈 공간)
        ax.text(45000, 0.74, L("LightGBM 강건", "LightGBM robust"),
                fontfamily=KO, fontsize=12.5, color=SIGNATURE, ha="center", va="top",
                fontweight="bold")
        # 드리프트 음영(마지막 구간 하락)
        ax.annotate(L("드리프트 - 노이즈 1.4~2.2x\n실배포 시 재선정", "drift - noise 1.4-2.2x\nreselect on deploy"),
                    xy=(88384, 0.841), xytext=(40000, 0.62),
                    fontsize=11.5, color=AMBER_INK, ha="left", va="center", fontstyle="italic",
                    arrowprops=dict(arrowstyle="-", color=AMBER, lw=1.5,
                                    connectionstyle="arc3,rad=-0.2"))
        style_axes(ax, hide_spines=("top", "right", "left"))
        ax.spines["left"].set_visible(False)
        ax.tick_params(left=False)
        ax.set_title(L("② walk-forward (드리프트)", "(2) Walk-forward (drift)"),
                     fontsize=16, color=INK, fontweight="bold", loc="left", pad=8)
        ax.set_xlabel(L("누적 학습량 (건)", "Cumulative training size"), fontsize=14, color=INK2)
        ax.set_xlim(0, 95000)
        ax.set_xticks([0, 40000, 80000])
        ax.set_xticklabels(["0", "40k", "80k"], fontfamily=MONO, fontsize=13)

    plot_fixed(axL)
    plot_wf(axR)
    axL.set_ylim(0.35, 0.95)
    axL.set_yticks(np.arange(0.4, 0.91, 0.1))
    axL.set_yticklabels([f"{t:.1f}" for t in np.arange(0.4, 0.91, 0.1)], fontfamily=MONO, fontsize=13)
    axL.set_ylabel("PR-AUC", fontsize=16, color=INK2)

    # 범례
    handles = [
        Line2D([], [], color=SIGNATURE, lw=4, label="LightGBM"),
        Line2D([], [], color=LR_COL, lw=3, label="Logistic Regression"),
        Line2D([], [], color=DUMMY_COL, lw=1.6, linestyle=(0, (2, 5)), label="Dummy · 0.387"),
    ]
    axL.legend(handles=handles, loc="lower right", fontsize=12.5, frameon=False,
               handlelength=1.8, borderpad=0.4)

    fig.suptitle(L("두 평가법 = rigor — 전환은 아티팩트, LightGBM은 강건",
                   "Two evaluations = rigor — crossover is an artifact, LightGBM robust"),
                 fontsize=21, color=INK, fontweight="bold", x=0.07, ha="left", y=0.965)
    fig.text(0.012, 0.012, L(
        "실데이터 성장곡선 · Bootstrap 95% CI · growth_curve_agg.csv / growth_curve_wf_agg.csv · 하이쿠 미사용",
        "Real-data growth curves · Bootstrap 95% CI · growth_curve_(wf_)agg.csv"),
        fontsize=11, color=INK3, ha="left", va="bottom")
    paths["c_growth.png"] = save(fig, "c_growth.png")

# ============================================================
# 3. c_shap.png — 상위 피처 (country 1위)
# ============================================================
def chart_shap():
    # shap_report.md LightGBM Top 8 (mean|SHAP|), country 1위
    feats = [
        ("country (PRT)", 1.0639, True),
        ("required_car_parking_spaces", 0.6797, False),
        ("total_of_special_requests", 0.6435, False),
        ("lead_time", 0.5312, False),
        ("previous_cancellations", 0.3941, False),
        ("market_segment (Online TA)", 0.3712, False),
        ("customer_type (Transient)", 0.2562, False),
        ("adr", 0.2525, False),
    ]
    feats = feats[::-1]  # barh 아래→위
    labels = [f[0] for f in feats]
    vals = [f[1] for f in feats]
    cols = [SIGNATURE if f[2] else LR_COL for f in feats]

    fig, ax = plt.subplots(figsize=(11.8, 6.8))
    fig.subplots_adjust(top=0.84, bottom=0.16, left=0.27, right=0.97)
    y = np.arange(len(feats))
    ax.barh(y, vals, height=0.62, color=cols, zorder=3)
    for yi, v, f in zip(y, vals, feats):
        ax.text(v + 0.018, yi, f"{v:.3f}", va="center", ha="left",
                fontfamily=MONO, fontsize=14,
                color=SIGNATURE if f[2] else INK2,
                fontweight="bold" if f[2] else "normal")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=14, color=INK2)
    # country 라벨 강조
    ax.get_yticklabels()[-1].set_color(SIGNATURE)
    ax.get_yticklabels()[-1].set_fontweight("bold")

    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(RULE_HARD); ax.spines["left"].set_linewidth(1.4)
    ax.spines["bottom"].set_color(RULE_HARD); ax.spines["bottom"].set_linewidth(1.4)
    ax.set_axisbelow(True)
    ax.grid(axis="x", color=RULE_SOFT, linewidth=1.0, zorder=0)
    ax.set_facecolor(SURFACE)
    ax.tick_params(length=4, width=1.0, colors=INK2)
    ax.set_xlim(0, 1.28)
    ax.set_xticks(np.arange(0, 1.21, 0.3))
    ax.set_xticklabels([f"{t:.1f}" for t in np.arange(0, 1.21, 0.3)], fontfamily=MONO, fontsize=13)
    ax.set_xlabel(L("평균 |SHAP| 기여도", "mean |SHAP| contribution"), fontsize=15, color=INK2)

    ax.set_title(L("취소 위험 — 피처 기여도 (LightGBM)", "Cancellation drivers — SHAP (LightGBM)"),
                 fontsize=21, color=INK, fontweight="bold", loc="left", pad=14)
    ax.text(0.0, 1.005, "country", transform=ax.transAxes, fontsize=15,
            color=SIGNATURE, fontstyle="italic", fontfamily="Georgia", ha="left", va="bottom")
    # 윤리 핀 (하위 막대들 우측의 완전 빈 공간에 배치)
    ax.annotate(L("국적 1위 → 행동 차등엔 배제 (윤리)", "country #1 -> excluded from differential action"),
                xy=(1.0639, len(feats) - 1.40), xytext=(0.70, len(feats) - 5.4),
                fontsize=12.5, color=AMBER_INK, ha="left", va="center", fontstyle="italic",
                arrowprops=dict(arrowstyle="-", color=AMBER, lw=1.5,
                                connectionstyle="arc3,rad=0.30"))

    src_caption(fig, L(
        "TreeSHAP · LightGBM · test 3,000행 샘플 · shap_report.md (mean|SHAP|)",
        "TreeSHAP · LightGBM · 3,000 test sample · shap_report.md"))
    paths["c_shap.png"] = save(fig, "c_shap.png")

# ============================================================
# 4. c_overbooking.png — 세그먼트 오버부킹 % by lead_time
# ============================================================
def chart_overbooking():
    rows = list(csv.DictReader(open(os.path.join(RESULTS, "overbooking_policy_segments.csv"))))
    bands = [r["lt_band"] for r in rows]
    obk = [float(r["overbook_buffer_pct"]) for r in rows]      # 8.4 ~ 30.2
    pred = [float(r["pred_noshow"]) * 100 for r in rows]       # 예측 노쇼율
    actual = [float(r["actual_cancel"]) * 100 for r in rows]   # 실제 취소율

    band_lbl = {
        "<=7d": "<=7d", "8-30d": "8-30d", "31-90d": "31-90d",
        "91-180d": "91-180d", ">180d": ">180d",
    }
    labels = [band_lbl.get(b, b) for b in bands]

    fig, ax = plt.subplots(figsize=(11.8, 6.8))
    fig.subplots_adjust(top=0.84, bottom=0.16, left=0.075, right=0.98)
    x = np.arange(len(bands))
    # 권장 오버부킹 % 막대 (시그니처, 위험도↑ 그라데이션 대신 단색 + amber 끝점)
    bars = ax.bar(x, obk, width=0.56, color=SIGNATURE, zorder=3)
    bars[0].set_color(SIG2)  # 가장 낮은 버퍼 약간 밝게
    for xi, v in zip(x, obk):
        ax.text(xi, v + 0.5, f"{v:.0f}%", ha="center", va="bottom",
                fontfamily=MONO, fontsize=17, color=SIGNATURE, fontweight="bold")

    # 예측 노쇼율(라인, 비율 관계 강조)
    ax.plot(x, pred, color=AMBER, lw=2.6, marker="D", ms=8, mfc="white",
            mec=AMBER, mew=2.0, zorder=5, label=L("모델 예측 노쇼율", "predicted no-show %"))
    # 실제 취소율(점선, 보정 맥락)
    ax.plot(x, actual, color=INK3, lw=1.8, marker="o", ms=6, mfc="white",
            mec=INK3, mew=1.6, linestyle=(0, (3, 3)), zorder=4,
            label=L("실제 취소율", "actual cancel %"))

    style_axes(ax)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=15, color=INK2, fontfamily=MONO)
    ax.set_ylim(0, 56)
    ax.set_yticks(np.arange(0, 51, 10))
    ax.set_yticklabels([f"{t:.0f}" for t in np.arange(0, 51, 10)], fontfamily=MONO, fontsize=13)
    ax.set_ylabel("%", fontsize=16, color=INK2)
    ax.set_xlabel(L("예약 리드타임 세그먼트", "lead_time segment"), fontsize=15, color=INK2)

    ax.legend(loc="upper left", fontsize=12.5, frameon=False, handlelength=1.8)

    ax.set_title(L("오버부킹 비율 = 세그먼트 정책 (리드타임별 8~30%)",
                   "Overbooking rate = segment policy (8-30% by lead_time)"),
                 fontsize=20, color=INK, fontweight="bold", loc="left", pad=14)
    ax.text(0.0, 1.006, "ratio", transform=ax.transAxes, fontsize=15,
            color=SIGNATURE, fontstyle="italic", fontfamily="Georgia", ha="left", va="bottom")
    # 한계비용=한계수익 메모 (우측 중단 빈 공간)
    ax.text(0.985, 0.60, L("한계비용 = 한계수익\n→ 세그먼트별 최적 버퍼", "marginal cost = marginal revenue"),
            transform=ax.transAxes, fontsize=11.5, color=INK3, ha="right", va="top", fontstyle="italic")

    src_caption(fig, L(
        "실데이터 세그먼트 정책 · test 40,687행 · overbooking_policy_segments.csv · 결정권은 매니저",
        "Real-data segment policy · test n=40,687 · overbooking_policy_segments.csv"))
    paths["c_overbooking.png"] = save(fig, "c_overbooking.png")

# ============================================================
# 5. c_negotiation.png — walk_sim D €46 step + B 앵커링 역설
# ============================================================
def chart_negotiation():
    # D_nohint: offer -> accept_rate (step), €46 첫 100% 수락
    D = list(csv.DictReader(open(os.path.join(RESULTS, "walk_sim_D_nohint_summary.csv"))))
    B = list(csv.DictReader(open(os.path.join(RESULTS, "walk_sim_B_fixed_summary.csv"))))
    d_off = [float(r["initial_offer"]) for r in D]
    d_acc = [float(r["accept_rate"]) for r in D]
    b_off = [float(r["initial_offer"]) for r in B]
    b_acc = [float(r["accept_rate"]) for r in B]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.6, 6.8),
                                   gridspec_kw=dict(wspace=0.22))
    fig.subplots_adjust(top=0.84, bottom=0.15, left=0.06, right=0.985)

    # ---- 좌: D 수락 step function ----
    axL.step(d_off, d_acc, where="post", color=SIGNATURE, lw=3.4, zorder=4)
    axL.scatter(d_off, d_acc, s=64, facecolor="white", edgecolor=SIGNATURE,
                linewidth=2.2, zorder=5)
    # €46 임계 마커
    axL.axvline(46, color=AMBER, lw=1.6, linestyle=(0, (2, 4)), zorder=2)
    axL.scatter([46], [1.0], s=130, facecolor=AMBER, edgecolor="white",
                linewidth=2.2, zorder=6)
    axL.annotate(L("€46 = 첫 100% 수락\n~ ADR 42% (D 아키타입)",
                   "€46 = first 100% accept\n~ 42% of ADR"),
                 xy=(46, 1.0), xytext=(52, 0.62),
                 fontsize=13, color=AMBER_INK, ha="left", va="center", fontweight="bold",
                 arrowprops=dict(arrowstyle="-", color=AMBER, lw=1.6,
                                 connectionstyle="arc3,rad=0.2"))
    style_axes(axL)
    axL.set_xlim(20, 105)
    axL.set_ylim(-0.05, 1.12)
    axL.set_yticks([0, 0.5, 1.0])
    axL.set_yticklabels(["0%", "50%", "100%"], fontfamily=MONO, fontsize=13)
    axL.set_xticks([29, 46, 66, 81, 99])
    axL.set_xticklabels(["€29", "€46", "€66", "€81", "€99"], fontfamily=MONO, fontsize=13)
    axL.set_xlabel(L("walk 보상 오퍼(€)", "walk compensation offer (€)"), fontsize=14, color=INK2)
    axL.set_ylabel(L("수락률", "accept rate"), fontsize=14, color=INK2)
    axL.set_title(L("D · Budget OTA — €46 step", "D · Budget OTA — €46 step"),
                  fontsize=16, color=INK, fontweight="bold", loc="left", pad=8)

    # ---- 우: B 앵커링 역설 ----
    bcols = [RISK_LO if a >= 0.5 else RISK_HI for a in b_acc]
    bx = np.arange(len(b_off))
    axR.bar(bx, b_acc, width=0.5, color=bcols, zorder=3)
    for xi, off, a in zip(bx, b_off, b_acc):
        axR.text(xi, a + 0.03, f"{a*100:.0f}%", ha="center", va="bottom",
                 fontfamily=MONO, fontsize=15, color=INK, fontweight="bold")
    axR.set_xticks(bx)
    axR.set_xticklabels([f"€{o:.0f}" for o in b_off], fontfamily=MONO, fontsize=14)
    style_axes(axR)
    axR.set_ylim(0, 1.18)
    axR.set_yticks([0, 0.5, 1.0])
    axR.set_yticklabels(["0%", "50%", "100%"], fontfamily=MONO, fontsize=13)
    axR.set_xlabel(L("초기 오퍼(€)", "initial offer (€)"), fontsize=14, color=INK2)
    axR.set_title(L("B · Leisure Couple — 앵커링 역설", "B · Leisure Couple — anchoring paradox"),
                  fontsize=16, color=INK, fontweight="bold", loc="left", pad=8)
    axR.annotate(L("더 높은 오퍼인데 수락↓\n(앵커링, p < 1e-6)",
                   "higher offer, lower accept\n(anchoring, p < 1e-6)"),
                 xy=(1, 0.0), xytext=(0.55, 0.6),
                 fontsize=12.5, color=RISK_HI, ha="left", va="center", fontstyle="italic",
                 arrowprops=dict(arrowstyle="-", color=RISK_HI, lw=1.5,
                                 connectionstyle="arc3,rad=-0.25"))

    fig.suptitle(L("협상 데이터 수집 — 세상에 없던 (위험도→오퍼→수락) 튜플",
                   "Negotiation data collection — (risk -> offer -> accept) tuples that don't exist"),
                 fontsize=20, color=INK, fontweight="bold", x=0.06, ha="left", y=0.955)
    fig.text(0.012, 0.012, L(
        "LLM 손님 시뮬 · n=40 runs/오퍼 · walk_sim_D_nohint / B_fixed_summary.csv · 정량 앵커는 실데이터, 시뮬은 수집 시연",
        "LLM guest sim · n=40/offer · walk_sim_D_nohint / B_fixed_summary.csv"),
        fontsize=11, color=INK3, ha="left", va="bottom")
    paths["c_negotiation.png"] = save(fig, "c_negotiation.png")

# ============================================================
# 6. c_ablation.png — country WITH/DROP/is_domestic (-5%/-1%)
# ============================================================
def chart_ablation():
    rows = list(csv.DictReader(open(os.path.join(RESULTS, "country_ablation.csv"))))
    lgb = {r["variant"]: r for r in rows if r["model"] == "LightGBM"}
    order = ["with", "drop", "is_domestic"]
    lbl = {
        "with": L("국적 포함\n(WITH)", "WITH country"),
        "drop": L("국적 제거\n(DROP)", "DROP country"),
        "is_domestic": L("국적→내/외국\n(is_domestic)", "is_domestic"),
    }
    vals = [float(lgb[v]["pr_auc"]) for v in order]
    los  = [float(lgb[v]["ci_low"]) for v in order]
    his  = [float(lgb[v]["ci_high"]) for v in order]
    cols = [SIGNATURE, RISK_HI, RISK_MID]

    fig, ax = plt.subplots(figsize=(11.2, 6.8))
    fig.subplots_adjust(top=0.84, bottom=0.18, left=0.085, right=0.97)
    x = np.arange(len(order))
    yerr = [[v - lo for v, lo in zip(vals, los)], [hi - v for v, hi in zip(vals, his)]]
    bars = ax.bar(x, vals, width=0.5, color=cols, zorder=3)
    ax.errorbar(x, vals, yerr=yerr, fmt="none", ecolor=INK2, elinewidth=1.6,
                capsize=7, capthick=1.6, zorder=5)
    for xi, v in zip(x, vals):
        ax.text(xi, his[order.index(order[xi])] + 0.004 if False else v + 0.001, "",
                ha="center")
    # 값 라벨 (CI 위)
    for xi, v, hi in zip(x, vals, his):
        ax.text(xi, hi + 0.004, f"{v:.4f}", ha="center", va="bottom",
                fontfamily=MONO, fontsize=15.5, color=INK, fontweight="bold")

    # WITH 기준선
    ax.axhline(vals[0], color=SIGNATURE, lw=1.2, linestyle=(0, (2, 5)), zorder=2, alpha=0.6)

    # Δ 콜아웃 (막대 옆 빈 공간 — x축 라벨과 분리)
    ax.annotate(L("-5.0% (CI 분리)\n성능 비용 측정됨", "-5.0% (CI separated)"),
                xy=(1, vals[1] + 0.004), xytext=(1.32, 0.7905),
                fontsize=12.5, color=RISK_HI, ha="left", va="center", fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=RISK_HI, lw=1.6,
                                connectionstyle="arc3,rad=-0.25"))
    ax.annotate(L("-1.0% (CI 겹침)\n대안 검토", "-1.0% (CI overlaps)"),
                xy=(2, vals[2] + 0.004), xytext=(1.36, 0.823),
                fontsize=12.5, color=AMBER_INK, ha="left", va="center", fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=AMBER, lw=1.5,
                                connectionstyle="arc3,rad=0.25"))

    style_axes(ax)
    ax.set_xticks(x)
    ax.set_xticklabels([lbl[v] for v in order], fontsize=14.5, color=INK2)
    ax.set_ylim(0.74, 0.835)
    ax.set_yticks(np.arange(0.75, 0.831, 0.02))
    ax.set_yticklabels([f"{t:.2f}" for t in np.arange(0.75, 0.831, 0.02)], fontfamily=MONO, fontsize=13)
    ax.set_ylabel("PR-AUC", fontsize=16, color=INK2)

    ax.set_title(L("국적 피처 윤리 — 제거 시 성능 비용 (LightGBM)",
                   "Country feature ethics — cost of removal (LightGBM)"),
                 fontsize=20, color=INK, fontweight="bold", loc="left", pad=14)
    ax.text(0.0, 1.006, "reckoning", transform=ax.transAxes, fontsize=15,
            color=SIGNATURE, fontstyle="italic", fontfamily="Georgia", ha="left", va="bottom")

    src_caption(fig, L(
        "실데이터 country ablation · Bootstrap 95% CI · country_ablation.csv · 한계를 먼저 드러내는 게 신뢰",
        "Real-data country ablation · Bootstrap 95% CI · country_ablation.csv"))
    paths["c_ablation.png"] = save(fig, "c_ablation.png")

# ============================================================
if __name__ == "__main__":
    chart_models()
    chart_growth()
    chart_shap()
    chart_overbooking()
    chart_negotiation()
    chart_ablation()
    print("FONT_KO=%s  FONT_MONO=%s  USE_KO=%s" % (KO, MONO, USE_KO))
    for k in ["c_models.png", "c_growth.png", "c_shap.png",
              "c_overbooking.png", "c_negotiation.png", "c_ablation.png"]:
        print("OK", paths.get(k))
