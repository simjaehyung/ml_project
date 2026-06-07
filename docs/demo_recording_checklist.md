# 데모 녹화 체크리스트 (코드방 검증판) — 최종발표 2026-06-10

> 작성: 코드방 데모 Run&Fix 엔지니어 · 2026-06-07
> 이 문서는 **실제로 돌려보고 확인한** 명령·순서만 담는다("돌려보고 말한다"). 전략 대본은 `docs/demo_run_guide.md` 참조.
> 검증 환경: Windows 11 · Node v24.14.1 · npm 11.11.0 · Python 3.13.1 (모두 설치됨, `node_modules`·백엔드 의존성 OK).

---

## 0. 핵심 사실 (먼저 외울 것)

- **허브는 백엔드가 필요 없다.** `npm run dev` 하나로 `/dashboard/hub`가 정적 JSON만으로 단독 구동된다(검증: HTTP 200, 페이지 에러 0).
- 예약/Flexi 탭까지 녹화할 때만 FastAPI(8001)를 띄운다.
- **모델은 실시간 학습하지 않는다.** 화면 우측 **'재학습 현황' 패널**의 모든 수치는 `public/hub_growth.json` **사전계산값**에서 파생된다. 패널 안에 그 사실이 라벨로 박혀 있다.
- 교수가 "지금 학습되는 건가요?" → **"아니요, 미리 계산한 성장 과정을 재생하는 겁니다. 실시간 재학습은 운영 단계(Phase 2, 월 1회)입니다."**

---

## 1. 서버 기동 (검증된 명령)

### 1-A. 허브만 녹화 (권장 · 가장 안정적)
```powershell
# hotel-dss-app 디렉터리에서
npm run dev
# → ✓ Ready, http://localhost:3000/dashboard/hub
```
백엔드 불필요. 이걸로 발표의 심장(데이터 유입 + 성장곡선 + 재학습 패널) 전체가 돈다.

### 1-B. 예약/Flexi 탭까지 녹화할 때만 (선택)
```powershell
# 프로젝트 루트(07_Hotel_DSS)에서 — 별도 터미널
python -m uvicorn api.main:app --port 8001
# 확인: http://localhost:8001/api/v1/dashboard/summary → JSON
```
검증됨: 실제 LightGBM 추론 + SHAP top3 + 한글 라벨 정상(`이전 취소 이력 1회`, `국적: 포르투갈 (PRT)` …). `--reload`는 발표 중 빼라.

> ※ 콘솔(Git Bash 등 cp949 환경)에서 curl 응답의 한글이 깨져 보일 수 있으나 **실제 HTTP 응답·브라우저 표시는 정상**(UTF-8). 화면만 믿어라.

---

## 2. 허브 재생 — 화면 구성 (2분)

`/dashboard/hub` 진입. 좌=예약 유입 스트림 / 우=PR-AUC 성장곡선 + **재학습 현황 패널(신규)**.

**재학습 현황 패널(우측)** — 재생에 동기해 갱신:
- **채택 모델 PR-AUC · LightGBM**: 0.359 → 0.820 (헤드라인 곡선과 동일)
- **현재 선두 (5개 중)**: 주차별 argmax(정직한 경쟁 — 초반 XGBoost/Logistic가 앞서다 종반 LightGBM이 선두). 마지막엔 `LightGBM 0.820`.
- **학습 누적 예약**: 좌측 스트림과 동일 기준(25k 시각화 샘플)으로 일치 — `trained ≤ collected` 모순 없음.
- **재학습 체크포인트**: 누적 walk-forward 재학습 횟수.
- **정직 라벨**(앰버 점선 박스): `데모용 사전 계산 · 실시간 재학습 아님 — 운영 시 월 1회 재학습(Phase 2)`.

### 조작 키
| 키 | 동작 |
|----|------|
| `Space` | 재생 / 일시정지 |
| `c` | 캡쳐모드(컨트롤바 숨김) |
| `f` | 풀스크린 |
| `r` | 처음으로 |
| `1/2/3/4` | 속도 0.5×/1×/2×/4× (기본 1× ≈ 114초 완주) |
| `?capture=1` | 진입 시 캡쳐모드 자동 |

> 컨트롤바 wk 입력칸으로 직접 seek 가능. **단, 입력칸에 포커스가 있으면 `c`/`Space` 키가 안 먹는다**(설계상 입력 중 단축키 무시). 키를 쓰려면 차트 빈 곳을 한 번 클릭해 포커스를 뺀다.

---

## 3. 슬라이드 캡쳐 컷 (자동 생성 검증됨)

6컷이 이미 `presentations/captures/`에 생성·검증되어 있다(컨트롤바 숨김, 1920×1080).

| 파일 | seek wk | 화면 | 패널 표시(검증값) |
|------|:------:|------|------|
| `cap_C1_empty_hub.png` | 27 | 빈 허브, 곡선 바닥 | PR-AUC — / 0건 |
| `cap_C2_early.png` | 40 | 점 누적 초기 | LightGBM 0.617 / 2,594건 |
| `cap_C3_pre_crossover.png` | 70 | 교차 직전 | 선두 XGBoost 0.768 / 7,724건 / 43회 |
| `cap_C4_W_crossover.png` | 84 | **W 전환(클라이맥스)** | LightGBM 0.809 / 11,226건 / 57회 |
| `cap_C5_risk_dist.png` | 100 | 위험 3색 분포 | LightGBM 0.818 / 15,412건 |
| `cap_C6_peak_0820.png` | 120 | **0.820 정점·동결** | LightGBM 0.820 / 16,484건 / 79회 |

### 캡쳐 재생성 (덱 수정 시)
```powershell
# 1) npm run dev 가 떠 있는 상태에서, 프로젝트 루트에서:
$env:PW_MODULE = (Get-ChildItem "$env:LOCALAPPDATA\npm-cache\_npx" -Recurse -Filter index.js |
  Where-Object { $_.FullName -like '*\playwright\index.js' } | Select-Object -First 1).FullName
node scripts/capture_hub.mjs
# → presentations/captures/cap_C1..C6.png 갱신 + 콘솔에 검증 수치 출력(PAGE_ERRORS=[] 확인)
```
(Playwright는 전역 설치본·chromium 캐시를 사용. 별도 npm install 불필요.)

---

## 4. 폴백 1 → 2 → 3 → 4 (위에서 아래로)

| 단계 | 트리거 | 대응 | 상태 |
|------|--------|------|------|
| **1 라이브** | 정상 | `npm run dev` → `/dashboard/hub` 재생 | ✅ 검증(에러 0) |
| **2 사전녹화 mp4** | 서버 안 뜸/버벅임 | 리허설 때 OBS/Game Bar로 받아둔 mp4 재생 | 발표 전 1회 녹화 필요 |
| **3 단독 HTML** | 녹화도 안 열림 | `presentations/dss_story_demo.html` **더블클릭**(서버 0개) | ✅ 검증(file:// 단독 구동, 에러 0) |
| **4 정지 캡쳐** | 프로젝터 호환 문제 | 슬라이드 박힌 `cap_C1~C6.png`로 멘트만으로 진행 | ✅ 6컷 생성됨 |

---

## 5. 발표 30분 전 체크 (코드방 버전)

- [ ] `npm run dev` → `localhost:3000/dashboard/hub` 진입, **빈 허브(wk27)** 확인
- [ ] `Space`로 1회 완주 — 곡선 0.387→0.820, **재학습 패널이 동기 갱신**되는지 눈으로 확인
- [ ] 패널 정직 라벨(`데모용 사전 계산…`) 보이는지 확인
- [ ] (예약/Flexi 녹화 시) `uvicorn … 8001` summary JSON 확인
- [ ] 풀스크린(`f` 또는 F11) + OS 알림 OFF + 북마크바 숨김
- [ ] **폴백 3** `dss_story_demo.html` 더블클릭으로 열리는지 1회 확인
- [ ] 멘트 숫자 = 화면 숫자 일치: **0.387 / wk84·5.4만 / 0.820**

---

## 6. 절대 안 바꾸는 정전 수치 (화면·멘트 공통)

PR-AUC **0.820**(=LightGBM 0.8189) · Dummy **0.387** · **2.1배** · 도심(리스본) **41.7%** / 리조트(알가르브) **27.8%** / 전체 **37%** · W 전환 **wk84 ≈ 5.4만건** · 데이터 **119,390건**(hub 시각화 25k 샘플). RevPAR 개선치는 사전계산·미검증 → **헤드라인 금지**, 쓰면 "데모용 참고치" 라벨.
