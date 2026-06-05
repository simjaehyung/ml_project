# 전처리 재점검 메모 — 2026-06-04

> 작성: PM 자율작업 (재형님 저녁 중) | 성격: **재점검 결과 + 의사결정 안건**
> 계기: 윤리 지뢰(국적 피처) 논의 → "우리가 어떻게 전처리해왔는지 다시 보자"
> 점검 대상: `src/preprocessing_pipeline.py`, `src/growth_curve.py`, `docs/design_04_preprocessing_decisions.md`
> 결론 미리: **성장곡선은 합의된 전처리로 정상 실행됨(A-1). 단 누수 1건(A-2)·윤리 1건(A-3)을 발표 전 처리해야 함.**

---

## A-1. 성장곡선은 "합의된 전처리"로 돌았는가? → 예 (확인 완료)

git 추적 결과:
- `preprocessing_pipeline.py` 마지막 변경 = `e880a8a`(deposit_type DROP, **5월**). 오늘(6/4) **안 바뀜**.
- 오늘 커밋은 `growth_curve.py`·`results/growth_curve.*`·문서만 변경.
- 학교서버 full run(`86cbad9`)은 `git pull && python preprocessing_pipeline.py && python growth_curve.py` 순서 → **레포의 표준 파이프라인으로 생성된 processed 데이터** 사용.
- `growth_curve.py`는 `train_processed.csv` / `test_processed.csv`를 로드(line 218~223). ✅

→ **"논의 끝에 만든 새 전처리안"은 레포에 존재하지 않는다.** 성장곡선 = `design_04`의 5/11 확정 전처리 그대로.
> ❓ 재형님이 떠올린 "새 전처리안"이 다른 작업방의 것이라면 무엇인지 확인 필요. 현재 레포 기준으론 변경 없음.

**부수 확인 — point-in-time 처리(누수 방지)는 대체로 잘 돼 있음:**
- 라벨: `arrival_week ≤ t`만 학습 → look-ahead 차단 ✅ (design_18 §2.2 그대로 구현)
- 스케일러: 구간 train_sub에만 fit ✅
- OHE: 구간별 `get_dummies` 후 test를 `reindex` → 그 구간에 등장한 카테고리만 사용 ✅

---

## A-2. ⚠️ 누수 — country Top10이 "전체 80주"로 결정됨 (point-in-time 위반)

**현상:** `preprocessing_pipeline.py:55`
```python
top10_countries = train["country"].value_counts().nlargest(10).index.tolist()
```
→ top10을 **train 전체(80주)** 에서 계산. `growth_curve.py`는 이미 그렇게 그룹핑된 `country_grouped`를 로드.

**문제:** 라벨은 point-in-time인데 **country 인코딩은 미래(전기간) 정보로 고정**. 콜드스타트 1주차 모델이 "앞으로 80주간 top10이 될 국가"를 미리 안다. 예: BRA(브라질)가 전기간 top10이라, 초기 주차에 BRA 예약이 `Other`가 아니라 `BRA`로 라벨됨 — 그 시점엔 알 수 없는 정보.

**심각도:** 경미~중간. top10 국가(PRT·GBR·FRA·ESP·DEU·ITA·IRL·BEL·NLD·BRA)는 비교적 안정적이라 **모델 간 상대 순위(LR↔LGB 전환주차 W)는 크게 안 바뀔 가능성**. 그러나 *"정직한 콜드스타트"* 서사엔 흠집:
> 심사자: "5주차 모델이 진짜 5주차 정보만 쓰나?" → 현재 답: "라벨은 예, 국적 인코딩은 아니오."

**옵션:**
| | 방법 | 비용 | 효과 |
|---|---|---|---|
| (i) 엄밀 수정 | 구간별로 top10 재계산(누적 ≤ t 데이터에서) | growth_curve 일부 수정 + 재실행 | 완전한 point-in-time |
| (ii) 디스클로즈 | 코드 유지, "인코딩은 전기간 고정" 슬라이드 각주 | 0 | 정직하되 흠 인정 |

→ **권고:** A-3(국적 재설계)을 어차피 할 거라면, 그때 (i)과 함께 처리. 국적을 `is_domestic`(아래)로 바꾸면 **top10 누수 문제 자체가 소멸**.

---

## A-3. 🔴 윤리 — country가 모델 1순위 피처 (차별 리스크)

**현상:** `country_grouped`가 OHE로 모델 입력. SHAP 1위(design_10: country 1.064). 즉 **국적이 위험도의 최대 동인**.

**문제:** "위험도 따라 오버부킹/보상 차등"인데 그 위험도를 국적이 좌우 → **국적 기반 차등 대우 = 차별**. GDPR(국적은 민감속성 인접)·반차별 규범 모두 저촉. 교수님 법률 지적보다 날카로운 지점.

**참고:** `design_04` §9에 **이미 "country 인코딩 재설계(Phase2-F, Week6)"가 예약**돼 있음. 지금이 그 시점 — 윤리 렌즈 추가해서.

**옵션:**
| | 방법 | 장점 | 단점 |
|---|---|---|---|
| (a) 거버넌스 | 예측엔 쓰되 *행동 차등*엔 국적 직접 금지 | 신호 보존 | 점수에 이미 녹아 enforce 어려움 |
| (b) **is_domestic 이진화** | PRT(리스본·알가르브 내국인) vs 외국인 | 운영상 정당("내국인은 단기·근거리"), 다국적 차별 광학 제거, PRT 지배신호 보존, **A-2 누수도 소멸** | 국가별 미세신호 손실 |
| (c) drop + ablation | country 빼고 PR-AUC 변화 측정 | 윤리 부채 최소·정량화 | 신호 클 경우 성능 손실 |

→ **권고: (c) ablation 먼저(비용 측정)** → 거의 안 떨어지면 drop, 떨어지면 (b) is_domestic로 절충하며 "성능-윤리 트레이드오프"를 정직하게 발표. **충돌 0(src/ 전용 실험), 발표 방어 카드로 직결.**

> 심화 한계(정직): 국적을 빼도 ADR·market_segment 등 상관 피처로 **간접 차별** 잔존 가능. 진짜 공정성은 disparate impact 측정이 필요하나 6일 범위 초과 → "한계"로 명시.

---

## A-4. 연계 발견 — expected_cost 비용비 가정 (design_21로 이관)

전처리는 아니지만 같은 재점검에서 발견: `growth_curve.py`의 `COST_RATIOS=[2,5,10]`(빈방/walk 비용비)이 **현실과 반대 방향일 수 있음**(reputation 포함 시 walk가 더 비쌈). 상세·근거는 [design_21 §4](design_21_overbooking_compensation_grounding.md) 참조.

---

## 종합 — 발표 전 의사결정 안건

| # | 안건 | 권고 | 충돌 | 시급도 |
|---|------|------|------|--------|
| 1 | country 윤리 처리 (a/b/c) | **(c) ablation → (b) is_domestic** | 0 (src/) | 높음(서사 핵심) |
| 2 | country Top10 누수 (A-2) | (b) 채택 시 자동 소멸 / 아니면 디스클로즈 | 0 | 중 |
| 3 | expected_cost 비용비 | `≤1` 포함 sweep or 각주 | 0 | 중 |
| 4 | "새 전처리안" 정체 확인 | 다른 방 산출물인지 재형님 확인 | — | 낮 |

**한 줄:** 성장곡선 결과 자체는 유효하나, **국적(윤리+누수)을 ablation으로 정리하면 발표 방어가 한 단계 단단**해진다. 코드 수정은 모두 `src/` 전용이라 앱 작업방과 충돌 없음 → 별도 방에서 안전하게 진행 가능.
