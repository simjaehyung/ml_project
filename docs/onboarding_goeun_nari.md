# 팀원 온보딩 가이드 — 중간발표 이후 작업 현황

> 작성: 심재형 | 기준일: 2026-05-30  
> 대상: 이고은, 김나리  
> 이 문서는 중간발표(5/27) 이후 재형이 진행한 작업을 팀원에게 설명하기 위해 작성됨.  
> LLM 에이전트가 읽어도 이해하기 좋도록 구체적으로 작성함.

---

## 목차

1. [시스템 전체 그림](#1-시스템-전체-그림)
2. [이고은 — DSS + PMS 2단 검증 가이드](#2-이고은--dss--pms-2단-검증-가이드)
3. [김나리 — 프로젝트 논리 강화 + 법률 조사 가이드](#3-김나리--프로젝트-논리-강화--법률-조사-가이드)
4. [금요일 대면회의 준비 체크리스트](#4-금요일-대면회의-준비-체크리스트)

---

## 1. 시스템 전체 그림

중간발표 이후 추가된 레이어가 2개다. 기존 DSS는 그대로고 위에 PMS + LLM 에이전트 층이 올라갔다.

```
[LLM 에이전트 5명] ← llm_sim/ 폴더
  Claude Haiku API 호출 → create_hotel_booking 툴 사용
         ↓
[PMS 서버 — port 3001] ← app_pms/ 폴더
  손님 언어 → DSS 언어 번역
  에이전트는 위험점수를 절대 모름
         ↓
[DSS 서버 — port 8001] ← api/ 폴더 (기존)
  LightGBM 예측 + SHAP
         ↓
[DSS 대시보드 — port 3000] ← hotel-dss-app/ 폴더
  /dashboard — 기존 매니저 뷰
  /pms       — 신규 PMS 관리자 뷰 (이번에 추가)
```

### 신규 추가된 파일 전체 목록

| 파일 | 역할 |
|------|------|
| `app_pms/pms_schemas.py` | PMS 전용 Pydantic 스키마 (손님 ↔ PMS ↔ DSS) |
| `app_pms/pms_mock.py` | PMS FastAPI 서버 (port 3001) |
| `llm_sim/__init__.py` | 패키지 init |
| `llm_sim/personas.py` | 5개 페르소나 정의 + 시스템 프롬프트 |
| `llm_sim/agents.py` | Claude Haiku 기반 에이전트 실행 로직 |
| `llm_sim/run_simulation.py` | CLI 실행기 |
| `hotel-dss-app/types/pms.ts` | TypeScript 타입 (Python 스키마와 1:1) |
| `hotel-dss-app/lib/pms-api.ts` | PMS API 클라이언트 |
| `hotel-dss-app/app/pms/layout.tsx` | PMS 레이아웃 (슬레이트 테마) |
| `hotel-dss-app/app/pms/page.tsx` | PMS 대시보드 |
| `hotel-dss-app/app/pms/reservations/page.tsx` | 예약 목록 + 상세 패널 |

---

## 2. 이고은 — DSS + PMS 2단 검증 가이드

### 2-1. 네가 맡은 일

> **PMS + DSS 전체를 실제로 실행하면서 오류를 찾고, 발전 가능한 부분을 제안한다.**

구체적으로:
- 서버 3개를 올리고 LLM 시뮬레이션을 돌려서 데이터가 PMS → DSS → 대시보드까지 제대로 흐르는지 검증
- PMS UI에서 표시 오류, 레이아웃 깨짐, 데이터 불일치를 찾아서 수정
- "이런 기능이 있으면 발표에서 더 설득력 있겠다"는 제안 목록 만들기

---

### 2-2. 코드 읽는 순서 (이 순서대로 읽으면 빠름)

**Step 1 — 스키마부터 읽어라**

`app_pms/pms_schemas.py` — 모든 데이터 형식이 여기서 정의됨.

주요 클래스:
- `GuestBookingRequest` — LLM 에이전트가 PMS에 보내는 예약 요청. 손님 언어.
- `GuestBookingConfirmation` — PMS가 에이전트에게 돌려주는 확인서.
- `PMSReservationRecord` — PMS 내부 저장용. 에이전트 메타 + DSS 연결 정보 포함.
- `PMSActivityEvent` — 실시간 활동 로그 이벤트. action 값: `thinking`, `booking`, `confirmed`, `error`
- `PMSStats` — `/admin/stats` 응답. 통계 요약.

**Step 2 — PMS 서버 로직 읽기**

`app_pms/pms_mock.py`

중요 함수들:
- `_translate_to_dss(req)` — GuestBookingRequest를 DSS의 BookingRequest로 변환하는 번역 레이어. 국적→country, 식사플랜→BB/HB/FB/SC 코드 등.
- `guest_book()` — POST /api/bookings 핸들러. 에이전트 인증 → DSS 호출 → 로그 기록 → 응답 반환.
- `_log(event)` — 활동 이벤트를 deque에 appendleft. 최신 것이 앞에 옴.
- `admin_reservations()` — GET /admin/reservations. UI 폴링용.
- `admin_activity()` — GET /admin/activity?limit=N. UI 폴링용.
- `admin_stats()` — GET /admin/stats. KPI 카드용.

중요 상수:
```python
DSS_BASE_URL = "http://localhost:8001"  # DSS 서버 주소
PMS_API_KEY = "pms-guest-key-2026"     # 에이전트 인증 키
```

**Step 3 — 페르소나 읽기**

`llm_sim/personas.py`

5개 페르소나:
| ID | 이름 | 국적 | 취소 경향 | 특징 |
|----|------|------|---------|------|
| guest-ana | Ana Rodrigues | PRT | HIGH | 비즈니스, 단기 리드타임 |
| guest-james | James Mitchell | GBR | MEDIUM | 레저, 가격 민감 |
| guest-marie | Marie Dubois | FRA | LOW | 가족, 특별요청 많음 |
| guest-thomas | Thomas Müller | DEU | MEDIUM | 컨퍼런스, 일정 불확실 |
| guest-paulo | Paulo Santos | BRA | HIGH | 배낭, 취소 이력 |

각 페르소나는 `booking_defaults` 딕셔너리를 가지고 있어서 날짜 범위, 숙박 일수 등을 자동 생성함.

**Step 4 — 에이전트 실행 로직**

`llm_sim/agents.py`

흐름:
1. Claude API 호출 (모델: `claude-haiku-4-5-20251001`)
2. 모델이 `create_hotel_booking` 툴을 호출
3. `_call_pms_api()` → POST http://localhost:3001/api/bookings
4. 응답을 툴 결과로 다시 모델에 전달
5. 모델이 예약 결과에 대한 "반응"을 출력

**Step 5 — 프론트엔드 UI**

`hotel-dss-app/app/pms/page.tsx` — PMS 대시보드
- 좌측 2/5: 5개 페르소나 카드 + 각자의 최근 예약 현황
- 우측 3/5: 실시간 활동 피드 (2초 폴링, 터미널 스타일)
- 하단: 최근 예약 테이블 (DSS 위험점수 + 링크 포함)

`hotel-dss-app/app/pms/reservations/page.tsx` — 예약 목록
- All / Flexi Rate / Standard Rate 탭 필터
- 행 클릭 시 우측에 상세 패널
- DSS 위험도 클릭하면 /dashboard/reservations/{id}로 이동

---

### 2-3. 실행 방법 (3개 터미널)

```powershell
# 터미널 1 — DSS 서버
uvicorn api.main:app --port 8001 --reload

# 터미널 2 — PMS 서버
uvicorn app_pms.pms_mock:app --port 3001 --reload

# 터미널 3 — Next.js
cd hotel-dss-app
npm run dev   # port 3000
```

LLM 시뮬레이션 실행 (별도 터미널):
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
python -m llm_sim.run_simulation --agents ana james marie thomas paulo
```

특정 에이전트만:
```powershell
python -m llm_sim.run_simulation --agents ana --rounds 2 --delay 1.0
```

---

### 2-4. 검증 체크리스트

실행 후 이 항목들을 순서대로 확인해라:

#### 서버 연결 확인
- [ ] http://localhost:8001/docs — DSS Swagger UI 열림
- [ ] http://localhost:3001/docs — PMS Swagger UI 열림
- [ ] http://localhost:3001/admin/stats — `{"total_reservations": 0, ...}` 반환

#### LLM 시뮬레이션 실행 확인
- [ ] 터미널에서 에이전트 실행 시 `✓ 예약 확인됨: GRAND-XXXX` 출력
- [ ] `confirmation_number`, `pricing_type`, `total_amount` 표시됨

#### PMS UI 확인
- [ ] http://localhost:3000/pms — PMS 대시보드 접속
- [ ] 페르소나 카드 5개 표시
- [ ] 활동 피드에 예약 로그 실시간 반영
- [ ] 하단 예약 테이블에 방금 만든 예약 표시
- [ ] DSS 위험점수 표시 (빨강/노랑/초록 색상 구분)
- [ ] DSS 링크 클릭 시 /dashboard/reservations/{id} 이동

#### 데이터 일관성 확인
- [ ] PMS 예약 테이블의 위험점수 = DSS 상세 페이지의 취소 확률
- [ ] Flexi 예약은 황색 ⚡ Flexi 배지, Standard는 초록 배지
- [ ] 할인율이 Flexi 배지에 표시됨 (예: ⚡ Flexi -8.5%)

---

### 2-5. 발전 방향 제안 (참고)

재형이 생각해둔 것들이지만 네가 코드 보면서 다른 아이디어가 생기면 추가해도 됨:

| 아이디어 | 난이도 | 발표 효과 |
|---------|--------|---------|
| 에이전트별 예약 히스토리 그래프 | 중 | 중 |
| 위험점수 분포 히스토그램 (PMS 대시보드) | 하 | 중 |
| Flexi vs Standard 비율 도넛 차트 | 하 | 중 |
| 에이전트가 Flexi를 "거절"하는 시나리오 추가 | 상 | 상 |
| 신규 예약 입력 폼 (/pms/new) | 중 | 상 |

---

## 3. 김나리 — 프로젝트 논리 강화 + 법률 조사 가이드

### 3-1. 네가 맡은 일

> **"왜 우리가 이 시스템을 만들었는가"에 대한 대답이 중간발표부터 최종발표까지 일관되게 이어지도록 논리를 다진다. 여기에 한국 오버부킹 법률 사건을 추가해서 현실 근거를 보강한다.**

---

### 3-2. 중간발표에서 교수님이 지적한 것

`docs/lessons_from_mid_presentation.md` 참고. 핵심만 요약:

> **"오버부킹 법적 리스크를 명시하지 않으면 현장에서 거부된다. 악의적 사용자 케이스, 한국 숙박업 법령 근거까지 포함해야 최종 발표가 완결된다."**

교수님 마무리 코멘트:
> **"발표 시작은 항상 이 서비스는 누구에게 어떤 도움을 주기 위해 만들었는가."**

---

### 3-3. 중간발표 → 최종발표 스토리 흐름 분석

**중간발표에서 우리가 한 것:**
- 취소 예측 모델 + DSS 개념 + Flexi 아이디어 소개
- 교수님 피드백: "좋은데, 실제로 쓸 수 있나? 법적으로 문제 없나?"

**최종발표에서 우리가 대답해야 하는 것:**

| 중간발표 질문 | 최종발표 대답 |
|-------------|------------|
| "이게 실제로 작동하나?" | LLM 에이전트 시뮬레이션 — 실시간 데모로 보여줌 |
| "법적으로 문제없나?" | 한국 숙박업 법령 + GDPR Art.22 + 시스템 설계 원칙으로 대답 |
| "왜 Flexi인가?" | walk_rate < 2% + RevPAR 개선 수치로 대답 |
| "날씨가 정말 도움이 되나?" | ablation study PR-AUC 차이로 대답 |

---

### 3-4. 프로젝트 존재가치 논증 구조 (슬라이드 스토리라인)

최종발표 도입부 슬라이드가 이 순서로 흘러야 한다:

```
1. 문제: 호텔은 왜 오버부킹을 하나?
   → 취소가 불확실하기 때문. 취소율 37%. 빈 방 = 손실.

2. 기존 해법의 한계: 오버부킹
   → 오버부킹은 법적 리스크 + 고객 신뢰 손상
   → 한국 실제 사례: 호텔이 walk 조치 후 소비자 분쟁 발생
   → 현행 법령: [나리가 조사할 부분]

3. 우리의 해법: 예측 기반 Flexi 라우팅
   → 취소할 것 같은 손님에게 미리 Flexi 요금 제안
   → 오버부킹 없이 객실 효율 확보
   → 매니저 결정을 보조 (자동화 아님 — GDPR 대응)

4. 증명: 실제로 작동하는가?
   → LLM 에이전트 5명이 실시간으로 예약
   → DSS가 위험점수 계산
   → Flexi 라우팅 작동 시뮬레이션

5. 한계 인정: 이 시스템을 쓰면 안 되는 경우
   → 데이터 없는 신규 호텔
   → GDPR 동의 없는 자동 결정
   → walk_rate 2% 초과 시 파라미터 재조정 필요
```

---

### 3-5. 한국 오버부킹 법률 조사 가이드

이것이 나리가 추가해야 할 핵심 파트다. 교수님이 명시적으로 지적한 부분.

#### 조사 방향 1 — 소비자 보호법

```
검색어: "호텔 오버부킹 소비자 분쟁" "숙박업 예약 취소 배상"
목표: 실제 판례 또는 소비자원 분쟁 사례 1-2건
포인트: 호텔이 walk 조치(다른 곳으로 보냄)를 했을 때 배상 기준
```

관련 법령:
- **소비자기본법** — 소비자 피해 구제
- **공정거래위원회 고시 「소비자분쟁해결기준」** — 숙박업 항목 확인
  - 예약 취소 시 환불 기준
  - 호텔 귀책 사유로 취소 시 배상 기준

#### 조사 방향 2 — 관광진흥법

```
검색어: "관광진흥법 숙박업" "호텔업 등록 기준"
목표: 오버부킹 관련 규제 조항이 있는지 확인
```

#### 조사 방향 3 — GDPR과 한국 개인정보보호법 비교

```
목표: 우리 시스템(자동 Flexi 라우팅)이 법적으로 허용되는지 근거
핵심: GDPR Art.22 "자동화된 개인 의사결정 금지"
  → 우리 시스템은 "권장"이지 "자동 결정"이 아님
  → 매니저가 최종 결정 → 적법

한국법: 개인정보보호법 제37조의2 (자동화된 결정에 대한 거부권)
  → 2023년 개정으로 한국도 유사 조항 신설
  → 우리 시스템 설계(매니저 개입 필수)가 이 조항에 대한 대응책
```

#### 발표 슬라이드에 넣을 내용 포맷

```
[실제 사례] 2023년 OOO호텔, 성수기 오버부킹으로 walk 발생
            → 소비자원 분쟁 조정 → 1박 요금 150% 배상 판정
            
[현행 법령] 소비자분쟁해결기준 숙박업 항목:
            호텔 귀책 cancellation → 요금 전액 환불 + 위약금

[우리 시스템의 포지션]
  - 오버부킹을 "대체"하는 솔루션
  - Flexi 라우팅으로 취소를 예측해서 선제 대응
  - walk 발생을 최소화 → 법적 리스크 감소
  - GDPR/개인정보보호법 대응: 자동 결정 아닌 "권장" 구조
```

---

### 3-6. 참고할 기존 문서들

| 문서 | 내용 |
|------|------|
| `docs/design_00_problem_definition.md` | AS-IS/TO-BE 문제 정의 원본 |
| `docs/design_06_flexi_system.md` | Flexi 시스템 설계 전체 |
| `docs/design_08_literature_review.md` | 관련 논문 정리 |
| `docs/design_09_beyond_cancellation.md` | 프로젝트 확장 논거 |
| `docs/design_12_sim_defense_logic.md` | 발표 방어 논리 |
| `docs/lessons_from_mid_presentation.md` | 중간발표 교훈 |
| `docs/presentation_evidence.md` | 발표 근거 수치 정리 |

---

### 3-7. 결과물 포맷

금요일 회의 전까지 아래 형식으로 정리해와라:

```markdown
## 프로젝트 존재가치 논증 (최종발표 버전)

### 1. 핵심 주장 1문장
### 2. 중간발표 → 최종발표 논리 개선 포인트
### 3. 한국 오버부킹 법률 사례
  - 출처, 사건 요약, 배상 기준
### 4. 관련 법령 조항
  - 법령명, 조항, 우리 시스템과의 관계
### 5. 발표 슬라이드 제안 (어떤 순서로 보여줄지)
```

---

## 4. 금요일 대면회의 준비 체크리스트

| 담당 | 가져올 것 |
|------|---------|
| 심재형 | LLM 시뮬레이션 실제 실행 데모 + 최종발표 PPT 초안 |
| 이고은 | PMS + DSS 2단 검증 결과 + 버그 리포트 + 개선 제안 목록 |
| 김나리 | 프로젝트 논리 강화 문서 + 한국 오버부킹 법률 조사 결과 |

회의에서 할 것:
1. PPT 초안 슬라이드별 피드백
2. 각자 파트 발표 연습 (1회)
3. 발표 형식 결정 — HTML vs PPT (재형: HTML 선호, 팀 합의)

---

*최종 업데이트: 2026-05-30 | 심재형*
