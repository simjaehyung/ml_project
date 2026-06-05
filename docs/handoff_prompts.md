# 코드 작업방 인계 프롬프트 모음 (Handoff Prompts)

> 작성: 전략·발표 작업방 | 2026-06-05
> 성격: **구현 인계서**. 이 방(전략·발표)은 docs/·presentations/·src/·results/만 만진다.
> 아래 3개 프롬프트는 **코드 작업방**(`hotel-dss-app/app/**`, `app_pms/**`, `llm_sim/**`)에 그대로 복붙해 착수한다.
> 각 프롬프트는 **자립형**(앞뒤 맥락 없이 단독으로 읽어도 작동)이며, 서로 의존하지 않는다.

---

## 0. 세 프롬프트 공통 규칙 (각 프롬프트 안에도 인라인으로 박혀 있음)

| # | 규칙 | 이유 |
|---|------|------|
| 1 | **착수 전 `hotel-dss-app/node_modules/next/dist/docs/`를 먼저 읽어라.** | 이 Next.js는 변형판이다 (`hotel-dss-app/AGENTS.md` 명시). App Router·라우트 규약·파일 구조가 학습 데이터와 다를 수 있다. 추측 금지. |
| 2 | **신규 파일만 생성**하라. 기존 파일 수정은 "충돌 파일" 절에 명시된 것만. | 동시 작업 중인 파일을 깨면 다른 사람 작업이 날아간다. |
| 3 | **risk_score·shap_values·flexi_recommended를 손님(Guest)에게 절대 노출하지 마라.** | `docs/design_16_api_contract.md` 핵심 원칙: "LLM(손님)은 PMS만 안다. DSS의 존재·risk_score를 모른다." 손님이 볼 수 있는 유일한 DSS 신호는 `pricing_type`(Standard/Flexi)과 할인율뿐이다. |
| 4 | 모든 UI 텍스트·주석은 **한국어**. 색·여백·라운드 톤은 기존 페이지와 통일. | 프로젝트 일관성. |
| 5 | 포트 규약: **DSS FastAPI = 8001**, **PMS = 3001**, **Next.js = 3000**. | `pms_mock.py`의 `DSS_BASE_URL`은 `http://localhost:8001`. design_16 본문이 8000으로 적은 곳이 있으나 **실제 코드는 8001이 정본**이다. |

**스타일 레퍼런스(읽고 톤 맞출 것):**
- DSS 대시보드 톤: `hotel-dss-app/app/dashboard/page.tsx`, `app/dashboard/layout.tsx` (CSS 변수 `--bg-card`, `--risk-high/medium/low`, `--flexi-color` 사용)
- PMS 톤: `hotel-dss-app/app/pms/page.tsx`, `app/pms/layout.tsx` (slate 팔레트, Avatar/FlexiBadge 컴포넌트)
- API 호출 패턴: `hotel-dss-app/lib/api.ts`, `lib/pms-api.ts` (fetch + handleResponse)

---

# 프롬프트 (1) — 손님 예약 앱 (Guest Booking App)

> 복붙 대상: **코드 작업방**
> 작업 폴더: `hotel-dss-app/app/book/**` (신규 라우트) + (선택) `app_pms/pms_mock.py`에 검색 엔드포인트 1개 추가

```
[역할] 너는 Hotel No-Show DSS 프로젝트의 손님 예약 앱(Guest Booking App)을 구현한다.

[필독 — 착수 전 반드시]
1. hotel-dss-app/node_modules/next/dist/docs/ 를 먼저 읽어라. 이 Next.js는 변형판이다
   (hotel-dss-app/AGENTS.md 참조). 라우트 파일 규약·App Router 관례가 네 학습 데이터와
   다를 수 있으니 추측하지 말고 docs를 확인한 뒤 작성하라.
2. docs/design_16_api_contract.md 의 "핵심 원칙"과 "연결고리 0"을 읽어라.
3. app_pms/pms_mock.py 와 app_pms/pms_schemas.py 를 읽어라 — 이미 존재하는
   POST /api/bookings (GuestBookingRequest → GuestBookingConfirmation)를 그대로 재사용한다.
4. 스타일 톤: hotel-dss-app/app/pms/page.tsx (slate 팔레트) 를 참고하되, 손님용이므로
   더 밝고 호텔 예약 사이트다운(Booking.com / 호텔 직영 사이트) 느낌으로.

[만드는 것 — 진짜 호텔 예약 플로우]
신규 라우트 /book 아래 단계별 예약 플로우. 손님(사람 또는 데모 진행자)이 직접 클릭해서 예약한다.

  단계 1) 검색       : 호텔(City/Resort) · 도착일 · 출발일 · 인원(adults/children) 입력
  단계 2) 객실 선택   : 룸 타입 카드 목록 (Single/Double/Twin/Suite). 가격(1박 ADR) 표시.
                       ADR 계산은 pms_mock._translate_to_dss 의 규칙과 동일하게:
                       base 80, City Hotel +20, 6~8월 ×1.3.
  단계 3) 손님 정보   : 국적(ISO alpha-3, 예 GBR) · 식사(BB/HB/FB/SC 라벨) · 특별요청(텍스트)
  단계 4) 요금 옵션   : ★핵심★ Standard Rate vs Flexi Rate 를 손님이 "선택"하는 화면.
                       - Standard: 기본가, 일반 취소 정책
                       - Flexi:    "7일 전까지 무료 취소, 단 취소 시 객실은 대기 손님에게"
                       두 카드를 나란히 보여주고 손님이 고른다.
  단계 5) 확정       : POST http://localhost:3001/api/bookings 호출
                       (헤더 Authorization: Bearer pms-guest-key-2026, body = GuestBookingRequest).
                       응답 GuestBookingConfirmation 으로 확인서 화면 표시
                       (확인번호·호텔·날짜·박수·요금제·총액·안내메시지).

[GuestBookingRequest 필드 (app_pms/pms_schemas.py 정본)]
  hotel("City Hotel"|"Resort Hotel"), arrival_date, departure_date,
  adults(1~9), children(0~5),
  room_type_preference("Single"|"Double"|"Twin"|"Suite"|"No Preference"),
  meal_plan("Bed & Breakfast"|"Half Board"|"Full Board"|"Room Only"),
  nationality(3자 대문자), special_requests(≤300자),
  agent_id, persona_description
  → 손님 앱에서는 agent_id="guest-web", persona_description="" 로 고정해 보내라.

[절대 금지 — design_16 원칙]
- risk_score, flexi_recommended, shap_values, discount_rate 계산 로직을 손님 화면에
  절대 노출하지 마라. 손님이 보는 것은 pricing_type(Standard/Flexi 라벨)과
  최종 할인율(discount_applied)·총액뿐이다.
- 손님 앱은 DSS(:8001)를 직접 호출하지 마라. 반드시 PMS(:3001)만 호출한다.
  위험도 판정은 PMS 내부에서 DSS를 부르고 pricing_type만 돌려준다.
- 단계 4의 Flexi 선택은 "손님 의향" 수집용이다. 단, 현재 pms_mock 의 pricing_type 은
  DSS 판정으로 결정된다(손님 선택과 무관). 그러므로 이번 작업 범위는 ★프론트 UI만★:
  손님 선택값을 special_requests 에 "[guest-pref: Flexi]" 같은 태그로 실어 보내되,
  최종 확인서의 pricing_type 은 서버 응답값을 그대로 표시한다.
  (협상 라이프사이클 Phase 2 — 손님 선택을 진짜 협상으로 바꾸는 작업 — 은
   별도 인계 건이다. 여기서 pms_mock 의 판정 로직을 바꾸지 마라.)

[충돌 파일 — 주의]
- app_pms/pms_mock.py 와 app_pms/pms_schemas.py : 읽기·재사용만. 수정하려면
  "호텔 목록·객실 가격 조회용 GET 엔드포인트 1개 추가" 정도까지만 허용하고,
  기존 POST /api/bookings·스키마는 절대 건드리지 마라. (llm_sim·PMS UI가 의존 중)
- hotel-dss-app/app/pms/** : 수정 금지(다른 화면). /book 은 완전히 새 라우트.

[신규 파일만]
- hotel-dss-app/app/book/page.tsx (또는 docs 규약에 맞는 라우트 파일)
- 필요 시 hotel-dss-app/app/book/layout.tsx, 단계별 컴포넌트, lib/guest-api.ts(신규)
- 기존 lib/pms-api.ts 는 admin 전용이므로 손님용 fetch 헬퍼는 새로 만들어라
  (Bearer pms-guest-key-2026 헤더 포함).

[완료 기준]
- /book 에서 검색→객실→정보→요금옵션→확정 5단계가 끝까지 동작
- 확정 시 PMS :3001 에 실제 예약이 생기고(=PMS 대시보드 Recent Reservations 에 나타남)
  확인서 화면이 표시된다
- 손님 화면 어디에도 위험도 숫자가 노출되지 않는다
```

---

# 프롬프트 (2) — hub 실시간 수집 시각화 (/dashboard/hub)

> 복붙 대상: **코드 작업방**
> 작업 폴더: `hotel-dss-app/app/dashboard/hub/**` (신규 라우트)
> 데이터 소스: `hotel-dss-app/public/hub_stream.json` (이미 생성 완료, {meta, stream})

```
[역할] 너는 Hotel No-Show DSS 대시보드에 "데이터 수집 허브 — 실시간 유입 시각화"
라우트(/dashboard/hub)를 신규로 추가한다. 발표 thesis의 주인공인 "데이터가 쌓일수록
자라는 인프라"를 눈으로 보여주는 화면이다.

[필독 — 착수 전 반드시]
1. hotel-dss-app/node_modules/next/dist/docs/ 를 먼저 읽어라. 이 Next.js는 변형판이다
   (hotel-dss-app/AGENTS.md). 라우트·App Router 규약을 추측하지 말 것.
2. hotel-dss-app/app/dashboard/page.tsx 와 app/dashboard/layout.tsx 를 읽어 톤을 맞춰라.
   (CSS 변수 --bg-card, --risk-high/medium/low, --flexi-color, recharts 사용 패턴)
3. docs/design_17_growth_and_collection_strategy.md 를 읽어 "왜 이 화면이 필요한가"를
   이해하라: 우리는 일반화가 아니라 "우리 호텔 데이터가 적은 데서 많은 데로 쌓일수록
   자라는 시스템"을 증명한다. 이 화면이 그 "쌓임"을 보여준다.

[데이터 — public/hub_stream.json]
구조: { "meta": {...}, "stream": [ {레코드}, ... ] }  // stream 길이 25,000(현재 커밋본 균등 다운샘플, n_full 119,390), 예약일(d) 순 정렬
meta 필드:
  n=25000, n_full=119390, date_range=["2013-06-24","2017-08-31"], 
  disclaimer="risk는 전체 LightGBM 모델로 사후 산출(point-in-time 아님). 시연용.",
  test_split_note, growth_curve="results/growth_curve_agg.csv 의 'wk'로 정규화"
stream 각 레코드 필드:
  d   = 예약일(booking date, "YYYY-MM-DD")
  arr = 도착일(arrival date)
  wk  = 정규화 주차(성장곡선 cutoff_week 와 동일 축)
  country, channel, hotel, lead(리드타임 일), adr
  risk = 0~1 (사후 산출값. ★주의★ point-in-time 아님 — 화면에 disclaimer 노출 필수)
  canceled = 0|1
  split = "train"|"test"
  color = "low"|"med"|"high"

[만드는 것 — /dashboard/hub]
A) 실시간 재생(replay) 패널 — "데이터가 한 건씩 들어오는 장면"
   - public/hub_stream.json 을 fetch 해서 stream 을 시간(예약일 d) 순으로 재생.
   - 재생 컨트롤: ▶︎ 재생 / ⏸ 일시정지 / 속도(×1 ×10 ×100 ×1000) / 진행 슬라이더.
   - stream 25,000건(n_full 119,390 다운샘플) 전부를 DOM 으로 그리면 죽는다. ★성능★:
     · 누적 카운터·집계는 숫자만 갱신(전체를 매 프레임 렌더 금지).
     · 최근 유입 N건(예 30건)만 터미널 스타일 피드로 흘려보낸다
       (app/pms/page.tsx 의 Live Agent Activity 피드 톤 차용).
     · 재생은 setInterval 로 "이번 틱 동안 들어온 레코드 묶음"을 배치 처리.
   - 누적 KPI: 총 유입 건수, 취소 건수, Flexi 후보(risk≥0.65) 건수, train/test 비율.
   - 상단에 meta.disclaimer 를 작은 글씨로 항상 표시(point-in-time 아님 명시).

B) 성장곡선 동기화 패널 — "쌓일수록 자란다"
   - results/growth_curve_agg.csv 를 화면에 띄우려면 public 으로 복사가 필요하다.
     ★이 방(코드 작업방)에서 public/ 데이터 산출물 생성은 허용된다★ →
     results/growth_curve_agg.csv 를 hotel-dss-app/public/growth_curve_agg.csv 로 복사하고
     fetch 해서 쓰거나, 필요한 열만 추린 작은 JSON 으로 변환해 public 에 둬라.
   - x축 = cutoff_week(주차), y축 = pr_auc, 모델별(Dummy/LR/RF/XGBoost/LightGBM) 선.
     window=="cumulative" 행만 사용. CI(ci_low/ci_high)가 있으면 음영 밴드로.
   - ★A의 재생 위치(현재 wk)와 동기화★: 재생 커서가 진행하면 성장곡선 위에
     "지금 여기" 세로선이 함께 이동. 데이터가 쌓이는 만큼 곡선이 차오르듯 보이게.
   - 핵심 서사 주석(고정 텍스트, 한국어):
       "W 이전은 대체로 tie(CI 겹침) — LR은 콜드스타트 구간 우위 → 전환주차(약 5.4만 건)에서 LightGBM 추월(끝까지 유지).
        full-data PR-AUC 0.820, Dummy 0.387 대비 2.1배.
        우리는 모델을 고르지 않는다 — 데이터가 모델을 고르게 한다."
     (이 수치는 docs/design_18_growth_curve_implementation.md·design_17 의 확정값과
      반드시 일치시켜라. 임의로 바꾸지 말 것.)

[사이드바 등록]
app/dashboard/layout.tsx 의 NAV_ITEMS 에 { label:"Data Hub", href:"/dashboard/hub", ... }
항목 1줄 추가는 허용(이 한 줄만). 아이콘은 lucide-react 에서 적절히(예: Database).

[충돌 파일 — 주의]
- app/dashboard/page.tsx, reservations/**, flexi/** : 수정 금지(다른 화면).
- app/dashboard/layout.tsx : NAV_ITEMS 배열에 항목 1개 추가만 허용. 다른 부분 손대지 마라.
- public/hub_stream.json : 읽기 전용(이미 생성됨). 덮어쓰지 마라.

[신규 파일만]
- hotel-dss-app/app/dashboard/hub/page.tsx (+ 필요한 컴포넌트)
- hotel-dss-app/public/growth_curve_agg.(csv|json)  ← results/ 에서 복사·변환
- 필요 시 lib/hub.ts (fetch·파싱 헬퍼)

[완료 기준]
- /dashboard/hub 에서 재생이 매끄럽게 동작(수만 건에도 프레임 드랍 없이 — 배치/카운터 방식)
- 성장곡선이 그려지고 재생 커서와 세로선이 동기화됨
- disclaimer 가 화면에 보이고, 수치(0.820 / 0.387 / 2.1배)가 문서 정본과 일치
```

---

# 프롬프트 (3) — 3D 인프라 룸 (Infrastructure Room)

> 복붙 대상: **코드 작업방**
> 기술 레퍼런스: `docs/html_in_canvas_threejs_guide.md` (HTML-in-Canvas + Three.js 정본)
> 참고: design_22 는 아직 미작성(이 방에서 작성 예정). 작성되면 그 요지 우선.

```
[역할] 너는 발표 피날레용 "3D 인프라 룸"을 구현한다. 우리 thesis("모델이 아니라
데이터 수집 인프라가 주인공")를 공간으로 은유한다: 한 방 안에 살아있는 DSS/허브
패널들이 벽·면에 텍스처로 붙어 데이터가 흐르는 장면.

[필독 — 착수 전 반드시]
1. docs/html_in_canvas_threejs_guide.md 를 처음부터 끝까지 읽어라. 이것이 기술 정본이다.
   핵심: gl.texElementImage2D 로 살아있는 HTML DOM 을 WebGL 텍스처로 올려 3D 면에 붙인다.
   - DOM 패널은 display:none 금지, position:fixed; left:-9999px 로 숨긴다(레이아웃 유지).
   - texElementImage2D 후 renderer.state.reset() 필수.
   - generateMipmaps=false, PlaneGeometry 비율 = DOM 패널 px 비율과 일치.
   - 활성화: chrome://flags/#canvas-draw-element → Enabled (Chrome M146+ / Canary).
     플래그 미지원 브라우저용 폴백(정적 이미지/캡처) 경로도 가이드의 ctx.drawElement 참고.
2. 이 화면이 Next.js 앱 안의 라우트라면 hotel-dss-app/node_modules/next/dist/docs/ 를
   먼저 읽어라(변형판 Next.js, hotel-dss-app/AGENTS.md). 단, 가이드의 최소 템플릿은
   단일 HTML 파일이므로 — 1차로는 hotel-dss-app/public/ 아래 독립 .html 로 만들고
   브라우저에서 직접 열어 동작을 확보한 뒤, 필요하면 라우트화하는 순서를 권장한다.

[중복 금지 — 요지 + 참조]
3D 기술 상세(API 시그니처, 텍스처 주입 패턴, 주의사항 표)는 가이드에 이미 정리돼 있다.
★여기서 그 내용을 다시 설명하거나 재작성하지 마라.★ 가이드를 import 하듯 따르고,
이 프롬프트는 "무엇을 그릴지(콘텐츠·배치)"만 정의한다.

[만드는 것 — 인프라 룸 한 장면]
- 어두운 방(背景 #07101F 계열) 안에 3~4개의 DOM 패널을 벽/면에 배치:
    패널 ① "데이터 유입 허브"   : 실시간 카운터(누적 건수↑) + 최근 유입 몇 줄
                                 (소스는 public/hub_stream.json 의 집계 — 프롬프트(2)와 동일 데이터.
                                  단 3D 안에서는 가볍게 카운터·로그 몇 줄만).
    패널 ② "성장곡선"           : PR-AUC가 차오르는 라인(LR→LightGBM 추월). 정적 SVG/캔버스도 OK.
    패널 ③ "DSS 위험 판정"      : 예약 1건의 risk 카드(예: 취소 위험 87%, 색상 --risk-high).
    패널 ④(선택) "협상 수집"    : (위험도→오퍼→수락→취소) 튜플이 한 줄씩 쌓이는 로그.
- 카메라가 패널 사이를 lerp 로 천천히 이동(가이드의 카메라 애니메이션 패턴).
- 패널 콘텐츠는 살아있는 DOM 이므로 숫자가 실제로 올라가는 게 보이면 임팩트가 크다.

[데이터·수치 일관성]
- 성장곡선·수치는 문서 정본과 일치: full-data PR-AUC 0.820, Dummy 0.387, 2.1배,
  "W 이전 대체로 tie(LR은 콜드스타트 구간 우위) → 전환주차(약 5.4만 건)에서 LightGBM 추월(끝까지 유지)".
  (출처: docs/design_17, design_18, results/growth_curve_agg.csv)
- risk 는 사후 산출값이며 point-in-time 이 아니다 — 발표 멘트로 disclaimer 를 언급
  (화면 구석 작은 글씨 권장). 손님이 아니라 "발표 청중·매니저 시점" 화면이므로
  risk 노출은 허용된다(design_16 의 손님 비노출 원칙은 손님 앱에만 적용).

[충돌 파일 — 주의]
- hotel-dss-app/app/** 의 기존 라우트는 수정 금지.
- 이 작업은 hotel-dss-app/public/ 아래 신규 .html(+ /assets) 또는
  app/showcase/ 같은 완전 신규 라우트로 격리하라.

[신규 파일만]
- hotel-dss-app/public/infra_room.html (1차, 단독 동작 우선)  또는
- hotel-dss-app/app/showcase/page.tsx (라우트화 단계 — docs 규약 확인 후)
- 필요한 assets(텍스처·JSON 집계)는 public/ 아래 신규로.

[완료 기준]
- Chrome(플래그 ON)에서 방이 렌더되고, 패널 ①의 카운터가 실제로 증가하는 게 보인다
- 카메라가 패널 사이를 부드럽게 이동
- 플래그 OFF 브라우저에서도 폴백 경로로 최소한 정적 화면은 뜬다(빈 화면 금지)
- 모든 수치가 문서 정본과 일치
```

---

## 부록 — 인계 시 같이 전달할 사실/포트 체크리스트

| 항목 | 값 | 출처 |
|------|----|------|
| DSS FastAPI 포트 | **8001** (pms_mock.DSS_BASE_URL 정본) | `app_pms/pms_mock.py` L71 |
| PMS 포트 | 3001 | `app_pms/pms_mock.py` |
| Next.js 포트 | 3000 | `lib/api.ts`, `lib/pms-api.ts` |
| PMS 손님 API 키 | `Bearer pms-guest-key-2026` | `app_pms/pms_mock.py` L70 |
| 손님 예약 엔드포인트 | `POST :3001/api/bookings` (GuestBookingRequest) | `pms_schemas.py` |
| hub 데이터 | `public/hub_stream.json` = {meta, stream}, stream 25,000건(n_full 119,390 다운샘플), 예약일 순 | 생성 완료 |
| 성장곡선 raw | `results/growth_curve_agg.csv` (window/cutoff_week/model/pr_auc/ci_low/ci_high) | 학습 완료 |
| 확정 수치 | full PR-AUC 0.820(=0.8189), Dummy 0.387, 2.1배, W 이전 대체로 tie(LR 콜드스타트 우위) 후 약 5.4만 건에서 LightGBM 추월 | design_17·18 |
| 운영 임계 | 0.65 | dashboard/page.tsx CURRENT_THRESHOLD |
| 손님 비노출 원칙 | risk_score·shap·flexi_recommended → 손님 앱에서 금지 | design_16 |

> **design_22 메모:** 프롬프트(3)이 참조하는 `design_22`(3D 인프라 룸 설계)는 현재 미작성이다.
> 이 방(전략·발표)에서 별도 착수 예정. 작성 전까지 3D 기술 정본은
> `docs/html_in_canvas_threejs_guide.md`, 콘텐츠 정본은 이 프롬프트(3)다.
