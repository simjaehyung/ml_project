# 핸드오프 — 성장곡선 Walk-forward 평가 추가 (Track I 보강)

> 작성: 전체흐름(전략·발표) 방 | 2026-06-05 | 대상: 코드(실행) 방
> 성격: **착수 가이드 + 복붙 구현 프롬프트.** src/ 전용이라 앱 코드(hotel-dss-app/·app_pms/·llm_sim/)와 충돌 0.
> ⚠️ 이건 **발표 헤드라인 수치(W≈5.4만/84주)를 락하기 전에** 돌려봐야 하는 검증이다. 결과에 따라 곡선/전환주차가 바뀔 수 있음.

---

## 1. 왜 이걸 하나 (상황)

발표 thesis = **"우리 호텔 데이터가 쌓일수록 모델이 자라고, 다음 기간을 서빙한다."** 그런데 현재 Track I 성장곡선(`src/growth_curve.py`)의 **평가 방식이 그 thesis와 안 맞는다는 걸 발견**했다.

**현재 `growth_curve.py`가 하는 것:**
- 평가셋 = **고정된 마지막 6개월(2017-03~08, test_processed.csv)**, 절대 안 움직임.
- 매 주차 t에서 `arrival_week ≤ t`(point-in-time, expanding)로 학습 → **그 고정 6개월**을 예측 → PR-AUC.
- 5모델(Dummy/LR/RF/XGB/LGB), 구간별 경량 재튜닝, Bootstrap 95% CI, robust 전환주차 W.
- 현재 결과: 콜드스타트 LR 우위 → **W=84주/n≈53,615(≈5.4만)에서 LightGBM 추월·유지**, full 0.820.

**문제 3가지:**
1. **비현실** — "업데이트 주기 1달 → 다음 1달 예측"이 아니라, 초반 주차(2015년)가 **1.5년 뒤 고정 구간**을 예측. 배포 시나리오와 불일치.
2. **숨은 confound(중요)** — cutoff이 2017년 test에 가까워질수록 **train↔test 시간 간격이 줄어든다.** → 곡선 상승의 일부가 "데이터량"이 아니라 **"최근 데이터라서"(recency)**. "데이터가 모델을 고른다" 주장에 노이즈.
3. **계절 편향** — test가 여름 한 구간 고정.

---

## 2. 원하는 것 = Walk-forward (rolling-origin)

```
매 cutoff t:  arrival_week ≤ t 로 학습  →  arrival_week ∈ (t, t+H] 만 예측  →  t 전진
H = horizon, 기본 4주(≈1달)
```
- **배포 현실과 일치**(월간 재학습 → 다음 달), train↔test 간격이 항상 ~H로 **일정** → 먼-미래 아티팩트 제거.
- **정직한 단점(반드시 명시):** test 구간이 매번 움직여 **각 점이 다른 달**(난이도·계절 다름) → 곡선이 더 노이즈하고, 상승에 "어느 달이냐"가 섞임. 완전 무편향이 아니라 **편향을 맞바꾸는** 것.
- **결론: 고정-미래(현재)와 walk-forward 둘 다 산출**해서 나란히 비교 → 발표에선 walk-forward를 주력(배포 현실), 고정을 보조(통제 벤치마크)로 쓸지 결정.

---

## 3. 구현 가이드 프롬프트 (코드 방 복붙용)

```
[작업] src/growth_curve.py 에 walk-forward(rolling-origin) 평가 모드 추가.
기존 고정-test 동작은 100% 보존하고, --eval 플래그로 분기한다.

■ 배경(현재 코드)
- 현재: train=arrival_week≤t(expanding, point-in-time), test=고정 마지막 6개월(test_processed.csv).
  매 cutoff에서 그 고정 test를 평가. 5모델·구간별 경량 재튜닝·Bootstrap CI·robust W.

■ 추가할 것: --eval {fixed, walkforward}  (기본 fixed = 기존 동작 불변)
walkforward 모드 사양:
1) 데이터 풀 = train_processed + test_processed 를 시간순(abs_week)으로 합친 전체 타임라인.
   (test 구간이 이제 전체 시간축을 훑으므로 합쳐야 함.)
2) horizon H = --horizon N (주, 기본 4 ≈ 1달).
3) 각 cutoff t 에서:
   - 학습셋 = arrival_week ≤ t  (point-in-time 유지. 기존과 동일 규칙)
   - 평가셋 = arrival_week ∈ (t, t+H]  ← '다음 H주'만
   - (옵션 --strict: 평가셋을 booking_week ≤ t 인 것으로 추가 제한 = "지금 장부에 있는 다음달 예약"만. 기본 off.)
4) cutoff 범위 = MIN_N 충족 ~ (max_week − H). 끝 H주는 평가창 확보 위해 cutoff에서 제외.
5) 평가창 표본이 너무 적거나(<100) 단일 클래스면 그 cutoff 스킵(로그 남김).
6) 전처리는 기존 패턴 그대로: 학습셋에 get_dummies → 평가창을 학습 컬럼으로 reindex(fill 0),
   StandardScaler는 학습셋에만 fit. (country top10 전기간 누수 이슈는 별도 — 여기선 기존과 동일하게 두되 로그에 '미해결' 표기.)
7) KPI 3층 동일: PR-AUC + Bootstrap 95% CI(평가창에서 리샘플), Brier, expected cost.
   단 CI는 평가창 표본이 작아 넓어질 수 있음(정상).
8) 전환주차 W: 동일 robust 정의로 재계산하되, 움직이는 test라 tie가 많고 W가 불안정/없을 수 있음 — 그대로 정직하게 보고(억지로 만들지 말 것).

■ 산출물 (기존 파일 덮어쓰지 말 것 — 둘 다 보존해 비교)
- results/growth_curve_wf_raw.csv / growth_curve_wf_agg.csv / growth_curve_wf.png
- png에 horizon·"평가창=다음 H주"·여름 무관(전 구간) 명시. 고정-test 곡선과 형태 대비 코멘트.

■ 실행/검증
- python src/growth_curve.py                          # 기존 fixed (불변 확인)
- python src/growth_curve.py --eval walkforward --horizon 4   # 신규
- 콘솔에 cutoff별 (n_train, n_test, 주요 모델 PR-AUC) 진행 출력. UTF-8 stdout 패턴 유지.

■ 보고할 것 (결과 요약)
- walk-forward에서 LR→LightGBM 전환이 유지되나? W가 어디로 이동하나(또는 사라지나)?
- 곡선이 고정-test 대비 얼마나 노이즈한가? 계절(달)별 출렁임?
- 한 줄 결론: 발표 주력을 walk-forward로 가도 되는가, 아니면 둘 다 제시인가.

■ 제약
- src/·results/ 만 수정. 앱 코드 금지. 정전 수치는 결과로 갱신(임의 변경 금지).
```

---

## 4. 결과 후 결정할 것 (전체흐름 방)

- walk-forward에서 **전환이 유지 + W 안정** → 발표 주력 곡선을 walk-forward로 교체(배포 현실 + confound 제거). 고정-test는 "통제 벤치마크" 보조.
- **전환이 흔들리거나 W가 사라짐** → "데이터가 모델을 고른다"의 강도를 재서술(예: "특정 평가 기준에선…"). 정직하게 약화.
- 어느 쪽이든 **두 곡선을 나란히** 보여주고 평가 방식 차이를 1줄 각주로(정직성).
- 이 결과 나오기 전엔 **덱(v15)의 W=5.4만/84주 수치를 '잠정'으로** 두고 최종 락 보류.

---

## 5. 주의

- 이 작업은 **`src/`·`results/` 전용** — 앱 코드(hotel-dss-app/·app_pms/·llm_sim/)와 충돌 0. Next.js "변형판" 주의는 해당 없음(순수 Python).
- 기존 고정-test 산출물(`growth_curve_agg.csv` 등)은 **덮어쓰지 말 것**(현재 덱·design_18/20/22가 참조 중).

---

## 6. 학교서버 복붙 프롬프트 (자립형 — 구현+실행+보고 한 번에)

> ✅ **walk-forward는 2026-06-05 `src/growth_curve.py` 에 구현·로컬 스모크 완료.** 학교서버는 **pull + 실행만** 하면 된다(아래 [실행 전용]). [구현 참조]는 재구현용 백업.
> **H(horizon) = 업데이트 주기**, 기본 4주(≈1달).

### [실행 전용 — 권장]
```
git pull                                   # walk-forward 구현된 growth_curve.py 받기
python src/preprocessing_pipeline.py       # processed 데이터 재생성(gitignore)
python src/growth_curve.py --eval walkforward --horizon 4 --quick        # 스모크(빠름)
nohup python src/growth_curve.py --eval walkforward --horizon 4 > logs/gc_wf.log 2>&1 &   # 풀런
python src/growth_curve.py                 # (sanity) fixed 재생성 → 기존 0.820/W84 재현 확인
# 보고: results/growth_curve_wf_agg.csv 의 LR↔LightGBM 전환주차 W / 곡선 노이즈 / fixed 대비 차이
# 커밋: results/growth_curve_wf_* + (sanity 통과 시) 푸시
```
산출물: `results/growth_curve_wf_{raw,agg}.csv`, `results/growth_curve_wf.png` (fixed 산출물과 분리, 안 덮어씀).

### [구현 참조 — 이미 구현됨, 재구현 필요시만]
> 아래는 위 코드가 이미 담고 있는 사양. 서버에서 코드를 다시 짤 필요 없음(pull로 받음).

```
[학교서버 — Hotel DSS Track I walk-forward 재실행]
목표: 성장곡선을 "가진 데이터로 다음 H주(다음 업데이트 기간)를 예측" 방식(walk-forward)으로 재산출.
현재 src/growth_curve.py 는 고정-test(마지막 6개월)만 평가 → 배포 현실 불일치 + recency confound. 이를 고친다.

[0] 준비
git pull
pip install -r requirements.txt        # 필요시
python src/preprocessing_pipeline.py   # train/test_processed.csv 재생성(gitignore라 서버에 없을 수 있음)

[1] src/growth_curve.py 에 walk-forward 평가 모드 추가 (기존 fixed 동작 100% 보존, --eval 분기)
 - 인자: --eval {fixed,walkforward} (기본 fixed) / --horizon N (주, 기본 4)
 - walkforward 사양:
   · 데이터 = train_processed + test_processed 합쳐 시간순(abs_week) 전체 타임라인
   · 각 cutoff t: 학습 = arrival_week ≤ t (point-in-time, 기존 규칙 유지), 평가 = arrival_week ∈ (t, t+H]
   · cutoff 범위 = MIN_N 충족 ~ (max_week − H). 끝 H주는 평가창 확보 위해 제외
   · 평가창 표본 <100 또는 단일클래스면 그 cutoff 스킵(로그)
   · 전처리 동일: 학습셋 get_dummies → 평가창을 학습 컬럼으로 reindex(fill 0), StandardScaler는 학습셋만 fit
   · KPI 동일: PR-AUC + Bootstrap 95% CI(평가창 리샘플), Brier, expected cost
   · 전환주차 W: 동일 robust 정의로 재계산하되, 움직이는 test라 tie가 많고 W가 불안정/없을 수 있음 → 억지로 만들지 말고 그대로 보고
   · 산출물 분리(기존 파일 덮어쓰기 금지): results/growth_curve_wf_raw.csv, growth_curve_wf_agg.csv, growth_curve_wf.png
   · 파일 상단의 sys.stdout=TextIOWrapper(UTF-8) 패턴 유지(콘솔 한글 깨짐 방지)
   · (옵션 --strict: 평가창을 booking_week ≤ t 인 것으로 추가 제한 = "지금 장부에 있는 다음달 예약만". 기본 off)

[2] 스모크 → 풀런
python src/growth_curve.py --eval walkforward --horizon 4 --quick   # 동작 확인(소요 짧음)
nohup python src/growth_curve.py --eval walkforward --horizon 4 > logs/gc_wf.log 2>&1 &   # 풀런(백그라운드)
python src/growth_curve.py                                          # 고정-test도 재생성(비교 기준, 기존과 동일해야 함)

[3] 보고 + 커밋
 - LR→LightGBM 전환이 walk-forward에서도 유지되나? W가 어디로 이동(또는 사라짐)?
 - 고정-test 대비 곡선이 얼마나 노이즈/계절 출렁임?
 - 한 줄 결론: 발표 주력 곡선을 walk-forward로 가도 되는가.
 - results/growth_curve_wf_* + 수정된 src/growth_curve.py 커밋·푸시.

[제약] src/·results/ 만 수정. 앱코드(hotel-dss-app/·app_pms/·llm_sim/) 금지. 정전 수치는 결과로 갱신(임의 변경 금지).
```

> ⚠️ 이 프롬프트는 서버가 직접 ML 평가코드를 구현하므로, point-in-time·평가창 정의를 위 사양대로 정확히 지켰는지 **결과 곡선으로 sanity check**할 것(예: 고정-test 재생성이 기존 0.820/W84와 일치해야 구현이 옳음).
