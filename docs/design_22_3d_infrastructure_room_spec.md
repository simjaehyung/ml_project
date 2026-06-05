# design_22 — 3D '인프라 룸' 명세 (html-in-canvas)

> 작성: 전체흐름(전략·발표) 작업방 | 2026-06-05
> 성격: **시각화 명세(visual spec)**. 발표 피날레용 3D 씬을 정의한다. 앱 코드는 직접 수정하지 않으며, 끝의 '구현 프롬프트'를 코드 작업방에 넘긴다.
> 선행 문서: `html_in_canvas_threejs_guide.md`(기술 레퍼런스), `design_17`(두 트랙 전략), `design_18`(성장곡선·전환주차 W), `design_16_api_contract.md`(앱 연결 구조)
> 데이터 산출물: `hotel-dss-app/public/hub_stream.json`(완료 — 현재 커밋본 25,000건 다운샘플, n_full=119,390, stream 길이 25,000), `results/growth_curve_agg.csv`(완료)
> ⚠️ 이 명세는 **신규 라우트 `/dashboard/hub`** 와 **신규 3D 페이지**를 정의한다. 기존 앱 파일은 건드리지 않는다. 충돌 파일은 8절 참조.

---

## 0. 한 줄 요약

> **살아있는 DSS 허브 DOM을 3D 텍스처로 올려, "이 프로젝트의 주인공은 모델이 아니라 데이터 수집 인프라"라는 thesis를 카메라 한 동선으로 보여준다.**
> 풀백하면 인프라 전체(채널 → 허브 코어 → 성장곡선)가 한 화면에 잡히고, push-in하면 각 패널의 실데이터가 정면으로 읽힌다. 데이터는 이미 만들어 둔 `hub_stream.json`을 시간순으로 재생한다.

---

## 1. 왜 3D인가 — thesis와의 정합

발표의 정전 thesis(전체흐름 방): **"호텔에 핏한 예약 데이터를 수집해, 그 데이터로 자라는 ML 예측으로 수익·경영 안정성을 극대화하는 데이터 수집 인프라. 주인공은 모델이 아니라 인프라."**

2D 대시보드는 "화면 하나"를 보여준다. 3D 인프라 룸은 **"여러 부품이 하나의 파이프라인으로 연결된 시스템"**을 공간으로 보여준다. 이것이 핵심 차이다:

| 2D가 말하는 것 | 3D 인프라 룸이 말하는 것 |
|---|---|
| "우리 모델 PR-AUC 0.82" | "데이터가 채널에서 허브로 흘러들어와, 쌓일수록 모델이 자란다" |
| 정적 결과 | 흐름·성장·연결 (= 인프라의 본질) |
| 모델이 주인공 | 수집 파이프라인이 주인공, 모델은 그 위 한 패널 |

→ **카메라 풀백 = thesis 그 자체.** "이건 모델 한 개가 아니라 시스템입니다"를 말로 안 하고 보여준다.

---

## 2. 씬 구성 — 3패널 파이프라인

좌→우로 데이터가 흐르는 **L자 또는 완만한 호(arc) 배치**. 카메라가 풀백하면 셋이 한 프레임에 들어오고, 흐름 방향(좌→우)이 곧 데이터 라이프사이클이다.

```
        [채널 소스]            [DSS 허브 코어]            [성장곡선 패널]
        Panel A      ──흐름──►   Panel B (중앙·최대)  ──공급──►  Panel C
   예약이 채널에서 유입         실시간 수집·위험분류          쌓인 데이터로 자라는 모델
   (OTA/Direct/Corporate)     (살아있는 hub DOM 텍스처)      (전환주차 W 마커)
```

### 2.1 Panel A — 채널 소스 (좌)

- **역할:** "데이터가 어디서 들어오는가"를 보여주는 유입구. 인프라의 입구.
- **형태:** 세로로 쌓인 3~4개의 채널 타일(`distribution_channel` 값: `TA/TO`, `Direct`, `Corporate`, `GDS`). 각 타일에서 입자(예약 1건 = 작은 발광 점)가 우측 허브로 흘러간다.
- **데이터 바인딩:** `hub_stream.json`의 각 레코드 `channel` 필드로 어느 타일에서 입자가 출발할지 결정. 입자 색은 `color`(low=초록 / med=황 / high=로즈).
- **읽는 텍스트:** 각 채널의 누적 유입 카운터(예 "TA/TO 41,203"). 이 숫자만 정면 billboard, 나머지는 공간감 위해 비스듬해도 됨.

### 2.2 Panel B — DSS 허브 코어 (중앙, 최대)

- **역할:** 이 씬의 심장. **살아있는 `/dashboard/hub` DOM을 그대로 텍스처로 올린다.** 입자가 도착하면 위험도별로 분류되어 카운터가 오른다.
- **형태:** 중앙의 가장 큰 평면(또는 약간 안으로 휜 곡면). html-in-canvas로 실시간 갱신.
- **DOM 소스:** 신규 라우트 `/dashboard/hub` (코드 방이 신설). 이 DOM이 곧 텍스처 원본.
- **표시 내용(DOM 안에서):**
  - 상단: 현재 재생 시점(예약일 커서, 예 "수집 중 — 2016-08-14")
  - 중앙: 위험 3색 분류 카운터 (high / med / low 누적, `color` 집계)
  - 하단 띠: 최근 유입 N건의 미니 리스트(country·channel·risk·hotel) — 스크롤되며 흐름
  - 좌하단 고정 각주: "risk는 최종 LightGBM 사전계산 — 수집 시연용(point-in-time 아님)" ← `meta.disclaimer` 그대로. **정직성 핀.**
- **billboard 규칙:** 카운터·각주·시점 커서는 반드시 정면. 발표 중 매니저가 읽는 핵심 숫자다.

### 2.3 Panel C — 성장곡선 패널 (우)

- **역할:** "쌓인 데이터로 모델이 자란다"의 정량 증거. thesis의 결론.
- **형태:** x=누적 주차, y=PR-AUC 5곡선(Dummy/LR/RF/XGB/LightGBM) + CI 밴드. **전환주차 W 세로 마커.**
- **데이터 바인딩:** `results/growth_curve_agg.csv`(`window==cumulative`). 허브 코어의 재생 시점 `wk`와 동기화 — 커서가 진행하면 곡선도 그 주차까지 자라며 그려진다(progressive reveal).
- **핵심 숫자(정전 일치, 9절):**
  - W 이전 구간은 **대체로 tie(CI 겹침, 구분 불가)** 음영이며, **LR은 콜드스타트 구간에서 우위** → 전환주차 W(≈84주차/약 5.4만건)에서 **LightGBM이 추월(끝까지 유지)**.
  - full-data PR-AUC **0.820(=0.8200, LightGBM)**, Dummy **0.387** 대비 **2.1배**.
  - 전환주차 마커 라벨: "약 84주차 / 약 5.4만건 이후 부스팅으로 전환".
- **billboard:** W 마커 라벨과 축 눈금은 정면. 곡선 자체는 패널 평면에 그려지므로 비스듬해도 읽힘 OK.

---

## 3. 카메라 동선 (발표 스크립트와 1:1)

카메라는 **lerp(부드러운 보간)**로 사전 정의된 키 위치 사이를 이동. 클릭/키(Space·→)로 다음 단계 전진. 자동재생도 옵션.

| # | 위치 이름 | 카메라 | 무엇을 말하는가 | 발표 멘트(예) |
|---|---|---|---|---|
| 0 | **풀백 (Establishing)** | 멀리·약간 위. 3패널 전체 + 흐름 입자 보임 | "이건 모델 하나가 아니라 시스템입니다" | "왼쪽 채널에서 데이터가 들어와 허브에서 분류되고, 그게 쌓여 오른쪽 모델을 키웁니다." |
| 1 | **push-in A (채널)** | Panel A 정면 | 유입구. 데이터 출처 | "예약은 OTA·Direct 등 채널에서 실시간으로 들어옵니다." |
| 2 | **push-in B (허브 코어)** | Panel B 정면 (최대 클로즈업) | 살아있는 수집·분류. 핵심 | "지금 보시는 건 정지 화면이 아니라 실제로 도는 대시보드입니다 — 한 건씩 위험도로 분류됩니다." |
| 3 | **push-in C (성장곡선)** | Panel C 정면 | 정량 증거·전환주차 W | "쌓일수록 자랍니다. 약 5.4만건에서 부스팅이 단순모델을 통계적으로 추월합니다." |
| 4 | **풀백 복귀 (Resolution)** | 0과 동일 | 닫는 그림 | "수집 인프라가 있으니, 데이터가 쌓이는 만큼 시스템이 자랍니다." |

- **이동 원칙:** push-in 시 대상 패널이 화면 비율에 꽉 차고 **정면(법선이 카메라를 향함)**이 되도록 타깃 위치 계산. 비스듬한 채로 텍스트를 읽히지 않는다.
- **풀백↔push-in 왕복**이 thesis의 "부품 ↔ 전체" 리듬. 발표자는 4단계만 클릭하면 된다.

---

## 4. hub_stream.json 데이터 바인딩 명세

### 4.1 파일 계약 (이미 생성됨 — 읽기 전용)

```
hotel-dss-app/public/hub_stream.json
  meta:   { disclaimer, n:25000, n_full:119390, n_sample:25000, date_range:["2013-06-24","2017-08-31"],
            test_split_note, growth_curve, fields }   // 현재 커밋본은 25,000건 균등 다운샘플
  stream: [ {d, arr, wk, country, channel, hotel, lead, adr, risk, color, canceled, split}, … ]
            // d(예약일) 오름차순 정렬됨. stream 길이 = 25,000(다운샘플)
```

| 필드 | 용도 (3D 씬) |
|---|---|
| `d` (예약일) | **재생 커서.** 시간순으로 한 건씩 흘린다. 허브 시점 표시. |
| `wk` (절대주차) | Panel C 성장곡선과 동기화하는 키. `d` 진행 시 현재 `wk`까지 곡선 reveal. |
| `channel` | Panel A 어느 타일에서 입자가 출발할지 |
| `color` (low/med/high) | 입자 색 + 허브 분류 카운터 버킷 |
| `risk` | 입자 hover/디버그용(평상시 표시 안 함) |
| `country`,`hotel`,`adr`,`lead` | 허브 하단 미니 리스트 행 내용 |
| `split` | `test`(2017-03~08)는 시각적으로 살짝 다르게(점선/반투명) — "수집되나 학습 제외" 각주와 연결 |

### 4.2 재생 정책 (성능 필수)

- 현재 커밋본 stream 25,000건(n_full 119,390 다운샘플)을 1건=1입자로 동시에 띄우지 않는다. **시간 가속 재생**: 실시간 1초 = 데이터 N주(예 1~2주)로 압축. 발표 전체 씬이 60~90초에 끝나도록 속도 튜닝.
- **입자 풀(pool):** 동시 표시 입자는 상한(예 300개)으로 고정하고 재활용. 도착(허브 진입)한 입자는 카운터에 누적 후 풀로 반납.
- **다운샘플 옵션:** 렌더가 무거우면 `?stride=K`로 K건당 1건만 입자화(카운터는 전수 집계 유지). 또는 사전 생성한 `hub_stream_lite.json`(`build_hub_stream.py --sample`) 사용.
- **시작점:** `?from=2015-01-01` 권장 — 2013~2014 희소 초기 꼬리는 시각적으로 비어 보이므로 건너뛴다(데이터엔 남아있되 재생 시작만 조정).

### 4.3 성장곡선 동기화

- `growth_curve_agg.csv`에서 `window=='cumulative'`, 모델별 `(cutoff_week, pr_auc, ci_low, ci_high)`을 프론트가 미리 파싱(소형 JSON으로 사전 변환 권장: `public/growth_curve_cumulative.json`).
- 재생 커서의 현재 `wk` ≥ `cutoff_week`인 점까지만 곡선/CI를 그린다 → "자라는" 애니메이션.
- 전환주차 **W=84** 도달 순간 마커 강조(펄스 1회) + 라벨 페이드인.

---

## 5. 가독성 규칙 (읽는 텍스트 = 정면)

| 규칙 | 내용 |
|---|---|
| **billboard 강제** | 발표자/심사위원이 **읽어야** 하는 모든 텍스트(카운터, W 라벨, 시점 커서, 각주, 축 눈금)는 push-in 시 카메라 법선에 정렬. 비스듬한 채 읽히지 않는다. |
| **장식 vs 정보 분리** | 흐르는 입자·채널 타일 측면 등 "분위기" 요소만 3D 원근 허용. 숫자는 항상 정면. |
| **대비** | 다크 배경(`--bg-dark`)에 고대비 텍스트. 위험 3색은 기존 토큰 재사용: high `#FB7185`, med `#FBBF24`, low `#34D399`(globals.css `--risk-*`). |
| **폰트 크기** | 텍스처 원본 DOM은 발표 투사 거리 기준으로 **크게**. 허브 카운터는 화면 높이의 8~12%로 보이도록 DOM px와 plane 비율 설계. |
| **텍스처 해상도** | DOM 패널 px ↔ PlaneGeometry 비율 일치(가이드 198행). 허브 코어는 1280×800 등 충분히 크게(투사 시 흐릿함 방지), `generateMipmaps=false`. |
| **각주 상시** | 허브 좌하단 정직성 각주(`meta.disclaimer`)는 push-in B에서 항상 보이게. 발표 의심핀(S 데이터 정직성)을 인라인으로 정산. |

---

## 6. 프래질리티 관리 (발표 사고 방지 — 최우선)

html-in-canvas는 실험적 API다. 발표 당일 깨지면 thesis 피날레가 통째로 날아간다. **3중 안전망 필수.**

| 레이어 | 내용 | 트리거 |
|---|---|---|
| **0. 정상 (live)** | Chrome **M146+** 또는 Canary + `chrome://flags/#canvas-draw-element` Enabled → `gl.texElementImage2D` 동작 | 기본 |
| **1. 녹화 백업 (필수)** | 정상 동작하는 씬 전체를 **고해상도 화면녹화**(mp4). 발표 전날까지 확보. 발표 PC에서 플래그가 안 켜지면 영상 재생으로 대체. | 라이브 실패·시간 부족 |
| **2. 2D 폴백** | `typeof gl.texElementImage2D !== 'function'`이면 자동 감지 → 3D를 끄고 **2D `/dashboard/hub` DOM을 풀스크린으로** 표시(같은 데이터·같은 카운터, 평면). thesis는 살되 공간감만 포기. | API 미지원 브라우저 |

- **자동 감지 코드 패턴**(가이드 146행): `const hasApi = typeof gl.texElementImage2D === 'function';` → false면 2D 폴백 라우트로 리다이렉트하거나 3D 마운트 스킵.
- **발표 환경 점검 체크리스트:** ① 발표 PC Chrome 버전 확인 ② 플래그 사전 Enable + Relaunch ③ 녹화 mp4 로컬 복사 ④ 폴백 2D 라우트 동작 확인 ⑤ `hub_stream.json` 경로 200 확인.
- **`display:none` 금지**(가이드 197행): 텍스처 원본 DOM은 `position:fixed; left:-9999px`로 숨긴다. `display:none`이면 레이아웃 미계산 → 빈 텍스처.

---

## 7. dirty-flag 텍스처 갱신 & 성능 실전 팁

| 팁 | 이유/방법 |
|---|---|
| **dirty-flag 업로드** | 매 프레임 `texElementImage2D`는 GPU 낭비(가이드 200행). 허브 DOM이 **실제로 바뀐 프레임에만** 업로드. 입자 카운터는 N프레임(예 4)마다, 또는 값 변경 시에만 dirty=true. |
| **`renderer.state.reset()`** | `texElementImage2D` 직후 **반드시** 호출(가이드 45·196행). 누락 시 Three.js 상태 꼬임. |
| **Three.Texture 주입** | `renderer.properties.get(tex).__webglTexture = glTex; __webglInit = true`(가이드 67~74행). Three가 재초기화 못 하게. |
| **패널별 분리 텍스처** | 허브 코어만 라이브 갱신(고빈도). Panel A·C는 변화 적음 → 낮은 빈도 dirty 또는 정적 캡처. 전부 매 프레임 갱신 금지. |
| **입자는 DOM이 아니라 3D** | 흐르는 예약 입자는 html-in-canvas가 아니라 **Three.js Points/InstancedMesh**로. DOM 텍스처는 "읽는 패널"에만 쓴다(허브·곡선). 입자까지 DOM이면 성능 폭발. |
| **곡선 패널 선택지** | Panel C 곡선은 ① 별도 DOM(canvas/svg 차트)을 텍스처로, 또는 ② Three.js Line으로 직접. progressive reveal·billboard 라벨 고려 시 **DOM 차트 텍스처가 단순**. |
| **POT 무시** | DOM 텍스처는 2의 거듭제곱 크기 아님 → `generateMipmaps=false`, `CLAMP_TO_EDGE`, `LinearFilter`(가이드 152~159행). |
| **재생 속도 노브** | URL 파라미터로 속도/stride 조절 가능하게(발표 리허설서 튜닝). |

---

## 8. 충돌 관리 (다른 코드 작업방과 병행 중)

⚠️ **이 방(전체흐름)은 앱 코드(`hotel-dss-app/app/**`, `app_pms/**`, `llm_sim/**`)를 절대 수정하지 않는다.** 본 문서는 명세만 제공.

| 파일/경로 | 상태 | 누가 |
|---|---|---|
| `hotel-dss-app/public/hub_stream.json` | ✅ 생성 완료 (이 방 산출물, 데이터) | 전체흐름 방 |
| `results/growth_curve_agg.csv` | ✅ 생성 완료 | 전체흐름 방 |
| `docs/design_22_*.md` (본 문서) | ✅ 명세 | 전체흐름 방 |
| **`hotel-dss-app/app/dashboard/hub/page.tsx`** (신규 2D 허브 DOM = 텍스처 원본) | ❌ 미존재 → **신설 필요** | **코드 방** |
| **`hotel-dss-app/app/infra-room/page.tsx`** (신규 3D 씬) | ❌ 미존재 → **신설 필요** | **코드 방** |
| `public/growth_curve_cumulative.json` (csv→소형 JSON, 선택) | ❌ → 신설 권장 | 코드 방 또는 이 방 |

- **신규 라우트만 추가** → 기존 `/dashboard`, `/dashboard/flexi`, `/dashboard/reservations`, `/pms` 와 **파일 충돌 0**.
- 사이드바(`dashboard/layout.tsx`)에 "Infra Room" 링크를 넣고 싶으면 **그 파일은 다른 방 소유** → 코드 방이 결정. 이 방은 건드리지 않는다.
- ⚠️ **AGENTS.md 주의:** 이 레포 Next.js는 "training data와 다를 수 있음" 경고가 있다. 코드 방은 라우트 신설 전 `node_modules/next/dist/docs/`의 관련 가이드를 먼저 읽을 것.

---

## 9. 정전(canonical) 수치 — 문서간 반드시 일치

| 항목 | 값 | 출처 |
|---|---|---|
| 전환주차 W (robust·지속성 정의) | **84주차** (LGB CI하한 > LR CI상한이 이후 끝까지 유지되는 첫 주차) | `growth_curve_agg.csv` 재계산 2026-06-05 |
| W 시점 누적 학습 건수 | **약 5.4만건 (53,615)** | hub_stream train `wk≤84` 집계 |
| W 이전 우위 | 대체로 tie(CI 겹침), LR은 콜드스타트 구간 우위 | design_18 §4 |
| W 이후 | LightGBM 추월·끝까지 유지 | design_18 §4 |
| 그 사이 | tie(구분 불가) 음영 | design_18 §4 honest-rule |
| full-data PR-AUC | **0.820** (LightGBM 0.8200, XGB 0.8192) | agg week106 |
| Dummy 기준선 | **0.387** | agg |
| 배수 | **2.1배** (0.820 / 0.387) | 계산 |
| 취소율 | 37% (City 41.7% / Resort 27.8%) | CLAUDE.md |
| 운영 임계 | 0.65 | design_18 §3 |
| 데이터 건수 | n_full 119,390 / 현재 커밋본 stream 25,000(균등 다운샘플) | hub_stream meta |
| 정직성 각주 | "risk는 최종 LightGBM 사전계산 — point-in-time 아님, 수집 시연용" | hub_stream `meta.disclaimer` |

> ⚠️ 발표 슬라이드·앱·이 3D 씬의 W·건수·PR-AUC가 어긋나면 신뢰가 깨진다. 위 표가 단일 진실 공급원.

---

## 10. 다른(코드) 방용 구현 프롬프트 — 복붙 블록

```
[작업] Hotel No-Show DSS — 발표 피날레 '3D 인프라 룸' 신규 구현.
명세 정전: docs/design_22_3d_infrastructure_room_spec.md (먼저 정독). 기술 레퍼런스: docs/html_in_canvas_threejs_guide.md.

[⚠️ 이 레포 Next.js 주의]
hotel-dss-app/AGENTS.md 경고: 이 버전 Next.js는 training data와 다를 수 있음.
라우트 신설 전 node_modules/next/dist/docs/ 의 관련 가이드를 반드시 먼저 읽을 것.

[신규 파일만 생성 — 기존 파일 수정 금지]
1) hotel-dss-app/app/dashboard/hub/page.tsx
   - 2D '허브 코어' DOM. 3D 씬의 텍스처 원본이자, 2D 폴백 화면을 겸한다.
   - public/hub_stream.json 을 fetch → 예약일(d) 시간순 가속 재생(1초≈1~2주).
   - 표시: 상단 재생 시점 커서("수집 중 — YYYY-MM-DD"), 중앙 위험3색 누적 카운터(color: high/med/low),
     하단 최근 N건 미니 리스트(country·channel·hotel·risk), 좌하단 고정 각주 = meta.disclaimer 그대로.
   - 색 토큰 재사용: --risk-high #FB7185 / --risk-medium #FBBF24 / --risk-low #34D399 (globals.css).
   - 다크 배경(--bg-dark). 투사 가독성 위해 폰트 크게. URL ?from=YYYY-MM-DD, ?speed=, ?stride= 지원.

2) hotel-dss-app/app/infra-room/page.tsx  (3D 씬, "use client")
   - Three.js(importmap 또는 npm) + html-in-canvas.
   - gl.texElementImage2D 로 위 /dashboard/hub DOM(숨김: position:fixed;left:-9999px, display:none 금지)을
     중앙 'DSS 허브 코어' 패널 텍스처로. dirty-flag 갱신, texElementImage2D 직후 renderer.state.reset() 필수,
     renderer.properties.get(tex).__webglTexture 주입(__webglInit=true), generateMipmaps=false.
   - 3패널 파이프라인: 좌 채널소스(Panel A) → 중앙 허브코어(Panel B,최대) → 우 성장곡선(Panel C). 좌→우 흐름.
   - 흐르는 예약 입자는 DOM이 아니라 Three.js Points/InstancedMesh(풀 상한 ~300, 재활용). 색=color 필드.
   - Panel C 성장곡선: results/growth_curve_agg.csv (window==cumulative) → public/growth_curve_cumulative.json
     로 사전 변환해 사용. 5모델 PR-AUC + CI밴드, 재생 wk와 동기 progressive reveal,
     전환주차 W=84 세로 마커("약 84주차 / 약 5.4만건 이후 부스팅 전환") + tie구간 음영.
   - 카메라: lerp 키프레임 5개 — (0)풀백 establishing → (1)push-in A → (2)push-in B(허브, 최대클로즈업)
     → (3)push-in C(W마커) → (4)풀백 복귀. Space/→ 로 다음 단계. push-in 시 대상 패널이 정면(법선=카메라)·꽉 차게.
   - 가독성: 읽는 텍스트(카운터·W라벨·시점커서·각주·축눈금)는 정면/billboard. 장식(입자·타일측면)만 원근 허용.

[프래질리티 3중 안전망 — 필수]
   - 0 정상: Chrome M146+/Canary + chrome://flags/#canvas-draw-element Enabled.
   - 1 녹화백업: 정상 동작 씬 고해상도 mp4 녹화(발표 전날까지). (수동 작업이지만 코드가 깨지지 않게 안정화)
   - 2 2D 폴백: const hasApi = typeof gl.texElementImage2D==='function'; false면 3D 마운트 스킵하고
     /dashboard/hub 2D 풀스크린으로 폴백(같은 데이터·카운터). thesis 유지, 공간감만 포기.

[정전 수치 — 절대 변경 금지, design_22 §9와 일치]
   전환주차 W=84(robust), 약 5.4만건(53,615), W전 대체로 tie(LR은 콜드스타트 구간 우위) → W후 LightGBM추월(끝까지), 사이는 tie음영,
   full-data PR-AUC 0.820, Dummy 0.387, 2.1배, 취소율37%, 운영임계0.65, 데이터 n_full 119,390건(현재 커밋 stream 25,000 다운샘플).
   허브 각주는 hub_stream.json meta.disclaimer 그대로.

[충돌 금지]
   - 신규 라우트(app/dashboard/hub/, app/infra-room/)만 추가. 기존 app/dashboard/page.tsx, flexi, reservations,
     app/pms/**, dashboard/layout.tsx 등은 수정 금지(다른 방 소유). 사이드바 링크 추가 여부는 코드 방 재량.
   - public/hub_stream.json, results/growth_curve_agg.csv 는 읽기 전용(전체흐름 방 산출물).
   모든 UI 텍스트 한국어. 발표 투사 가독성 최우선.
```

---

## 11. 미결 항목

| # | 항목 | 비고 |
|---|---|---|
| 1 | 발표 PC Chrome 버전·플래그 확인 | M146 미만이면 2D 폴백/녹화로 진행. 리허설서 확정 |
| 2 | 재생 속도·stride 최종값 | 리허설서 60~90초 안에 4단계 끝나도록 튜닝 |
| 3 | Panel C 곡선 = DOM차트 vs Three.Line | DOM차트 권고(progressive·billboard 단순). 코드 방 판단 |
| 4 | `growth_curve_cumulative.json` 생성 주체 | 코드 방 또는 이 방. 소형 변환 스크립트(`src/`)면 이 방 가능 |
| 5 | 사이드바 "Infra Room" 진입 링크 | `dashboard/layout.tsx` = 다른 방 소유. 조율 필요 |
| 6 | test split(2017-03~08) 입자 시각 구분 방식 | 점선/반투명 — "수집되나 학습 제외" 각주 연결 |
