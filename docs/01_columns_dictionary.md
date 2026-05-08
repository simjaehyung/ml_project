# 호텔 예약 데이터 — 32개 컬럼 사전

> **데이터 출처:** Kaggle `jessemostipak/hotel-booking-demand` (`hotel_bookings.csv`)
> **검증 기준 시점:** Week 1 (Dev A 이고은)
> **이 문서의 목적:** 모델링 전에 32개 컬럼 각각이 무엇을 담고 있는지 기록. 누수 컬럼 분류는 별도 문서(`leakage_candidates.md`)에서 진행.

---

## 📌 데이터 한눈에

| 항목 | 값 |
|---|---|
| 전체 행 수 | **119,390** |
| 전체 컬럼 수 | **32** |
| 타깃 변수 | `is_canceled` (0=정상, 1=취소/노쇼) |
| 전체 취소율 | **37.04%** |
| 호텔 종류 | City Hotel (79,330건, 취소율 41.7%) / Resort Hotel (40,060건, 취소율 27.8%) |
| 도착일 범위 | 2015-07 ~ 2017-08 (2015 하반기 + 2016 전체 + 2017 상반기) |
| 결측 발견 컬럼 | `company` 94.31%, `agent` 13.69%, `country` 0.41%, `children` 4건 |

---

## 📋 컬럼 사전 (원본 순서)

| # | 컬럼명 | 타입 | 결측% | 고유값 | 한국어 의미 | 예시값(빈도순 Top3) | 비고 |
|---|---|---|---|---|---|---|---|
| 1 | `hotel` | str | 0.00% | 2 | 호텔 종류 | `City Hotel`, `Resort Hotel` | 두 호텔의 취소율이 14%p 차이남 → 호텔별 분리 분석 검토 |
| 2 | `is_canceled` | int | 0.00% | 2 | **타깃 변수.** 예약이 최종적으로 취소(또는 노쇼)되었는지 | `0`, `1` | 1 = Canceled 또는 No-Show. 학습/평가 기준 |
| 3 | `lead_time` | int | 0.00% | 479 | 예약일부터 도착 예정일까지의 일수 | `0`, `1`, `2` | 0~737일. 평균 104일, 중앙값 69일. 어려움 ②(시간 비대칭성)의 핵심 변수 |
| 4 | `arrival_date_year` | int | 0.00% | 3 | 도착 예정 연도 | `2016`, `2017`, `2015` | 시간 split의 기준 |
| 5 | `arrival_date_month` | str | 0.00% | 12 | 도착 예정 월 (영문 문자열) | `August`, `July`, `May` | 숫자 변환 필요 (`pd.to_datetime` 처리 시) |
| 6 | `arrival_date_week_number` | int | 0.00% | 53 | 도착 예정 주차 (1~53) | `33`, `30`, `32` | year/month/day와 중복 정보. 모델링 시 중복 변수 처리 검토 |
| 7 | `arrival_date_day_of_month` | int | 0.00% | 31 | 도착 예정일 (1~31) | `17`, `5`, `15` | year/month와 합쳐 `arrival_date` datetime 생성에 사용 |
| 8 | `stays_in_weekend_nights` | int | 0.00% | 17 | 토·일 숙박 박수 | `0`, `2`, `1` | 0이면 평일만 묵음 |
| 9 | `stays_in_week_nights` | int | 0.00% | 35 | 평일(월~금) 숙박 박수 | `2`, `1`, `3` | 두 컬럼 합 = 총 숙박일 |
| 10 | `adults` | int | 0.00% | 14 | 성인 인원 수 | `2`, `1`, `3` | 0인 행 존재 → 영유아만 있는 경우 또는 데이터 오류 |
| 11 | `children` | float | 0.00% | 5 | 어린이 인원 수 | `0.0`, `1.0`, `2.0` | float인 이유: 결측 4건이 NaN으로 존재 |
| 12 | `babies` | int | 0.00% | 5 | 영아 인원 수 | `0`, `1`, `2` | 거의 대부분 0 |
| 13 | `meal` | str | 0.00% | 5 | 식사 옵션 | `BB`, `HB`, `SC` | BB=조식, HB=조·석식, FB=세 끼, SC=식사 미포함, Undefined=정보없음 (Undefined와 SC를 같이 봐야 할 가능성) |
| 14 | `country` | str | 0.41% | 177 | 손님 국적 (ISO 3166 3자리 코드) | `PRT`, `GBR`, `FRA` | 포르투갈 손님이 압도적. 고유값 177개 → 인코딩 전략 필요 |
| 15 | `market_segment` | str | 0.00% | 8 | 시장 세그먼트 (예약 경로의 마케팅 분류) | `Online TA`, `Offline TA/TO`, `Groups` | TA = Travel Agent, TO = Tour Operator |
| 16 | `distribution_channel` | str | 0.00% | 5 | 유통 채널 | `TA/TO`, `Direct`, `Corporate` | market_segment와 비슷한 정보 → 다중공선성 가능 |
| 17 | `is_repeated_guest` | int | 0.00% | 2 | 재방문 손님 여부 | `0`, `1` | 1 = 과거에 묵은 적 있음 |
| 18 | `previous_cancellations` | int | 0.00% | 15 | 같은 손님의 과거 취소 횟수 | `0`, `1`, `2` | 손님 행동 패턴 변수 |
| 19 | `previous_bookings_not_canceled` | int | 0.00% | 73 | 같은 손님의 과거 정상 예약(취소 아님) 횟수 | `0`, `1`, `2` | 0~72까지 분포 |
| 20 | `reserved_room_type` | str | 0.00% | 10 | 예약 시점에 손님이 요청한 객실 타입 (코드화) | `A`, `D`, `E` | A가 가장 흔함. 실제 알파벳-객실 매핑은 비공개 |
| 21 | `assigned_room_type` | str | 0.00% | 12 | 체크인 시점에 실제 배정된 객실 타입 | `A`, `D`, `E` | reserved와 12.5% 케이스에서 불일치. 누수 분석에서 따져볼 컬럼 |
| 22 | `booking_changes` | int | 0.00% | 21 | 예약 후 변경된 횟수 | `0`, `1`, `2` | 변경이 잦은 예약 = 취소 가능성과 관련될 가능성 |
| 23 | `deposit_type` | str | 0.00% | 3 | 보증금 유형 | `No Deposit`, `Non Refund`, `Refundable` | Non Refund = 환불 불가 선납, Refundable = 환불 가능 선납 |
| 24 | `agent` | float | 13.69% | 333 | 예약을 처리한 여행사/에이전시 ID (익명화 숫자) | `9.0`, `240.0`, `1.0` | 결측 = 에이전시 통하지 않은 예약. ID는 333개 |
| 25 | `company` | float | 94.31% | 352 | 예약·결제를 맡은 기업 ID | `40.0`, `223.0`, `67.0` | **94% 결측 — 사실상 사용 어려움.** 결측 자체를 "법인 예약 아님" 플래그로 변환 검토 |
| 26 | `days_in_waiting_list` | int | 0.00% | 128 | 대기자 명단에 있던 일수 | `0`, `39`, `58` | 0이면 즉시 확정. 대부분 0 |
| 27 | `customer_type` | str | 0.00% | 4 | 고객 유형 | `Transient`, `Transient-Party`, `Contract` | Transient = 일반 단기, Transient-Party = 그룹 내 단기, Contract = 계약, Group = 그룹 |
| 28 | `adr` | float | 0.00% | 8,879 | Average Daily Rate (1박 평균 객실 단가, EUR) | `62.0`, `75.0`, `90.0` | 음수·0·극단값 존재 가능 → EDA에서 이상치 확인 필요 |
| 29 | `required_car_parking_spaces` | int | 0.00% | 5 | 손님이 요청한 주차 공간 수 | `0`, `1`, `2` | 거의 대부분 0 |
| 30 | `total_of_special_requests` | int | 0.00% | 6 | 특별 요청 총 개수 (예: 고층, 트윈베드) | `0`, `1`, `2` | 0~5. 요청 많을수록 진지한 예약일 가능성 |
| 31 | `reservation_status` | str | 0.00% | 3 | **마지막 예약 상태** | `Check-Out`, `Canceled`, `No-Show` | ⚠️ `is_canceled`와 100% 일치 관계. 누수 분석에서 다룰 것 |
| 32 | `reservation_status_date` | str | 0.00% | 926 | 위 상태가 마지막으로 갱신된 날짜 | `2015-10-21`, `2015-07-06`, `2016-11-25` | ⚠️ 도착 이후에도 갱신될 수 있는 시점 정보. 누수 분석에서 다룰 것 |

---

## 🔎 한 줄 정리

32개 컬럼을 성격별로 묶으면 — **타깃**(2개: `is_canceled`, ⚠️`reservation_status`/`reservation_status_date`), **시간**(5개: `lead_time` + `arrival_date_*`), **숙박 구성**(5개: `stays_in_*`, `adults`, `children`, `babies`), **예약 채널·세그먼트**(4개: `meal` 제외 `country`/`market_segment`/`distribution_channel`/`agent`/`company`), **손님 이력**(3개: `is_repeated_guest`, `previous_*` 2개), **객실·예약 변동**(3개: `reserved_room_type`, `assigned_room_type`, `booking_changes`), **결제·운영**(7개: `meal`, `deposit_type`, `days_in_waiting_list`, `customer_type`, `adr`, `required_car_parking_spaces`, `total_of_special_requests`).

다음 단계: 이 표를 토대로 **각 컬럼이 "예약 시점에 알 수 있는가"를 판정**하는 누수 후보 분류표(`leakage_candidates.md`) 작성.
