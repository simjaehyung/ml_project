"""
정보 분리 원칙 시각화 — 손님 화면 vs 호텔 내부(DSS)
Dev A 검증(2026-06-02)에서 확인한 실제 PMS→DSS 응답 데이터 기반.

발표 포인트:
  - 손님은 "위험점수"를 절대 못 봄 → "Flexi 할인"만 봄
  - 호텔(매니저)만 위험점수·SHAP을 봄 → 최종 승인
  - 이 구조가 법률 방어(계약 불이행 차단·사전 동의·매니저 승인)와 직결

output: presentations/info_separation_diagram.png
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

fig = plt.figure(figsize=(13, 7.3), dpi=150)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 130)
ax.set_ylim(0, 73)
ax.axis("off")

# 색
C_GUEST   = "#2e86de"   # 손님(파랑)
C_HOTEL   = "#c0392b"   # 호텔 내부(빨강)
C_BG_G    = "#eaf2fb"
C_BG_H    = "#fdecea"
C_TEXT    = "#222222"
C_GRAY    = "#777777"

# ─── 제목 ───
ax.text(65, 69, "정보 분리 원칙 — 같은 예약, 다른 화면",
        ha="center", fontsize=19, weight="bold", color=C_TEXT)
ax.text(65, 65, "손님은 '위험점수'를 절대 보지 못한다 · 호텔만 본다",
        ha="center", fontsize=11, color=C_GRAY)

# ─── 중앙 예약 (공통 입력) ───
ax.add_patch(FancyBboxPatch((48, 55), 34, 6, boxstyle="round,pad=0.4",
                            facecolor="#f4f4f4", edgecolor="#bbbbbb", linewidth=1))
ax.text(65, 58, "예약 1건  ·  포르투갈 손님 · 12월 City Hotel 3박",
        ha="center", fontsize=10.5, weight="bold", color=C_TEXT)

# 화살표 양쪽으로
arrow_l = FancyArrowPatch((55, 55), (32, 49), arrowstyle="-|>", mutation_scale=18,
                          color="#999999", linewidth=1.5)
arrow_r = FancyArrowPatch((75, 55), (98, 49), arrowstyle="-|>", mutation_scale=18,
                          color="#999999", linewidth=1.5)
ax.add_patch(arrow_l)
ax.add_patch(arrow_r)

# ─── 좌측: 손님 화면 ───
ax.add_patch(FancyBboxPatch((4, 6), 52, 43, boxstyle="round,pad=0.6",
                            facecolor=C_BG_G, edgecolor=C_GUEST, linewidth=2))
ax.text(30, 45, "[ 손님이 보는 화면 ]", ha="center",
        fontsize=13, weight="bold", color=C_GUEST)
ax.plot([8, 52], [42.5, 42.5], color=C_GUEST, linewidth=0.6, alpha=0.4)

guest_lines = [
    ("예약 확인서  PMS-535BBE", "bold", C_TEXT, 11),
    ("", "n", C_TEXT, 4),
    ("객실      Double Room", "n", C_TEXT, 10.5),
    ("요금제    Flexi Rate (체크인 7일 전 무료취소)", "n", C_TEXT, 10.5),
    ("할인      14.3% 적용", "bold", C_GUEST, 11),
    ("1박 요금  €100  →  총 €257", "n", C_TEXT, 10.5),
    ("식사      Bed & Breakfast", "n", C_TEXT, 10.5),
    ("상태      Confirmed (확정)", "bold", "#27ae60", 11),
]
y = 39
for text, w, c, fs in guest_lines:
    weight = "bold" if w == "bold" else "normal"
    ax.text(8, y, text, fontsize=fs, color=c,
            weight=weight, family="Malgun Gothic")
    y -= 3.4

# 손님이 못 보는 것 강조
ax.add_patch(FancyBboxPatch((7, 7.5), 46, 4.5, boxstyle="round,pad=0.3",
                            facecolor="#ffffff", edgecolor=C_GUEST,
                            linewidth=1, linestyle="--"))
ax.text(30, 9.7, "X  위험점수 · SHAP · Flexi 풀 분류 — 안 보임",
        ha="center", fontsize=9.5, color=C_GUEST, style="italic")

# ─── 우측: 호텔 내부(DSS) 화면 ───
ax.add_patch(FancyBboxPatch((74, 6), 52, 43, boxstyle="round,pad=0.6",
                            facecolor=C_BG_H, edgecolor=C_HOTEL, linewidth=2))
ax.text(100, 45, "[ 호텔 내부 · DSS 화면 ]", ha="center",
        fontsize=13, weight="bold", color=C_HOTEL)
ax.plot([78, 122], [42.5, 42.5], color=C_HOTEL, linewidth=0.6, alpha=0.4)

hotel_lines = [
    ("취소 위험 점수   0.94  (HIGH)", "bold", C_HOTEL, 12),
    ("", "n", C_TEXT, 3),
    ("주요 위험 요인 (SHAP):", "bold", C_TEXT, 10),
    ("  • 포르투갈 국적        +1.02", "n", C_TEXT, 10),
    ("  • 리드타임 182일       +1.01", "n", C_TEXT, 10),
    ("  • 특별요청 0건         +0.56", "n", C_TEXT, 10),
    ("", "n", C_TEXT, 3),
    ("→ Flexi 풀 라우팅 권장 (할인 16.4%)", "bold", C_HOTEL, 10.5),
]
y = 39
for text, w, c, fs in hotel_lines:
    weight = "bold" if w == "bold" else "normal"
    ax.text(78, y, text, fontsize=fs, color=c, weight=weight)
    y -= 3.3

# 매니저 승인 강조 박스
ax.add_patch(FancyBboxPatch((77, 7.5), 46, 4.8, boxstyle="round,pad=0.3",
                            facecolor="#ffffff", edgecolor=C_HOTEL, linewidth=1.2))
ax.text(100, 9.9, "O  최종 결정은 매니저 승인 (GDPR Art.22)",
        ha="center", fontsize=9.5, weight="bold", color=C_HOTEL)

# ─── 하단 메시지 ───
ax.text(65, 2.3,
        "AI는 '권장', 결정은 '사람' · 손님 사전 동의 + 매니저 승인 = 계약 불이행 사후 통보 차단",
        ha="center", fontsize=10, color=C_GRAY, style="italic")

out = Path(__file__).parent / "info_separation_diagram.png"
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print(f"✓ 저장: {out}")
