# Week 3 계획 — PM 상세 문서

> 작성: 심재형 (PM) | 기준일: 2026-05-11 (5/11 의존성 재설계)
> 대상 기간: 2026-05-12 ~ 2026-05-18 (월)
> Gate: **5/18 모델 동결** — 이후 피처·모델 변경 금지

---

## 0. Week 2 이월 사항 (시작 전 처리)

| 항목 | 내용 | 담당 | 기한 |
|------|------|------|------|
| **deposit_type 공지 수정** | 노션 "Week 2 작업흐름 현황" 테이블에 KEEP으로 기록됨 → DROP으로 수정 공지 필요 | 심재형 | ✅ 완료 |
| **파이프라인 기준 재공지** | train_processed.csv (33컬럼) 기준, cat_cols에서 deposit_type 제거 | 심재형 | ✅ 완료 |
| RF baseline 정식 수치 | 노션 결과(0.8143)는 구버전. 정식: 0.7785 (`src/run_baselines.py` 기준) | 심재형 | ✅ 완료 |
| previous_cancellations EDA | 이고은 완료 (커밋 e7b4be1). B2B 블록 패턴 발견 → Week 3 SHAP 감시 항목 추가 | ✅ 확인 완료 | — |

---

## 1. Week 3 목표

**XGBoost 학습 → 인터페이스 확정 → 이고은 탭1 연동. LightGBM은 5/16 이전 도착 시 비교에 반영.**

5/18까지 모델이 동결되지 않으면 Week 4 SHAP·앱 개발이 밀린다. Gate 엄수.

---

## 2. 의존성 설계 원칙

```
심재형 XGBoost ──→ 인터페이스 규격 확정 ──→ 이고은 연동 시작
                        (5/13 이전)
김나리 LightGBM ─────────────────→ 5/16 정오까지 수치 도착 시 비교·선정에 반영
```

**핵심 근거:** XGBoost와 LightGBM의 `predict_proba()` 출력 포맷은 동일. 인터페이스를 먼저 잡고 연동해도 최종 모델 교체 시 파일명만 바꾸면 된다.

---

## 3. 타임라인

```
5/12(화) ~ 5/13(수)  심재형 독립 트랙 + 이고은 탭1 뼈대
  심재형  │ XGBoost 학습 완료 + PR-AUC·F1 노션 기록
          │ ★ 모델 출력 인터페이스 규격 문서화 → 이고은에게 전달 (5/13 자정 전)
  이고은  │ 탭1 뼈대 구현 (예약 리스트 + 위험도 컬럼)
  김나리  │ LightGBM 학습 시작 (독립 진행)

5/14(목)  심재형 PR curve 4종 완성
  심재형  │ PR curve 4종 통합 (Dummy·LR·RF·XGB) → results/pr_curve_xgb.png
          │ XGBoost 잠정 동결 선언 (김나리 LGBM 대기 상태)
  이고은  │ 인터페이스 규격 기반 탭1 연동 시작
  김나리  │ LightGBM 학습 계속

5/15(금) ~ 5/16(토)  비교·확정
  심재형  │ LGBM 수치 합류 시 → PR curve 5종으로 갱신 + 최종 선정
          │ 5/16 정오 기준 수치 미합류 시 → XGBoost 최종 확정
  이고은  │ 탭1 연동 완성도 향상 (모델 교체 여부 무관하게 계속 진행)
  김나리  │ ★ 5/16 정오 이전 PR-AUC + F1 노션 기록

──── 5/16 정오: 김나리 LGBM 수치 데드라인 ────

5/17(일) ~ 5/18(월)  동결 + 마무리
  심재형  │ 최종 모델 results/model_final.pkl 저장
          │ 5종 비교표 최종본 작성 (LGBM 수치 있으면 포함, 없으면 4종)
          │ ★ SHAP 퀵 체크 (5/18 모델 동결 직후, 30분)
          │   → previous_cancellations 상위 독식 여부만 확인
          │   → 독식 확인 시 Phase 2 ablation 우선순위 상향 결정
          │ ★ EDA master 채널·BQS 섹션 수치 확인 + BQS 변수 후보 노트 (0.5일)
  이고은  │ 탭1 완성도 마무리
  김나리  │ 전 모델 비교표 보조 작성 (LGBM 수치 있는 경우)

─────────────────────────────────────────────
  5/18(월)  Gate: 모델 동결. 이후 피처·모델 변경 금지.
─────────────────────────────────────────────
```

---

## 4. 팀원별 상세

### 심재형

| 항목 | 산출물 | 기한 | 선행 조건 |
|------|--------|------|---------|
| **XGBoost 학습** | PR-AUC + F1@0.5 노션 기록 | 5/13 | 없음 |
| **모델 출력 인터페이스 규격 작성** | `docs/model_interface.md` → 이고은 전달 | 5/13 | XGBoost 완료 |
| PR curve 4종 (Dummy·LR·RF·XGB) | `results/pr_curve_xgb.png` | 5/14 | XGBoost 완료 |
| 모델 최종 선정 | XGBoost or LGBM | 5/16 | XGBoost 완료 (LGBM 선택지) |
| PR curve 5종 갱신 (LGBM 도착 시) | `results/pr_curve_all.png` | 5/16 | 김나리 수치 |
| 최종 모델 저장 | `results/model_final.pkl` | 5/18 | 모델 선정 완료 |

### 이고은

| 항목 | 산출물 | 기한 | 선행 조건 |
|------|--------|------|---------|
| 탭1 뼈대 구현 | 예약 리스트 + 위험도 컬럼 레이아웃 | 5/13 | 없음 |
| 인터페이스 규격 수신 | `docs/model_interface.md` 확인 | 5/13 | 심재형 전달 |
| 탭1 모델 연동 | predict_proba 배열 기반 위험도 표시 | 5/15~16 | 인터페이스 규격 |
| 탭1 완성도 향상 | 정렬·필터·위험 등급 표시 | 5/17~18 | 없음 |

> **이고은 독립성 보장:** 심재형이 5/13까지 인터페이스 규격 전달 → 이후 작업은 최종 모델 선정 결과에 무관하게 진행.  
> 모델이 XGBoost→LightGBM으로 교체되더라도 `predict_proba` 포맷 동일 → 코드 변경 없음.

### 김나리

| 항목 | 설정 | 산출물 | 데드라인 |
|------|------|--------|---------|
| LightGBM 학습 | `n_estimators=100, random_state=42, verbose=-1` | PR-AUC + F1@0.5 | ★ **5/16 정오** |
| 입력 파일 | **`train_processed.csv`** (33컬럼) | — | — |
| cat_cols | deposit_type **제외** | — | — |
| 노션 기록 | 수치 기록 후 심재형에게 공유 | 노션 기재 | 5/16 정오 |

> 5/16 정오 기준으로 확보된 수치로 최종 선정을 진행한다. LGBM 수치가 이후 나오면 `results/baseline_results.md`에 추가 기록하고 Phase 2 참고용으로 보관.

---

## 5. 모델 출력 인터페이스 규격 (5/13 전달 내용)

심재형이 이고은에게 전달할 내용 (`docs/model_interface.md`):

```python
# 모델 로드
import pickle
model = pickle.load(open("results/model_final.pkl", "rb"))

# 예측
proba = model.predict_proba(X_te)[:, 1]   # shape: (n_samples,) — 취소 확률 0~1

# 탭1 연동 형태
df["cancel_risk"] = proba
df_sorted = df.sort_values("cancel_risk", ascending=False)
```

XGBoost·LightGBM 모두 위 형태 동일. 최종 모델이 바뀌어도 pkl 파일명만 교체하면 됨.

---

## 6. 파이프라인 기준 (Week 3 전원 공통)

```python
# 입력
train = pd.read_csv("data/train_processed.csv")   # 33컬럼
test  = pd.read_csv("data/test_processed.csv")    # 33컬럼

# OHE — deposit_type 없음, country_grouped 사용
cat_cols = ["hotel", "meal", "market_segment", "distribution_channel",
            "reserved_room_type", "customer_type", "country_grouped"]

train_e = pd.get_dummies(train, columns=cat_cols)
test_e  = pd.get_dummies(test,  columns=cat_cols)
test_e  = test_e.reindex(columns=train_e.columns, fill_value=0)

X_tr = train_e.drop("is_canceled", axis=1)
y_tr = train_e["is_canceled"]
X_te = test_e.drop("is_canceled", axis=1)
y_te = test_e["is_canceled"]
# OHE 후 컬럼 수: 70개
```

**스케일링:** XGBoost·LightGBM 모두 불필요 (트리 기반)

---

## 7. 미결 #3 해소 — 모델 확정 기준

### 제안 합의안

> PR-AUC 차이가 0.01 미만이면 LightGBM 선택 (속도·메모리 우위).  
> 0.01 이상 차이나면 PR-AUC 높은 쪽 선택.  
> **5/16 정오까지 LGBM 수치 없으면 XGBoost 단독 확정 — 추가 합의 불필요.**

### 후보 기준

| 기준 | 설명 | 비고 |
|------|------|------|
| PR-AUC 최고값 | 가장 단순하고 명확 | 수치 차이 작으면 타이브레이커 필요 |
| 속도 | LightGBM이 일반적으로 XGBoost보다 빠름 | 대용량 데이터에서 유의미 |
| SHAP 호환성 | 둘 다 TreeSHAP 지원 — 동등 | 차이 없음 |
| 재현성 | `random_state=42` 고정 — 동등 | 차이 없음 |

---

## 8. SHAP 감시 항목 (Week 3 모델 돌리면서 미리 인지)

| 항목 | 근거 | 감시 내용 |
|------|------|---------|
| `deposit_type` | Non Refund 99.2% 취소율 (B2B 패턴) — 이미 DROP | SHAP에서 잔존 신호 여부 |
| `previous_cancellations` | ≥1 그룹 취소율 94.97%, 89%가 B2B 블록 패턴 | SHAP 상위 독식 여부. deposit_type 제거 후 대리 변수로 올라왔을 가능성 |

두 변수가 동시에 SHAP 상위를 독식하면 B2B 패턴 신호의 중복 포착 → Phase 2 ablation 우선순위 상향.

---

## 9. Gate 조건 (5/18 동결 기준)

| 조건 | 기준 | 필수 여부 |
|------|------|---------|
| XGBoost PR-AUC 기록 | 노션에 수치 있어야 함 | ✅ 필수 |
| 최종 모델 1개 선정 | PM 확정 | ✅ 필수 |
| `results/model_final.pkl` 저장 | XGBoost or LightGBM | ✅ 필수 |
| 이고은 탭1 모델 연동 | predict_proba 기반 위험도 표시 | ✅ 필수 |
| `results/baseline_results.md` | 4종 이상 비교표 (LGBM 있으면 5종) | ✅ 필수 |
| LightGBM PR-AUC 기록 | 노션에 수치 있어야 함 | ⚠️ 권장 (없으면 XGBoost 확정) |
| PR curve 5종 그래프 | LGBM 포함 비교 | ⚠️ 권장 (없으면 4종으로 대체) |

Gate 통과 못 하면 Week 4 SHAP·앱 일정 전체가 밀린다. 5/17(일) 심재형 점검 시 필수 항목 미달이면 당일 긴급 완료.
