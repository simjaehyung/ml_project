# ORCHESTRA — 최종발표 빌드 마스터 문서

> 작성: 심재형 | 2026-05-29  
> 전략: 심재형이 전체 뼈대 구축 → 이고은이 문제 수정·개선  
> LLM 라이브 API 호출 데모: **제거** (시뮬레이션 결과 슬라이드로 대체)

---

## 에이전트 팀 — 분석 페르소나 (검토용)

빌드 에이전트가 코드를 완성하면, 아래 페르소나 팀이 각자의 시각으로 결과물을 검토한다.  
각 페르소나는 다른 페르소나가 놓치는 것을 잡아낸다.

| 페르소나 | 역할 | 검토 대상 | 언제 실행 |
|---------|------|---------|---------|
| **Sentinel (ML 감시자)** | 훈련 파이프라인 vs 추론 파이프라인 일관성 검사 | `api/predictor.py` | A3 완료 후 |
| **Architect (설계 검토자)** | API 계약 vs 실제 구현 일치 검사 | `api/schemas.py` ↔ `src/types/api.ts` ↔ 실제 응답 | Gate C 후 |
| **Presenter (발표 시뮬레이터)** | 데모 시나리오 6/10 실행 가능성 + 실패 포인트 분석 | 전체 시스템 | Gate D 후 |
| **Scope Guard (범위 경찰)** | 스코프 초과·일정 초과 경고 | ORCHESTRA.md + 현재 작업량 | 매 Gate마다 |
| **Generic Detector (범용성 탐지기)** | "AI가 만든 흔한 UI" 징후 목록 작성 + 수정 지점 | 스크린샷 + 소스코드 | Gate C 후 |
| **Trend Scout (트렌드 스카우트)** | Linear·Vercel·Raycast 등 2024-25 레퍼런스 앱과 비교 | 스크린샷 | Gate C 후 |
| **Design Surgeon (디자인 외과의)** | 수술 단위로 교체할 컴포넌트 우선순위 + 코드 패치 | Generic Detector 결과 기반 | Generic 후 |

### Sentinel 프롬프트 (A3 완료 후 실행)
```
[읽어야 할 파일]
- src/preprocessing_pipeline.py
- src/run_all_models.py
- api/predictor.py (방금 생성된 것)

검토 관점: "ML 파이프라인 감시자"
훈련 시 적용된 모든 변환이 추론 시에도 동일하게 적용되는지 검사.

체크리스트:
1. 피처 70개 이름과 순서가 모델 feature_name_과 완전히 일치하는가?
2. country를 Top10+Other로 그룹핑하는 로직이 predictor.py에 있는가?
3. arrival_date_year 피처가 추론 시에도 계산되는가? (훈련 데이터엔 있었음)
4. 날씨 피처 7개가 계절 평균값으로 채워지는가? 어느 달에 어떤 값을 쓰는가?
5. meal "Undefined"→"SC" 변환이 추론에도 있는가?
6. 훈련에서 쓴 OHE 컬럼 중 inference 시 나타나지 않는 컬럼을 0으로 채우는가?

발견한 불일치를 목록으로 출력. 없으면 "PASS"라고만 쓸 것.
```

### Architect 프롬프트 (Gate C 후 실행)
```
[읽어야 할 파일]
- api/schemas.py
- api/types.ts
- hotel-dss-app/src/lib/api.ts
- hotel-dss-app/src/types/api.ts

검토 관점: "API 계약 검토자"
Python 스키마 ↔ TypeScript 타입 ↔ 실제 fetch 호출 사이의 불일치 탐지.

체크리스트:
1. BookingRequest 필드명이 schemas.py ↔ types.ts 사이에 모두 일치하는가?
2. enum 값 (HotelType, ChannelType 등)이 양쪽에서 완전히 동일한가?
3. api.ts의 fetch 함수가 올바른 URL과 method를 사용하는가?
4. 422 에러 응답을 프론트엔드가 올바르게 처리하는가?
5. snake_case vs camelCase 혼용 여부 (우리는 snake_case 통일 원칙)

불일치 목록 출력. 없으면 "PASS".
```

---

### Generic Detector 프롬프트 (Gate C 완료 + 스크린샷 촬영 후 실행)

```
당신은 "AI가 만든 흔한 UI"를 탐지하는 전문가입니다.
수백 개의 Shadcn 기반 Next.js 대시보드를 봤고, 어떤 것이 복붙처럼 보이는지 즉시 압니다.

[분석 대상]
- 스크린샷 (제공됨)
- hotel-dss-app/src/app/dashboard/page.tsx
- hotel-dss-app/src/app/dashboard/reservations/page.tsx
- hotel-dss-app/src/app/dashboard/flexi/page.tsx

[AI 흔한 UI 징후 체크리스트 - 각 항목 해당 여부 판정]

레이아웃:
□ KPI 카드가 단순 흰 박스에 숫자만 있는가? (최악: 그림자도 없음)
□ 테이블이 zebra-stripe 없이 전부 같은 배경인가?
□ 사이드바가 링크 목록 나열 수준인가? (그룹핑, 구분선, 뱃지 없음)
□ 페이지 상단에 제목 텍스트만 덩그러니 있는가? (breadcrumb, action 버튼 없음)
□ 카드들이 전부 동일한 크기와 비중인가? (시각적 계층 없음)

색상:
□ 기본 Shadcn zinc/gray 팔레트에서 벗어나지 않았는가?
□ Risk score가 텍스트 색상이나 배지 색상 외에 다른 시각화가 없는가?
□ 전체가 단색 배경인가? (미세한 그라디언트, 노이즈 텍스처 없음)

데이터 표현:
□ 숫자가 그냥 숫자로만 표시되는가? (단위, 변화율, 스파크라인 없음)
□ 날짜가 ISO 형식(2026-05-29)으로 표시되는가? (상대 시간 없음)
□ Risk score가 소수점 숫자로만 표시되는가? (게이지, 미니바 없음)
□ 빈 상태(empty state)가 그냥 빈 테이블인가? (일러스트, 메시지 없음)

인터랙션:
□ 행 hover 효과가 기본 Shadcn blue인가?
□ 로딩 상태가 없거나 기본 spinner인가? (skeleton UI 없음)
□ 성공/실패 피드백이 없거나 기본 alert인가? (toast 없음)

[출력 형식]
점수: X/16 (체크된 항목 수, 낮을수록 좋음)
심각도: 🔴 12+ / 🟡 7-11 / 🟢 6 이하

상위 5개 문제 (영향도 순):
1. [문제] → [구체적 수정 방향]
2. ...

이 앱을 처음 보는 교수님 반응 예측 (솔직하게):
```

---

### Trend Scout 프롬프트 (Generic Detector와 동시 실행)

```
당신은 2023-2025년 최신 SaaS 대시보드 트렌드에 정통한 UI 전문가입니다.
Vercel, Linear, Raycast, Resend, Neon, Clerk, Liveblocks, Supabase Dashboard 등을
직접 사용해봤고 이들이 왜 "전문적으로" 보이는지 압니다.

[레퍼런스 앱 특징 요약 (당신이 알고 있는 것)]

Linear (선형 디자인):
- 정보 밀도 높음. 행 간격 타이트. 폰트 크기 12-13px가 기본
- 모든 요소에 단축키 힌트 (⌘K, ⌘N 등)
- 미세한 색상 구분 (priority별 dot indicator)
- 테이블에 hover 시 action 버튼 나타남

Vercel Dashboard:
- 배포 상태를 색상 있는 dot + 텍스트로 동시 표현
- 수치 변화를 항상 이전 대비 % 변화로 표시
- 섹션 구분이 선이 아닌 여백으로
- 모노스페이스 폰트로 ID, 해시값 표시

Raycast (macOS 앱이지만 웹 포팅도 있음):
- Context-sensitive 패널 (선택하면 오른쪽에 상세 뜸)
- 검색이 최우선 (cmd+K 스타일)
- 미니멀하지만 rich한 결과 항목

Resend / Neon:
- 코드 스니펫이 앱 안에 자연스럽게 녹아있음
- 차트가 단순하지만 인터랙티브 (hover tooltip)
- 상태 표시가 색상 ring으로

[분석 대상]
- 스크린샷 (제공됨)
- hotel-dss-app/ 의 주요 페이지 소스

[질문]
1. 이 앱이 닮은 레퍼런스 앱은 무엇인가? (있다면)
2. 위 레퍼런스들과 비교했을 때 가장 큰 격차는 무엇인가?
3. 지금 당장 적용 가능한 "트렌디해 보이는" 변경 3가지
   (구현 난이도 낮은 것부터: CSS만 / 컴포넌트 교체 / 구조 변경)
4. "이거 Claude가 만든 것 같다"는 인상을 주는 가장 강한 요소 1가지

[출력]
레퍼런스 닮음: [앱 이름 or "없음"]
격차 요약: 2-3문장
즉시 적용 3가지:
  🟢 CSS만: [구체적 변경]
  🟡 컴포넌트: [구체적 변경]
  🔴 구조: [구체적 변경]
AI 냄새 1위: [구체적 요소]
```

---

### Design Surgeon 프롬프트 (Generic Detector + Trend Scout 결과 수신 후 실행)

```
당신은 Generic Detector와 Trend Scout의 분석 결과를 받아
실제 코드를 수정하는 디자인 외과의입니다.

[역할]
코드를 읽고, 우선순위가 높은 시각적 문제 3개를 선택해서 실제로 고친다.
전체 리디자인이 아님. "수술"처럼 정확하게 해당 부분만 교체.

[수술 우선순위 기준]
1. 발표 시 3초 안에 눈에 보이는 것
2. 구현 시간 30분 이내인 것
3. "흔한 템플릿" 인상을 가장 많이 줄이는 것

[수술 대상 후보 (Generic Detector 결과 기반으로 선택)]

후보 A — Risk Score 시각화 업그레이드
현재: 숫자 + 배지
목표: 미니 horizontal bar (w-full, 색상 그라디언트) + 숫자

후보 B — KPI 카드 depth 추가  
현재: 단순 흰 박스
목표: 상단 컬러 액센트 라인 + 이전 대비 변화율 표시 (mock: +3 today)

후보 C — 테이블 행 시각 계층
현재: 모든 행 동일한 배경
목표: risk >= 0.7 행은 좌측 3px 빨간 border-l + 미세한 빨간 tint 배경

후보 D — 날짜 표시 개선
현재: 2026-07-15 (ISO)
목표: "Jul 15" + 상대 시간 ("in 47 days") 서브텍스트

후보 E — 사이드바 활성 상태
현재: 기본 Shadcn 하이라이트
목표: 좌측 2px 컬러 라인 + 배경 미세 tint + 볼드

[작업]
1. Generic Detector와 Trend Scout 결과를 읽고
2. 위 후보 중 3개 선택 (또는 발견한 더 나은 수술 포인트)
3. 실제 코드 수정 (Edit 툴 사용)
4. 수정 후 변경 요약

[제약]
- Tailwind 클래스만 사용 (새 CSS 파일 추가 없음)
- shadcn 컴포넌트 교체 없음 (내부 스타일링만)
- 기능 변경 없음 (시각만)
```

---

### Presenter 프롬프트 (Gate D 후 실행)
```
[읽어야 할 파일]
- ORCHESTRA.md (스코프 섹션, 발표 시나리오)
- api/main.py
- hotel-dss-app/src/app/dashboard/reservations/new/page.tsx

검토 관점: "발표 당일 데모 시뮬레이터"
6/10 발표장에서 라이브 데모할 때 실패할 수 있는 지점을 미리 찾는다.

시나리오:
1. 심재형이 /dashboard/reservations/new에서 예약 입력
2. City Hotel, 도착 180일 후, TA/TO 채널, adults=2, country=GBR
3. 제출 → Flexi Rate 판정 나와야 함
4. /dashboard → KPI 업데이트 확인

질문:
- 이 시나리오가 실제로 동작하는가? 막히는 지점이 있는가?
- FastAPI가 다운되면 어떤 에러가 보이는가? 사용자가 이해할 수 있는가?
- 발표장 WiFi가 느리면 어떤 증상이 나오는가?
- 백업 계획 (녹화 영상)이 필요한 시점은 언제인가?

위험 등급으로 목록 출력: 🔴 치명 / 🟡 주의 / 🟢 양호
```

---

## 스코프 (최종 확정)

**만드는 것:**
1. `api/main.py` — 실제 LightGBM 연결 FastAPI
2. `api/predictor.py` — 모델 로딩 + 피처 엔지니어링
3. `api/pms_adapter.py` — Apaleo → DSS 컬럼 변환
4. `hotel-dss-app/` — Next.js 프론트엔드 (App 1 PMS + App 2 Dashboard)

**만들지 않는 것:**
- `demo/llm_demo.py` (라이브 LLM API 호출 데모) — **제거**
- LLM 에이전트가 실시간으로 API 때리는 시연 — **제거**

**발표 데모 시나리오 (수정):**
```
슬라이드 6: App 1 PMS에서 스태프가 예약 입력
              → FastAPI DSS → Flexi 판정
              → App 2 대시보드 실시간 반영
슬라이드 7: 시뮬레이션 결과 (사전 실행 완료 데이터 표시)
```

---

## 현재 상태

| 레이어 | 파일 | 상태 |
|--------|------|------|
| API 계약 | `api/schemas.py`, `api/types.ts` | ✅ 완성 |
| FastAPI 목업 | `api/main_mock.py` | ✅ 완성 (이고은 시작용) |
| PMS 목업 | `app_pms/pms_mock.py`, `pms_schemas.py` | ✅ 완성 |
| FastAPI 실제 | `api/main.py` | ❌ |
| 모델 로더 | `api/predictor.py` | ❌ |
| PMS 어댑터 | `api/pms_adapter.py` | ❌ |
| Next.js 프로젝트 | `hotel-dss-app/` | ❌ |

---

## 빌드 순서 (의존성 그래프)

```
[A] Backend (심재형 혼자)
  A1 predictor.py  →  A2 pms_adapter.py  →  A3 main.py
                                                  │
                                           Gate A: 서버 실행 확인
                                                  │
[B] Frontend 셋업 (심재형)                         │
  B1 Next.js 프로젝트 생성                         │
  B2 shadcn + 공통 레이아웃                        │
  B3 lib/api.ts (API 클라이언트)                   │
                    │                              │
             Gate B: npm run dev 확인              │
                    │                              │
[C] App 2 Dashboard (심재형 뼈대 → 이고은 수정)   │
  C1 KPI 카드 4개 + polling ◄──────────────────── ┘
  C2 예약 목록 DataTable
  C3 Flexi 슬라이더 패널
  C4 사이드바 네비게이션
                    │
             Gate C: 목업 데이터 정상 표시
                    │
[D] App 1 PMS (심재형 뼈대 → 이고은 수정)
  D1 신규 예약 폼 (Form + Zod)
  D2 예약 목록 (Flexi 배지 포함)
  D3 예약 상세 + 위험도 패널
                    │
             Gate D: 예약 제출 → App 2에 반영 확인
                    │
[E] 통합 + 이고은 인계
  E1 전체 플로우 테스트
  E2 발견된 버그 → 이고은에게 문서화해서 전달
```

---

## 에이전트 팀

각 Phase마다 Claude Code에게 줄 최적화된 프롬프트.  
**한 번에 하나씩.** 이전 Gate 통과 확인 후 다음 에이전트 실행.

---

### Agent A1 — predictor.py (모델 로더)

```
[읽어야 할 파일]
- api/schemas.py (BookingRequest 구조 확인)
- results/model_final.pkl (경로 확인용)

[작업]
api/predictor.py 파일을 만들어줘.

LightGBM 모델 로더 + 예측 함수.

요구사항:
1. 모듈 레벨에서 `results/model_final.pkl` 로드 (joblib)
2. `predict(booking: BookingRequest) -> tuple[float, list[RiskFactor]]` 함수
   - BookingRequest에서 모델 입력 피처 계산:
     - lead_time = (arrival_date - 오늘).days
     - stays_in_weekend_nights = arrival_date ~ departure_date 중 토/일 수
     - stays_in_week_nights = 전체 박수 - stays_in_weekend_nights
     - arrival_date_week_number = arrival_date.isocalendar().week
     - arrival_date_day_of_month = arrival_date.day
     - arrival_date_month = arrival_date.month
     - 날씨 피처: hotel + arrival_date_month 기반 계절 평균값 (하드코딩 딕셔너리)
   - SHAP TreeExplainer로 top 3 피처 추출 → list[RiskFactor]
   - risk_score = predict_proba[:, 1][0]
3. 피처 컬럼 순서는 모델 훈련 시와 정확히 일치해야 함
   (훈련 파이프라인 확인 필요: src/preprocessing_pipeline.py 또는 src/train_*.py)

[출력]
api/predictor.py (완성 파일)

[검증]
python -c "from api.predictor import predict; print('OK')" 실행 시 에러 없음
```

---

### Agent A2 — pms_adapter.py (Apaleo 변환)

```
[읽어야 할 파일]
- api/schemas.py (BookingRequest 필드 확인)
- docs/design_16_api_contract.md (pms_adapter 매핑 테이블 섹션)
- app_pms/pms_schemas.py (GuestBookingRequest 구조 참고)

[작업]
api/pms_adapter.py 파일을 만들어줘.

Apaleo PMS JSON → BookingRequest 변환 함수.

요구사항:
1. `adapt_apaleo(raw: dict) -> BookingRequest` 함수
   - docs/design_16_api_contract.md의 매핑 테이블 기준으로 변환
   - lead_time 계산: raw["arrival"] - raw["bookingDate"]
   - mealPlan 문자열 → BB/HB/FB/SC 코드 변환
   - channelCode → distribution_channel 변환 (OTA → "TA/TO" 등)
2. `adapt_form(form_data: dict) -> BookingRequest` 함수
   - App 1 스태프 폼 직접 입력 데이터 변환
   - 필드명 차이 처리 (camelCase → snake_case)
3. 변환 실패 시 명확한 ValueError 메시지

[출력]
api/pms_adapter.py (완성 파일)
```

---

### Agent A3 — main.py (실제 FastAPI)

```
[읽어야 할 파일]
- api/main_mock.py (구조 그대로 복사, 예측 부분만 교체)
- api/schemas.py (모든 스키마)
- api/predictor.py (방금 만든 것)

[작업]
api/main.py 파일을 만들어줘.

api/main_mock.py를 기반으로, 목업 예측 로직을 실제 predictor.py 호출로 교체.

바꾸는 것:
1. create_booking() 함수:
   - 기존 mock risk 계산 코드 → `predict(booking)` 호출로 교체
   - `risk, risk_factors = predict(booking)` 받아서 사용
2. import: LLMBookingRequest, LLMDashboardState 없음 (이미 제거됨)

바꾸지 않는 것:
- 모든 엔드포인트 URL
- 모든 응답 스키마
- CORS 설정
- _seed_bookings() (목업 초기 데이터 유지)
- dashboard_summary(), list_bookings(), flexi_preview() 전체

[검증]
uvicorn api.main:app --port 8000 --reload 실행 후
curl http://localhost:8000/docs 응답 확인
```

---

### Agent B — Next.js 셋업

```
[읽어야 할 파일]
- api/types.ts (TypeScript 타입 전체)
- docs/design_16_api_contract.md (API 엔드포인트 목록)

[작업]
Next.js 14 + shadcn/ui 프로젝트 셋업 + API 클라이언트 생성.

1. 프로젝트 생성 (프로젝트 루트에서 실행):
   npx create-next-app@latest hotel-dss-app --typescript --tailwind --app --no-git

2. 의존성 설치:
   cd hotel-dss-app
   npx shadcn@latest init (style: default, base color: zinc, CSS variables: yes)
   npx shadcn@latest add table button badge card progress slider

3. api/types.ts → hotel-dss-app/src/types/api.ts 로 복사

4. hotel-dss-app/src/lib/api.ts 생성:
   - BASE_URL = "http://localhost:8000/api/v1"
   - createBooking(data: BookingRequest): Promise<BookingResponse>
   - listBookings(params?: {status?: BookingStatus, min_risk?: number}): Promise<BookingListResponse>
   - getBooking(id: string): Promise<BookingListItem>
   - getDashboardSummary(): Promise<DashboardSummary>
   - getFlexiPreview(threshold: number): Promise<FlexiPreview>
   - 모든 함수: fetch + error handling (422 → throw Error with field detail)

5. hotel-dss-app/src/app/dashboard/layout.tsx 생성:
   - 왼쪽 사이드바: "Hotel DSS" 로고 + 메뉴 4개
     - Overview → /dashboard
     - Reservations → /dashboard/reservations
     - Flexi Policy → /dashboard/flexi
     - New Booking → /dashboard/reservations/new
   - 하단 뱃지: "LightGBM PR-AUC 0.8189"
   - 배경: #1C1E26 (사이드바), #0F1117 (메인)

[검증]
npm run dev → localhost:3000 접속 확인
```

---

### Agent C — App 2 Dashboard

```
[읽어야 할 파일]
- hotel-dss-app/src/types/api.ts
- hotel-dss-app/src/lib/api.ts
- docs/design_16_api_contract.md (연결고리 2, 3 섹션)

[작업]
App 2 DSS 대시보드 페이지 3개 구현.

**C1. hotel-dss-app/src/app/dashboard/page.tsx (Overview)**
- getDashboardSummary() → 5초마다 polling (useEffect + setInterval)
- KPI 카드 4개 (shadcn Card):
  - 전체 예약 수
  - 고위험 예약 수 (빨간 강조, risk >= current_threshold)
  - Flexi 라우팅 완료 수 (노란 강조)
  - 평균 위험도 (Progress bar)
- 그 아래: 최근 예약 목록 (최대 10건, risk_score 내림차순)
  - 컬럼: Booking ID / Hotel / Country / Arrival / Risk Score (배지) / Status

**C2. hotel-dss-app/src/app/dashboard/reservations/page.tsx**
- listBookings() 호출
- shadcn DataTable (전체 컬럼)
- Risk Score 배지: 0.7+ 빨강, 0.4~0.7 노랑, 미만 초록
- pricing_type "Flexi Rate"이면 "Flexi" 노란 배지 추가
- 검색: booking_id, country 필터

**C3. hotel-dss-app/src/app/dashboard/flexi/page.tsx**
- Threshold Slider (shadcn Slider, 0.50~0.85, 기본 0.65)
- 슬라이더 변경 시 getFlexiPreview(threshold) 호출 (debounce 300ms)
- 표시: estimated_pool_size / estimated_walk_rate / walk_rate_improvement
- 하단: Flexi 라우팅된 예약 목록 (status === "flexi-routed")

[색상 시스템]
--risk-low: #2ECC71
--risk-medium: #F39C12
--risk-high: #E74C3C
배경: #0F1117, 카드: #1C1E26

[검증]
localhost:3000/dashboard 접속 → KPI 카드 데이터 표시 확인
(FastAPI 목업 서버 먼저 실행 필요: uvicorn api.main_mock:app --port 8000)
```

---

### Agent D — App 1 PMS

```
[읽어야 할 파일]
- hotel-dss-app/src/types/api.ts
- hotel-dss-app/src/lib/api.ts
- api/schemas.py (BookingRequest 필드 목록)

[작업]
App 1 Hotel PMS 페이지 3개 구현.

**D1. hotel-dss-app/src/app/dashboard/reservations/new/page.tsx**
신규 예약 입력 폼:
- 폼 필드 (shadcn Form + Zod 유효성):
  - Hotel (Select: City Hotel / Resort Hotel)
  - Arrival Date (shadcn DatePicker)
  - Departure Date (DatePicker, arrival보다 나중 강제)
  - Adults (1~9 숫자 input)
  - Children (0~5 숫자 input)
  - Distribution Channel (Select: Direct / Corporate / TA/TO / GDS)
  - Market Segment (Select: Direct / Corporate / Online TA / Offline TA/TO)
  - Room Type (Select: A/B/C/D/E/F/G — 코드로 표시)
  - Meal Plan (Select: BB / HB / FB / SC)
  - Country (Select, ISO alpha-3, 자주 쓰는 20개 + 기타)
  - Customer Type (Select: Transient / Contract / Group)
  - ADR (숫자 input, EUR)
  - Special Requests (Slider 0~5)
- 제출 시 createBooking() 호출
- 응답 모달:
  - risk_score 0.7+ : "⚠️ 고위험 예약 — Flexi 라우팅 권장 (할인율 X.X%)" 빨간 배경
  - flexi_recommended : "Flexi Rate 배정" 노란 배경 + 할인율
  - 그 외: "✅ Standard 배정 완료" 초록 배경
  - top_risk_factors 3개 카드로 표시

**D2. hotel-dss-app/src/app/dashboard/reservations/page.tsx**
(App 2의 reservations 페이지와 동일한 컴포넌트 재사용.
 pricing_type Flexi 배지만 추가로 표시)

**D3. hotel-dss-app/src/app/dashboard/reservations/[id]/page.tsx**
- getBooking(id) 호출
- 좌측 2/3: 예약 상세 정보 카드
- 우측 1/3: 위험도 패널
  - Progress bar (risk_score)
  - top_risk_factors 3개 (feature / label / shap_value)
  - flexi_recommended: "Flexi 라우팅 권장" 배너
  - discount_rate 있으면 할인율 표시

[검증]
/dashboard/reservations/new 에서 폼 제출 → 모달 확인
→ /dashboard 에서 새 예약이 KPI에 반영되는지 확인
```

---

### Agent E — 통합 검증 + 이고은 인계 문서

```
[작업]
전체 시스템 통합 테스트 후 이고은에게 전달할 버그/개선 목록 작성.

테스트 시나리오:
1. uvicorn api.main:app --port 8000 실행
2. cd hotel-dss-app && npm run dev 실행
3. localhost:3000/dashboard → KPI 수치 확인
4. /dashboard/reservations/new → 고위험 예약 제출 테스트
   (City Hotel, arrival 180일 후, TA/TO 채널 → 높은 위험도 예상)
5. /dashboard → 새 예약이 KPI에 반영됐는지 확인
6. /dashboard/flexi → 슬라이더 조작 → pool_size 변화 확인

[출력]
HANDOFF.md 파일 생성:
- 이고은에게: "이 파일만 읽으면 됩니다"
- 발견된 버그 목록 (재현 방법 포함)
- UI 개선 요청 목록 (우선순위별)
- 환경 설정 방법
```

---

## Gate 조건 요약

| Gate | 조건 | 다음 단계 |
|------|------|---------|
| A | `uvicorn api.main:app --port 8000` 정상 실행 | B 시작 |
| B | `npm run dev` → localhost:3000 접속 | C 시작 |
| C | 대시보드 KPI 카드 데이터 표시 | D 시작 |
| D | 예약 폼 제출 → 대시보드 반영 | E 시작 |
| E | 전체 플로우 동작 + 이고은 인계 문서 완성 | 발표 준비 |

---

## 컷 기준

| 날짜 | 조건 | 조치 |
|------|------|------|
| 6/5 | Gate D 미통과 | App 1 폼 제거, App 2만 시연 |
| 6/7 | 이고은 수정 미완료 | 현재 상태 그대로 발표 |
| 6/8 | 어떤 이유든 불안정 | 사전 녹화 영상으로 대체 |
| **6/5 이후** | **코딩 완전 중단** | **발표 자료 전용** |
