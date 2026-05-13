"""
shap_analysis.py
XGBoost + LightGBM 양쪽 TreeSHAP 분석

산출물:
  results/model_xgb.pkl          - XGBoost 모델 (단독 저장)
  results/model_lgbm.pkl         - LightGBM 모델 (단독 저장)
  results/shap_xgb_bar.png       - XGBoost global 중요도 bar
  results/shap_lgbm_bar.png      - LightGBM global 중요도 bar
  results/shap_xgb_beeswarm.png  - XGBoost beeswarm
  results/shap_lgbm_beeswarm.png - LightGBM beeswarm
  results/shap_comparison.png    - 두 모델 나란히 비교
  results/shap_waterfall.png     - 최고위험 예약 개별 설명 (LGBM 기준)
  results/shap_report.md         - 비교표 + 감시 결과 + 액션

실행:
  python src/shap_analysis.py
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Malgun Gothic"   # Windows 한글 폰트
plt.rcParams["axes.unicode_minus"] = False
import shap
from pathlib import Path
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

ROOT    = Path(__file__).parent.parent
DATA    = ROOT / "data"
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)

SHAP_SAMPLE = 3000  # beeswarm 시각화용 샘플 수

# ── 1. 로드 + OHE ────────────────────────────────────────────────────────────
train = pd.read_csv(DATA / "train_processed.csv")
test  = pd.read_csv(DATA / "test_processed.csv")
print(f"로드  train {train.shape}  test {test.shape}")

cat_cols = ["hotel", "meal", "market_segment", "distribution_channel",
            "reserved_room_type", "customer_type", "country_grouped"]

train_e = pd.get_dummies(train, columns=cat_cols)
test_e  = pd.get_dummies(test,  columns=cat_cols)
test_e  = test_e.reindex(columns=train_e.columns, fill_value=0)

X_tr = train_e.drop("is_canceled", axis=1)
y_tr = train_e["is_canceled"]
X_te = test_e.drop("is_canceled", axis=1)
y_te = test_e["is_canceled"]

feature_names = list(X_tr.columns)
print(f"OHE 후  X_tr {X_tr.shape}  X_te {X_te.shape}  피처 {len(feature_names)}개\n")

# ── 2. 모델 학습 / 로드 ───────────────────────────────────────────────────────
def load_or_train(pkl_path, model_cls, model_kwargs, X, y, label):
    if pkl_path.exists():
        print(f"[{label}] pkl 로드 ← {pkl_path.name}")
        with open(pkl_path, "rb") as f:
            return pickle.load(f)
    print(f"[{label}] 학습 중...")
    m = model_cls(**model_kwargs)
    m.fit(X, y)
    with open(pkl_path, "wb") as f:
        pickle.dump(m, f)
    print(f"  저장 → {pkl_path}")
    return m

xgb = load_or_train(
    RESULTS / "model_xgb.pkl",
    XGBClassifier,
    {"n_estimators": 100, "random_state": 42,
     "eval_metric": "logloss", "verbosity": 0, "n_jobs": -1},
    X_tr, y_tr, "XGBoost",
)

lgb = load_or_train(
    RESULTS / "model_lgbm.pkl",
    LGBMClassifier,
    {"n_estimators": 100, "random_state": 42, "verbose": -1, "n_jobs": -1},
    X_tr, y_tr, "LightGBM",
)

# model_final.pkl 은 LightGBM 이 맞는지 확인용으로만 — 덮어쓰지 않음
print()

# ── 3. SHAP 샘플 선택 ─────────────────────────────────────────────────────────
np.random.seed(42)
idx_sample = np.random.choice(len(X_te), size=min(SHAP_SAMPLE, len(X_te)), replace=False)
X_shap = X_te.iloc[idx_sample].reset_index(drop=True)
print(f"SHAP 샘플  {len(X_shap):,}행\n")

# ── 4. TreeSHAP 계산 ──────────────────────────────────────────────────────────
print("[XGBoost] TreeSHAP 계산...")
exp_xgb = shap.TreeExplainer(xgb)
sv_xgb  = exp_xgb.shap_values(X_shap)
ev_xgb  = exp_xgb.expected_value
if isinstance(sv_xgb, list):   # 구버전 호환
    sv_xgb = sv_xgb[1]
if isinstance(ev_xgb, (list, np.ndarray)):
    ev_xgb = ev_xgb[1]
print(f"  sv_xgb shape: {sv_xgb.shape}")

print("[LightGBM] TreeSHAP 계산...")
exp_lgb = shap.TreeExplainer(lgb)
sv_lgb  = exp_lgb.shap_values(X_shap)
ev_lgb  = exp_lgb.expected_value
if isinstance(sv_lgb, list):
    sv_lgb = sv_lgb[1]
if isinstance(ev_lgb, (list, np.ndarray)):
    ev_lgb = ev_lgb[1]
print(f"  sv_lgb shape: {sv_lgb.shape}\n")

# ── 5. mean |SHAP| 중요도 ─────────────────────────────────────────────────────
def shap_importance(sv, feat_names, top_n=20):
    imp = np.abs(sv).mean(axis=0)
    df  = pd.DataFrame({"feature": feat_names, "importance": imp})
    return df.sort_values("importance", ascending=False).head(top_n).reset_index(drop=True)

top_xgb = shap_importance(sv_xgb, feature_names)
top_lgb = shap_importance(sv_lgb, feature_names)

def pc_rank(df):
    mask = df["feature"] == "previous_cancellations"
    return int(df[mask].index[0]) + 1 if mask.any() else "> 20"

rank_xgb = pc_rank(top_xgb)
rank_lgb = pc_rank(top_lgb)
print(f"[감시] previous_cancellations — XGB: {rank_xgb}위  LGBM: {rank_lgb}위")

# ── 6. 플롯 ───────────────────────────────────────────────────────────────────

# 6-1. Bar: XGBoost
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(top_xgb["feature"][::-1], top_xgb["importance"][::-1], color="seagreen")
ax.set_xlabel("Mean |SHAP value|")
ax.set_title("XGBoost — Top 20 Feature Importance (SHAP)")
ax.grid(axis="x", alpha=0.3)
plt.tight_layout()
fig.savefig(RESULTS / "shap_xgb_bar.png", dpi=120)
plt.close(fig)
print("저장 → shap_xgb_bar.png")

# 6-2. Bar: LightGBM
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(top_lgb["feature"][::-1], top_lgb["importance"][::-1], color="crimson")
ax.set_xlabel("Mean |SHAP value|")
ax.set_title("LightGBM ★ — Top 20 Feature Importance (SHAP)")
ax.grid(axis="x", alpha=0.3)
plt.tight_layout()
fig.savefig(RESULTS / "shap_lgbm_bar.png", dpi=120)
plt.close(fig)
print("저장 → shap_lgbm_bar.png")

# 6-3. Beeswarm: XGBoost
plt.figure(figsize=(10, 8))
shap.summary_plot(sv_xgb, X_shap, feature_names=feature_names,
                  max_display=20, show=False)
plt.title("XGBoost — SHAP Beeswarm (Top 20)")
plt.tight_layout()
plt.savefig(RESULTS / "shap_xgb_beeswarm.png", dpi=120, bbox_inches="tight")
plt.close()
print("저장 → shap_xgb_beeswarm.png")

# 6-4. Beeswarm: LightGBM
plt.figure(figsize=(10, 8))
shap.summary_plot(sv_lgb, X_shap, feature_names=feature_names,
                  max_display=20, show=False)
plt.title("LightGBM ★ — SHAP Beeswarm (Top 20)")
plt.tight_layout()
plt.savefig(RESULTS / "shap_lgbm_beeswarm.png", dpi=120, bbox_inches="tight")
plt.close()
print("저장 → shap_lgbm_beeswarm.png")

# 6-5. 나란히 비교 bar
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
ax1.barh(top_xgb["feature"][::-1], top_xgb["importance"][::-1], color="seagreen")
ax1.set_xlabel("Mean |SHAP value|")
ax1.set_title("XGBoost Top 20")
ax1.grid(axis="x", alpha=0.3)
ax2.barh(top_lgb["feature"][::-1], top_lgb["importance"][::-1], color="crimson")
ax2.set_xlabel("Mean |SHAP value|")
ax2.set_title("LightGBM ★ Top 20")
ax2.grid(axis="x", alpha=0.3)
plt.suptitle("SHAP Feature Importance 비교 — XGBoost vs LightGBM (★ = 최종 선정)", fontsize=13)
plt.tight_layout()
fig.savefig(RESULTS / "shap_comparison.png", dpi=120)
plt.close(fig)
print("저장 → shap_comparison.png")

# 6-6. Waterfall: 최고위험 예약 1건 (LightGBM 기준)
proba_shap = lgb.predict_proba(X_shap)[:, 1]
top_idx    = int(np.argmax(proba_shap))

try:
    explanation = shap.Explanation(
        values      = sv_lgb[top_idx],
        base_values = float(ev_lgb),
        data        = X_shap.iloc[top_idx].values,
        feature_names = feature_names,
    )
    plt.figure(figsize=(10, 6))
    shap.plots.waterfall(explanation, max_display=15, show=False)
    plt.title(f"LightGBM Waterfall — 최고위험 예약 (p={proba_shap[top_idx]:.3f})")
    plt.tight_layout()
    plt.savefig(RESULTS / "shap_waterfall.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("저장 → shap_waterfall.png")
except Exception as e:
    # SHAP 버전 호환 실패 시 manual bar chart 대체
    print(f"  waterfall 신규 API 실패 ({e}), 대체 bar chart 저장")
    sv_row    = sv_lgb[top_idx]
    feat_imp  = pd.DataFrame({"feature": feature_names, "shap": sv_row})
    feat_imp  = feat_imp.reindex(feat_imp["shap"].abs().sort_values(ascending=False).index)
    feat_imp  = feat_imp.head(15)
    fig, ax   = plt.subplots(figsize=(9, 6))
    colors    = ["crimson" if v > 0 else "steelblue" for v in feat_imp["shap"]]
    ax.barh(feat_imp["feature"][::-1], feat_imp["shap"][::-1], color=colors[::-1])
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("SHAP value")
    ax.set_title(f"LightGBM Individual SHAP — 최고위험 예약 (p={proba_shap[top_idx]:.3f})")
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    fig.savefig(RESULTS / "shap_waterfall.png", dpi=120)
    plt.close(fig)
    print("저장 → shap_waterfall.png (대체)")

# ── 7. shap_report.md ─────────────────────────────────────────────────────────
def top_table_md(df, model_name, star=""):
    lines = [
        f"### {model_name}{star} Top 20",
        "| Rank | Feature | Mean \\|SHAP\\| |",
        "|------|---------|--------------|",
    ]
    for i, row in df.iterrows():
        lines.append(f"| {i+1} | `{row['feature']}` | {row['importance']:.4f} |")
    return "\n".join(lines)

# B2B 신호 판단
def is_top3(rank):
    return isinstance(rank, int) and rank <= 3

b2b_alert = is_top3(rank_xgb) or is_top3(rank_lgb)
b2b_msg = (
    "⚠️ **상위 3위 이내 — B2B 블록 대리 변수 가능성 높음. Phase 2 ablation 우선순위 상향.**"
    if b2b_alert else
    "✅ 상위 3위 밖 — 현재는 허용 범위 내. Phase 2에서 ablation 예정대로 진행."
)

# 두 모델 top-10 공통 피처
top10_xgb = set(top_xgb["feature"][:10])
top10_lgb = set(top_lgb["feature"][:10])
common    = sorted(top10_xgb & top10_lgb)
only_xgb  = sorted(top10_xgb - top10_lgb)
only_lgb  = sorted(top10_lgb - top10_xgb)

report = f"""# SHAP 분석 리포트

생성일: 2026-05-12 | 샘플: {len(X_shap):,}행 (테스트셋 무작위) | 최종 선정 모델: LightGBM ★

---

## 1. 모델별 Top 20 피처 중요도

{top_table_md(top_xgb, "XGBoost")}

{top_table_md(top_lgb, "LightGBM", " ★")}

---

## 2. Top-10 피처 비교

| 구분 | 피처 |
|------|------|
| 공통 (양쪽 Top 10) | {", ".join(f"`{f}`" for f in common) if common else "없음"} |
| XGBoost 전용 | {", ".join(f"`{f}`" for f in only_xgb) if only_xgb else "없음"} |
| LightGBM 전용 | {", ".join(f"`{f}`" for f in only_lgb) if only_lgb else "없음"} |

---

## 3. previous_cancellations B2B 신호 감시

| 모델 | 순위 |
|------|------|
| XGBoost | {rank_xgb}위 |
| LightGBM | {rank_lgb}위 |

{b2b_msg}

---

## 4. 플롯 파일

| 파일 | 내용 |
|------|------|
| `shap_xgb_bar.png` | XGBoost global 중요도 (bar) |
| `shap_lgbm_bar.png` | LightGBM global 중요도 (bar) |
| `shap_xgb_beeswarm.png` | XGBoost beeswarm (방향성 포함) |
| `shap_lgbm_beeswarm.png` | LightGBM beeswarm (방향성 포함) |
| `shap_comparison.png` | 두 모델 나란히 비교 |
| `shap_waterfall.png` | 최고위험 예약 개별 설명 (LGBM, 앱 데모용) |

---

## 5. 액션 항목

- [ ] previous_cancellations 순위 확인 후 Phase 2 ablation 우선순위 결정 (미결 #6)
- [ ] SHAP top 피처 기반 ACTION 규칙 초안 작성 (미결 #5)
- [ ] 임계값 결정 시 beeswarm 방향성 참고 — 높은 값이 취소 위험 올리는 피처 파악 (미결 #4)
- [ ] 앱 탭1: `shap_lgbm_bar.png` 전역 중요도 패널로 활용
- [ ] 앱 탭2 Flexi: 개별 예약 waterfall → `shap_waterfall.png` 로직 재사용
"""

(RESULTS / "shap_report.md").write_text(report, encoding="utf-8")
print("저장 → shap_report.md")

# ── 8. 최종 요약 ──────────────────────────────────────────────────────────────
print("\n" + "=" * 55)
print(f"previous_cancellations: XGB {rank_xgb}위  LGBM {rank_lgb}위")
print(f"B2B 경보: {'ON ⚠' if b2b_alert else 'OFF ✅'}")
print(f"공통 Top-10 피처 ({len(common)}개): {', '.join(common[:5])}{'...' if len(common) > 5 else ''}")
print("=" * 55)
print("\n산출물:")
for f in ["model_xgb.pkl", "model_lgbm.pkl",
          "shap_xgb_bar.png", "shap_lgbm_bar.png",
          "shap_xgb_beeswarm.png", "shap_lgbm_beeswarm.png",
          "shap_comparison.png", "shap_waterfall.png",
          "shap_report.md"]:
    print(f"  results/{f}")
