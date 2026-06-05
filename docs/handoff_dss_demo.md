# Handoff — DSS 앱 "수집 허브" 데모 (캡쳐용)

> 수신: **코드 방** (Next.js 앱 담당) / 발신: 전체흐름(전략·발표) 방
> 목적: 최종발표(2026-06-10) 핵심 스토리 — **"실제 DSS 앱에 예약 데이터가 시간순으로 흘러들며 모델이 진화(자라남)"** — 를 **실제 앱에서** 시연하고, 그 화면을 **캡쳐해 슬라이드에 박을 수준**으로 만든다.
> 데모는 실제 DSS 앱(Next.js)으로 따로 수행한다. 슬라이드는 그 캡쳐를 쓴다. HTML 슬라이드 안에 라이브 시뮬레이션을 넣지 않는다.

---

## 0. 한 줄 요약

신규 라우트 `/dashboard/hub` 를 만든다. `public/hub_stream.json`(25k, 시간순)을 재생하면서 화면 좌측엔 예약이 흘러 쌓이고, 우측엔 성장곡선(주차별 PR-AUC)이 같은 커서로 동기화돼 그려진다. **W≈84주 / n≈53,615(≈5.4만)에서 LightGBM이 LR을 추월**하는 순간이 데모의 클라이맥스.

---

## 1. 목표 화면 — `/dashboard/hub`

### 레이아웃 (좌 스트림 / 우 성장곡선)

```
┌───────────────────────────────────────────────────────────────┐
│  HUB — Reservation Intake Stream            [▶/❚❚] [seek] [fs] │  ← 컨트롤(캡쳐 시 자동 숨김)
├──────────────────────────────┬────────────────────────────────┤
│  좌: 시간 흐름 스트림         │  우: 성장곡선 (PR-AUC vs 주차)  │
│  ─ 현재 커서: 2016-08-14      │   0.82 ┤            ╭ LightGBM  │
│    wk 84 · n=53,615          │        ┤        ╭──╯  ╭ LR      │
│  ─ 최근 유입 카드 N장 (배치)  │   0.50 ┤   ╭───╯ ────╯          │
│  ─ 누적 카운터:              │   0.39 ┤━━━━━━━━━━━ Dummy        │
│      수집 53,615 · 취소 …     │        └────┬────┬────┬──── wk  │
│      low/med/high 분포 바     │         재생커서 ───┘ (수직선)  │
├──────────────────────────────┴────────────────────────────────┤
│  ⓘ risk는 사전계산(point-in-time 아님) · hub는 25k 다운샘플(n_full 119,390) │  ← meta.disclaimer 노출
└───────────────────────────────────────────────────────────────┘
```

### 동작
1. **시간순 재생.** `hub_stream.json`의 `stream[]`을 `d`(예약일) 순서대로 흘린다(이미 정렬돼 있음). 재생 커서가 진행하며 좌측에 카드가 유입되고 누적 카운터가 오른다.
2. **성장곡선 동기화.** 우측 곡선은 `results/growth_curve_agg.csv`를 미리 정적 데이터로 임베드(아래 4-③). 좌측 스트림의 현재 `wk`와 **같은 x축(주차)**에 수직 재생커서를 그려, "지금 이 주까지 모인 데이터로 학습한 모델 성능"이 곡선 위 점으로 동기화돼 보이게 한다.
3. **클라이맥스.** wk 84 도달 시 LightGBM 라인이 LR을 추월. 이 구간에서 잠깐 강조(앰버 글로우·라벨 핀). 캡쳐 1순위 프레임.
4. **종료.** 마지막 학습 주차(곡선 full)에서 LightGBM PR-AUC **0.820**, LR ~0.78, Dummy 0.387 라벨 고정.

### 정직성 (반드시 화면에 노출)
- 하단 각주에 `meta.disclaimer` 그대로 출력: *"risk는 최종 LightGBM 모델로 사전 계산(point-in-time 아님). 수집 시연용."*
- 추가 각주: *"hub는 25k 다운샘플 (n_full 119,390). split=='test'(2017-03~08)는 수집되나 고정 평가셋이라 학습 제외."*
- **test split 데이터**는 스트림에 흘러도 되지만(수집은 됨), 곡선 학습엔 안 들어갔음을 시각적으로 구분(예: 카드에 옅은 해치/`test` 태그).

---

## 2. 복붙 구현 프롬프트 (코드 방이 그대로 사용)

> 아래 블록을 코드 방 에이전트에게 그대로 전달.

```
[작업] Next.js 앱에 신규 라우트 app/dashboard/hub/page.tsx 만 추가한다.
기존 라우트(reservations, flexi, pms, overview)·api·types·lib·components 의 동작은 절대 바꾸지 않는다. 신규 파일만 추가하고, 불가피한 수정은 아래 "충돌 파일"에만 한정한다.

[★ 먼저 읽어라 — 이 Next.js는 네가 아는 Next가 아니다]
이 앱은 next@16.2.6 (변형판). 코드 쓰기 전에 반드시:
  - hotel-dss-app/AGENTS.md
  - hotel-dss-app/node_modules/next/dist/docs/01-app/01-getting-started/03-layouts-and-pages.md
  - .../01-getting-started/05-server-and-client-components.md
  - .../01-getting-started/06-fetching-data.md
를 읽고 deprecation/관례 확인 후 작성. 학습데이터의 옛 관례로 추측 금지.

[느낌 레퍼런스]
presentations/dss_story_demo.html 가 시각·모션 '느낌' 레퍼런스다. 색·타이포·모션 위계를 여기서 가져오되, 실제 구현은 앱의 globals.css 토큰을 우선 사용한다.

[데이터]
- 좌 스트림: public/hub_stream.json (이미 존재, 25k, 시간순). fetch로 1회 로드.
  필드: d=예약일 arr=도착일 wk=절대주차 country channel hotel lead adr risk(0~1) color(low/med/high) canceled(0/1) split(train|test).
  meta.disclaimer / meta.n_full(119390) / meta.n_sample(25000) 존재 → 각주에 노출.
- 우 곡선: results/growth_curve_agg.csv 를 빌드타임에 정적 TS 배열로 임베드(앱은 results/ 를 런타임에 못 읽으니, 필요한 컬럼만 추린 hub_growth.json 을 public/ 에 두거나 page 파일 내 상수로 인라인). window=='cumulative' 행만 사용. 모델 5개(Dummy/LR/RF/XGBoost/LightGBM) 중 발표는 Dummy·LR·LightGBM 3개 라인만 그린다(나머지는 옵션). x=cutoff_week, y=pr_auc.

[필수 동작]
1) 시간순 재생: stream을 d 순서대로(이미 정렬됨) 재생. requestAnimationFrame 기반 가상시계. 재생속도/일시정지/시크 컨트롤. 시드/순서 고정(난수 셔플 금지) — 캡쳐 재현성.
2) 성능(절대 준수):
   - 25,000건 DOM 카드 동시 렌더 금지. 좌측 "최근 유입"은 최대 ~30~50장만 DOM에 유지(윈도잉/큐), 나머지는 누적 카운터·분포바로만 표현.
   - 누적 카운터는 매 프레임 setState 금지 → 배치(예: 4~8프레임 또는 N건마다 1회 flush)로 리렌더 최소화.
   - 곡선은 SVG path 1회 계산 후 캐시, 재생커서(수직선)만 매 프레임 이동.
   - 119k 원본 절대 로드 금지(25k만).
3) 재생커서 ↔ 곡선 동기: 좌측 현재 wk → 우측 곡선 x축 같은 wk에 수직선 + 각 라인 현재값 점. wk 84 추월구간 강조(앰버 글로우·라벨), full에서 LightGBM 0.820 / LR ~0.78 / Dummy 0.387 라벨 고정.
4) meta.disclaimer 항상 하단 노출. test split 카드는 시각 구분(해치/태그)하고 "학습 제외" 명시.
5) 캡쳐 모드: 키(예: c) 또는 ?capture=1 쿼리로 모든 컨트롤·커서 chrome 자동 숨김 + 풀스크린 토글. 자동숨김 후에도 곡선·카운터·각주는 유지. 캡쳐용 정지 프레임(특정 wk로 seek 후 pause) 쉽게 잡히도록 seek 입력 제공.

[디자인 가드(anti-AI / 덱 일관)]
- 금지: 보라·파랑 그라데이션, 다크대시보드 클리셰, Inter 범벅, 둥근카드 떡칠, 이모지, 평평한 위계, 균일 모션.
- 지향: 지배색 + 샤프 액센트, 실데이터, 강한 타이포 위계, 목적 있는 다양한 모션(유입=빠르게 슬라이드, 곡선=느린 draw, 추월=순간 강조), mono tabular 숫자, hairline 구분선, 의도적 비대칭.
- 액센트 토큰: 시그니처 인디고 #1B3A8F, 데이터 앰버 #8A5A0F, 위험3색 brick #B23A2E / ochre #B8862B / forest #3F7A52. 앱 globals.css의 --risk-* 토큰과 충돌 시 hub 라우트 한정 로컬 변수로 덮어쓴다(전역 변경 금지).

[충돌 파일 — 여기만 수정 허용]
- app/dashboard/layout.tsx : NAV_ITEMS 에 { label:"Hub", href:"/dashboard/hub" } 1줄 추가(아이콘은 lucide의 Radio 또는 Activity). 그 외 레이아웃 변경 금지. (발표 때 사이드바에서 보이게.)
  ※ 나머지 파일은 신규 추가만. 충돌이 더 필요하면 추가 전 보고.

[산출물]
- app/dashboard/hub/page.tsx (+ 필요 시 같은 폴더 안 컴포넌트/유틸 파일, public/hub_growth.json)
- 캡쳐 가이드: 어떤 wk로 seek하면 어떤 프레임(추월·full)이 잡히는지 1~2줄.
```

---

## 3. 데모용 추가 요구

| # | 요구 | 이유 |
|---|------|------|
| 1 | **고정 시드·고정 순서** — 재생할 때마다 동일 프레임이 동일 시점에 나와야 함 | 캡쳐 재현성. 발표 리허설=본 발표 동일 |
| 2 | **seek-to-week** 입력(숫자/슬라이더) | 캡쳐할 정지 프레임(wk 84 추월, full 0.820)을 정확히 잡기 위함 |
| 3 | **캡쳐 모드 자동숨김** — 컨트롤·재생커서 chrome 숨김, 풀스크린 | 슬라이드에 박을 때 UI 군더더기 제거 |
| 4 | **2~3개 핵심 정지 프레임** 권장 seek 값 명시 | ① 초기 혼돈(작은 n, 모델 미분화) ② wk 84 추월 ③ full 0.820. 슬라이드 3컷 |
| 5 | **누적 카운터 가독성** — mono tabular, 천단위 구분, low/med/high 분포 바 | 데이터가 "쌓이는" 체감. 캡쳐 시 숫자가 핵심 |
| 6 | **각주 항상 노출** (캡쳐 모드에서도) | 정직성. 발표 평가에서 감점 방지 |
| 7 | 좌측 유입 카드는 **risk color로 좌측 보더만** 칠하고 본문은 차분하게 | 위험 3색이 화면을 도배하지 않게 (anti-AI 균일 금지) |

---

## 4. 참고 데이터 사실 (코드 방이 라벨링에 사용)

- `public/hub_stream.json`: 25,000건, 2013-06-24~2017-08-31, `n_full`=119,390.
- 성장곡선 핵심 수치 (`window==cumulative`):
  - wk 28 (n≈844): LR 0.478 > LightGBM 0.359 — 초기엔 단순모델 우위.
  - wk 53 (n≈21,996): LR 0.712 > LightGBM 0.645 — 아직 LR 우위.
  - **wk 84 (n=53,615): LightGBM 0.799 ≈/> LR 0.781 — 추월 지점(≈5.4만). XGBoost 0.809.**
  - full(마지막 학습주차): LightGBM **0.820**, LR ~0.78, Dummy 0.387(상수).
- ③ 임베드용 추림: `results/growth_curve_agg.csv`에서 `window,cutoff_week,model,pr_auc` 4컬럼, `window=='cumulative'`만 → `public/hub_growth.json`로 변환(작은 정적 파일). 코드 방이 변환 스크립트 1개 작성하거나 손으로 추출.

---

## 5. 미해결 / 전체흐름 방이 챙길 것

- [ ] `presentations/dss_story_demo.html` (느낌 레퍼런스) — **전체흐름 방에서 별도 작성 예정**. 코드 방은 없으면 globals.css 토큰 + 본 문서 디자인 가드만으로 진행 가능.
- [ ] 캡쳐 완료 후 슬라이드 3컷(초기/추월/full) 배치는 전체흐름 방이 v15 덱에 삽입.
- [ ] 추월 "≈5.4만" 메시지를 발표 카피로 확정(전체흐름 방).
