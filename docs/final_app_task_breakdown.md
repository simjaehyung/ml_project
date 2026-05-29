# 최종발표 앱 개발 — 업무 분배표

> 작성: 심재형 | 2026-05-28  
> 심재형(백엔드·ML·LLM) / 이고은(프론트엔드·UI) 완전 분리

---

## 핵심 규칙

1. **심재형이 Day 1에 목업 API를 배포**하면 이고은은 그날부터 독립 작업 시작
2. **이고은은 실제 모델이 연결되기 전까지 목업 API로만 작업** — 나중에 실제 모델로 교체해도 UI 코드는 안 바꿔도 됨
3. 둘 다 **Claude Code 에이전트** 활용. 이 문서의 각 태스크가 에이전트에게 줄 스펙

---

## 심재형 태스크

### Day 0 — 5/28(수) 오전 (최우선)

**[T-심-00] 목업 API 배포** ← 이고은 작업 시작 조건

이고은이 오늘부터 작업하려면 이것부터.

```python
# 할 일: api/main.py 만들고 로컬에서 실행 확인
# 출력: localhost:8000 에서 아래 엔드포인트 응답 확인

POST /api/v1/bookings
  → { "bookingId": "RES-001", "riskScore": 0.78,
      "flexiRecommended": true, "discountRate": 0.164,
      "topRiskFactors": ["리드타임 92일", "OTA 채널", "디포짓 없음"] }

GET /api/v1/bookings
  → { "bookings": [20건 더미 데이터] }

GET /api/v1/bookings/{id}
  → 단건 상세

GET /api/v1/dashboard/summary
  → { "totalBookings": 147, "highRisk": 34,
      "flexiRouted": 12, "avgRiskScore": 0.61 }
```

완료 후 이고은에게 URL + API 응답 스키마 문서 전달.

---

### Day 1 — 5/28(수) 오후

**[T-심-01] Vercel Next.js + FastAPI 스타터 셋업**

```
1. npx create-next-app@latest hotel-dss-app --typescript --tailwind --app
2. cd hotel-dss-app
3. npx shadcn@latest init  (← 디자인 시스템 설치)
4. npx shadcn@latest add table button badge card
5. api/ 폴더 만들고 main.py 이동
6. uvicorn api.main:app --port 8000 실행 확인
7. 이고은에게 레포 URL + 실행법 전달
```

**[T-심-02] API 응답 스키마 문서 작성**

이고은이 Claude Code 에이전트에게 줄 명세 기반.

```markdown
# API 스키마 문서 (이고은 전달용)

## POST /api/v1/bookings
Request 필드: arrivalDate, departureDate, adults, children,
             country(ISO3), channel, mealPlan, roomType,
             specialRequests, leadTimeDays, previousCancellations

Response:
{
  "bookingId": string,
  "riskScore": float (0~1),
  "flexiRecommended": boolean,
  "discountRate": float (0.05~0.18),
  "topRiskFactors": string[] (3개)
}

## GET /api/v1/bookings
Response:
{
  "bookings": [{
    "bookingId": string,
    "guestCountry": string,
    "arrivalDate": string,
    "hotel": "City Hotel" | "Resort Hotel",
    "riskScore": float,
    "flexiRecommended": boolean,
    "status": "confirmed" | "high-risk" | "flexi-routed"
  }]
}
```

---

### Day 2~3 — 5/29~30

**[T-심-03] 학교 서버 셋업 + 시뮬레이션**

기존 계획 유지:
- 5/29: 학교 서버 셋업 + dry-run 50건
- 5/30 야간: 전수 시뮬레이션 (~13,355건)

**[T-심-04] pms_adapter.py 작성**

```python
# 할 일: Apaleo JSON → 우리 모델 입력 형식 변환
# 파일: api/pms_adapter.py

FIELD_MAP = {
    "stay.adults":                        "adults",
    "stay.arrivalDate":                   "arrival_date",
    "channelCode":                        "distribution_channel",
    "guestProfile.nationality":           "country",
    "guestProfile.previousCancellations": "previous_cancellations",
    "mealPlan":                           "meal",
    # lead_time = arrivalDate - bookingDate (계산)
    # 날씨: 월별 계절 평균값 자동 주입
}

def adapt(apaleo_json: dict) -> dict:
    # 변환 로직
    ...
```

---

### Day 4 — 5/31(토)

**[T-심-05] 시뮬레이션 결과 분석**

기존 계획: `python src/sim_analyze.py`

**[T-심-06] 실제 LightGBM 목업 교체**

```python
# api/predictor.py
import joblib
model = joblib.load("results/model_final.pkl")

def predict(features: dict) -> float:
    # 실제 모델로 교체
    ...
```

이 시점부터 이고은 UI가 실제 예측값을 받음. UI 코드 변경 없음.

---

### Day 5~6 — 6/1~2

**[T-심-07] 이고은과 통합 테스트**

- App 1에서 예약 입력 → FastAPI → App 2 대시보드 반영 확인
- 에러 있으면 백엔드 쪽 수정

---

### Day 7~8 — 6/3~4

**[T-심-08] LLM 게스트 API 구축**

```python
# 추가할 엔드포인트
POST /api/v1/llm/book       # LLM 에이전트 예약용 (Bearer 토큰)
GET  /api/v1/llm/status     # 실시간 대시보드 상태

# Claude tool_use 정의 파일
# demo/tool_definitions.json
```

**[T-심-09] LLM 데모 스크립트**

```python
# demo/llm_demo.py
# 4개 페르소나 에이전트가 순서대로 예약
# 고위험 예약이 Flexi 라우팅되는 과정 실시간 출력
```

---

### Day 9~10 — 6/5~6

**[T-심-10] 발표 자료 + 데모 시나리오 완성**

---

## 이고은 태스크

> Claude Code 에이전트에게 아래 태스크를 **하나씩** 준다.  
> 에러나면 에러 메시지 전체 복사해서 에이전트에게 줄 것.

### 시작 전 환경 설정

심재형에게 받아야 하는 것:
- [ ] 레포 URL (또는 폴더)
- [ ] `localhost:8000` 목업 API 실행 확인
- [ ] API 스키마 문서

```bash
# 이고은 환경 설정
cd hotel-dss-app
npm install
npm run dev  # localhost:3000 확인
```

---

### [T-은-01] App 1 — 예약 목록 페이지

**Claude Code에게 줄 프롬프트:**
```
Next.js 14 App Router + shadcn/ui 기반.
`/dashboard/reservations` 페이지 만들어줘.

`GET http://localhost:8000/api/v1/bookings` 호출해서 데이터 받아와.
응답 스키마:
{
  bookings: [{
    bookingId: string,
    guestCountry: string,
    arrivalDate: string,
    hotel: "City Hotel" | "Resort Hotel",
    riskScore: number (0~1),
    flexiRecommended: boolean,
    status: "confirmed" | "high-risk" | "flexi-routed"
  }]
}

shadcn DataTable로 표시. 컬럼:
1. Booking ID
2. Guest Country (국기 이모지 + 국가명)
3. Arrival Date
4. Hotel
5. Risk Score — 0.7 이상: 빨간 Badge, 0.4~0.7: 노란 Badge, 미만: 초록 Badge
6. Status

테이블 상단에 검색 input (bookingId, country 필터).
TypeScript 타입 포함.
```

---

### [T-은-02] App 1 — 신규 예약 입력 폼

**Claude Code에게 줄 프롬프트:**
```
Next.js + shadcn/ui.
`/dashboard/reservations/new` 페이지. 신규 예약 입력 폼.

폼 필드:
- Arrival Date (DatePicker)
- Departure Date (DatePicker)
- Adults (1~10 숫자 input)
- Children (0~10 숫자 input)
- Guest Country (Select, ISO3 국가 코드 목록)
- Distribution Channel (Select: Direct / OTA / Corporate / TA)
- Meal Plan (Select: BB / HB / FB / SC)
- Room Type (Select: EP / DBL / SNG / TWN)
- Special Requests (0~5 Slider)
- Deposit Type (Select: No Deposit / Non Refund / Refundable)

제출 시 POST http://localhost:8000/api/v1/bookings 호출.
응답에서 riskScore 받으면 모달로 표시:
  - riskScore 0.7 이상: "⚠️ 고위험 예약 — Flexi 라우팅 권장 (할인율 XX%)"
  - 미만: "✅ 일반 배정"
shadcn Form + Zod 유효성 검사 포함.
```

---

### [T-은-03] App 1 — 예약 상세 & SHAP 패널

**Claude Code에게 줄 프롬프트:**
```
`/dashboard/reservations/[id]` 동적 라우트 페이지.
`GET http://localhost:8000/api/v1/bookings/{id}` 호출.

레이아웃: 좌측 2/3 예약 정보 카드, 우측 1/3 위험도 패널.

왼쪽 카드: 예약 상세 정보 표 (label: value 형식)

오른쪽 패널:
- 위험도 게이지 (0~1 Progress bar, 0.7 이상 빨간색)
- topRiskFactors 3개를 카드 형태로 표시
- flexiRecommended true이면 "Flexi 라우팅 권장" 배너 (노란 배경)
  + 할인율 표시

shadcn Card, Progress, Badge 사용.
```

---

### [T-은-04] App 2 DSS — 메인 대시보드

**Claude Code에게 줄 프롬프트:**
```
Next.js + shadcn/ui.
`/dashboard` 메인 페이지.
`GET http://localhost:8000/api/v1/dashboard/summary` 호출.

응답:
{
  totalBookings: number,
  highRisk: number,
  flexiRouted: number,
  avgRiskScore: number
}

상단 4개 KPI 카드:
1. 전체 예약 수
2. 고위험 예약 수 (빨간 강조)
3. Flexi 라우팅 완료
4. 평균 위험도

그 아래 예약 목록 테이블 (T-은-01과 동일한 DataTable, 재사용).
5초마다 자동 refresh (useEffect + setInterval).

shadcn Card, Table 사용. 다크 테마 (#0F1117 배경).
```

---

### [T-은-05] App 2 DSS — Flexi 라우팅 패널

**Claude Code에게 줄 프롬프트:**
```
`/dashboard/flexi` 페이지.
Flexi 정책 설정 + 현황 대시보드.

상단: 임계값 설정 카드
- Threshold Slider (0.50~0.85, 기본 0.65)
- 슬라이더 값 바꾸면 아래 예측 수치 실시간 업데이트
  (GET /api/v1/flexi/preview?threshold=0.65 호출)
- 예상 Flexi 풀 규모 / 예상 walk rate 표시

하단: 현재 Flexi 풀 테이블
- Flexi 라우팅된 예약 목록
- 각 예약의 risk_score, 할인율, 고객 국가

shadcn Slider, Card, Table 사용.
```

---

### [T-은-06] 사이드바 네비게이션

**Claude Code에게 줄 프롬프트:**
```
Next.js App Router 레이아웃.
`app/dashboard/layout.tsx` 에 왼쪽 사이드바 추가.

메뉴 항목:
- Overview (집 아이콘) → /dashboard
- Reservations (목록 아이콘) → /dashboard/reservations
- Flexi Policy (설정 아이콘) → /dashboard/flexi
- New Booking (+ 아이콘) → /dashboard/reservations/new

상단에 "Hotel DSS" 로고 텍스트.
하단에 "LightGBM PR-AUC 0.8189" 작은 뱃지.

shadcn 기반, 다크 테마 (#1C1E26 사이드바 배경).
선택된 메뉴 아이템 강조 표시.
```

---

### [T-은-07] App 1 ↔ App 2 연결 확인

심재형의 실제 모델 교체(T-심-06) 이후:

- [ ] App 1 폼 제출 → FastAPI → App 2 대시보드에 새 예약 표시되는지 확인
- [ ] risk_score가 실제 모델 값으로 바뀌는지 확인
- [ ] 고위험 예약 Flexi 라우팅 플로우 전체 테스트

---

## 의존성 다이어그램

```
심재형 T-심-00 (목업 API)
    │
    └──→ 이고은 T-은-01 ~ T-은-06 (독립 진행)
    
심재형 T-심-06 (실제 모델 교체)
    │
    └──→ T-은-07 (통합 확인, 둘이 같이)

심재형 T-심-08 (LLM API)
    │
    └──→ 발표 데모 시나리오
```

---

## 컷 기준

| 조건 | 조치 |
|------|------|
| 6/7까지 App 1 미완성 | 발표에서 App 1 생략, App 2만 시연 |
| LLM API 미완성 | 녹화 영상으로 대체 |
| Next.js 에러로 이고은 블로킹 | 심재형이 해당 컴포넌트 인계 |

---

## 관련 문서

| 문서 | 내용 |
|------|------|
| [design_15_final_app_architecture.md](design_15_final_app_architecture.md) | 전체 아키텍처 + API 엔드포인트 스펙 |
| [final_presentation_appdev_plan.md](final_presentation_appdev_plan.md) | 계획서 + 타임라인 |
