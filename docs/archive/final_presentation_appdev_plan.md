# 최종발표 앱 개발 계획

> 작성: 심재형 | 2026-05-28  
> 이 문서는 `project_roadmap.md`의 Phase 2 일정 위에 **앱 개발 방향 전환**을 추가 기록한다.

---

## 배경: 왜 방향을 바꾸는가

중간발표(2026-05-27) 이후 관찰:

- 다른 팀들도 Claude 에이전트로 앱을 만들어 Streamlit 완성도가 수렴되고 있음
- 우리 시스템의 핵심 주장("연동이 쉽다", "AI 시스템도 이 DSS를 쓸 수 있다")을 시연 없이 말로만 하면 설득력이 약함
- 기존 Streamlit 단일 앱으로는 이 두 주장을 데모로 보여줄 수 없음

**결정 (2026-05-28):**

```
기존:  Streamlit 단일 앱 (탭 1 + 탭 2)
변경:  App 1 (Hotel PMS Simulator) + App 2 (DSS, UI 격상) + LLM API 레이어
```

---

## 세 가지 구현 방안

### 방안 1 — App 2: DSS UI 격상

**목표:** 현재 Streamlit 앱을 "데모" 수준에서 상용 레벨로 올림

**경로 A — Streamlit 극한 커스텀 (2일, 권장)**
- `st.markdown` CSS 주입으로 버튼·카드·사이드바 전면 교체
- `streamlit-option-menu`로 네비게이션 바 교체
- Matplotlib → Plotly 전환 (인터랙티브 + 시각적 품질)
- 색상 팔레트: 저위험(`#2ECC71`) → 고위험(`#E74C3C`) 그라디언트

**경로 B — FastAPI + Next.js 분리 (5~7일, 고위험)**
- 백엔드: FastAPI (`/predict`, `/shap`, `/bookings` 엔드포인트)
- 프론트엔드: Next.js 14 + shadcn/ui + Tailwind CSS
- ML 모델은 백엔드에 joblib 로드
- 시간 없으면 cut — 상세는 `design_15_final_app_architecture.md` 참고

**전문 바이브코딩이 다른 이유:** 컴포넌트 단위로 명세를 먼저 쓰고 AI에게 하나씩 주문. "대시보드 만들어줘"가 아니라 "shadcn DataTable, 컬럼 6개, 행 클릭 시 오른쪽 패널 SHAP waterfall 표시"처럼 스펙이 있어야 차이가 난다.

---

### 방안 2 — App 1: Hotel PMS Simulator ★ (핵심)

**목표:** 실제 호텔 PMS와 같은 인터페이스를 만들고, 여기서 DSS로 데이터가 자동으로 흘러가는 연동 시연

**참고 실제 PMS:**

| PMS | 특징 | 활용 방안 |
|-----|------|----------|
| **Apaleo** | 클라우드 네이티브, REST API, 개발자 샌드박스 있음 | API 스키마 모방 1순위 |
| **Mews** | 스타트업 호텔 다수, 커넥터 마켓플레이스 | 스키마 구조 참고 |
| Cloudbeds | 소규모 호텔, 단순한 API | 필드명 참고 |

**App 1이 뱉는 데이터 형식 (Apaleo 스키마 모방):**
```json
{
  "reservationId": "RES-2847",
  "channelCode": "OTA",
  "guestProfile": {
    "country": "GBR",
    "previousStays": 2,
    "previousCancellations": 1
  },
  "stay": {
    "arrivalDate": "2026-07-15",
    "departureDate": "2026-07-18",
    "adults": 2
  },
  "roomType": "DBL",
  "rateCode": "BAR",
  "totalGrossAmount": { "amount": 420.00, "currency": "EUR" },
  "mealPlan": "BB",
  "specialRequests": 1,
  "leadTimeDays": 92,
  "bookingDate": "2026-04-14"
}
```

**DSS가 받아서 처리하는 것:**
1. Apaleo 스키마 → 우리 모델 입력 형식 자동 변환 (`pms_adapter.py`)
2. LightGBM 예측 → risk_score
3. App 2 대시보드에 실시간 반영

**발표 포인트:** 매핑 레이어를 화면에 보여주면서 "연동은 컬럼 매핑 문제입니다"를 데이터로 증명

---

### 방안 3 — LLM 인터페이스 API (방안 1·2 완성 후)

**목표:** 외부 LLM 에이전트가 우리 DSS를 직접 호출할 수 있는 API 제공 — "AI-native DSS" 포지션

**활용:**
- 손님 역할 LLM이 App 1(PMS)에 예약 → DSS API로 위험도 실시간 조회
- 발표에서 라이브 데모: AI 에이전트들이 예약하고, DSS가 고위험 예약을 Flexi로 라우팅

**상세 스펙:** `design_15_final_app_architecture.md` 참고

---

## 2주 타임라인

> 기존 `project_roadmap.md` Phase 2 일정을 유지하면서 앱 개발을 병행.  
> **시뮬레이션 실행(5/30 야간)이 최우선. 앱 개발은 그 전후 슬롯에 배치.**

### Week 5 (5/28~6/2) — 시뮬레이션 + App 1 구축

| 날짜 | 작업 | 담당 | 비고 |
|------|------|------|------|
| 5/28(수) | 학교 서버 셋업 + Qwen 다운로드 | 심재형 | 기존 계획 유지 |
| 5/28~29 | **App 1 PMS Simulator 설계 + Apaleo 스키마 분석** | 심재형 | 신규 |
| 5/29(목) 저녁 | 시뮬레이션 dry-run 50건 검증 | 심재형 | 기존 계획 유지 |
| 5/29~30 | **App 1 예약 입력 폼 + 목록 UI 구현** | 이고은 | 신규 |
| 5/30(금) 야간 | ★ 전수 시뮬레이션 런 (~13,355건) | 심재형 | 기존 계획 유지 |
| 5/30~31 | **pms_adapter.py + DSS 연동 테스트** | 심재형 | 신규 |
| 5/31(토) | 시뮬레이션 결과 분석 | 심재형 | 기존 계획 유지 |
| 5/31~6/1 | **App 2 UI CSS 격상 (경로 A)** | 이고은 | 신규 |
| 6/1~2 | Phase 2 실험 (날씨 윈도우·previous_cancellations) | 팀 | 기존 계획 유지 |

### Week 6 (6/3~6/9) — LLM API + 발표 준비

| 날짜 | 작업 | 담당 | 비고 |
|------|------|------|------|
| 6/3~4 | **FastAPI LLM API 구축** (방안 3) | 심재형 | 신규 |
| 6/3~4 | 음식 낭비 탭 + BQS 앱 통합 | 이고은 | 기존 계획 유지 |
| 6/4~5 | **두 앱 통합 테스트 + 라이브 데모 리허설** | 팀 | 신규 |
| 6/5~8 | 최종 발표 자료 완성 | 팀 | 기존 계획 유지 |
| 6/9(월) | 최종 리허설 | 팀 | |

---

## 우선순위 및 컷 기준

| 우선순위 | 방안 | 컷 조건 |
|---------|------|---------|
| 1 | **시뮬레이션 실행** (기존 계획) | 절대 컷 안 함 |
| 2 | **App 1 PMS Simulator** | 발표 3일 전까지 미완성 시 컷 |
| 3 | **App 2 UI 격상 (경로 A, CSS)** | 1~2일 내 안 되면 미진행 |
| 4 | **LLM API (방안 3)** | App 1+2 완성 후에만 착수 |
| 5 | App 2 React 이전 (경로 B) | 이번 발표에서는 컷 |

---

## 리스크

| 리스크 | 대응 |
|--------|------|
| 라이브 데모 중 API 지연·장애 | 시연 영상 미리 녹화해서 백업 |
| App 1+2 연동 버그 | 5/31 이전 컷오프 — 미완성이면 시연 영상만 사용 |
| 시뮬레이션 실행 실패 | dry-run 검증 단계에서 파이프라인 확인 |
| 발표 자료 준비 시간 부족 | 6/5 이후는 슬라이드 전용. 코딩 완전 중단 기준 |

---

## 발표에서 이 앱들이 하는 역할

```
발표 6번 슬라이드 (Flexi 시스템):
  App 1에서 신규 예약 입력 → App 2가 위험도 + Flexi 권장 실시간 표시

발표 7번 슬라이드 (LLM 시뮬레이션 피날레):
  LLM 에이전트들이 API로 예약 → DSS가 위험 분류 → 대시보드 실시간 업데이트
```

**핵심 메시지:** "우리는 두뇌(위험 예측 엔진)를 만들었습니다. 어떤 시스템이든 API 하나로 연결할 수 있습니다."

---

## 관련 문서

| 문서 | 내용 |
|------|------|
| [design_15_final_app_architecture.md](design_15_final_app_architecture.md) | 기술 스펙 — API 엔드포인트, 컴포넌트, 데이터 플로우 |
| [project_roadmap.md](project_roadmap.md) | Phase 2 전체 일정 (이 문서가 앱 개발 부분을 보완) |
| [design_05_system_architecture.md](design_05_system_architecture.md) | 기존 ML 파이프라인 아키텍처 |
| [design_11_wireframe.md](design_11_wireframe.md) | 기존 Streamlit 와이어프레임 |
