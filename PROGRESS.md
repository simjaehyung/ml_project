# 진행 상황 — Hotel DSS 최종발표 빌드

> 자동 갱신 | 마지막 업데이트: 2026-05-29

---

## 현재 실행 중인 서버

| 서버 | 포트 | 상태 |
|------|------|------|
| FastAPI DSS (main_mock.py) | 8000 | ✅ 실행 중 |
| Next.js 프론트엔드 | 3000 | ✅ 실행 중 |

접속: http://localhost:3000/dashboard

---

## 빌드 완료 현황

### ✅ Backend (Gate A 통과)

| 파일 | 줄 수 | 검증 |
|------|-------|------|
| `api/predictor.py` | 343줄 | ✅ `predict()` 동작 확인 |
| `api/pms_adapter.py` | 370줄 | ✅ `adapt_form()` 동작 확인 |
| `api/main.py` | 248줄 | ✅ uvicorn 실행 확인 |

실제 예측 테스트 결과:
- 입력: City Hotel / TA/TO / 취소이력 2회 / 180일 후 체크인
- 출력: risk_score 0.9857 → Flexi: True ✅
- SHAP top 3 정상 반환

### ✅ Frontend App 2 (Gate B+C 통과)

| 파일 | 내용 |
|------|------|
| `hotel-dss-app/src/types/api.ts` | API 타입 정의 |
| `hotel-dss-app/src/lib/api.ts` | 5개 API 함수 |
| `hotel-dss-app/src/app/dashboard/layout.tsx` | 사이드바 + 네비게이션 |
| `hotel-dss-app/src/app/dashboard/page.tsx` | Overview (KPI 4개 + polling) |
| `hotel-dss-app/src/app/dashboard/reservations/page.tsx` | 예약 목록 DataTable |
| `hotel-dss-app/src/app/dashboard/flexi/page.tsx` | Flexi 슬라이더 패널 |

빌드 결과: TypeScript 에러 0개 ✅

### ✅ 디자인 수술 완료

| 페르소나 | 결과 |
|---------|------|
| Sentinel | ✅ 완료 — PASS 6/7, meal Undefined FAIL(발표용 현상유지) |
| Generic Detector | ✅ 완료 — 11/12 FAIL 진단 |
| Trend Scout | ✅ 완료 — Status 컬럼이 "AI 냄새 1위" |
| Design Surgeon | ✅ 완료 — 4가지 수술 적용, 빌드 성공 |

**적용된 수술:**
- Status 컬럼 제거 (Risk Score와 중복)
- Risk Score → 배지 + inline bar + 레이블
- 행 레벨 left border 위험도 색상 (빨강/노랑/초록)
- KPI 카드 아이콘 추가 + 고위험 카드 빨간 ring
- 날짜 → "Aug 17 · 79d" 형식

---

## 남은 작업

### 이번 세션 (Gate D 목표)

| # | 작업 | 담당 | 상태 |
|---|------|------|------|
| 1 | App 1 PMS 3페이지 구현 | 에이전트 | ⬜ 대기 |
| 2 | 디자인 수술 1차 (Overview) | Design Surgeon | ✅ 완료 |
| 3 | 디자인 수술 2차 (Reservations) | Design Surgeon | ✅ 완료 |
| 4 | Lead Time × Risk Score 산점도 + 클릭 패널 | Chart Agent | ✅ 완료 |
| 8 | 뷰 탭 (Overview/Priority/List) + 막대그래프 기본 차트 | View Switch Agent | ✅ 완료 |
| 9 | NAV 순서 수정 (New Booking 상단으로) | 직접 적용 | ✅ 완료 |
| 10 | Flexi Policy 슬라이더↔테이블 연동 수정 | 직접 적용 | ✅ 완료 |
| 11 | UI 편의성 분석 | UI Expert | ✅ 완료 |
| 12 | 디자인 리서치 (실제 운영 앱 조사) | Design Research | ✅ 완료 |
| 13 | Overview 막대그래프 → 도넛+즉시처리목록 교체 | Design Surgeon | ✅ 완료 |
| 14 | PMS New Booking 폼 구현 | Build Agent | ✅ 완료 |
| 15 | 색상 시스템 전문가 리뷰 + 팔레트 교체 | Color Surgeon | ✅ 완료 |
| 5 | Sentinel 결과 반영 (meal Undefined — 현상 유지 결정) | — | ✅ 결정 완료 |
| 6 | api/main.py (실제 모델) 교체 | 심재형 | ⬜ |
| 7 | E2E 통합 테스트 | 심재형 | ⬜ |

### 이고은 인계 예정 (Gate D 완료 후)

- HANDOFF.md 작성 (버그 목록 + 개선 요청)
- 이고은이 받아서 수정·개선

---

## 알려진 이슈

| # | 이슈 | 심각도 | 상태 |
|---|------|--------|------|
| 1 | SHAP 버전별 ndarray 형태 차이 → 분기 처리됨 | 낮음 | ✅ 해결 |
| 2 | Windows 터미널 한국어 인코딩 깨짐 (API 응답은 정상) | 낮음 | 무시 |
| 3 | 스크린샷 Python playwright 미설치 → Node.js로 전환 | 중간 | 🔧 처리 중 |

---

## 파일 구조 (현재)

```
07_Hotel_DSS/
├── api/
│   ├── schemas.py          ✅ 완성
│   ├── types.ts            ✅ 완성
│   ├── main_mock.py        ✅ 완성
│   ├── main.py             ✅ 완성 (실제 LightGBM)
│   ├── predictor.py        ✅ 완성
│   └── pms_adapter.py      ✅ 완성
├── app_pms/
│   ├── pms_schemas.py      ✅ 완성
│   └── pms_mock.py         ✅ 완성
├── hotel-dss-app/          ✅ Next.js 프로젝트
│   └── src/app/dashboard/  ✅ App 2 완성
├── data/
│   └── seasonal_weather.csv ✅ 자동 생성됨
├── results/
│   └── model_final.pkl     ✅ LightGBM PR-AUC 0.8189
├── ORCHESTRA.md            ✅ 마스터 문서
└── PROGRESS.md             ← 이 파일
```
