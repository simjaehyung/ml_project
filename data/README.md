# data/

CSV 파일은 `.gitignore`로 추적 제외. 아래 경로·출처에서 직접 받아서 배치.

| 파일 | 출처 | 설명 |
|------|------|------|
| `hotel_bookings.csv` | [Kaggle](https://www.kaggle.com/datasets/jessemostipak/hotel-booking-demand) | 원본 예약 데이터 (119,390행 × 32컬럼) |
| `weather_data.csv` | Open-Meteo Historical API | 리스본·알가르브 일별 날씨 (2015-07 ~ 2017-08) |
| `bookings_weather.csv` | `src/join.py` 실행 결과 | 예약 + 날씨 Left Join (누수 컬럼 2개 제거) |
| `bookings_weather_pm.csv` | `src/join.py` + PM 결정 적용 | Week 2 EDA 시작점 (보류 컬럼 3개 추가 drop, agent·company 인디케이터 변환) |

## 재현 순서

```bash
# 1. hotel_bookings.csv → Kaggle에서 수동 다운로드
# 2. 날씨 수집
python src/weather.py
# 3. Join + 전처리
python src/join.py
```
