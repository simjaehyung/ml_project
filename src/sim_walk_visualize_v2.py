"""
src/sim_walk_visualize_v2.py
Walk 협상 시뮬레이션 — 정교한 시각화 v2.1

추가 API 비용 없이 기존 + 보완 실험 결과 통합.
개선 포인트:
  1. Clopper-Pearson 95% CI 신뢰구간 밴드
  2. 오퍼 금액 -> 숙박비 대비 % 정규화 (아키타입 간 직접 비교 가능)
  3. D(nohint) 보완 포인트 추가 (33/37/42) -> 로지스틱 피팅 정밀화
  4. hint有/無 비교 서브플롯 (방법론 개선 근거)
  5. B 앵커링 역설 서브플롯 (Ceiling Artifact 아님, 앵커 효과 확인)

실행:
  python src/sim_walk_visualize_v2.py
"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from scipy.stats import beta as beta_dist
from scipy.optimize import curve_fit
from pathlib import Path

matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False

ROOT    = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

# ── 공통 상수 ─────────────────────────────────────────────────────────────────
MULTS_BASE = np.array([0.26, 0.42, 0.60, 0.74, 0.90])
N40        = np.array([40,   40,   40,   40,   40  ])

# ── D 아키타입 — 기존 5포인트 + 보완 3포인트 (총 8포인트) ──────────────────────
# room_cost = adr(55) × nights(2) = 110
D_MULTS_ALL  = np.array([0.26, 0.30, 0.34, 0.38, 0.42, 0.60, 0.74, 0.90])
D_RATES_ALL  = np.array([0.00, 0.00, 0.00, 0.125, 1.00, 0.975, 1.00, 1.00])
D_OFFERS_ALL = np.array([29,   33,   37,   42,    46,   66,    81,   99  ])
D_N_ALL      = np.array([40,   40,   40,   40,    40,   40,    40,   40  ])

# hint有 (1차 실험 — 방법론 오염 버전, 5포인트만)
D_HINT_RATE  = np.array([0.00, 0.00, 0.00, 0.00, 0.95])
D_OFFERS_5   = np.array([29,   46,   66,   81,   99  ])  # 기존 5포인트 오퍼

# ── A 아키타입 (기존 5포인트) ─────────────────────────────────────────────────
# room_cost = adr(120) × nights(2) = 240 (실측 오퍼로 역산)
A_RATES  = np.array([1.00, 1.00, 1.00, 1.00, 1.00])
A_OFFERS = np.array([62,  101,  144,  178,  216 ])

# ── C 아키타입 (기존 5포인트) ─────────────────────────────────────────────────
C_RATES  = np.array([0.00, 0.00, 0.00, 0.00, 0.00])
C_OFFERS = np.array([143,  231,  330,  407,  495 ])

# ── B 아키타입 — 기존 5포인트 + 보완 3포인트 (총 8포인트) ──────────────────────
# room_cost = adr(95) × nights(2) = 190, ceiling = 190 × 0.60 = 114
# 기존: €49(65%), €80(100%), €114(0%), €141(0%), €171(0%)
# 보완: €91(100%), €99(0%), €106(0%)
B_OFFERS_ALL = np.array([49,   80,   91,   99,   106,  114,  141,  171 ])
B_RATES_ALL  = np.array([0.65, 1.00, 1.00, 0.00, 0.00, 0.00, 0.00, 0.00])
B_N_ALL      = np.array([40,   40,   40,   40,   40,   40,   40,   40  ])
B_MULTS_ALL  = B_OFFERS_ALL / 190.0


# ── 통계 함수 ─────────────────────────────────────────────────────────────────
def cp_ci(rates: np.ndarray, n: np.ndarray, alpha: float = 0.05):
    """Clopper-Pearson 95% 신뢰구간."""
    lo, hi = [], []
    for r, ni in zip(rates, n):
        k = int(round(r * ni))
        lo.append(beta_dist.ppf(alpha / 2, k, ni - k + 1) if k > 0 else 0.0)
        hi.append(beta_dist.ppf(1 - alpha / 2, k + 1, ni - k) if k < ni else 1.0)
    return np.array(lo), np.array(hi)


def logistic(x, k, x0):
    return 1.0 / (1.0 + np.exp(-k * (x - x0)))


def fit_logistic(mults, rates):
    try:
        popt, _ = curve_fit(logistic, mults, rates, p0=[30, 0.40], maxfev=8000)
        return popt
    except Exception:
        return None


# ── Figure: 1행 3열 ───────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(18, 5.8))
fig.suptitle(
    "Walk 협상 시뮬레이션 결과  (Sonnet 4.6, n = 40 / 구간)",
    fontsize=13, fontweight="bold",
)

x_smooth = np.linspace(0.22, 0.95, 400)


# ── 서브플롯 1: A / D(nohint, 8포인트) / C 비교 ─────────────────────────────
ax1 = axes[0]
ax1.set_title("Claim 2 — 아키타입별 수락률\n(오퍼 = 숙박비 대비 %)", fontsize=10.5)

archetypes_main = [
    ("A — 비즈니스 솔로", MULTS_BASE,    A_RATES,      N40,       A_OFFERS, "#2980b9", False),
    ("D — 예산형 OTA (hint 제거)", D_MULTS_ALL, D_RATES_ALL, D_N_ALL, D_OFFERS_ALL, "#e67e22", True),
    ("C — 가족",          MULTS_BASE,    C_RATES,      N40,       C_OFFERS, "#c0392b", False),
]

for label, mults, rates, ns, offers, color, do_logistic in archetypes_main:
    lo, hi = cp_ci(rates, ns)
    ax1.fill_between(mults * 100, lo * 100, hi * 100, alpha=0.12, color=color)
    ax1.plot(mults * 100, rates * 100, "o", color=color, markersize=6, zorder=5)
    ax1.plot(mults * 100, rates * 100, "-", color=color, linewidth=2.0, label=label)

    if do_logistic:
        popt = fit_logistic(mults, rates)
        if popt is not None:
            k, x0 = popt
            y_fit = logistic(x_smooth, k, x0) * 100
            ax1.plot(x_smooth * 100, y_fit,
                     "--", color=color, linewidth=1.5, alpha=0.55)
            thresh = x0 * 100
            ax1.axvline(thresh, color=color, linestyle=":", linewidth=1.2, alpha=0.4)
            ax1.annotate(
                f"50% 수락 추정\n약 숙박비의 {thresh:.0f}%\n(약 {thresh/100 * 110:.0f})",
                xy=(thresh, 50),
                xytext=(thresh + 2, 32),
                fontsize=8, color=color,
                arrowprops=dict(arrowstyle="->", color=color, lw=0.8),
            )

# 보완 포인트 강조 (D 새 포인트: 0.30/0.34/0.38)
new_mults = np.array([0.30, 0.34, 0.38])
new_rates = np.array([0.00, 0.00, 0.125])
ax1.scatter(new_mults * 100, new_rates * 100,
            marker="D", s=55, color="#e67e22", zorder=6,
            label="_nolegend_", edgecolors="white", linewidths=0.8)

ax1.axhline(50, color="#bdc3c7", linestyle="--", linewidth=0.8, alpha=0.7)
ax1.text(22.5, 52, "50%", fontsize=8, color="#999")

# 상단 보조 x축 (D 기준 실제 오퍼)
ax2_top = ax1.secondary_xaxis("top")
ax2_top.set_xticks(MULTS_BASE * 100)
ax2_top.set_xticklabels([f"{o}" for o in D_OFFERS_5], fontsize=7.5, color="#e67e22")
ax2_top.set_xlabel("D 기준 오퍼 (EUR, 기존 5포인트)", fontsize=8, color="#e67e22")

ax1.set_xlabel("보상금 / 숙박비 (%)", fontsize=10)
ax1.set_ylabel("수락률 (%)", fontsize=10)
ax1.set_xlim(21, 95)
ax1.set_ylim(-8, 118)
ax1.set_xticks(MULTS_BASE * 100)
ax1.set_xticklabels([f"{int(m*100)}%" for m in MULTS_BASE])
ax1.legend(fontsize=8.5, loc="center left")
ax1.grid(True, alpha=0.22)
ax1.text(0.97, 0.04, "◆ = 보완 포인트 (n=40)",
         transform=ax1.transAxes, ha="right", fontsize=7.5, color="#e67e22")


# ── 서브플롯 2: D hint有 vs hint無 (기존 5포인트 기준) ───────────────────────
ax2 = axes[1]
ax2.set_title("D 아키타입: Normative Hint 제거 효과\n(방법론 수정 전후)", fontsize=10.5)

D_NOHINT_5 = D_RATES_ALL[[0, 4, 5, 6, 7]]  # 기존 5포인트만 (mults 0.26/0.42/0.60/0.74/0.90)

x = np.arange(len(D_OFFERS_5))
w = 0.36

lo_h, hi_h = cp_ci(D_HINT_RATE, N40)
ax2.bar(x - w / 2, D_HINT_RATE * 100, w,
        label="1차 (hint 有, 방법론 오염)", color="#95a5a6",
        yerr=[(D_HINT_RATE - lo_h) * 100, (hi_h - D_HINT_RATE) * 100],
        capsize=4, error_kw={"linewidth": 1.2})

lo_n, hi_n = cp_ci(D_NOHINT_5, N40)
ax2.bar(x + w / 2, D_NOHINT_5 * 100, w,
        label="2차 (hint 無, 방법론 수정)", color="#e67e22",
        yerr=[(D_NOHINT_5 - lo_n) * 100, (hi_n - D_NOHINT_5) * 100],
        capsize=4, error_kw={"linewidth": 1.2})

for i, (rh, rn) in enumerate(zip(D_HINT_RATE, D_NOHINT_5)):
    diff = (rn - rh) * 100
    if abs(diff) > 2:
        ax2.annotate(
            f"+{diff:.0f}%p",
            xy=(x[i] + w / 2, rn * 100 + hi_n[i] * 100 - rn * 100 + 4),
            ha="center", fontsize=8.5,
            color="#e67e22", fontweight="bold",
        )

ax2.set_xticks(x)
ax2.set_xticklabels([f"EUR{o}" for o in D_OFFERS_5])
ax2.set_xlabel("초기 오퍼 (EUR)", fontsize=10)
ax2.set_ylabel("수락률 (%)", fontsize=10)
ax2.set_ylim(0, 130)
ax2.legend(fontsize=9)
ax2.grid(True, alpha=0.22, axis="y")
ax2.text(0.5, 0.97,
         "Horton & Argyle 2023: normative hint -> LLM 판단 유도 -> 제거 필요",
         transform=ax2.transAxes, ha="center", va="top",
         fontsize=7.8, color="#7f8c8d",
         bbox=dict(boxstyle="round,pad=0.3", fc="#f8f9fa", ec="#ddd", alpha=0.8))


# ── 서브플롯 3: B 앵커링 역설 ───────────────────────────────────────────────
ax3 = axes[2]
ax3.set_title("B 아키타입: 앵커링 역설 확인\n(높은 초기 오퍼 -> 협상 결렬)", fontsize=10.5)

B_COLOR = "#8e44ad"
B_COLOR_NEW = "#6c3483"

lo_b, hi_b = cp_ci(B_RATES_ALL, B_N_ALL)

# 색상 구분: 기존 포인트 vs 보완 포인트
B_IS_NEW = np.array([False, False, True, True, True, False, False, False])

ax3.fill_between(B_OFFERS_ALL, lo_b * 100, hi_b * 100,
                 alpha=0.10, color=B_COLOR)
ax3.plot(B_OFFERS_ALL, B_RATES_ALL * 100,
         "-", color=B_COLOR, linewidth=2.0, label="B — 레저 커플")

# 기존 포인트
ax3.scatter(B_OFFERS_ALL[~B_IS_NEW], B_RATES_ALL[~B_IS_NEW] * 100,
            marker="o", s=50, color=B_COLOR, zorder=5, label="기존 포인트")
# 보완 포인트
ax3.scatter(B_OFFERS_ALL[B_IS_NEW], B_RATES_ALL[B_IS_NEW] * 100,
            marker="D", s=60, color=B_COLOR_NEW, zorder=6,
            label="보완 포인트 (Ceiling 이하)", edgecolors="white", linewidths=0.8)

# 전환 구간 강조
ax3.axvspan(91, 99, alpha=0.08, color="#e74c3c")
ax3.axvline(91, color="#27ae60", linestyle="--", linewidth=1.2, alpha=0.6)
ax3.axvline(99, color="#e74c3c", linestyle="--", linewidth=1.2, alpha=0.6)
ax3.text(95, 55, "전환\n구간", ha="center", fontsize=8, color="#e74c3c", fontweight="bold")

# Ceiling 표시
ax3.axvline(114, color="#7f8c8d", linestyle=":", linewidth=1.5, alpha=0.6)
ax3.text(116, 80, "Ceiling\n(EUR114)", fontsize=8, color="#7f8c8d")

# 앵커링 설명 화살표
ax3.annotate("EUR91: R1 역제안 EUR140\n-> R2=EUR114 -> 수락",
             xy=(91, 100), xytext=(55, 88),
             fontsize=7.5, color="#27ae60",
             arrowprops=dict(arrowstyle="->", color="#27ae60", lw=0.9))
ax3.annotate("EUR99: R1 역제안 EUR150\n-> R2=EUR114 -> 거절",
             xy=(99, 0), xytext=(60, 15),
             fontsize=7.5, color="#e74c3c",
             arrowprops=dict(arrowstyle="->", color="#e74c3c", lw=0.9))

ax3.set_xlabel("초기 오퍼 (EUR)", fontsize=10)
ax3.set_ylabel("수락률 (%)", fontsize=10)
ax3.set_xlim(40, 185)
ax3.set_ylim(-8, 118)
ax3.legend(fontsize=8.5, loc="center right")
ax3.grid(True, alpha=0.22)
ax3.text(0.5, 0.97,
         "높은 초기 오퍼 -> 고객 앵커 상승 -> Ceiling에 묶인 R2가 상대적으로 낮아 보임",
         transform=ax3.transAxes, ha="center", va="top",
         fontsize=7.5, color="#7f8c8d",
         bbox=dict(boxstyle="round,pad=0.3", fc="#f8f9fa", ec="#ddd", alpha=0.8))


plt.tight_layout()
out = RESULTS / "walk_accept_v2.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"저장 완료: {out}")
plt.show()
