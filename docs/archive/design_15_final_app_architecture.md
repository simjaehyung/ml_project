# 최종발표 앱 아키텍처 (v2)

> 최종 업데이트: 2026-05-28  
> 기존 Streamlit 단일 앱 → 두 앱 + LLM API 구조로 전환

---

## 전체 시스템 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                        발표 데모 흐름                              │
│                                                                   │
│  [App 1: Hotel PMS Simulator]                                     │
│       예약 입력 UI (Apaleo 스키마 모방)                              │
│              │                                                    │
│              │ POST /api/v1/bookings (JSON)                       │
│              ▼                                                    │
│  [FastAPI Backend — DSS 엔진]                                     │
│       pms_adapter.py: Apaleo → 모델 입력 형식 변환                  │
│       LightGBM 추론: risk_score, flexi_recommended                │
│       SHAP: top 3 위험 피처                                        │
│              │                                                    │
│              │ WebSocket / polling                                │
│              ▼                                                    │
│  [App 2: DSS 대시보드]                                             │
│       예약 우선순위 테이블 (탭 1)                                    │
│       Flexi 라우팅 패널 (탭 2)                                      │
│              ▲                                                    │
│              │ tool_use (Bearer 토큰)                             │
│  [LLM 에이전트들]  — Claude API, 손님 페르소나                      │
│       손님 A (비즈니스 여행자)                                       │
│       손님 B (마지막 순간 예약형)                                    │
│       손님 C (취소 이력 있는 레저형)                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## App 1 — Hotel PMS Simulator

### 목적
실제 호텔 PMS(Property Management System)처럼 생긴 예약 관리 인터페이스.
여기서 입력한 예약 데이터가 자동으로 DSS로 흘러간다는 것을 시연.

### 참고 PMS: Apaleo

Apaleo는 클라우드 네이티브 PMS로 REST API와 개발자 샌드박스가 공개되어 있다.
App 1은 Apaleo의 Reservation 오브젝트 스키마를 모방해서 만든다.

**Apaleo Reservation 오브젝트 (핵심 필드):**
```json
{
  "id": "RES-2847",
  "status": "Confirmed",
  "arrival": "2026-07-15",
  "departure": "2026-07-18",
  "adults": 2,
  "children": 0,
  "channelCode": "OTA",
  "ratePlan": { "id": "BAR" },
  "roomType": { "id": "DBL" },
  "totalGrossAmount": { "amount": 420.00, "currency": "EUR" },
  "mealPlan": "Breakfast",
  "guestProfile": {
    "nationality": "GBR",
    "previousStays": 2,
    "previousCancellations": 1
  },
  "specialRequests": ["Early check-in"],
  "bookingDate": "2026-04-14",
  "requiresCreditCard": false
}
```

### 컴포넌트

| 화면 | 내용 |
|------|------|
| 예약 목록 | 체크인 날짜순, 상태 뱃지(Confirmed/Modified/Cancelled), DSS 위험도 컬럼 |
| 신규 예약 폼 | Apaleo 필드 기반 입력, 제출 시 DSS API 자동 호출 |
| 예약 상세 | 우측 패널 — 예약 정보 + DSS 위험도 + SHAP 근거 3개 |

### 기술 스택

**경량 버전 (권장):** Streamlit + 커스텀 CSS
- 기존 Streamlit 스킬 재활용
- 독립 실행: `streamlit run app_pms.py --server.port 8502`

**풀 버전 (시간 있을 때):** Next.js 14 + shadcn/ui
- 더 실제 PMS처럼 보임
- 개발 시간 3~4일 추가

---

## App 2 — DSS 대시보드

### App 1과의 차이

| 항목 | App 1 | App 2 |
|------|-------|-------|
| 사용자 | 프런트데스크 직원 (예약 입력) | 호텔 매니저 (의사결정) |
| 입력 | 예약 폼 | App 1의 API 데이터 자동 수신 |
| 출력 | 예약 접수 확인 | 위험도 순위 + Flexi 권장 |

### UI 격상 방향 (경로 A — CSS 커스텀)

**색상 시스템:**
```css
:root {
  --risk-low:    #2ECC71;   /* 위험도 0~0.4 */
  --risk-medium: #F39C12;   /* 위험도 0.4~0.7 */
  --risk-high:   #E74C3C;   /* 위험도 0.7+ */
  --bg-dark:     #0F1117;
  --bg-card:     #1C1E26;
  --text-primary: #FAFAFA;
}
```

**교체할 컴포넌트:**
- 기본 Streamlit 버튼 → 커스텀 CSS 버튼
- 기본 테이블 → `st.dataframe` + 조건부 셀 색상
- 기본 사이드바 → `streamlit-option-menu`로 교체
- Matplotlib 차트 → Plotly (인터랙티브)

**전문 바이브코딩 워크플로우:**
1. 디자인 시스템(색상·타이포·간격) 먼저 결정
2. 컴포넌트 단위로 명세 작성
3. 명세를 Claude에게 하나씩 주문 (전체 X, 컴포넌트 O)
4. 예시 지시: "shadcn DataTable 스타일로 예약 목록 테이블. risk_score 0.7 이상은 빨간 뱃지, 행 클릭 시 오른쪽 패널에 SHAP waterfall 표시. Plotly 사용."

---

## FastAPI 백엔드

### 엔드포인트 정의

```python
# 예약 제출 (App 1 → 백엔드)
POST /api/v1/bookings
  Request:  ApaleoReservation (JSON)
  Response: BookingResult

# 위험도 조회
GET /api/v1/bookings/{booking_id}/risk
  Response: RiskAssessment

# Flexi 라우팅 결정
POST /api/v1/bookings/{booking_id}/route
  Request:  { "manager_decision": "flexi" | "standard" }
  Response: RoutingResult

# 전체 대시보드 요약 (App 2 polling용)
GET /api/v1/dashboard/summary
  Response: DashboardSummary

# OpenAPI 스펙 (자동 생성)
GET /docs
GET /openapi.json
```

### 응답 스키마

```python
class BookingResult(BaseModel):
    bookingId: str
    riskScore: float            # 0~1
    flexiRecommended: bool
    discountRate: float         # 0.05~0.18
    topRiskFactors: list[str]   # SHAP top 3 자연어
    confidence: str             # "HIGH" | "MEDIUM" | "LOW"

class RiskAssessment(BaseModel):
    bookingId: str
    riskScore: float
    shapValues: dict[str, float]
    recommendation: str         # "FLEXI" | "STANDARD" | "FLAG"
```

### pms_adapter.py — 핵심 매핑 레이어

```python
# 발표에서 이 매핑 테이블을 화면에 보여주는 것이 핵심
APALEO_TO_MODEL = {
    "adults":                  "adults",
    "children":                "children",
    "arrival":                 "arrival_date",          # 날짜 파싱 필요
    "channelCode":             "distribution_channel",
    "ratePlan.id":             "reserved_room_type",
    "guestProfile.nationality":"country",
    "guestProfile.previousStays":         "previous_bookings_not_canceled",
    "guestProfile.previousCancellations": "previous_cancellations",
    "mealPlan":                "meal",
    # lead_time: arrival - bookingDate (계산 필요)
    # hotel: 앱 설정에서 가져옴 (City / Resort)
    # 날씨: 계절 평균값 자동 입력 (arrival_date 기준)
}
```

**발표 포인트:** 매핑 테이블 슬라이드 한 장 — "Apaleo 기준 필드의 80%가 직접 대응됩니다. 나머지 20%는 계산(lead_time)이거나 계절 기본값(날씨)입니다."

---

## LLM 인터페이스 API (방안 3)

### 인증

```python
# Bearer 토큰 방식 (단순, 발표용)
Authorization: Bearer hotel-dss-demo-key-2026
```

### LLM Tool Definitions (Claude tool_use 형식)

FastAPI의 `/openapi.json`을 Claude tool 정의로 변환:

```json
{
  "name": "submit_hotel_booking",
  "description": "호텔 예약을 시스템에 제출하고 취소 위험도와 Flexi 라우팅 권장 여부를 받는다.",
  "input_schema": {
    "type": "object",
    "properties": {
      "arrival_date":    { "type": "string", "description": "YYYY-MM-DD 형식" },
      "nights":          { "type": "integer" },
      "adults":          { "type": "integer" },
      "country":         { "type": "string", "description": "ISO 3166-1 alpha-3" },
      "channel":         { "type": "string", "enum": ["Direct", "OTA", "Corporate"] },
      "meal":            { "type": "string", "enum": ["BB", "HB", "FB", "SC"] },
      "room_type":       { "type": "string" },
      "special_requests":{ "type": "integer", "minimum": 0, "maximum": 5 }
    },
    "required": ["arrival_date", "nights", "adults", "country", "channel"]
  }
}
```

### 데모 시나리오

```
손님 에이전트 A (비즈니스 여행자):
  → submit_hotel_booking(arrival="2026-08-15", nights=2, channel="Corporate", ...)
  ← riskScore: 0.23, flexiRecommended: false
  → "Standard room assigned"

손님 에이전트 B (마지막 순간 취소 이력 있는 레저 여행자):
  → submit_hotel_booking(arrival="2026-08-01", nights=7, channel="OTA",
                         previous_cancellations=3, ...)
  ← riskScore: 0.84, flexiRecommended: true, discountRate: 0.164
  → "Flexi pool routing recommended (16.4% discount)"

[App 2 대시보드 실시간 업데이트: 에이전트 B 예약이 빨간 뱃지로 표시]
```

---

## 폴더 구조 (추가 파일)

```
07_Hotel_DSS/
├── app_pms/                    # App 1 — Hotel PMS Simulator
│   ├── app.py                  # Streamlit 메인 (port 8502)
│   └── components/
│       ├── booking_form.py
│       └── booking_list.py
│
├── api/                        # FastAPI 백엔드
│   ├── main.py                 # FastAPI 앱 + 라우터
│   ├── pms_adapter.py          # Apaleo → 모델 입력 변환
│   ├── predictor.py            # LightGBM 로드 + 추론
│   ├── shap_service.py         # SHAP waterfall 생성
│   ├── schemas.py              # Pydantic 스키마
│   └── auth.py                 # Bearer 토큰 검증
│
├── dashboard/
│   └── app.py                  # App 2 — DSS 대시보드 (port 8501, 기존)
│
└── demo/
    ├── llm_guest_agents.py     # LLM 에이전트 데모 스크립트
    └── tool_definitions.json   # Claude tool_use 정의
```

---

## 실행 순서 (발표 당일)

```bash
# 1. FastAPI 백엔드
uvicorn api.main:app --port 8000

# 2. App 1 (PMS Simulator)
streamlit run app_pms/app.py --server.port 8502

# 3. App 2 (DSS 대시보드)
streamlit run dashboard/app.py --server.port 8501

# 4. LLM 에이전트 데모 (발표 피날레 슬라이드에서)
python demo/llm_guest_agents.py
```

---

## 관련 문서

| 문서 | 내용 |
|------|------|
| [final_presentation_appdev_plan.md](final_presentation_appdev_plan.md) | 계획서 — 타임라인, 우선순위, 리스크 |
| [design_06_flexi_system.md](design_06_flexi_system.md) | Flexi 할인율 공식 + 임계값 설계 |
| [design_11_wireframe.md](design_11_wireframe.md) | 기존 Streamlit 와이어프레임 (App 2 기준) |
| [design_10_sim_persona_design.md](design_10_sim_persona_design.md) | LLM 에이전트 페르소나 (방안 3 시나리오 참고) |
