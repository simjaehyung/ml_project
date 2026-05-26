"""
Reveal.js HTML → PPTX (playwright screenshot 방식)
v13.html 11슬라이드를 Chromium으로 렌더링 → PNG → python-pptx 삽입
실행: /c/Users/jhsim/miniconda3/python src/html_to_pptx.py
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from pptx import Presentation
from pptx.util import Inches

# ── 경로 ─────────────────────────────────────────────────────────────────────
ROOT     = Path("c:/Users/jhsim/Erica261/M.L/projects/07_Hotel_DSS")
HTML     = ROOT / "presentations" / "Hotel No-Show DSS v13.html"
OUT_PPTX = ROOT / "presentations" / "Hotel_No-Show_DSS_v13.pptx"
IMG_DIR  = ROOT / "presentations" / "_slide_screenshots_v13"

SLIDE_N  = 11
W_PX, H_PX = 1280, 720      # Reveal.js 기본 해상도
SCALE    = 2                 # 레티나 2× → PNG 2560×1440

# PPTX 16:9 — 13.33" × 7.5"
PPTX_W = Inches(13.33)
PPTX_H = Inches(7.5)

# ── 발표자 노트 ──────────────────────────────────────────────────────────────
NOTES = {
    1:  "타이틀. Hotel No-Show DSS — 취소 예측 기반 의사결정 지원 시스템. 팀: 심재형·이고은·김나리.",
    2:  "문제. City Hotel 취소율 41.7%, Resort 27.8%. 빈방 손실 vs 오버부킹 보상 — 두 방향 모두 비용.",
    3:  "접근법 3단계: ① LightGBM 취소 예측(PR-AUC 0.8189) ② Flexi 풀 라우팅 ③ LLM 협상 시뮬.",
    4:  "시나리오 — 4개 고객 아키타입. LLM 시뮬레이션 1,240회 기반 수락 패턴 분석.",
    5:  "Q1 증거. LightGBM PR-AUC 0.8189, Bootstrap 95% CI [0.8128, 0.8245]. 날씨 ablation +0.0022(비유의). lead_time·country가 상위 피처.",
    6:  "앱 데모. Tab1: 예약 우선순위(SHAP 근거). Tab2: Flexi 라우팅 권장 + 매니저 승인. GDPR Art.22 — 최종 결정은 매니저.",
    7:  "Q2 이유. 협상 이력 데이터가 실제로 존재하지 않음. ABM·설문·통계모델 모두 대안 불가 → LLM이 유일한 합리적 선택.",
    8:  "Q2 결과. B: €91 앵커링 역설(Fisher p<0.000001). D: €46 계단 임계값. RevPAR +81.4%(threshold=0.60, n=50 파일럿).",
    9:  "데이터 인프라. ML①(취소 예측) 완성. 앱 → 협상 로그 → ML②(수락 예측). Cold Start: D €46·B ≤€91 LLM 디폴트.",
    10: "비전. 데이터 플라이휠 — 사용할수록 이 호텔 전용 패턴으로 보정. LLM은 브릿지, ML②가 대체.",
    11: "클로징. RevPAR +81%(threshold=0.60 파일럿). 범위: 취소 예측 엔진 + 재배치 보상 두뇌. PMS·결제·OTA 연동은 범위 외.",
}


def screenshot_slides():
    IMG_DIR.mkdir(exist_ok=True)
    file_url = HTML.as_uri()
    print(f"HTML: {HTML.name}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": W_PX, "height": H_PX},
            device_scale_factor=SCALE,
        )
        page = ctx.new_page()

        print("Loading…")
        page.goto(file_url, wait_until="networkidle", timeout=60000)
        time.sleep(3)

        # Reveal.js — 트랜지션/자동재생 끄기
        page.evaluate("""() => {
            if (!window.Reveal) return;
            Reveal.configure({ transition:'none', backgroundTransition:'none', autoSlide:0 });
        }""")

        for idx in range(SLIDE_N):
            page.evaluate(f"() => {{ if (window.Reveal) Reveal.slide({idx}); }}")
            time.sleep(0.9)
            # 비디오 일시정지
            page.evaluate("() => { document.querySelectorAll('video').forEach(v=>v.pause()); }")
            time.sleep(0.2)

            out = IMG_DIR / f"slide_{idx+1:02d}.png"
            page.screenshot(path=str(out), full_page=False)
            print(f"  [{idx+1:02d}/{SLIDE_N}] {out.name}")

        ctx.close()
        browser.close()
    print()


def build_pptx():
    prs = Presentation()
    prs.slide_width  = PPTX_W
    prs.slide_height = PPTX_H
    blank = prs.slide_layouts[6]

    for i in range(1, SLIDE_N + 1):
        img = IMG_DIR / f"slide_{i:02d}.png"
        if not img.exists():
            print(f"  SKIP slide {i} (image not found)")
            continue

        sl = prs.slides.add_slide(blank)
        sl.shapes.add_picture(str(img), left=0, top=0,
                              width=PPTX_W, height=PPTX_H)

        note = NOTES.get(i, "")
        if note:
            sl.notes_slide.notes_text_frame.text = f"[{i:02d}/{SLIDE_N}] {note}"

        print(f"  [{i:02d}/{SLIDE_N}] added")

    prs.save(str(OUT_PPTX))
    mb = OUT_PPTX.stat().st_size / 1_048_576
    print(f"\nSaved: {OUT_PPTX.name}  ({mb:.1f} MB)")


if __name__ == "__main__":
    print("=== Step 1: Screenshot ===")
    screenshot_slides()
    print("=== Step 2: Build PPTX ===")
    build_pptx()
    print("Done!")
