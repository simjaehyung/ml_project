# API 계약 문서 — 연결고리 정의

> 작성: 심재형 | 2026-05-28  
> **이 문서와 `api/schemas.py`가 바뀌면 반드시 두 사람 모두 확인.**  
> 이고은은 `api/types.ts`를 기준으로 코드를 작성.

---

## 연결 지점 전체 지도 (Option B 확정)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│  [LLM 손님 에이전트들]                                                      │
│    Claude API 페르소나 4종                                                  │
│                                                                            │
│  GuestBookingRequest ──────────────────────────────────────┐              │
│  Authorization: Bearer pms-guest-key-2026                   │              │
│                                                             ▼              │
│                              ┌──────────────────────────────────────┐     │
│                              │  App 1: Hotel PMS (port 3001)         │     │
│                              │  app_pms/pms_mock.py                  │     │
│                              │                                        │     │
│  [호텔 스태프 UI]              │  POST /api/bookings  (LLM용)          │     │
│  Next.js 프런트엔드 ──────────►│  GET  /api/bookings  (LLM용)          │     │
│  예약 입력 폼·목록              │                                        │     │
│                              │  _translate_to_dss()  ← 번역 레이어    │     │
│                              │  GuestBookingRequest                   │     │
│                              │       ↓ 변환                           │     │
│                              │  BookingRequest                        │     │
│                              └──────────────┬───────────────────────┘     │
│                                              │ 내부 proxy 호출              │
│                                              │ POST /api/v1/bookings        │
│                                              ▼                              │
│                              ┌──────────────────────────────────────┐     │
│                              │  FastAPI DSS (port 8000)              │     │
│                              │  api/main.py (혹은 main_mock.py)      │     │
│                              │                                        │     │
│                              │  POST /api/v1/bookings ──► LightGBM  │     │
│                              │  GET  /api/v1/bookings        + SHAP  │     │
│                              │  GET  /api/v1/bookings/{id}           │     │
│                              │  GET  /api/v1/dashboard/summary       │     │
│                              │  GET  /api/v1/flexi/preview           │     │
│                              └──────────────┬───────────────────────┘     │
│                                              │                              │
│                              BookingListResponse  DashboardSummary         │
│                              FlexiPreview                                  │
│                                              │ polling (5초마다)            │
│                                              ▼                              │
│                              ┌──────────────────────────────────────┐     │
│                              │  App 2: DSS 대시보드 (port 3000)      │     │
│                              │  Next.js 프런트엔드                    │     │
│                              │  읽기 전용 — 절대 쓰기 없음             │     │
│                              └──────────────────────────────────────┘     │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

### 핵심 원칙

| 원칙 | 내용 |
|------|------|
| LLM은 PMS만 안다 | DSS의 존재, risk_score, shap_values 모름 |
| PMS는 번역자다 | GuestBookingRequest ↔ BookingRequest 변환 담당 |
| DSS는 엔진이다 | ML 추론만. 손님이 누군지 모름 |
| App 2는 독자다 | 쓰기 없음. GET 요청만 |
| 데이터는 단방향 | LLM → PMS → DSS. 역방향 없음 |

---

## 연결고리 0 — LLM 에이전트 → App 1 PMS (신규)

**엔드포인트:** `POST http://localhost:3001/api/bookings`  
**인증:** `Authorization: Bearer pms-guest-key-2026`  
**스키마:** `app_pms/pms_schemas.py` → `GuestBookingRequest`

```python
# LLM 에이전트 데모 스크립트 호출 예시
import httpx

headers = {"Authorization": "Bearer pms-guest-key-2026"}
response = httpx.post(
    "http://localhost:3001/api/bookings",
    json={
        "hotel": "City Hotel",
        "arrival_date": "2026-08-15",
        "departure_date": "2026-08-18",
        "adults": 2,
        "room_type_preference": "Double",
        "meal_plan": "Bed & Breakfast",
        "nationality": "GBR",
        "special_requests": "Late check-out requested",
        "agent_id": "guest-agent-B",
        "persona_description": "마지막 순간 예약형 레저 여행자, 취소 이력 2회",
    },
    headers=headers,
)
# 응답: GuestBookingConfirmation
# {
#   "confirmation_number": "PMS-A3F29C",
#   "pricing_type": "Flexi Rate",   ← 손님이 볼 수 있는 유일한 DSS 신호
#   "discount_applied": 0.164,
#   "message": "Flexi 요금제로 예약되었습니다...",
#   ...
# }
```

**LLM이 알 수 있는 것:**
- 예약 확정 여부
- Standard vs Flexi 요금제 (할인율)
- 안내 메시지

**LLM이 절대 모르는 것:**
- risk_score (0.78 같은 숫자)
- flexi_recommended (내부 판단)
- shap_values (모델 해석)

---

## 연결고리 1 — App 1 폼 → FastAPI

**엔드포인트:** `POST http://localhost:8000/api/v1/bookings`  
**Content-Type:** `application/json`  
**인증:** 없음 (내부 앱)

### 이고은이 보내야 하는 것

```typescript
// 폼 제출 예시 (Next.js)
const response = await fetch("http://localhost:8000/api/v1/bookings", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(formData),  // BookingRequest 타입
});
const result: BookingResponse = await response.json();
```

### 반드시 지켜야 할 규칙

| 항목 | 규칙 | 위반 시 |
|------|------|---------|
| 날짜 형식 | `"YYYY-MM-DD"` 문자열 | 422 Validation Error |
| country | 3자리 대문자 ISO alpha-3 | 422 Error |
| departure_date | arrival_date보다 무조건 나중 | 422 Error |
| 필수 필드 누락 | hotel, arrival_date, departure_date, adults, distribution_channel, market_segment, reserved_room_type, meal, country, customer_type, adr | 422 Error |
| adr | 0 이상 실수 | 422 Error |

### 응답에서 꺼내야 하는 것

```typescript
const {
  booking_id,        // "BK-3F9A1C" 형태 문자열
  risk_score,        // 0~1 실수
  flexi_recommended, // boolean
  discount_rate,     // null 또는 0.05~0.18 실수
  top_risk_factors,  // RiskFactor[] — 항상 3개
  confidence,        // "HIGH" | "MEDIUM" | "LOW"
  status,            // "confirmed" | "high-risk" | "flexi-routed"
} = result;
```

---

## 연결고리 2 — App 2 대시보드 → FastAPI (polling)

**방식:** 5초마다 자동 refresh (`useEffect` + `setInterval`)

```typescript
// App 2 대시보드 polling 예시
useEffect(() => {
  const fetchSummary = async () => {
    const res = await fetch("http://localhost:8000/api/v1/dashboard/summary");
    const data: DashboardSummary = await res.json();
    setSummary(data);
  };
  fetchSummary();
  const timer = setInterval(fetchSummary, 5000);
  return () => clearInterval(timer);
}, []);
```

### GET /api/v1/bookings 쿼리 파라미터

| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `status` | `BookingStatus` (선택) | 상태 필터 |
| `min_risk` | `number` (선택, 0~1) | 최소 위험도 필터 |

```
GET /api/v1/bookings?status=high-risk
GET /api/v1/bookings?min_risk=0.7
```

---

## 연결고리 3 — App 2 Flexi 패널 슬라이더 → FastAPI

```typescript
// 슬라이더 값 바뀔 때마다 호출 (debounce 300ms 권장)
const preview = await fetch(
  `http://localhost:8000/api/v1/flexi/preview?threshold=${threshold}`
).then(r => r.json()) as FlexiPreview;
```

---

## 연결고리 4 — LLM 에이전트 → FastAPI

**엔드포인트:** `POST http://localhost:8000/api/v1/llm/book`  
**인증:** `Authorization: Bearer hotel-dss-demo-key-2026` 헤더 필수

```python
# LLM 에이전트 호출 예시 (Python)
import httpx
headers = {"Authorization": "Bearer hotel-dss-demo-key-2026"}
response = httpx.post(
    "http://localhost:8000/api/v1/llm/book",
    json={**booking_data, "agent_id": "guest-B", "persona": "마지막 순간 레저 여행자"},
    headers=headers,
)
```

---

## 변경 금지 사항 (Breaking Changes)

다음을 바꾸면 **반드시 상대방에게 먼저 알려야** 한다:

| 항목 | 영향 |
|------|------|
| 응답 필드명 변경 (예: `risk_score` → `riskScore`) | 이고은 코드 전체 파손 |
| enum 값 변경 (예: `"TA/TO"` → `"OTA"`) | 이고은 코드 전체 파손 |
| 필수 필드 추가 | 이고은 폼 수정 필요 |
| 응답 구조 중첩 변경 | 이고은 코드 수정 필요 |

---

## 개발 환경 실행

### 심재형 — 목업 서버

```bash
# 프로젝트 루트에서
pip install fastapi uvicorn pydantic
uvicorn api.main_mock:app --port 8000 --reload

# 확인: http://localhost:8000/docs → Swagger UI
```

### 이고은 — Next.js

```bash
# Next.js 프로젝트 폴더에서
npm run dev   # localhost:3000

# api/types.ts → src/types/api.ts 로 복사
```

### 동시 실행 (통합 테스트)

```bash
# 터미널 1
uvicorn api.main_mock:app --port 8000 --reload

# 터미널 2
cd hotel-dss-app && npm run dev
```

---

## 목업 → 실제 모델 교체 시 이고은이 할 것

**없다.** 심재형이 `main_mock.py` → `main.py`로 교체하면 URL과 스키마가 동일하기 때문에 이고은의 프론트엔드 코드는 변경 없이 실제 예측값을 받는다.

---

## pms_adapter.py — Apaleo → DSS 컬럼 매핑

실제 PMS 연동 시연의 핵심. 발표에서 이 테이블을 화면에 보여주면서  
"연동은 컬럼 매핑 문제입니다 — Apaleo 필드의 80%가 직접 대응됩니다" 설명.

| Apaleo 필드 | DSS 모델 입력 | 처리 방식 |
|------------|-------------|---------|
| `adults` | `adults` | 직접 매핑 |
| `children` | `children` | 직접 매핑 |
| `arrival` | `arrival_date` | 날짜 파싱 |
| `departure` | `departure_date` | 날짜 파싱 |
| `channelCode` | `distribution_channel` | 직접 매핑 |
| `ratePlan.id` | `reserved_room_type` | 직접 매핑 |
| `guestProfile.nationality` | `country` | 직접 매핑 (ISO alpha-3) |
| `guestProfile.previousCancellations` | `previous_cancellations` | 직접 매핑 |
| `mealPlan` | `meal` | BB/HB/FB/SC 코드 변환 |
| `arrival` - `bookingDate` | `lead_time` | **계산** (서버 자동 처리) |
| _(없음)_ | 날씨 피처 | **계절 평균값 자동 주입** (arrival_date 기준) |
| _(없음)_ | `hotel` | 앱 설정에서 가져옴 (City / Resort) |

---

## 발표 당일 실행 순서

```bash
# 터미널 1 — FastAPI DSS (두뇌)
uvicorn api.main:app --port 8000

# 터미널 2 — App 1 PMS + App 2 Dashboard
cd hotel-dss-app && npm run dev   # localhost:3000 (App 2 대시보드)

# 터미널 3 — PMS API (LLM 에이전트용)
uvicorn app_pms.pms_mock:app --port 3001

# 터미널 4 — LLM 데모 (발표 피날레)
python demo/llm_demo.py
```

**실행 순서 주의:** FastAPI(8000) 먼저, 그 다음 PMS(3001), 마지막에 Next.js(3000).  
LLM 데모는 발표 7번 슬라이드 타이밍에 실행.

---

## 관련 파일

| 파일 | 역할 |
|------|------|
| `api/schemas.py` | Pydantic 스키마 — 백엔드 계약의 단일 진실 공급원 |
| `api/types.ts` | TypeScript 타입 — 프론트엔드 계약의 단일 진실 공급원 |
| `api/main_mock.py` | 목업 FastAPI 서버 — 이고은 UI 개발 시작용 |
| `api/main.py` | 실제 FastAPI 서버 — 심재형이 모델 연결 후 작성 |
| `api/pms_adapter.py` | Apaleo → DSS 모델 입력 변환 레이어 |
| `app_pms/pms_mock.py` | LLM 에이전트용 PMS 서버 (port 3001) |
| `demo/llm_demo.py` | LLM 손님 에이전트 데모 스크립트 |
