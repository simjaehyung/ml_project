"""
make_week3_html.py
Week 3 미팅용 HTML 슬라이드 — 밝은 디자인 + SHAP 결과 + 용어 설명 슬라이드
python src/make_week3_html.py
"""
import base64
from pathlib import Path

ROOT = Path(__file__).parent.parent
RES  = ROOT / "results"

def b64(fname):
    p = RES / fname
    if not p.exists():
        return ""
    with open(p, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

img_pr       = b64("pr_curve_all.png")
img_shap_cmp = b64("shap_comparison.png")
img_shap_bee = b64("shap_lgbm_beeswarm.png")
img_shap_wf  = b64("shap_waterfall.png")

# ─── CSS ──────────────────────────────────────────────────────────────────────
CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family:'Segoe UI','Malgun Gothic',Apple SD Gothic Neo,sans-serif;
  background:#F0F2F5; color:#1C2333; overflow:hidden;
}
.deck { width:100vw; height:100vh; position:relative; }
.slide {
  position:absolute; inset:0;
  display:flex; flex-direction:column; justify-content:center; align-items:center;
  padding:46px 80px;
  opacity:0; pointer-events:none;
  transition:opacity .3s ease;
}
.slide.active { opacity:1; pointer-events:all; }

/* ── nav ── */
.nav { position:fixed; bottom:22px; right:28px; display:flex; gap:8px; z-index:100; }
.nav button {
  background:#fff; border:1px solid #D0D7DE; color:#555;
  padding:7px 16px; border-radius:6px; cursor:pointer; font-size:14px;
  box-shadow:0 1px 3px rgba(0,0,0,.08);
}
.nav button:hover { background:#EEF2FF; color:#3451D1; }
.progress { position:fixed; bottom:28px; left:50%; transform:translateX(-50%);
  font-size:13px; color:#8899AA; letter-spacing:.5px; }

/* ── typography ── */
.tag {
  font-size:11px; font-weight:700; letter-spacing:2.5px; text-transform:uppercase;
  color:#3451D1; background:#EEF2FF; padding:4px 12px; border-radius:20px;
  margin-bottom:16px; flex-shrink:0;
}
.tag.glossary {
  color:#7C3AED; background:#F5F3FF;
}
h1 { font-size:46px; font-weight:800; line-height:1.2; text-align:center; color:#0F172A; }
h2 { font-size:31px; font-weight:700; margin-bottom:6px; color:#0F172A; }
h3 { font-size:18px; color:#64748B; margin-bottom:16px; font-weight:400; }
.sub { font-size:16px; color:#64748B; margin-top:10px; text-align:center; line-height:1.8; }
.accent { color:#3451D1; }
.green  { color:#166534; }
.orange { color:#C05621; }
.red    { color:#C62828; }
.yellow { color:#B45309; }
code {
  background:#EEF2FF; padding:1px 7px; border-radius:4px;
  font-size:12px; color:#3451D1; font-family:'Cascadia Code','Consolas',monospace;
}

/* ── glossary slide bg ── */
.glossary-slide { background:#FDFAFF; }
.glossary-slide::before {
  content:''; position:absolute; inset:0;
  background:linear-gradient(135deg,#F5F3FF 0%,#EDE9FE 100%);
  z-index:-1;
}
.glo-card {
  background:#fff; border:2px solid #DDD6FE; border-radius:16px;
  padding:32px 40px; width:100%; max-width:860px;
  box-shadow:0 4px 24px rgba(124,58,237,.1);
}
.glo-header { display:flex; align-items:center; gap:14px; margin-bottom:20px; }
.glo-icon  { font-size:36px; }
.glo-title { font-size:22px; font-weight:800; color:#4C1D95; }
.glo-body  { font-size:15px; color:#374151; line-height:1.9; }
.glo-example {
  background:#F5F3FF; border-left:4px solid #7C3AED;
  border-radius:0 8px 8px 0; padding:12px 18px; margin-top:16px; font-size:14px; color:#4C1D95;
}
.glo-vs { display:flex; gap:16px; margin-top:16px; }
.glo-vs-box {
  flex:1; border-radius:10px; padding:16px; font-size:13px; line-height:1.75;
}

/* ── table ── */
table { width:100%; border-collapse:collapse; font-size:15px; }
th { background:#F8FAFC; color:#64748B; font-weight:600; padding:10px 14px;
  text-align:left; border-bottom:2px solid #E2E8F0; font-size:13px; }
td { padding:11px 14px; border-bottom:1px solid #F1F5F9; }
tr:last-child td { border-bottom:none; }
tr.winner { background:#F0FDF4; }
tr.winner td { font-weight:600; color:#14532D; }
.badge { display:inline-block; padding:2px 10px; border-radius:20px;
  font-size:11px; font-weight:700; }
.badge-green  { background:#DCFCE7; color:#16A34A; }
.badge-gray   { background:#F1F5F9; color:#94A3B8; }
.badge-blue   { background:#EEF2FF; color:#3451D1; }
.badge-orange { background:#FFF7ED; color:#C05621; }
.badge-red    { background:#FEF2F2; color:#C62828; }
.badge-purple { background:#F5F3FF; color:#7C3AED; }

/* ── cards ── */
.cards { display:flex; gap:18px; width:100%; }
.card { flex:1; background:#fff; border:1px solid #E2E8F0;
  border-radius:12px; padding:22px 20px; box-shadow:0 1px 4px rgba(0,0,0,.06); }
.card-icon { font-size:26px; margin-bottom:10px; }
.card h4 { font-size:14px; font-weight:700; color:#334155; margin-bottom:8px; }
.card p  { font-size:13px; color:#64748B; line-height:1.75; }
.card ul { padding-left:16px; }
.card ul li { font-size:13px; color:#64748B; line-height:1.9; }
.card.hl { border-color:#818CF8; border-width:2px; }
.card.ok { border-color:#4ADE80; border-width:2px; }

/* ── agenda ── */
.agenda-item { background:#fff; border-left:4px solid #3451D1;
  border-radius:0 10px 10px 0; padding:16px 20px; margin-bottom:12px;
  box-shadow:0 1px 3px rgba(0,0,0,.06); }
.agenda-item.p2 { border-color:#16A34A; }
.agenda-num   { font-size:11px; color:#94A3B8; letter-spacing:1px; margin-bottom:4px; text-transform:uppercase; }
.agenda-title { font-size:17px; font-weight:700; color:#0F172A; }
.agenda-sub   { font-size:13px; color:#64748B; margin-top:4px; }

/* ── out grid ── */
.out-grid { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; width:100%; }
.out-box { background:#fff; border:1px solid #E2E8F0; border-radius:10px; padding:16px;
  box-shadow:0 1px 3px rgba(0,0,0,.05); }
.out-box .num   { font-size:18px; font-weight:800; color:#3451D1; }
.out-box .title { font-size:13px; font-weight:700; color:#334155; margin:5px 0 3px; }
.out-box .desc  { font-size:12px; color:#94A3B8; line-height:1.6; }

/* ── prob rows ── */
.prob-row { display:flex; align-items:flex-start; gap:14px;
  background:#fff; border:1px solid #E2E8F0; border-left:4px solid #EF4444;
  border-radius:10px; padding:16px; margin-bottom:10px;
  box-shadow:0 1px 3px rgba(0,0,0,.04); }
.prob-row.med { border-color:#F97316; }
.prob-row.low { border-color:#EAB308; }
.prob-icon  { font-size:20px; flex-shrink:0; margin-top:1px; }
.prob-title { font-size:14px; font-weight:700; color:#0F172A; margin-bottom:4px; }
.prob-desc  { font-size:13px; color:#64748B; line-height:1.7; }

/* ── two-col ── */
.two-col { display:flex; gap:24px; width:100%; align-items:flex-start; }
.col { flex:1; }
.p2-card { background:#fff; border:1px solid #E2E8F0;
  border-radius:10px; padding:18px; margin-bottom:10px;
  box-shadow:0 1px 3px rgba(0,0,0,.05); }
.p2-header { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
.p2-icon  { font-size:22px; }
.p2-title { font-size:15px; font-weight:700; color:#0F172A; }
.p2-tag   { font-size:10px; padding:2px 9px; border-radius:20px;
  background:#EEF2FF; color:#3451D1; font-weight:700; margin-left:auto; }
.p2-body  { font-size:13px; color:#64748B; line-height:1.8; }

/* ── discuss ── */
.discuss-item { display:flex; gap:14px; align-items:flex-start;
  background:#fff; border:1px solid #E2E8F0;
  border-radius:10px; padding:14px 18px; margin-bottom:8px;
  box-shadow:0 1px 3px rgba(0,0,0,.04); }
.discuss-q     { font-size:15px; font-weight:800; color:#3451D1; flex-shrink:0; min-width:28px; }
.discuss-title { font-size:14px; font-weight:700; color:#1C2333; margin-bottom:3px; }
.discuss-desc  { font-size:12px; color:#64748B; line-height:1.6; }

/* ── meter ── */
.meter-wrap { width:100%; margin-top:12px; }
.meter-label { display:flex; justify-content:space-between; font-size:12px; color:#94A3B8; margin-bottom:6px; }
.meter-bar   { height:12px; background:#F1F5F9; border-radius:6px; overflow:hidden; }
.meter-fill  { height:100%; border-radius:6px;
  background:linear-gradient(90deg,#818CF8,#34D399); }

/* ── shap table ── */
.shap-row { display:flex; align-items:center; gap:10px; padding:7px 0;
  border-bottom:1px solid #F1F5F9; }
.shap-rank { font-size:12px; font-weight:700; color:#94A3B8; width:24px; flex-shrink:0; }
.shap-bar-wrap { flex:1; }
.shap-bar-bg { height:8px; background:#F1F5F9; border-radius:4px; overflow:hidden; }
.shap-bar-fill { height:100%; border-radius:4px; background:linear-gradient(90deg,#818CF8,#6EE7B7); }
.shap-feat { font-size:11.5px; color:#334155; font-family:'Cascadia Code','Consolas',monospace; width:230px; flex-shrink:0; }
.shap-val  { font-size:12px; font-weight:700; color:#3451D1; width:46px; text-align:right; flex-shrink:0; }
.shap-badge { font-size:10px; padding:1px 7px; border-radius:20px; flex-shrink:0; }

/* ── alert ── */
.alert { border-radius:10px; padding:10px 16px; font-size:13px; font-weight:500;
  display:flex; align-items:flex-start; gap:8px; }
.alert-green  { background:#F0FDF4; color:#166534; border:1px solid #BBF7D0; }
.alert-red    { background:#FEF2F2; color:#991B1B; border:1px solid #FECACA; }
.alert-blue   { background:#EEF2FF; color:#3730A3; border:1px solid #C7D2FE; }
.alert-orange { background:#FFF7ED; color:#9A3412; border:1px solid #FED7AA; }

/* ── cover ── */
.cover-bg { position:absolute; inset:0; z-index:-1;
  background:linear-gradient(135deg,#EEF2FF 0%,#F0FDF4 60%,#FFF7ED 100%); }
.cover-card { background:#fff; border-radius:20px; padding:44px 60px;
  box-shadow:0 8px 40px rgba(52,81,209,.12); text-align:center; max-width:740px; }

/* ── divider ── */
.divider-slide .cover-bg {
  background:linear-gradient(135deg,#1E3A8A 0%,#1D4ED8 60%,#0EA5E9 100%); }
.divider-slide h1 { color:#fff; }
.divider-slide .tag { background:rgba(255,255,255,.2); color:#fff; }
.divider-slide .sub { color:rgba(255,255,255,.8); }

/* ── img panel ── */
.img-panel { background:#fff; border:1px solid #E2E8F0; border-radius:12px;
  padding:10px; box-shadow:0 2px 8px rgba(0,0,0,.07); }
"""

# ─── SLIDES HTML ──────────────────────────────────────────────────────────────
SLIDES = """
<!-- ══ 1. 표지 ════════════════════════════════════════════ -->
<div class="slide">
  <div class="cover-bg"></div>
  <div class="cover-card">
    <div class="tag">Hotel No-Show DSS &middot; Week 3 팀 미팅 &middot; 2026-05-12</div>
    <h1 style="font-size:38px; margin-bottom:14px;">
      모델이 만든 숫자,<br>어떻게 읽을 것인가
    </h1>
    <div class="sub">
      심재형 &middot; 이고은 &middot; 김나리<br>
      <strong class="accent">LightGBM PR-AUC 0.8189 확보 &mdash; 오늘 모델 동결</strong>
    </div>
    <div style="display:flex; gap:20px; justify-content:center; margin-top:26px;">
      <div style="text-align:center;">
        <div style="font-size:30px; font-weight:800; color:#3451D1;">0.8189</div>
        <div style="font-size:12px; color:#94A3B8;">LightGBM PR-AUC</div>
      </div>
      <div style="width:1px; background:#E2E8F0;"></div>
      <div style="text-align:center;">
        <div style="font-size:30px; font-weight:800; color:#16A34A;">70.5%</div>
        <div style="font-size:12px; color:#94A3B8;">Dummy 대비 갭 해소</div>
      </div>
      <div style="width:1px; background:#E2E8F0;"></div>
      <div style="text-align:center;">
        <div style="font-size:30px; font-weight:800; color:#0F172A;">5위</div>
        <div style="font-size:12px; color:#94A3B8;">prev_cancel SHAP 순위</div>
      </div>
    </div>
  </div>
</div>

<!-- ══ 2. 안건 ════════════════════════════════════════════ -->
<div class="slide">
  <div class="tag">Agenda</div>
  <h2>오늘 미팅, 두 가지</h2>
  <h3>총 60분 목표</h3>
  <div style="width:100%; max-width:620px; margin-top:4px;">
    <div class="agenda-item">
      <div class="agenda-num">Part 1 &middot; 40분</div>
      <div class="agenda-title">우리 모델, 어디에 있는가?</div>
      <div class="agenda-sub">PR-AUC 결과 해석 &middot; SHAP 분석 &middot; 문제점 진단 &middot; 보완 방향 합의</div>
    </div>
    <div class="agenda-item p2">
      <div class="agenda-num">Part 2 &middot; 20분</div>
      <div class="agenda-title">취소 예측 너머 &mdash; 의미있는 지표 3개</div>
      <div class="agenda-sub">Channel Effective Yield &middot; Booking Quality Score &middot; 음식 낭비 예측</div>
    </div>
  </div>
</div>

<!-- ══ 3. 5모델 결과 ══════════════════════════════════════ -->
<div class="slide">
  <div class="tag">Part 1 &mdash; Model Results</div>
  <h2>5개 모델 비교 결과</h2>
  <h3>테스트셋 40,687행 &middot; 취소율 38.7% &middot; n_estimators=100 (all default)</h3>
  <table>
    <thead><tr><th>#</th><th>모델</th><th>PR-AUC</th><th>F1@0.5</th><th>비고</th></tr></thead>
    <tbody>
      <tr><td style="color:#94A3B8;">0</td><td style="color:#94A3B8;">Dummy (most_frequent)</td>
          <td class="red">0.3870</td><td class="red">0.0000</td>
          <td><span class="badge badge-gray">기준선</span></td></tr>
      <tr><td>1</td><td>Logistic Regression</td>
          <td>0.7818</td><td><strong>0.7073</strong></td><td>C=1, StandardScaler</td></tr>
      <tr><td>2</td><td>Random Forest</td>
          <td>0.7785</td><td>0.6482</td><td>n_estimators=100</td></tr>
      <tr><td>3</td><td>XGBoost</td>
          <td>0.8053</td><td>0.6863</td><td>n_estimators=100</td></tr>
      <tr class="winner"><td>4</td><td><strong>LightGBM &#9733;</strong></td>
          <td><strong>0.8189</strong></td><td>0.6872</td>
          <td><span class="badge badge-green">최종 선정</span></td></tr>
    </tbody>
  </table>
  <div style="display:flex; gap:10px; margin-top:14px; width:100%;">
    <div class="alert alert-green" style="flex:1;">
      &#10003; LightGBM &mdash; XGBoost 대비 +0.0136, 합의 기준(0.01 이상) 충족 &rarr; LightGBM 확정
    </div>
    <div class="alert alert-blue" style="flex:1;">
      &#9432; LR F1(0.707) &gt; LGBM F1(0.687) &mdash; 임계값 0.5 고정 시 LR이 유리. PR-AUC 기준이 옳은 이유는 다음 슬라이드.
    </div>
  </div>
</div>

<!-- ══ 4-a. 용어: Dummy Classifier ═══════════════════════════ -->
<div class="slide glossary-slide">
  <div class="tag glossary">&#128218; 개념 설명</div>
  <div class="glo-card">
    <div class="glo-header">
      <div class="glo-icon">&#129302;</div>
      <div class="glo-title">Dummy Classifier란? &mdash; 왜 PR-AUC 0.387이 나오는가</div>
    </div>
    <div class="glo-body">
      Dummy(most_frequent)는 <strong>아무것도 학습하지 않고 항상 "취소 없음(0)"만 예측</strong>하는 모델이다.<br>
      어떤 예약이 들어와도 무조건 "이 사람은 취소 안 한다"고 말한다.
    </div>
    <div class="glo-vs" style="margin-top:14px;">
      <div class="glo-vs-box" style="background:#FEF2F2; border:1px solid #FECACA; font-size:13px;">
        <strong style="color:#991B1B;">F1@0.5 = 0.000 이유</strong><br><br>
        취소(1)를 한 번도 예측하지 않음<br>
        &rarr; True Positive(TP) = 0<br>
        &rarr; Precision = 0, Recall = 0<br>
        &rarr; F1 = 0
      </div>
      <div class="glo-vs-box" style="background:#FFF7ED; border:1px solid #FED7AA; font-size:13px;">
        <strong style="color:#C05621;">PR-AUC = 0.387 이유</strong><br><br>
        테스트셋 취소율 = 38.7%<br>
        랜덤 예측기의 PR-AUC<br>= <strong>양성 클래스 비율</strong><br>
        0.387 = 이론값과 일치
      </div>
      <div class="glo-vs-box" style="background:#F0FDF4; border:1px solid #BBF7D0; font-size:13px;">
        <strong style="color:#166534;">존재 이유</strong><br><br>
        "이 모델이 아무것도<br>안 한 것보다 나은가?"를<br>증명하는 기준선<br><br>
        LightGBM 0.819<br>= Dummy의 <strong>2.11배</strong>
      </div>
    </div>
    <div class="glo-example">
      &#128161; PR-AUC가 0.387보다만 높으면 "Dummy보다 낫다"는 증명은 된다. 우리 목표는 0.8 이상 &mdash; Dummy와 비교 자체가 의미 없는 수준.
    </div>
  </div>
</div>

<!-- ══ 4-b. 용어: 비고 항목 설명 ══════════════════════════════ -->
<div class="slide glossary-slide">
  <div class="tag glossary">&#128218; 개념 설명</div>
  <div class="glo-card" style="max-width:980px;">
    <div class="glo-header">
      <div class="glo-icon">&#9881;&#65039;</div>
      <div class="glo-title">비고 항목들이 의미하는 것 &mdash; 우리가 아직 결정하지 않은 것들</div>
    </div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:4px;">
      <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:16px;">
        <div style="font-size:12px; font-weight:700; color:#94A3B8; letter-spacing:1px; margin-bottom:8px;">LOGISTIC REGRESSION</div>
        <div style="font-size:13px; color:#334155; line-height:1.9;">
          <code>C=1</code> &mdash; <strong>규제 강도</strong>. C가 클수록 규제 약함(과적합 위험), 작을수록 규제 강함(과소적합 위험). C=1은 sklearn 기본값.<br>
          <span style="color:#64748B;">→ 우리가 최적화한 값이 아님. Phase 2에서 GridSearch 가능.</span><br><br>
          <code>StandardScaler</code> &mdash; <strong>피처 정규화</strong>. LR은 거리 기반 계산이라 adr(0~500)과 lead_time(0~700)의 스케일 차이에 민감함.<br>
          <span style="color:#64748B;">→ 트리 모델(RF·XGB·LGBM)은 분기점 기반이라 스케일 불필요.</span>
        </div>
      </div>
      <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:16px;">
        <div style="font-size:12px; font-weight:700; color:#94A3B8; letter-spacing:1px; margin-bottom:8px;">RANDOM FOREST / XGBOOST / LIGHTGBM</div>
        <div style="font-size:13px; color:#334155; line-height:1.9;">
          <code>n_estimators=100</code> &mdash; <strong>트리 개수</strong>. 100개의 결정 트리를 만들어 다수결. 많을수록 정확하지만 느림.<br>
          <span style="color:#64748B;">→ 100은 빠른 기준선용. 최적값은 보통 300~1000. Phase 2 튜닝 대상.</span><br><br>
          <code>eval_metric=logloss</code> &mdash; <strong>XGBoost 내부 평가 지표</strong>. 학습 중 손실 계산용. 우리 PR-AUC 수치와 무관.<br><br>
          <code>verbose=-1</code> &mdash; <strong>학습 로그 끄기</strong>. LightGBM 기본 설정은 매 100 트리마다 로그 출력. 끄는 것.
        </div>
      </div>
    </div>
    <div class="glo-example" style="margin-top:12px;">
      &#128161; <strong>핵심 메시지:</strong> 비고 항목들은 모두 "기본값 그대로 돌렸다"는 의미다.
      PR-AUC 0.8189는 아무것도 튜닝하지 않은 상태의 수치. 이 수치가 높게 나온 것은 <strong>모델이 아니라 데이터와 피처가 좋다는 신호</strong>.
      Phase 2에서 n_estimators·num_leaves·learning_rate를 조정하면 0.83+ 가능.
    </div>
  </div>
</div>

<!-- ══ 4-b. 용어: PR-AUC vs F1 ══════════════════════════════ -->
<div class="slide glossary-slide">
  <div class="tag glossary">&#128218; 개념 설명</div>
  <div class="glo-card">
    <div class="glo-header">
      <div class="glo-icon">&#128202;</div>
      <div class="glo-title">PR-AUC vs F1, 뭐가 다른가?</div>
    </div>
    <div class="glo-vs">
      <div class="glo-vs-box" style="background:#FEF2F2; border:1px solid #FECACA;">
        <strong style="color:#991B1B;">F1@0.5</strong><br><br>
        확률을 0.5 기준으로 잘라서<br>
        취소 / 비취소 두 클래스만 본다<br><br>
        문제: <strong>임계값 0.5는 임의적</strong><br>
        실제 최적 임계값은 0.4일 수도,<br>
        0.7일 수도 있다<br><br>
        "지금 이 순간 단면" 하나만 봄
      </div>
      <div style="display:flex; align-items:center; font-size:24px; color:#94A3B8;">&rarr;</div>
      <div class="glo-vs-box" style="background:#F0FDF4; border:1px solid #BBF7D0;">
        <strong style="color:#166534;">PR-AUC</strong><br><br>
        임계값을 0~1 전체로 바꿔가며<br>
        Precision-Recall 곡선을 그린다<br><br>
        곡선 아래 면적 = 모든 임계값에서<br>
        평균적으로 얼마나 잘 맞추는가<br><br>
        <strong>임계값 선택에 독립적</strong>
      </div>
    </div>
    <div class="glo-example">
      &#128161; 우리는 나중에 PR curve 보고 임계값을 직접 결정한다.
      그 전에 0.5로 고정하는 F1이 메인 지표가 되면 안 된다.
      LR의 F1이 높아 보여도, PR-AUC 전 구간에서는 LightGBM이 이긴다.
    </div>
  </div>
</div>

<!-- ══ 5. PR Curve ════════════════════════════════════════ -->
<div class="slide">
  <div class="tag">Part 1 &mdash; PR Curve</div>
  <h2>PR Curve &mdash; 5종 비교</h2>
  <div style="margin-top:12px;">
    <div class="img-panel" style="display:inline-block;">
      <img src="IMG_PR" style="max-height:420px; max-width:100%; display:block; border-radius:6px;" alt="PR Curve">
    </div>
  </div>
  <div class="sub" style="font-size:13px; margin-top:10px;">
    좌상단 모서리에 가까울수록 좋음 &middot; LightGBM(빨강)이 전 구간에서 XGBoost(초록)를 상회
  </div>
</div>

<!-- ══ 5-b. 용어: Precision / Recall ══════════════════════════ -->
<div class="slide glossary-slide">
  <div class="tag glossary">&#128218; 개념 설명</div>
  <div class="glo-card">
    <div class="glo-header">
      <div class="glo-icon">&#9878;&#65039;</div>
      <div class="glo-title">Precision과 Recall &mdash; 두 가지 실수의 비용</div>
    </div>
    <div class="glo-body">
      모델은 두 종류의 실수를 한다. 어느 실수가 더 비싼가에 따라 임계값을 선택한다.
    </div>
    <div class="glo-vs" style="margin-top:14px;">
      <div class="glo-vs-box" style="background:#FEF2F2; border:1px solid #FECACA; font-size:13px;">
        <strong style="color:#991B1B;">False Positive (헛알람)</strong><br><br>
        취소 안 할 손님인데<br>"취소 위험" 경보를 울림<br><br>
        비용: 불필요한 오버부킹 대응,<br>매니저 시간 낭비<br><br>
        <strong>Precision ↑ = 헛알람 적음</strong><br>
        경보 울린 것 중 진짜 취소 비율
      </div>
      <div class="glo-vs-box" style="background:#FFF7ED; border:1px solid #FED7AA; font-size:13px;">
        <strong style="color:#C05621;">False Negative (놓침)</strong><br><br>
        취소할 손님인데<br>"안전" 판정을 내림<br><br>
        비용: 빈 방 손실,<br>수익 기회 소멸<br><br>
        <strong>Recall ↑ = 놓치는 취소 적음</strong><br>
        실제 취소 중 잡아낸 비율
      </div>
      <div class="glo-vs-box" style="background:#EEF2FF; border:1px solid #C7D2FE; font-size:13px;">
        <strong style="color:#3451D1;">우리 선택 기준</strong><br><br>
        빈 방 손실 vs 오버부킹 보상<br>중 어느 쪽이 더 비싸냐?<br><br>
        일반적으로 <strong>빈 방이 더 비쌈</strong><br>&rarr; Recall 조금 더 중시<br>&rarr; 임계값을 낮게 설정<br><br>
        Week 4에서 정확히 결정
      </div>
    </div>
    <div class="glo-example">
      &#128161; F1 = Precision과 Recall의 조화평균. 둘 다 높아야 F1이 높다. 하나만 극단적으로 올리면 다른 쪽이 망가진다.
    </div>
  </div>
</div>

<!-- ══ 6. PR-AUC 해석 ═════════════════════════════════════ -->
<div class="slide">
  <div class="tag">Part 1 &mdash; Interpretation</div>
  <h2>PR-AUC 0.8189, 이게 좋은 건가?</h2>
  <div class="cards" style="margin-top:20px;">
    <div class="card">
      <div class="card-icon">&#128205;</div>
      <h4>Dummy 대비 위치</h4>
      <p>Dummy(0.387) &rarr; LightGBM(0.819)<br>
      <strong style="font-size:22px; color:#3451D1;">2.11배</strong> 개선<br><br>
      갭 해소율<br>
      <strong style="color:#166534;">(0.819&minus;0.387)/(1&minus;0.387) = <span style="font-size:18px;">70.5%</span></strong></p>
    </div>
    <div class="card">
      <div class="card-icon">&#9878;&#65039;</div>
      <h4>임계값에 따라 달라짐</h4>
      <p>임계값 0.7 선택 &rarr; Precision ↑ = 헛알람 적음<br>
      임계값 0.4 선택 &rarr; Recall ↑ = 놓치는 취소 최소<br><br>
      <span class="yellow">&#9888; 임계값 최적화가 Week 4 핵심</span></p>
    </div>
    <div class="card">
      <div class="card-icon">&#128202;</div>
      <h4>현재 단계 평가</h4>
      <p>Default 파라미터, 미튜닝<br>
      피처 엔지니어링 없음<br><br>
      <strong class="green">&#10003; 충분히 강력한 시작점</strong><br>
      Phase 2 Optuna 튜닝으로 0.83+ 목표</p>
    </div>
  </div>
  <div style="width:100%; margin-top:16px;">
    <div class="meter-wrap">
      <div class="meter-label">
        <span>Dummy 0.387</span>
        <span style="font-weight:700; color:#3451D1;">&#9733; 우리 모델 0.819</span>
        <span>Perfect 1.000</span>
      </div>
      <div class="meter-bar"><div class="meter-fill" style="width:70.5%;"></div></div>
    </div>
  </div>
</div>

<!-- ══ 7. 용어: 임계값 ═══════════════════════════════════ -->
<div class="slide glossary-slide">
  <div class="tag glossary">&#128218; 개념 설명</div>
  <div class="glo-card">
    <div class="glo-header">
      <div class="glo-icon">&#9985;</div>
      <div class="glo-title">임계값(Threshold)이란?</div>
    </div>
    <div class="glo-body">
      모델은 각 예약에 <strong>취소 확률 0~1</strong>을 출력한다.<br>
      임계값은 "이 숫자 이상이면 취소 위험 예약으로 분류하겠다"는 기준선이다.
    </div>
    <div class="glo-vs" style="margin-top:14px;">
      <div class="glo-vs-box" style="background:#FFF7ED; border:1px solid #FED7AA; font-size:13px;">
        <strong style="color:#C05621;">임계값 낮게 (0.4)</strong><br><br>
        취소 확률 40% 이상이면 모두 경보<br>
        &rarr; Recall ↑ (놓치는 취소 없음)<br>
        &rarr; Precision ↓ (안 취소하는 손님도 경보)<br>
        "헛알람 많지만 취소 놓치지 않는다"
      </div>
      <div class="glo-vs-box" style="background:#EEF2FF; border:1px solid #C7D2FE; font-size:13px;">
        <strong style="color:#3451D1;">임계값 높게 (0.7)</strong><br><br>
        취소 확률 70% 이상만 경보<br>
        &rarr; Precision ↑ (경보 대부분 진짜 취소)<br>
        &rarr; Recall ↓ (낮은 확률 취소는 놓칠 수 있음)<br>
        "헛알람 없지만 일부는 놓친다"
      </div>
    </div>
    <div class="glo-example">
      &#128161; 빈 방 손실(FN, 취소 놓침) vs 오버부킹 보상(FP, 헛알람) 중 어느 비용이 더 크냐에 따라 임계값을 선택한다.
      Week 4에서 walk_rate 곡선 보고 확정.
    </div>
  </div>
</div>

<!-- ══ 7-b. 용어: 호텔 도메인 용어 ══════════════════════════ -->
<div class="slide glossary-slide">
  <div class="tag glossary">&#128218; 개념 설명</div>
  <div class="glo-card" style="max-width:980px;">
    <div class="glo-header">
      <div class="glo-icon">&#127970;</div>
      <div class="glo-title">호텔 데이터 도메인 용어 &mdash; SHAP 결과를 읽기 전에</div>
    </div>
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:4px;">
      <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:14px;">
        <div style="font-size:11px; font-weight:700; color:#94A3B8; letter-spacing:1px; margin-bottom:8px;">예약 관련</div>
        <div style="font-size:13px; color:#334155; line-height:2.0;">
          <code>adr</code> &mdash; Average Daily Rate. <strong>1박 평균 객실 요금</strong> (세금·식사 제외)<br>
          <code>lead_time</code> &mdash; 예약일~체크인까지 <strong>일수</strong>. 길수록 취소 ↑ (계획 바뀔 시간 많음)<br>
          <code>total_of_special_requests</code> &mdash; 아기 침대·금연실 등 <strong>특별 요청 수</strong>. 많을수록 "진짜 올 손님"<br>
          <code>required_car_parking_spaces</code> &mdash; <strong>주차 요청</strong>. 있으면 차를 가지고 옴 = 취소 낮음<br>
          <code>booking_changes</code> &mdash; 예약 후 <strong>변경 횟수</strong>. 바꿀수록 적극적 손님
        </div>
      </div>
      <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:14px;">
        <div style="font-size:11px; font-weight:700; color:#94A3B8; letter-spacing:1px; margin-bottom:8px;">채널 / 세그먼트</div>
        <div style="font-size:13px; color:#334155; line-height:2.0;">
          <code>market_segment_Online TA</code> &mdash; <strong>OTA 채널</strong> (부킹닷컴·익스피디아 등). 취소율 높음<br>
          <code>market_segment_Offline TA/TO</code> &mdash; <strong>오프라인 여행사·투어오퍼레이터</strong><br>
          <code>market_segment_Groups</code> &mdash; <strong>단체 예약</strong>. B2B 블록 해제 위험<br>
          <code>customer_type_Transient</code> &mdash; <strong>1회성 개인 예약자</strong>. 가장 많은 유형<br>
          <code>customer_type_Transient-Party</code> &mdash; <strong>동행 있는 개인 예약</strong> (커플·가족 등)
        </div>
      </div>
    </div>
    <div class="glo-example" style="margin-top:12px;">
      &#128161; SHAP 결과에서 컬럼명이 <code>market_segment_Online TA</code>처럼 생긴 이유:
      카테고리 변수를 One-Hot Encoding(OHE)하면 각 값이 별도 열이 된다.
      <code>market_segment</code> 하나가 여러 열로 쪼개진 것 &rarr; 33컬럼 &rarr; 70피처가 되는 이유.
    </div>
  </div>
</div>

<!-- ══ 8. SHAP Top 10 ════════════════════════════════════ -->
<div class="slide">
  <div class="tag">Part 1 &mdash; SHAP Analysis</div>
  <h2>LightGBM SHAP Top 10 &mdash; 무엇이 취소를 만드는가</h2>
  <div style="display:flex; gap:22px; width:100%; margin-top:16px;">
    <div style="flex:1.1;">
      <div class="shap-row">
        <span class="shap-rank">1</span>
        <span class="shap-feat">country_grouped_PRT</span>
        <div class="shap-bar-wrap"><div class="shap-bar-bg"><div class="shap-bar-fill" style="width:100%;"></div></div></div>
        <span class="shap-val">1.064</span>
        <span class="badge badge-red shap-badge">취소 ↑</span>
      </div>
      <div class="shap-row">
        <span class="shap-rank">2</span>
        <span class="shap-feat">required_car_parking_spaces</span>
        <div class="shap-bar-wrap"><div class="shap-bar-bg"><div class="shap-bar-fill" style="width:63.9%;"></div></div></div>
        <span class="shap-val">0.680</span>
        <span class="badge badge-green shap-badge">취소 ↓</span>
      </div>
      <div class="shap-row">
        <span class="shap-rank">3</span>
        <span class="shap-feat">total_of_special_requests</span>
        <div class="shap-bar-wrap"><div class="shap-bar-bg"><div class="shap-bar-fill" style="width:60.5%;"></div></div></div>
        <span class="shap-val">0.644</span>
        <span class="badge badge-green shap-badge">취소 ↓</span>
      </div>
      <div class="shap-row">
        <span class="shap-rank">4</span>
        <span class="shap-feat">lead_time</span>
        <div class="shap-bar-wrap"><div class="shap-bar-bg"><div class="shap-bar-fill" style="width:49.9%;"></div></div></div>
        <span class="shap-val">0.531</span>
        <span class="badge badge-red shap-badge">길수록 ↑</span>
      </div>
      <div class="shap-row" style="background:#FFF7ED; border-radius:6px; padding:7px 4px;">
        <span class="shap-rank" style="color:#C05621;">5</span>
        <span class="shap-feat" style="color:#C05621; font-weight:700;">previous_cancellations</span>
        <div class="shap-bar-wrap"><div class="shap-bar-bg"><div class="shap-bar-fill" style="width:37.1%; background:linear-gradient(90deg,#FB923C,#FBBF24);"></div></div></div>
        <span class="shap-val" style="color:#C05621;">0.394</span>
        <span class="badge badge-orange shap-badge">&#9733; 감시중</span>
      </div>
      <div class="shap-row">
        <span class="shap-rank">6</span>
        <span class="shap-feat">market_segment_Online TA</span>
        <div class="shap-bar-wrap"><div class="shap-bar-bg"><div class="shap-bar-fill" style="width:34.9%;"></div></div></div>
        <span class="shap-val">0.371</span>
        <span class="badge badge-red shap-badge">채널 위험</span>
      </div>
      <div class="shap-row">
        <span class="shap-rank">7</span>
        <span class="shap-feat">customer_type_Transient</span>
        <div class="shap-bar-wrap"><div class="shap-bar-bg"><div class="shap-bar-fill" style="width:24.1%;"></div></div></div>
        <span class="shap-val">0.256</span>
        <span class="badge badge-gray shap-badge">&mdash;</span>
      </div>
      <div class="shap-row">
        <span class="shap-rank">8</span>
        <span class="shap-feat">market_segment_Offline TA/TO</span>
        <div class="shap-bar-wrap"><div class="shap-bar-bg"><div class="shap-bar-fill" style="width:24.0%;"></div></div></div>
        <span class="shap-val">0.256</span>
        <span class="badge badge-gray shap-badge">&mdash;</span>
      </div>
      <div class="shap-row">
        <span class="shap-rank">9</span>
        <span class="shap-feat">adr</span>
        <div class="shap-bar-wrap"><div class="shap-bar-bg"><div class="shap-bar-fill" style="width:23.7%;"></div></div></div>
        <span class="shap-val">0.253</span>
        <span class="badge badge-gray shap-badge">&mdash;</span>
      </div>
      <div class="shap-row">
        <span class="shap-rank">10</span>
        <span class="shap-feat">market_segment_Groups</span>
        <div class="shap-bar-wrap"><div class="shap-bar-bg"><div class="shap-bar-fill" style="width:15.8%;"></div></div></div>
        <span class="shap-val">0.168</span>
        <span class="badge badge-gray shap-badge">&mdash;</span>
      </div>
    </div>
    <div style="flex:.9; display:flex; flex-direction:column; gap:10px;">
      <div class="alert alert-green">
        &#10003; <strong>B2B 경보 OFF</strong> &mdash; previous_cancellations 5위 (Top 3 밖). 현재 허용 범위.
      </div>
      <div class="p2-card" style="margin:0;">
        <div class="p2-body">
          <strong style="color:#0F172A; font-size:13px;">&#128204; 해석 포인트</strong><br><br>
          <strong>PRT (포르투갈) #1</strong> — 리스본/알가르브 소재 호텔에서 내국인 예약이 외국인보다 취소율 높음<br><br>
          <strong>주차 요청 #2 (취소 낮춤)</strong> — 차량 동반 = 실제 방문 의향 강함<br><br>
          <strong>특별 요청 #3 (취소 낮춤)</strong> — 요청 많을수록 "진짜 올 손님" 신호<br><br>
          <strong>리드타임 #4 (취소 높임)</strong> — 일찍 잡고 늦게 취소하는 패턴
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ══ 9. 용어: SHAP ══════════════════════════════════════ -->
<div class="slide glossary-slide">
  <div class="tag glossary">&#128218; 개념 설명</div>
  <div class="glo-card">
    <div class="glo-header">
      <div class="glo-icon">&#127775;</div>
      <div class="glo-title">SHAP이란? &mdash; 모델을 해부하는 도구</div>
    </div>
    <div class="glo-body">
      모델은 "예약 A의 취소 확률이 0.82다"라고 말해준다.<br>
      SHAP은 <strong>"왜 0.82인가?"</strong>를 피처별로 분해해준다.
    </div>
    <div class="glo-vs" style="margin-top:14px;">
      <div class="glo-vs-box" style="background:#F0FDF4; border:1px solid #BBF7D0; font-size:13px;">
        <strong style="color:#166534;">Bar Chart (전역)</strong><br><br>
        "전체 예약을 봤을 때<br>어떤 피처가 평균적으로<br>가장 많이 영향을 줬나?"<br><br>
        &rarr; 우리 모델이 무엇에 의존하는지 파악
      </div>
      <div class="glo-vs-box" style="background:#EEF2FF; border:1px solid #C7D2FE; font-size:13px;">
        <strong style="color:#3451D1;">Waterfall (개별)</strong><br><br>
        "이 예약 하나가 왜<br>취소 확률이 0.82인가?"<br><br>
        lead_time +0.3<br>
        special_requests &minus;0.2<br>
        country_PRT +0.4 ...<br><br>
        &rarr; 앱에서 매니저에게 근거 제시
      </div>
      <div class="glo-vs-box" style="background:#FFF7ED; border:1px solid #FED7AA; font-size:13px;">
        <strong style="color:#C05621;">Beeswarm (방향성)</strong><br><br>
        Bar Chart + 방향까지<br>높은 값이 취소를 올리는가<br>낮추는가를 같이 본다<br><br>
        빨간점 = 피처 값 높음<br>
        오른쪽 = 취소 ↑
      </div>
    </div>
    <div class="glo-example">
      &#128161; TreeSHAP은 샘플링 없이 정확하게 계산된다. 우리가 LightGBM을 쓰는 이유 중 하나도 TreeSHAP 완벽 지원.
    </div>
  </div>
</div>

<!-- ══ 10. SHAP 이미지 비교 ═════════════════════════════ -->
<div class="slide">
  <div class="tag">Part 1 &mdash; SHAP Comparison</div>
  <h2>XGBoost vs LightGBM SHAP 중요도 비교</h2>
  <div style="margin-top:12px;">
    <div class="img-panel" style="display:inline-block;">
      <img src="IMG_CMP" style="max-height:410px; max-width:100%; display:block; border-radius:6px;" alt="SHAP Comparison">
    </div>
  </div>
  <div style="display:flex; gap:10px; margin-top:12px; width:100%;">
    <div class="alert alert-blue" style="flex:1.5;">
      &#9432; <strong>공통 Top-10</strong> (9개) — adr &middot; country_PRT &middot; customer_Transient &middot; lead_time &middot; market_Groups &middot; market_OnlineTA &middot; previous_cancellations &middot; parking &middot; special_requests
    </div>
    <div class="alert alert-green" style="flex:.8;">
      &#10003; 두 모델 Top-10이 9/10 일치 &rarr; 피처 신뢰도 높음
    </div>
  </div>
</div>

<!-- ══ 11. SHAP Beeswarm ══════════════════════════════════ -->
<div class="slide">
  <div class="tag">Part 1 &mdash; SHAP Beeswarm</div>
  <h2>LightGBM Beeswarm &mdash; 피처 방향성</h2>
  <div style="display:flex; gap:18px; width:100%; margin-top:10px; align-items:flex-start;">
    <div class="img-panel" style="flex:1.4;">
      <img src="IMG_BEE" style="max-height:400px; width:100%; object-fit:contain; border-radius:6px;" alt="SHAP Beeswarm">
    </div>
    <div style="flex:.6; display:flex; flex-direction:column; gap:10px;">
      <div class="p2-card" style="margin:0;">
        <div class="p2-body" style="font-size:13px;">
          <strong style="color:#0F172A;">읽는 법 (색상)</strong><br>
          빨간점 = 해당 피처 값이 높음<br>
          파란점 = 해당 피처 값이 낮음<br><br>
          <strong style="color:#0F172A;">읽는 법 (위치)</strong><br>
          오른쪽 = 취소 확률 올림 ↑<br>
          왼쪽 = 취소 확률 낮춤 ↓<br><br>
          <strong style="color:#0F172A;">주요 패턴</strong><br>
          special_requests: 높으면(빨강) 왼쪽 = 취소 ↓<br>
          lead_time: 높으면(빨강) 오른쪽 = 취소 ↑<br>
          parking: 있으면(빨강) 왼쪽 = 취소 ↓
        </div>
      </div>
      <div class="alert alert-blue">
        &#9432; 이 방향성을 참고해서 ACTION 규칙 설계 (Week 4 미결 #5)
      </div>
    </div>
  </div>
</div>

<!-- ══ 12. SHAP Waterfall ════════════════════════════════ -->
<div class="slide">
  <div class="tag">Part 1 &mdash; SHAP Waterfall</div>
  <h2>최고위험 예약 개별 설명 &mdash; 앱 데모용</h2>
  <div style="display:flex; gap:18px; width:100%; margin-top:10px; align-items:flex-start;">
    <div class="img-panel" style="flex:1.4;">
      <img src="IMG_WF" style="max-height:390px; width:100%; object-fit:contain; border-radius:6px;" alt="SHAP Waterfall">
    </div>
    <div style="flex:.6; display:flex; flex-direction:column; gap:10px;">
      <div class="p2-card" style="margin:0;">
        <div class="p2-body" style="font-size:13px;">
          <strong style="color:#0F172A;">읽는 법</strong><br>
          E[f(X)] = 시작점 (전체 평균 예측)<br>
          빨간 막대 = 취소 확률 올리는 요인<br>
          파란 막대 = 취소 확률 낮추는 요인<br>
          f(x) = 이 예약의 최종 취소 확률<br><br>
          <strong style="color:#0F172A;">앱 탭1 활용</strong><br>
          매니저가 예약 클릭하면<br>이 형태로 "왜 위험한가" 제시<br>
          책임 전가 아닌 근거 제공
        </div>
      </div>
      <div class="alert alert-green">
        &#10003; 앱 탭1 개별 SHAP 설명 로직 확정 &rarr; 이고은 Week 4 구현
      </div>
    </div>
  </div>
</div>

<!-- ══ 13. 용어: B2B 패턴 ════════════════════════════════ -->
<div class="slide glossary-slide">
  <div class="tag glossary">&#128218; 개념 설명</div>
  <div class="glo-card">
    <div class="glo-header">
      <div class="glo-icon">&#127970;</div>
      <div class="glo-title">previous_cancellations의 B2B 오염이란?</div>
    </div>
    <div class="glo-body">
      <code>previous_cancellations</code>는 "이 손님이 과거에 취소한 횟수"다.<br>
      문제는 이 변수의 98%가 0이고, &ge;1인 그룹이 <strong>취소율 99.15%</strong>라는 점이다.
    </div>
    <div class="glo-vs" style="margin-top:14px;">
      <div class="glo-vs-box" style="background:#F0FDF4; border:1px solid #BBF7D0; font-size:13px;">
        <strong style="color:#166534;">&#10003; 우리가 가정한 것</strong><br><br>
        "previous_cancellations &ge; 1인 손님은<br>과거에 실제로 취소한 고객이므로<br>재취소 가능성이 높다"
      </div>
      <div class="glo-vs-box" style="background:#FEF2F2; border:1px solid #FECACA; font-size:13px;">
        <strong style="color:#991B1B;">&#10005; 실제로 보니</strong><br><br>
        is_repeated_guest=0인데<br>previous_cancellations&ge;1인 행이 5,520개<br><br>
        89%가 B2B 블록 예약 해제 패턴<br>
        (여행사가 단체 블록을 잡았다가 취소)<br>
        개인 고객의 재취소가 아님
      </div>
    </div>
    <div class="glo-example">
      &#128161; deposit_type(Non Refund)을 DROP한 이후, previous_cancellations가 그 B2B 신호를 단독으로 흡수했을 가능성이 있다.
      SHAP 5위(0.394)는 허용 범위. Phase 2에서 이 변수를 제거해보고 PR-AUC 변화를 확인한다 (미결 #6).
    </div>
  </div>
</div>

<!-- ══ 13-b. 용어: OHE와 33→70 컬럼 ══════════════════════════ -->
<div class="slide glossary-slide">
  <div class="tag glossary">&#128218; 개념 설명</div>
  <div class="glo-card">
    <div class="glo-header">
      <div class="glo-icon">&#128200;</div>
      <div class="glo-title">OHE (One-Hot Encoding) &mdash; 왜 33컬럼이 70피처가 되는가</div>
    </div>
    <div class="glo-body">
      머신러닝 모델은 숫자만 읽는다. <strong>"Online TA"</strong> 같은 문자열을 직접 이해하지 못한다.<br>
      OHE는 카테고리 변수의 각 값을 <strong>별도의 0/1 열</strong>로 만들어 숫자로 변환하는 방법이다.
    </div>
    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:16px; margin-top:14px; font-size:13px; color:#334155;">
      <strong>예시: market_segment (1개 컬럼) &rarr; 여러 열</strong><br><br>
      <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:8px;">
        <span style="background:#EEF2FF; color:#3451D1; padding:4px 10px; border-radius:6px; font-family:monospace; font-size:12px;">market_segment_Online TA</span>
        <span style="background:#EEF2FF; color:#3451D1; padding:4px 10px; border-radius:6px; font-family:monospace; font-size:12px;">market_segment_Offline TA/TO</span>
        <span style="background:#EEF2FF; color:#3451D1; padding:4px 10px; border-radius:6px; font-family:monospace; font-size:12px;">market_segment_Direct</span>
        <span style="background:#EEF2FF; color:#3451D1; padding:4px 10px; border-radius:6px; font-family:monospace; font-size:12px;">market_segment_Groups</span>
        <span style="background:#EEF2FF; color:#3451D1; padding:4px 10px; border-radius:6px; font-family:monospace; font-size:12px;">market_segment_Corporate</span>
      </div>
      <div style="margin-top:12px; color:#64748B;">
        Online TA로 예약한 행: [1, 0, 0, 0, 0] &nbsp;&nbsp; Direct로 예약한 행: [0, 0, 1, 0, 0]
      </div>
    </div>
    <div style="display:flex; gap:12px; margin-top:12px;">
      <div style="flex:1; background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:12px; font-size:13px;">
        <strong style="color:#166534;">OHE 적용 컬럼 (7개)</strong><br>
        hotel, meal, market_segment,<br>distribution_channel,<br>reserved_room_type,<br>customer_type, country_grouped
      </div>
      <div style="flex:1; background:#EEF2FF; border:1px solid #C7D2FE; border-radius:8px; padding:12px; font-size:13px;">
        <strong style="color:#3451D1;">결과: 33 &rarr; 70피처</strong><br>
        country_grouped만 해도<br>Top10 + Other = 11개 열<br>market_segment = 7개 열<br>나머지도 각각 쪼개짐
      </div>
      <div style="flex:1; background:#FFF7ED; border:1px solid #FED7AA; border-radius:8px; padding:12px; font-size:13px;">
        <strong style="color:#C05621;">주의: deposit_type 제거</strong><br>
        Non Refund 99.2% 취소율<br>= 사후 기록 오염<br>OHE 대상에서 제외됨<br>→ CLAUDE.md 참고
      </div>
    </div>
  </div>
</div>

<!-- ══ 14. 모델 산출물 전체 ══════════════════════════════ -->
<div class="slide">
  <div class="tag">Part 1 &mdash; Model Outputs</div>
  <h2>이 모델이 만들 수 있는 것들</h2>
  <div class="out-grid" style="margin-top:18px;">
    <div class="out-box">
      <div class="num">①</div>
      <div class="title">취소 확률 순위표</div>
      <div class="desc"><code>predict_proba[:,1]</code><br>예약별 0~1 취소 확률<br>&rarr; 앱 탭1 우선순위 리스트</div>
    </div>
    <div class="out-box" style="border-color:#818CF8; border-width:2px;">
      <div class="num">②</div>
      <div class="title">SHAP 전역 중요도</div>
      <div class="desc">beeswarm / bar chart<br>어떤 변수가 취소를 만드는가<br>&rarr; 매니저 신뢰 근거</div>
    </div>
    <div class="out-box" style="border-color:#818CF8; border-width:2px;">
      <div class="num">③</div>
      <div class="title">SHAP 개별 설명</div>
      <div class="desc">waterfall per booking<br>이 예약이 왜 위험한가<br>&rarr; 앱 탭1 클릭 상세</div>
    </div>
    <div class="out-box">
      <div class="num">④</div>
      <div class="title">walk_rate 곡선</div>
      <div class="desc">threshold 0.5~0.85 sweep<br>블라인드 vs 모델 비교<br>&rarr; Flexi 슬롯 설계 근거</div>
    </div>
    <div class="out-box">
      <div class="num">⑤</div>
      <div class="title">채널 실효 수익</div>
      <div class="desc">ADR &times; (1&minus;cancel_rate)<br>채널별 실제 수익 비교<br>&rarr; Phase 2 김나리</div>
    </div>
    <div class="out-box">
      <div class="num">⑥</div>
      <div class="title">음식 낭비 위험</div>
      <div class="desc">meal &times; cancel_proba<br>HB/FB 고위험 예약 집계<br>&rarr; Phase 2 이고은</div>
    </div>
  </div>
  <div style="margin-top:12px; text-align:center; font-size:13px; color:#64748B;">
    ①②③ = Phase 1 MVP &nbsp;&middot;&nbsp; ④⑤⑥ = Phase 2 (같은 모델 재활용, 재학습 없음)
  </div>
</div>

<!-- ══ 15. 용어: walk_rate ════════════════════════════════ -->
<div class="slide glossary-slide">
  <div class="tag glossary">&#128218; 개념 설명</div>
  <div class="glo-card">
    <div class="glo-header">
      <div class="glo-icon">&#128694;&#65039;</div>
      <div class="glo-title">walk_rate란? &mdash; Flexi 시스템의 핵심 지표</div>
    </div>
    <div class="glo-body">
      호텔이 오버부킹(정원 초과 예약)을 받으면, 실제로 손님이 다 왔을 때 일부를 돌려보내야 할 수 있다.<br>
      <strong>walk_rate = Flexi 풀로 받은 예약 중 실제로 돌려보낸(walk) 비율</strong>
    </div>
    <div class="glo-vs" style="margin-top:14px;">
      <div class="glo-vs-box" style="background:#FEF2F2; border:1px solid #FECACA; font-size:13px;">
        <strong style="color:#991B1B;">walk_rate 높음</strong><br><br>
        Flexi 슬롯을 너무 많이 열었음<br>
        예상보다 취소가 적어서<br>실제 손님이 많이 왔는데<br>방이 부족해 돌려보냄<br><br>
        손님 불만, 보상 비용 발생
      </div>
      <div class="glo-vs-box" style="background:#F0FDF4; border:1px solid #BBF7D0; font-size:13px;">
        <strong style="color:#166534;">walk_rate 낮음 (목표 &lt; 2%)</strong><br><br>
        취소 예측이 정확해서<br>오버부킹 슬롯이 적절히 채워짐<br><br>
        빈 방 손실 줄이면서도<br>손님을 돌려보내는 일 없음
      </div>
    </div>
    <div class="glo-example">
      &#128161; 우리 프로젝트에서는 Pool A(실제 취소한 예약)만 있다. walk_rate는 "임계값을 높일수록
      낮아지는가?"를 시뮬레이션으로 확인한다. Pool B(Flexi 전환 수요)는 반사실적이라 사용하지 않는다.
    </div>
  </div>
</div>

<!-- ══ 16. 문제점 ══════════════════════════════════════════ -->
<div class="slide">
  <div class="tag">Part 1 &mdash; Problems</div>
  <h2>현재 모델의 문제점 3가지</h2>
  <div style="width:100%; margin-top:16px;">
    <div class="prob-row med">
      <div class="prob-icon">&#9888;&#65039;</div>
      <div>
        <div class="prob-title">previous_cancellations B2B 오염 가능성 (中) &mdash; SHAP 5위</div>
        <div class="prob-desc">
          &ge;1 그룹 취소율 99.15% / 89%가 B2B 블록 해제 (개인 취소 아님). deposit_type DROP 이후 대리 신호 역할 가능.
          <strong class="orange">현재 Top 3 밖(5위) &rarr; 허용 범위. Phase 2 ablation 예정대로.</strong>
        </div>
      </div>
    </div>
    <div class="prob-row med">
      <div class="prob-icon">&#128197;</div>
      <div>
        <div class="prob-title">테스트셋 계절 편향 (中) &mdash; 봄~여름 성수기 집중</div>
        <div class="prob-desc">
          테스트셋 2017-03~08. 비수기(11~2월) 성능 미확인. PR-AUC 0.8189는 성수기 기준 수치.
          <strong class="orange">발표 시 "이 데이터셋에서의 유효성" 범위 명시 필요.</strong>
        </div>
      </div>
    </div>
    <div class="prob-row low">
      <div class="prob-icon">&#128204;</div>
      <div>
        <div class="prob-title">하이퍼파라미터 미튜닝 (低) &mdash; 모두 default</div>
        <div class="prob-desc">
          n_estimators=100, num_leaves/learning_rate/min_child_samples 미조정.
          <strong class="yellow">Phase 2 Optuna로 0.83+ 시도 가능. MVP 단계에서는 허용.</strong>
        </div>
      </div>
    </div>
  </div>
  <div class="alert alert-green" style="margin-top:6px;">
    &#10003; 세 문제 모두 MVP 진행을 막는 수준 아님. 현재 모델로 Phase 1 완주 가능.
  </div>
</div>

<!-- ══ 17. 보완 방향 ══════════════════════════════════════ -->
<div class="slide">
  <div class="tag">Part 1 &mdash; Next Steps</div>
  <h2>보완 방향 합의</h2>
  <div class="cards" style="margin-top:20px;">
    <div class="card ok">
      <div class="card-icon">&#128269;</div>
      <h4>SHAP 퀵 체크 (이미 완료 &#10003;)</h4>
      <ul>
        <li>previous_cancellations: 5위 &rarr; Top 3 밖</li>
        <li>B2B 경보 OFF &rarr; Phase 2 ablation 예정대로</li>
        <li>공통 Top-10 피처 9개 &rarr; 모델 안정성 확인</li>
      </ul>
    </div>
    <div class="card hl">
      <div class="card-icon">&#127919;</div>
      <h4>임계값 최적화 (Week 4)</h4>
      <ul>
        <li>PR curve에서 F1 최대화 지점 확인</li>
        <li>walk_rate &lt; 2% 달성 지점 &rarr; Flexi 임계값</li>
        <li>beeswarm 방향성 참고해서 ACTION 규칙 설계</li>
      </ul>
    </div>
    <div class="card">
      <div class="card-icon">&#9881;&#65039;</div>
      <h4>하이퍼파라미터 (Phase 2)</h4>
      <ul>
        <li>MVP 이후 Optuna로 num_leaves &middot; lr 탐색</li>
        <li>목표: PR-AUC 0.83+</li>
        <li>class_weight 불균형 실험 병행</li>
      </ul>
    </div>
  </div>
  <div style="margin-top:16px; background:#F0FDF4; border:1px solid #BBF7D0; border-radius:10px; padding:11px 22px; width:100%; text-align:center; font-size:14px;">
    <strong class="green">오늘 완료</strong>
    <span style="color:#94A3B8; margin:0 8px;">&mdash;</span>
    <span class="green">&#10003; 모델 동결</span>&nbsp;&nbsp;
    <span class="green">&#10003; model_final.pkl</span>&nbsp;&nbsp;
    <span class="green">&#10003; PR curve 5종</span>&nbsp;&nbsp;
    <span class="green">&#10003; SHAP 분석</span>&nbsp;&nbsp;
    <span class="green">&#10003; baseline_results.md</span>
  </div>
</div>

<!-- ══ 18. Part 2 전환 ════════════════════════════════════ -->
<div class="slide divider-slide">
  <div class="cover-bg"></div>
  <div style="text-align:center;">
    <div class="tag">Part 2</div>
    <h1 style="font-size:40px; color:#fff; margin-bottom:14px;">
      취소 예측 너머<br>의미있는 지표 3가지
    </h1>
    <div class="sub">
      같은 모델, 같은 <code style="background:rgba(255,255,255,.2); color:#fff;">cancel_proba</code> 출력<br>
      재학습 없이 세 가지 운영 문제를 더 푼다
    </div>
  </div>
</div>

<!-- ══ 18-b. 용어: Flexi 시스템 개요 ════════════════════════ -->
<div class="slide glossary-slide">
  <div class="tag glossary">&#128218; 개념 설명</div>
  <div class="glo-card">
    <div class="glo-header">
      <div class="glo-icon">&#128260;</div>
      <div class="glo-title">Flexi 시스템이란? &mdash; 취소를 역이용하는 운영 전략</div>
    </div>
    <div class="glo-body">
      호텔은 취소가 발생하면 빈 방이 생긴다. Flexi 시스템은 이를 역이용해
      <strong>"어차피 취소할 것 같은 예약 자리에 추가 예약을 받는다"</strong>는 전략이다.
    </div>
    <div class="glo-vs" style="margin-top:14px;">
      <div class="glo-vs-box" style="background:#F8FAFC; border:1px solid #E2E8F0; font-size:13px;">
        <strong style="color:#334155;">Pool A (우리가 쓰는 것)</strong><br><br>
        실제로 취소된 예약들의 데이터<br>이 패턴으로 취소 확률 학습<br><br>
        "이 예약은 취소될 가능성이 높으니<br>이 자리에 Flexi 예약을 추가로 받자"<br><br>
        <span style="color:#166534;">&#10003; 실데이터 기반 &rarr; 방어 가능</span>
      </div>
      <div class="glo-vs-box" style="background:#FEF2F2; border:1px solid #FECACA; font-size:13px;">
        <strong style="color:#991B1B;">Pool B (우리가 안 쓰는 것)</strong><br><br>
        Flexi로 전환한 예약이<br>실제로 왔을 경우의 수요<br><br>
        문제: 이 수요가 실제로 존재하는지<br>어떤 수치도 구조적으로 증명 불가<br><br>
        <span style="color:#991B1B;">&#10005; 반사실적 수요 &rarr; 방어 불가</span>
      </div>
      <div class="glo-vs-box" style="background:#EEF2FF; border:1px solid #C7D2FE; font-size:13px;">
        <strong style="color:#3451D1;">우리의 접근 (Policy-Level DSS)</strong><br><br>
        매니저가 임계값·슬롯 수를<br>설정하면 시스템이 자동 실행<br><br>
        개별 예약 판단 아님<br>&rarr; 책임 전가 아닌 정책 설계<br><br>
        <span style="color:#3451D1;">&#10003; Talluri &amp; van Ryzin 2004</span>
      </div>
    </div>
    <div class="glo-example">
      &#128161; <strong>walk_rate</strong>: Flexi 슬롯으로 받은 예약 중 실제로 돌려보낸 비율. 취소 예측이 정확할수록 walk_rate ↓.
      목표: walk_rate &lt; 2%. 이것이 우리 모델의 <strong>실제 운영 가치 증명 포인트</strong>.
    </div>
  </div>
</div>

<!-- ══ 19. 3가지 방향 ════════════════════════════════════ -->
<div class="slide">
  <div class="tag">Part 2 &mdash; Beyond Cancellation</div>
  <h2>취소 예측이 풀 수 있는 운영 문제 3개</h2>
  <div style="display:flex; flex-direction:column; gap:12px; width:100%; margin-top:16px;">
    <div class="p2-card" style="margin:0;">
      <div class="p2-header">
        <div class="p2-icon">&#128176;</div>
        <div class="p2-title">채널 실효 수익 분석 (Channel Effective Yield)</div>
        <div class="p2-tag">김나리 &middot; Week 5</div>
      </div>
      <div class="p2-body">
        <code>effective_adr = ADR &times; (1 &minus; cancel_rate)</code> &rarr;
        Online TA가 ADR 높아도 취소율이 높으면 실효 수익이 낮다.
        "Direct 채널이 실제로 더 수익적이다"를 데이터로 증명.
        <strong style="color:#0F172A;">현재 SHAP 6위: market_segment_Online TA (0.371) &rarr; 취소 올림 확인됨.</strong>
      </div>
    </div>
    <div class="p2-card" style="margin:0;">
      <div class="p2-header">
        <div class="p2-icon">&#11088;</div>
        <div class="p2-title">예약 품질 점수 (Booking Quality Score)</div>
        <div class="p2-tag">심재형 &middot; Week 5</div>
      </div>
      <div class="p2-body">
        <code>BQS = w1&middot;ADR + w2&middot;stays + w3&middot;special_requests &minus; w4&middot;cancel_proba</code> &rarr;
        취소 확률만으로 우선순위를 잡으면 안 된다.
        <strong style="color:#0F172A;">SHAP에서 total_of_special_requests가 #3 (취소 낮춤) 확인 &rarr; BQS 가중치 근거 확보됨.</strong>
      </div>
    </div>
    <div class="p2-card" style="margin:0;">
      <div class="p2-header">
        <div class="p2-icon">&#127869;&#65039;</div>
        <div class="p2-title">음식 낭비 예측 (Food Waste Prediction)</div>
        <div class="p2-tag">이고은 &middot; Week 6</div>
      </div>
      <div class="p2-body">
        <code>food_risk = cancel_proba &gt; 0.65 &amp; meal in [HB, FB]</code> &rarr;
        기존 도구는 사후 모니터링. 우리는 사전 예측으로 발주 전 조정.
        EU CSRD 2024 식품 낭비 보고 의무화 맥락과 맞물림.
      </div>
    </div>
  </div>
</div>

<!-- ══ 20. 논의 안건 ══════════════════════════════════════ -->
<div class="slide">
  <div class="tag">Discussion</div>
  <h2>오늘 결정해야 할 것들</h2>
  <div style="width:100%; margin-top:14px;">
    <div class="discuss-item">
      <div class="discuss-q">Q1</div>
      <div>
        <div class="discuss-title">SHAP 결과 해석 공유 &mdash; country_PRT #1 의미</div>
        <div class="discuss-desc">포르투갈 국적이 1위인 이유. 내국인 패턴 차이로 설명 가능한가? 발표 내러티브에 어떻게 녹일 것인가.</div>
      </div>
    </div>
    <div class="discuss-item">
      <div class="discuss-q">Q2</div>
      <div>
        <div class="discuss-title">임계값 결정 기준 합의</div>
        <div class="discuss-desc">F1 최대화 지점 vs walk_rate &lt; 2% 달성 지점 vs 비용 비율 추정 기반. Week 4 전에 어떤 기준으로 자를 것인가.</div>
      </div>
    </div>
    <div class="discuss-item">
      <div class="discuss-q">Q3</div>
      <div>
        <div class="discuss-title">Phase 2 방향 중 중간발표(5/27) 포함 범위</div>
        <div class="discuss-desc">채널 실효 수익 / BQS / 음식 낭비 중 EDA 수준이라도 5/27에 포함할 항목. 김나리&middot;이고은 Week 3 선행 착수 가능 여부.</div>
      </div>
    </div>
    <div class="discuss-item">
      <div class="discuss-q">Q4</div>
      <div>
        <div class="discuss-title">previous_cancellations 감시 기준 &mdash; 몇 위부터 즉시 대응?</div>
        <div class="discuss-desc">현재 5위 허용 범위. 제안: Top 2 이내 진입 시 Phase 2 ablation을 MVP 사이클로 즉시 당긴다. 팀 합의 필요.</div>
      </div>
    </div>
  </div>
</div>

<!-- ══ 21. 이번 주 실행 ════════════════════════════════════ -->
<div class="slide">
  <div class="tag">Week 3 Execution</div>
  <h2>이번 주 각자 할 것</h2>
  <div class="cards" style="margin-top:18px;">
    <div class="card hl">
      <div class="card-icon">&#128100;</div>
      <h4>심재형</h4>
      <ul>
        <li><strong>model_interface.md &rarr; 이고은 전달 (오늘)</strong></li>
        <li>SHAP 분석 결과 노션 공유</li>
        <li>Week 4 SHAP 연동 설계서 작성</li>
        <li>baseline_results.md 노션 기록</li>
      </ul>
    </div>
    <div class="card ok">
      <div class="card-icon">&#128100;</div>
      <h4>이고은</h4>
      <ul>
        <li>탭1 뼈대 구현 (5/12~13)</li>
        <li>인터페이스 수신 후 predict_proba 연동</li>
        <li>위험 등급 표시 (High/Med/Low)</li>
        <li>EDA master 음식 낭비 섹션 확인</li>
      </ul>
    </div>
    <div class="card">
      <div class="card-icon">&#128100;</div>
      <h4>김나리</h4>
      <ul>
        <li>LightGBM 수치 노션 기록 확인</li>
        <li>EDA master 채널&middot;BQS 섹션 수치 확인</li>
        <li>BQS 변수 후보 노트 작성</li>
        <li>채널 실효 수익 분석 선행 착수 (선택)</li>
      </ul>
    </div>
  </div>
  <div style="margin-top:16px; background:#EEF2FF; border:1.5px solid #818CF8; border-radius:10px; padding:11px 22px; width:100%; text-align:center; font-size:14px;">
    <strong style="color:#3451D1;">Gate 5/18(월)</strong>
    <span style="color:#94A3B8; margin:0 8px;">&mdash;</span>
    <span style="color:#334155;">탭1 모델 연동 + SHAP 분석 공유 + baseline_results.md 5종 완성</span>
  </div>
</div>
"""

html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Week 3 팀 미팅 — 모델 결과 해석</title>
<style>{CSS}</style>
</head>
<body>
<div class="deck" id="deck">
{SLIDES}
</div>

<div class="nav">
  <button onclick="go(-1)">&#8592; 이전</button>
  <button onclick="go(1)">다음 &#8594;</button>
</div>
<div class="progress" id="prog"></div>

<script>
const slides = document.querySelectorAll('.slide');
let cur = 0;
function show(n) {{
  slides[cur].classList.remove('active');
  cur = (n + slides.length) % slides.length;
  slides[cur].classList.add('active');
  document.getElementById('prog').textContent = (cur+1) + ' / ' + slides.length;
}}
function go(d) {{ show(cur+d); }}
document.addEventListener('keydown', e => {{
  if (e.key==='ArrowRight'||e.key==='ArrowDown'||e.key===' ') go(1);
  if (e.key==='ArrowLeft' ||e.key==='ArrowUp') go(-1);
}});
show(0);
</script>
</body>
</html>"""

html = (html
    .replace("IMG_PR",  img_pr)
    .replace("IMG_CMP", img_shap_cmp)
    .replace("IMG_BEE", img_shap_bee)
    .replace("IMG_WF",  img_shap_wf))

out = ROOT / "presentations" / "week3_meeting.html"
out.write_text(html, encoding="utf-8")
print(f"done -> {out}")
count = SLIDES.count('class="slide')
print(f"slides: {count}")
