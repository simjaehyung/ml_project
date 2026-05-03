# 문제 정의 — 호텔 No-Show 의사결정 지원 시스템

## AS-IS

호텔 매니저는 예약 취소 여부를 직관에 의존해 판단한다.
취소율이 37%에 달하지만, 어떤 예약이 위험한지 미리 알 방법이 없다.

## TO-BE

예약 정보 + 날씨 데이터를 입력받아 세 가지를 자동 출력하는 시스템:

1. **취소 확률** — XGBoost 기반 예측값
2. **주도 변수 Top 3** — SHAP 기반 자동 해석 ("왜 이 확률인가")
3. **비즈니스 액션 권장** — 매니저가 즉시 실행할 수 있는 조치

## 비즈니스 시나리오

```
입력: 예약 ID 12345
  - lead_time: 180일
  - previous_cancellations: 2회
  - deposit_type: No Deposit
  - 도착일 강수량: 25mm

출력:
  취소 확률: 0.78 (HIGH)
  주도 변수: lead_time(+0.21), 과거 취소 이력(+0.15), No Deposit(+0.12)
  권장 액션: 도착 30일 전 재확인 콜 / 선결제 전환 유도 / 오버부킹 후보 분류
```

## 데이터

- **예약 데이터**: Kaggle `hotel-booking-demand` (119,390행, 2015–2017)
  - City Hotel (포르투갈 리스본) / Resort Hotel (포르투갈 알가르브)
  - 취소율 37.04% (City 41.7% / Resort 27.8%)
- **날씨 데이터**: Open-Meteo Historical API
  - 두 호텔 좌표 기준 일별 11개 변수 수집

## 우리가 정직하게 다루는 4가지 어려움

### ① 데이터 누수 (Target Leakage)
- 확정 drop: `reservation_status`, `reservation_status_date` (타깃과 동치 또는 미래 갱신값)
- PM 임시 결정 drop: `assigned_room_type`(체크인 시점 배정), `previous_bookings_not_canceled`(정합성 모순), `days_in_waiting_list`(간접 미래 정보)
- 조건부 keep: `previous_cancellations` (Week 2 EDA 재검증 예정)

### ② 시간 비대칭성
- 학습 시점: 도착일 실제 날씨 사용
- 추론 시점: 손님은 예약 당시 일기예보만 알 수 있음 (평균 lead_time 104일)
- 대응: 실제 날씨로 학습 + SHAP interaction으로 lead_time별 날씨 영향 정량화, 한계 명시

### ③ 임계값 함정
- 기본값 0.5는 빈 방 손실 vs 오버부킹 보상비 비대칭 무시
- 대응: PR curve 분석 후 0.35 수준으로 하향, 비즈니스 논리 문서화

### ④ 클래스 불균형 + 평가지표
- accuracy 기반 평가 시 "모두 취소 안 함" 전략이 63% 달성 → 무의미
- 대응: PR-AUC 메인, F1 보조

## 모델 구성

| 역할 | 모델 |
|------|------|
| 메인 | XGBoost |
| Baseline 1 | Logistic Regression |
| Baseline 2 | Random Forest |

## 평가 지표

- **메인**: PR-AUC
- **보조**: F1-score (threshold 0.35 기준)

## 시스템 한계

- 학습/추론 시점 날씨 데이터 비대칭은 해소되지 않음
- 임계값 0.35는 가정된 손실비 기반 — 실제 호텔마다 다를 수 있음
- 이야기 생성·액션 매핑은 호텔 운영 전문가 검증 없는 합리적 가설 수준
