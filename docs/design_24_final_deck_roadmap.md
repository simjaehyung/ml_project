# 최종 발표 덱 로드맵 — 스토리 기반 (단일 진실 문서)

> 작성: 2026-06-05 | 최종발표 6/10 | 전체 폴더 점검 후 자료→슬라이드 매핑
> 성격: **최종본까지의 길.** 모든 누적 자료를 어디에 쓸지 확정하고, 빌드 순서를 박는다.
> 디자인: design_23 "Editorial Instrument". 콘텐츠 정전: 아래 + design_20·21·country_ablation·walkforward·overbooking_policy.

---

## 0. 최종 thesis & 스토리 원칙

> **"호텔 데이터를 수집해, 그 데이터로 ML 예측(오버부킹 + 새 도메인)을 돌려 수익·경영 안정성을 극대화하는 데이터 수집 인프라."**

피벗 확정(2026-06-05):
- **증거 앵커 = 실데이터 취소모델 0.820** (가장 방어). **주요 가치(타겟) = 협상 수집 + 확장.**
- "데이터가 모델을 고른다(전환)" → **demote**(walk-forward에서 fixed-test 아티팩트로 판명). "모델 고정 금지"는 **드리프트** 각도로만 생존.
- 의미있는 예측 = **오버부킹 *비율*(실데이터 세그먼트 정책)** + 보상 **삼각측량**. LLM 협상은 *수집 씨앗*.
- 스토리 기반(회의). 데모는 **실제 DSS앱**으로 따로 + **캡쳐를 슬라이드에**.

---

## 1. 최종 스토리 아크 (슬라이드별 · 자료 매핑 · 상태)

> 🟢 자료 있음·바로 / 🟡 자료 있음·가공 필요 / 🔨 빌드 / 📸 데모 캡쳐

| # | 슬라이드(스토리 비트) | 핵심 메시지 | **사용 자료(파일·수치)** | 상태 |
|---|---|---|---|---|
| S1 | 타이틀+thesis | 모델 아닌 "자라는 수집 인프라" | design_23 디자인 | 🟢 |
| S2 | 문제+리프레임 | 취소 37%(City 41.7%/Resort 27.8%), 빈 방=영구손실, 오버부킹 마찰 / 주인공=인프라 | design_00, 기존 deck 수치 | 🟢 |
| S3 | **데이터 유입(수집구)** | 예약이 시간순으로 허브에 쌓임 | 📸 `dss_story_demo.html` 캡쳐 / `hub_stream.json` / (옵션 3D `canvas_demo_v3`) | 📸 |
| S4 | **취소 예측 = 앵커** | LightGBM **0.820**(Dummy 0.387, 2.1배), SHAP 상위(lead_time·country·prev_cancel). **두 평가법(fixed·walk-forward) = rigor; 전환은 아티팩트, LGB 강건; 실배포 드리프트→재선정** | 🟡 `pr_curve_all.png`·`baseline_results.md`·`shap_lgbm_bar.png`·`growth_curve.png`·`growth_curve_wf.png`·`walkforward_findings_2026-06-05.md` | 🟡 |
| S5 | **오버부킹 비율 예측** | 세그먼트 정책: lead_time별 권장 오버부킹 **8~30%**(실 모델). 한계비용=한계수익 | 🟢 `overbooking_policy.png`·`_segments.csv`·`overbooking_ev.png`·`overbooking_policy_result.md` | 🟢 |
| S6 | 예측 틀림→보상 | walk 보상, **삼각측량 €46~107(0.4~1.0×ADR, 3 독립소스)** | 🟢 `overbooking_policy_result.md`§2·design_21·`walk_sim_*` | 🟢 |
| S7 | **협상 데이터 수집(ML②·차별화)** | 세상에 없는 (위험도→오퍼→수락→취소) 수집. D **€46 step**, B **앵커링 역설(p<1e-6)** | 🟡 `walk_sim_results.jsonl`/`D_nohint`/`B_fixed`·`walk_accept_curves.png`·`walk_claim2_barplot.png`·`sim_prob_vs_acceptance.png`·design_19/21 grounding | 🟡 |
| S8 | 확장성 | 같은 인프라→가격·수요·인력. **새 도메인은 0에서 시작(콜드스타트 부활)** | 🟡 design_09(beyond_cancellation)·domain2(예시로만) | 🟡 |
| S9 | **왜 믿나(집중블록)** | 윤리(country ablation **DROP −5%/is_domestic −1%**, consent-by-design, GDPR Art.7/22) · 효과(시뮬≠현실, **calibration**: 순위 vs 수량) | 🟢 `country_ablation.csv`·`country_ablation_result.md`·`overbooking_policy_result.md`§3·design_23 | 🟢 |
| S10 | 결론 | 3기둥: 수집 인프라 / 실데이터 앵커 / 없던 데이터 수집·확장 | — | 🟢 |

→ 약 10슬라이드(스토리 흐름). 압축 시 S2+S1, S5+S6 병합 가능.

---

## 2. 자료 활용 표 — 강한 실증 자산을 낭비하지 않기

| 자산 | 어디에 | 비고 |
|---|---|---|
| `pr_curve_all.png`, `baseline_results.md` | S4 | 5모델 비교, 0.820 |
| `shap_lgbm_bar/beeswarm/waterfall.png` | S4(피처), S9(country=1위→윤리) | |
| `weather_ablation.md` | S4 또는 S9 각주 | "날씨 검증했고 유의X — 정직" |
| `growth_curve.png` + `growth_curve_wf.png` + walkforward_findings | S4 | **rigor 카드**(두 평가법·드리프트) |
| `country_ablation.csv/_result.md` | S9 | 윤리 정량 |
| `overbooking_policy.png/_segments.csv` + `overbooking_ev.png` | S5 | 비율 예측 |
| `walk_sim_*` + `walk_accept_curves.png` + `walk_claim2_barplot.png` + `sim_prob_vs_acceptance.png` | S6/S7 | 협상 정량(D €46, B 앵커링) |
| `dss_story_demo.html` + `hub_stream.json` | S3(캡쳐) + 데모 폴백 | |
| `info_separation_diagram.png` | S7 보조 | LLM/PMS/DSS 분리(손님 risk 비노출) |
| design_23 | 덱 전체 디자인 | Editorial Instrument |

**안 쓰는 것(명시적 은퇴):** domain2 업셀(예약시점 값→예측 무의미, "파이프라인 예시"로만), 구 deck v2~v14·variant·v15_hybrid(보관), 3D 키네틱(빔가독성 탈락), "데이터가 모델을 고른다 전환 W" 헤드라인(아티팩트).

---

## 3. 데모·캡쳐 계획
- 실제 DSS앱(`/dashboard/hub`, handoff_dss_demo.md) → 라이브 데모 + 캡쳐 → S3.
- 폴백/캡쳐 소스: `dss_story_demo.html` (4비트 자동정지). 캡쳐 컷: demo_run_guide.md C1·C3·C4·C6.

---

## 4. 최종본까지의 길 (빌드 순서·체크리스트)

1. **[로드맵 합의]** 이 문서(아크·자료매핑) 재형님 확정 ← 지금.
2. **[차트 실물화]** 덱의 SVG placeholder → 실제 PNG로 교체:
   - S4 `growth_curve_wf.png`/`pr_curve_all.png`, S5 `overbooking_policy.png`, S7 `walk_accept_curves.png`. (필요시 발표용으로 재렌더 — 폰트·라벨 한글/영문 통일)
3. **[v15 → 최종 스토리 덱]** 현 v15(8슬·Editorial Instrument)를 위 10슬 아크로 갱신:
   - S4 재프레이밍(앵커+드리프트+rigor, 전환 헤드라인 제거)
   - S5 오버부킹 세그먼트 정책 테이블 신규
   - S6 삼각측량 / S7 협상 정량 보강 / S9 calibration·ablation
4. **[캡쳐]** 데모 스크린샷 → S3 삽입.
5. **[검수]** 교수·디자인·타임·윤리 패널 + 수치 정합.
6. **[리허설·백업]** 9분 리허설 + 녹화 백업.

---

## 5. 결정 대기 (재형님)
- 슬라이드 수: **10 vs 8 압축** — 어느 쪽?
- 3D(canvas_demo) S3에 쓸지 vs `dss_story_demo.html` 캡쳐만.
- 차트 재렌더를 발표용으로 통일할지(현 PNG 그대로 vs 한글/디자인 맞춤).
- 위 §1 아크 그대로 vs 비트 조정.
