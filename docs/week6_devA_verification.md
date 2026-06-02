# Week 6 — DSS + PMS 2단 검증 결과 (Dev A)

> 작성: 이고은 (Dev A) | 검증일: 2026-06-02
> 대상: `api/` (DSS, port 8000) + `app_pms/` (PMS, port 3001) + `hotel-dss-app/` (Next.js, port 3000)
> 목적: 최종발표 Demo 슬라이드 신뢰도 검증 — "실제로 돌아간다" 증명 + 버그·개선점 정리

---

## ✅ 검증 통과 (정상 작동)

### 1. DSS 서버 (api/, port 8000)

| 항목 | 결과 |
|------|------|
| 서버 부팅 | ✅ 모델·SHAP 로드 에러 없음 |
| 엔드포인트 7개 | ✅ `/api/v1/bookings`, `/dashboard/summary`, `/flexi/preview` 등 |
| 초기 시드 데이터 | ✅ 20건 (고위험 7건, Flexi 2건, 평균 위험 0.556) |
| **실제 예측** | ✅ 고위험 예약 POST → risk_score **0.9386** |
| Flexi 판단 | ✅ `flexi_recommended: true`, 할인율 16.4% |
| SHAP top 3 | ✅ 포르투갈 국적 / 리드타임 182일 / 특별요청 0 |

→ **DSS 백엔드는 실제 LightGBM 모델로 예측 + SHAP + Flexi 판단까지 완전 동작.**

### 2. PMS → DSS 2단 흐름 (port 3001 → 8000)

| 항목 | 결과 |
|------|------|
| PMS 부팅 | ✅ (httpx 설치 후) |
| 손님 예약 POST | ✅ `PMS-535BBE` 확인서 발급 |
| 손님 언어 → DSS 번역 | ✅ PRT/Double/Bed&Breakfast → DSS 스키마 |
| DSS 위험점수 수신 | ✅ 0.94 → Flexi Rate 판정 |
| **정보 분리 원칙** | ✅ 손님 확인서엔 "Flexi 14.3% 할인"만, 위험점수 노출 안 됨 |

→ **PMS-DSS 연동 핵심 흐름(손님↔번역↔예측↔재번역)은 정상 작동.**

---

## 🐛 버그 / 미완성 (회의 안건)

### 🔴 B1. PMS DSS_BASE_URL 포트 불일치 — 가이드 vs 코드

- **가이드 문서**: DSS를 `--port 8001`로 띄우라고 안내
- **실제 코드** (`app_pms/pms_mock.py:65`): `DSS_BASE_URL = "http://localhost:8000"`
- **영향**: 가이드대로 DSS를 8001로 띄우면 PMS가 DSS를 못 찾아 예약 실패
- **임시 해결**: DSS를 8000으로 띄우면 정상. 가이드 또는 코드 중 하나로 통일 필요.

### 🔴 B2. PMS admin API 미구현 — UI 폴링 불가

- **가이드 설명**: `admin_reservations()`, `admin_activity()`, `admin_stats()` + `/admin/stats` 등
- **실제 코드**: PMS에 `POST /api/bookings`, `GET /api/bookings` **두 개만** 존재
- `/admin/stats`, `/admin/reservations`, `/admin/activity` → **404**
- **영향**: PMS UI(`/pms` 페이지)가 폴링할 데이터 소스 없음 → 실시간 활동 피드·통계 카드 작동 불가
- **상태**: PMS 서버가 *예약 처리 코어만* 완성, 관리자/UI 연동 API 미구현

### 🔴 B3. Next.js PMS 프론트엔드 미존재

- **가이드 파일 목록**: `app/pms/page.tsx`, `app/pms/reservations/page.tsx`, `lib/pms-api.ts`, `types/pms.ts`
- **실제 repo**: `app/pms/` 폴더 없음. `app/dashboard/*` 만 존재. `lib/pms-api.ts` 없음
- **영향**: 가이드가 설명한 PMS 관리자 뷰가 repo에 push 안 됨
- **추정**: PM이 로컬 작업 중 (아직 미push) — 회의에서 진행 상황 확인 필요

### 🟡 B4. llm_sim/ 폴더 미존재

- **가이드 설명**: `llm_sim/personas.py`, `agents.py`, `run_simulation.py` — LLM 손님 에이전트 5명
- **실제 repo**: `llm_sim/` 폴더 없음
- **상태**: 가이드에도 "LLM 시뮬레이션 아직 미완"이라 명시됨. PM 작업 대기.

### 🟡 B5. requirements.txt 미갱신

- 현재 `requirements.txt`에 **fastapi, uvicorn, httpx 없음** (streamlit 시대 그대로)
- 새 팀원이 clone하면 서버 못 띄움
- **수정 필요**: fastapi, uvicorn[standard], httpx, anthropic(LLM용) 추가

---

## 💡 개선 제안 (발표 효과 ↑)

> PM 제시 5개 + Dev A 추가. 우리 Streamlit 작업 자산 활용 가능한 것 우선.

| # | 아이디어 | 난이도 | 발표 효과 | Dev A 메모 |
|---|---------|--------|----------|-----------|
| 1 | 위험점수 분포 히스토그램 (PMS 대시보드) | 하 | 중 | matplotlib 경험 활용 |
| 2 | Flexi vs Standard 비율 도넛 차트 | 하 | 중 | |
| 3 | 에이전트별 예약 히스토리 그래프 | 중 | 중 | |
| 4 | **신규 예약 입력 폼 (/pms/new)** | 중 | **상** | **Streamlit 탭2 폼 로직 그대로 이식 가능** |
| 5 | 에이전트 Flexi "거절" 시나리오 | 상 | 상 | LLM 프롬프트 작업 — PM 영역 |
| 6 | **(추가) 정보 분리 시각화** | 하 | **상** | 손님 화면 vs 매니저 화면 나란히 — "손님은 위험점수 모름"을 시각적으로 강조. 검증에서 확인된 강점 |
| 7 | **(추가) 데이터 일관성 배지** | 하 | 중 | PMS 위험점수 = DSS 상세 일치 표시 (검증 항목이라 자연스러움) |

---

## 📋 금요일 회의 가져갈 것

1. **버그 B1~B5** — 특히 B1(포트), B2·B3(PMS UI 미완) 진행 상황 PM에게 확인
2. **검증 통과 항목** — DSS 예측·PMS 2단 흐름은 완전 동작 (Demo 슬라이드 신뢰도 OK)
3. **개선 제안 #4, #6** — Dev A가 맡으면 좋을 것 (Streamlit 자산 활용 + 발표 효과 높음)
4. **requirements.txt 갱신** — Dev A가 바로 처리 가능

---

## 실행 방법 (검증 재현용 — 포트 정정 반영)

```bash
# 터미널 1 — DSS (8000! 가이드의 8001 아님)
.venv/Scripts/python.exe -m uvicorn api.main:app --port 8000

# 터미널 2 — PMS (3001)
.venv/Scripts/python.exe -m uvicorn app_pms.pms_mock:app --port 3001

# 터미널 3 — Next.js (npm install 먼저!)
cd hotel-dss-app && npm install && npm run dev

# 사전 설치 필요 패키지
pip install fastapi uvicorn httpx
```

---

## 변경 이력

| 날짜 | 작성자 | 내용 |
|------|--------|------|
| 2026-06-02 | 이고은 (Dev A) | DSS·PMS 2단 검증 완료 + 버그 5건 + 개선 제안 7건 |
