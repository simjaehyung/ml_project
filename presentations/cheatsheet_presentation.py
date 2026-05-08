"""
발표용 수치 치트시트 PNG 생성 (A4 portrait, 300 dpi)
- 출력: docs/cheatsheet_presentation.png
- 한국어 폰트: Malgun Gothic (Windows 기본)
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# 한국어 폰트 설정
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

# A4 portrait (210 x 297 mm) → 8.27 x 11.69 inch
fig = plt.figure(figsize=(8.27, 11.69), dpi=300)
ax = fig.add_axes([0.05, 0.02, 0.90, 0.96])
ax.set_xlim(0, 100)
ax.set_ylim(0, 140)
ax.axis("off")

# 색상 팔레트
C_TITLE = "#16140f"
C_HEAD = "#a85432"
C_BODY = "#16140f"
C_GRAY = "#666666"
C_HILITE = "#c4391f"

# 폰트 크기 (A4에 맞춰 작게)
FS_TITLE = 13
FS_SUBTITLE = 7
FS_SECTION = 8.5
FS_TABLE_HEAD = 6.5
FS_TABLE_BODY = 6.5
FS_NOTE = 6.0

# 줄 간격 단위 (1단위 = ax y축 1)
ROW_H = 2.4

# y 좌표 (위에서부터 내려감)
y = 138

# ─── 헤더 ───
ax.text(50, y, "발표용 수치 치트시트",
        ha="center", fontsize=FS_TITLE, weight="bold", color=C_TITLE)
y -= 2.8
ax.text(50, y, "호텔 No-Show DSS · Week 1 누수 후보 검증 결과 요약",
        ha="center", fontsize=FS_SUBTITLE, color=C_GRAY)
y -= 1.5
ax.plot([0, 100], [y, y], color=C_GRAY, linewidth=0.4)
y -= 3


def section(title, num):
    """섹션 헤더 그리기"""
    global y
    ax.text(0, y, f"{num}. {title}", fontsize=FS_SECTION, weight="bold", color=C_HEAD)
    y -= ROW_H


def kvrow(label, value, x_label=2, x_value=42, hilite=False):
    """라벨 - 값 한 줄"""
    global y
    ax.text(x_label, y, label, fontsize=FS_TABLE_BODY, color=C_BODY)
    ax.text(x_value, y, value, fontsize=FS_TABLE_BODY,
            weight="bold", color=C_HILITE if hilite else C_BODY)
    y -= ROW_H


def table(headers, rows, col_x, hilite_col=None):
    """간단 표: 헤더 1줄 + 행들. col_x = 컬럼 시작 x좌표 리스트"""
    global y
    # 헤더
    for i, h in enumerate(headers):
        ax.text(col_x[i], y, h, fontsize=FS_TABLE_HEAD,
                weight="bold", color=C_GRAY)
    y -= 0.6
    ax.plot([col_x[0], 99], [y, y], color=C_GRAY, linewidth=0.3)
    y -= 1.5
    # 본문
    for row in rows:
        for i, cell in enumerate(row):
            is_hi = (hilite_col is not None and i == hilite_col)
            ax.text(col_x[i], y, str(cell), fontsize=FS_TABLE_BODY,
                    weight="bold" if is_hi else "normal",
                    color=C_HILITE if is_hi else C_BODY)
        y -= ROW_H
    y -= 0.6


def gap(h=1.2):
    global y
    y -= h


# ─── 1. 데이터 전체 ───
section("데이터 전체", 1)
kvrow("전체 행 × 컬럼", "119,390 × 32", hilite=True)
kvrow("전체 취소율", "37.04%", hilite=True)
kvrow("도착일 범위", "2015.07 ~ 2017.08 (약 26개월)")
kvrow("City Hotel", "79,330건 / 취소율 41.7%")
kvrow("Resort Hotel", "40,060건 / 취소율 27.8%")
gap()

# ─── 2. Train / Test 분할 ───
section("Train / Test 분할 (페이지 6)", 2)
kvrow("Train", "2015.07 ~ 2017.02 (약 20개월)")
kvrow("Test", "2017.03 ~ 2017.08 (마지막 6개월)", hilite=True)
gap()

# ─── 3. 확정 누수 검증 [L1, L2] ───
section("확정 누수 검증 결과 [페이지 9]", 3)
ax.text(2, y, "[L1] 31번 reservation_status × is_canceled — 정의상 동치 위반",
        fontsize=FS_TABLE_BODY, color=C_BODY)
y -= ROW_H
ax.text(4, y, "위반 행:",
        fontsize=FS_TABLE_BODY, color=C_BODY)
ax.text(20, y, "0 / 119,390 (0.0000%) → 완벽 일치",
        fontsize=FS_TABLE_BODY, weight="bold", color=C_HILITE)
y -= ROW_H
ax.text(4, y, "분포: Check-Out 75,166 / Canceled 43,017 / No-Show 1,207",
        fontsize=FS_NOTE, color=C_GRAY)
y -= ROW_H + 0.4

ax.text(2, y, "[L2] 32번 reservation_status_date - arrival_date (일 단위)",
        fontsize=FS_TABLE_BODY, color=C_BODY)
y -= ROW_H
table(
    ["그룹", "n", "min", "median", "max", "도착일 이후 비율"],
    [
        ["정상 체크인", "75,166", "0", "+3", "+69", "100.00%"],
        ["취소·노쇼", "44,224", "-526", "-54", "0", "4.72%"],
    ],
    col_x=[4, 28, 40, 50, 62, 74],
    hilite_col=5,
)

# ─── 4. 시점 어긋난 컬럼 [Y1, Y2] ───
section("시점 어긋난 컬럼 검증", 4)
ax.text(2, y, "[Y1] 21번 assigned_room_type ≠ reserved_room_type 불일치율",
        fontsize=FS_TABLE_BODY, color=C_BODY)
y -= ROW_H
table(
    ["그룹", "n", "불일치율"],
    [
        ["정상 체크인", "75,166", "18.78%"],
        ["취소·노쇼", "44,224", "1.81%"],
        ["전체", "119,390", "12.49% (14,917건)"],
    ],
    col_x=[4, 30, 50],
    hilite_col=2,
)

ax.text(2, y, "[Y2] 22번 booking_changes (변경 있음 vs 없음)",
        fontsize=FS_TABLE_BODY, color=C_BODY)
y -= ROW_H
table(
    ["그룹", "n", "취소율"],
    [
        ["변경 없음 (=0)", "101,314", "40.85%"],
        ["변경 있음 (≥1)", "18,076", "15.67%"],
        ["차이", "—", "+25.18%p"],
    ],
    col_x=[4, 30, 50],
    hilite_col=2,
)

# ─── 5. 행 단위 누수 검증 불가 [Y3] ───
section("행 단위 누수 검증 불가 컬럼 [Y3]", 5)
ax.text(2, y, "18번 previous_cancellations (0 vs ≥1)",
        fontsize=FS_TABLE_BODY, color=C_BODY)
y -= ROW_H
table(
    ["그룹", "n", "취소율"],
    [
        ["=0", "112,906", "33.91%"],
        ["≥1", "6,484", "91.64%"],
        ["차이", "—", "+57.73%p"],
    ],
    col_x=[4, 30, 50],
    hilite_col=2,
)

ax.text(2, y, "19번 previous_bookings_not_canceled (0 vs ≥1)",
        fontsize=FS_TABLE_BODY, color=C_BODY)
y -= ROW_H
table(
    ["그룹", "n", "취소율"],
    [
        ["=0", "115,770", "38.03%"],
        ["≥1", "3,620", "5.52%"],
        ["차이", "—", "-32.51%p"],
    ],
    col_x=[4, 30, 50],
    hilite_col=2,
)

ax.text(2, y, "※ 정의 어긋남: is_repeated_guest=0인데 previous_*≥1인 행 약 2,674개 존재",
        fontsize=FS_NOTE, color=C_HILITE, style="italic")
y -= ROW_H + 0.3

# ─── 6. 결측 처리 안건 [Y4] ───
section("결측 처리 안건 [Y4]", 6)
table(
    ["컬럼", "결측률", "결측 그룹 취소율", "비결측 그룹", "차이"],
    [
        ["24번 agent (여행사 ID)", "13.69%", "24.66%", "39.00%", "-14.34%p"],
        ["25번 company (법인 ID)", "94.31%", "38.22%", "17.52%", "+20.70%p"],
    ],
    col_x=[2, 35, 50, 70, 85],
    hilite_col=4,
)

# ─── 7. 평가 지표 ───
section("평가 지표", 7)
kvrow("더미 모델(\"전부 정상\") accuracy", "약 63% (= 1 - 37.04%)", hilite=True)
kvrow("클래스 비율 (정상 : 취소)", "약 63 : 37")
kvrow("메인 / 보조 지표", "PR-AUC / F1", hilite=True)
kvrow("임계값 검토 후보", "약 0.35 (Week 3 결정 예정)")
gap(1.5)

# ─── 핵심 5개 강조 박스 ───
y_box_top = y
y -= 1
ax.text(0, y, "★ 빠르게 답해야 할 핵심 5개",
        fontsize=FS_SECTION, weight="bold", color=C_HILITE)
y -= ROW_H

key5 = [
    "① 18.78%  — 정상 체크인 건 중 21번 assigned_room_type ≠ reserved_room_type 불일치율",
    "② 91.64% vs 33.91%  — 18번 previous_cancellations ≥1 / =0 그룹 취소율 (차이 약 57%p)",
    "③ 100%  — 32번 reservation_status_date가 정상건에서 도착일 이후로 박힌 비율",
    "④ 0건 / 119,390  — 31번 reservation_status × is_canceled 동치 위반",
    "⑤ 37.04% / 63%  — 전체 취소율 / 더미 baseline accuracy",
]
for line in key5:
    ax.text(2, y, line, fontsize=FS_TABLE_BODY, color=C_BODY)
    y -= ROW_H

# 박스 그리기
box_height = y_box_top - y
ax.add_patch(Rectangle(
    (-0.5, y - 0.5), 101, box_height + 0.5,
    fill=False, edgecolor=C_HILITE, linewidth=0.8,
))
y -= 1

# ─── 푸터 ───
y_footer = 0.5
ax.text(50, y_footer,
        "출처: docs/leakage_candidates.md + notebooks/02_leakage_check.py · 2026-05-03 검증",
        ha="center", fontsize=FS_NOTE, color=C_GRAY, style="italic")

# 저장 — 스크립트가 docs/ 폴더에 있으므로 같은 폴더에 PNG 생성
out_path = Path(__file__).parent / "cheatsheet_presentation.png"
out_path.parent.mkdir(exist_ok=True)
plt.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")
plt.close()
print(f"✓ 저장 완료: {out_path}")
print(f"  크기: A4 portrait (8.27 × 11.69 inch, 300 dpi)")
