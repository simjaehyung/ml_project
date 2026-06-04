# 학교서버 Claude 에이전트 핸드오프 — 트랙 I 성장곡선 실행

> 용도: 학교서버의 Claude Code 에이전트에게 **아래 블록을 그대로 복사·붙여넣기**.
> 트랙 I(성장곡선)은 순수 ML·CPU 작업이라 **API 키 불필요**. 노트북에서 4시간+ 걸려 서버로 이관.

---

## 📋 복사해서 학교서버 Claude에게 줄 프롬프트

```
You are running on a school compute server. Task: run the "Track I growth-curve"
ML experiment for the Hotel No-Show DSS project, then report results.

## Context
- Repo: https://github.com/simjaehyung/ml_project.git  (branch: main)
- Project: hotel booking cancellation prediction. Track I tests HOW the best model
  CLASS changes as our hotel's data accumulates week by week (cold-start → grown).
- Pure ML, CPU-only. NO API key / no LLM call needed for this task.

## Setup
1. git clone (or cd existing repo && git pull) main.
2. Python 3.10+ env with deps:  pip install -r requirements.txt
   (must include: pandas numpy scikit-learn xgboost lightgbm matplotlib)
3. Processed data is gitignored — regenerate from the raw CSVs that ARE in the repo:
       python src/preprocessing_pipeline.py
   → reads data/train.csv, data/test.csv → writes data/{train,test}_processed.csv

## Run
1. Smoke first (~1 min, verify env is OK):
       python src/growth_curve.py --quick
   Expect: 5 cutoffs × {cumulative,sliding}, prints "전환주차 W",
   writes results/growth_curve_{raw,agg}.csv + results/growth_curve.png
2. Full run (the definitive one for the presentation):
       python src/growth_curve.py
   Config: ~70 weekly cumulative cutoffs, seeds [42,7,123], bootstrap 1000,
   cumulative + sliding(26w) windows. Heavy (multi-hour on 1 machine; faster with
   many cores — RF/XGB/LGB use n_jobs=-1). Output is line-buffered: watch per-cutoff progress.
   - Faster presentable alternative if time-limited:
       python src/growth_curve.py --stride 3 --seeds 1 --boot 300   (~20 cutoffs, minutes)

## What the script does (sanity-check points)
- Time axis: weekly CUMULATIVE (expanding) + SLIDING (26-week) over arrival-date weeks.
- point-in-time labels: only bookings with arrival_week <= t are used (NO look-ahead leakage).
- 5 models: Dummy, LogReg, RandomForest, XGBoost, LightGBM — each with LIGHTWEIGHT
  per-cutoff retune (1 regularization axis, selected via train-internal time-order holdout).
- KPI: PR-AUC + bootstrap 95% CI (for LR & LightGBM), Brier score, expected cost (cost ratios 2/5/10).
- Headline output: transition week W = first cumulative week where LightGBM CI-low > LR CI-high.

## Report back to the user
- results/growth_curve.png (the curve)
- transition week W (precise)
- final-cutoff model ranking (PR-AUC, Brier)
- confirm the thesis: does LR win at small data and LightGBM overtake at large data? at which week do CIs separate?
- total runtime
- Commit results back so the team can pull:
       git add results/growth_curve_raw.csv results/growth_curve_agg.csv results/growth_curve.png
       git commit -m "results: Track I growth curve (school server full run)"
       git push origin main
  (If no push access, just paste the W value + final ranking + attach the PNG.)

## Expected finding (from laptop 5-point smoke — confirm & refine)
- week 28 (small data):  LR PR-AUC ~0.48  >>  LightGBM ~0.36   → LR wins
- week 88 (large data):  LightGBM ~0.81  >  LR ~0.78  (CIs separated) → boosting overtakes
- Thesis: "small data → simple model; large data → boosting. The growth system must NOT
  fix one model." Visual crossover ~week 60-65; statistical (CI-separated) overtake later.
  Pinpoint the exact W.

If anything fails (missing dep, data path, encoding), report the exact error and stop —
do not silently skip steps.
```

---

## 결과 회수 방법 (재형님)

학교서버 Claude가 `git push`하면:
```
git pull origin main
```
→ `results/growth_curve.png` + `growth_curve_agg.csv`에 full 결과(정밀 전환주차 W·매끄러운 곡선) 들어옴.

push 권한이 없으면 W값·최종순위·PNG만 받아서 알려주세요 — 제가 해석·발표 반영하겠습니다.

## 참고
- 상세 설계: `docs/design_18_growth_curve_implementation.md`
- 실행 스크립트: `src/growth_curve.py` (이번에 `--stride`, line-buffered 진행표시 추가)
- 노트북 스모크 결과(미리보기): `results/growth_curve.png` (5점판 — full로 교체됨)
