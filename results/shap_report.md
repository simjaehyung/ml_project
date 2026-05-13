# SHAP 분석 리포트

생성일: 2026-05-12 | 샘플: 3,000행 (테스트셋 무작위) | 최종 선정 모델: LightGBM ★

---

## 1. 모델별 Top 20 피처 중요도

### XGBoost Top 20
| Rank | Feature | Mean \|SHAP\| |
|------|---------|--------------|
| 1 | `country_grouped_PRT` | 1.1091 |
| 2 | `total_of_special_requests` | 0.7652 |
| 3 | `lead_time` | 0.5720 |
| 4 | `required_car_parking_spaces` | 0.4615 |
| 5 | `market_segment_Online TA` | 0.3772 |
| 6 | `adr` | 0.3718 |
| 7 | `customer_type_Transient` | 0.2454 |
| 8 | `arrival_date_week_number` | 0.2249 |
| 9 | `previous_cancellations` | 0.2048 |
| 10 | `market_segment_Groups` | 0.1863 |
| 11 | `arrival_date_year` | 0.1817 |
| 12 | `booking_changes` | 0.1738 |
| 13 | `customer_type_Transient-Party` | 0.1576 |
| 14 | `market_segment_Offline TA/TO` | 0.1553 |
| 15 | `temperature_2m_min` | 0.0974 |
| 16 | `stays_in_week_nights` | 0.0890 |
| 17 | `temperature_2m_max` | 0.0859 |
| 18 | `wind_speed_10m_max` | 0.0731 |
| 19 | `relative_humidity_2m_mean` | 0.0672 |
| 20 | `cloud_cover_mean` | 0.0653 |

### LightGBM ★ Top 20
| Rank | Feature | Mean \|SHAP\| |
|------|---------|--------------|
| 1 | `country_grouped_PRT` | 1.0639 |
| 2 | `required_car_parking_spaces` | 0.6797 |
| 3 | `total_of_special_requests` | 0.6435 |
| 4 | `lead_time` | 0.5312 |
| 5 | `previous_cancellations` | 0.3941 |
| 6 | `market_segment_Online TA` | 0.3712 |
| 7 | `customer_type_Transient` | 0.2562 |
| 8 | `market_segment_Offline TA/TO` | 0.2556 |
| 9 | `adr` | 0.2525 |
| 10 | `market_segment_Groups` | 0.1680 |
| 11 | `booking_changes` | 0.1430 |
| 12 | `arrival_date_week_number` | 0.1090 |
| 13 | `customer_type_Transient-Party` | 0.1057 |
| 14 | `arrival_date_year` | 0.0611 |
| 15 | `is_repeated_guest` | 0.0551 |
| 16 | `country_grouped_DEU` | 0.0464 |
| 17 | `temperature_2m_min` | 0.0416 |
| 18 | `temperature_2m_max` | 0.0390 |
| 19 | `agent` | 0.0385 |
| 20 | `country_grouped_FRA` | 0.0374 |

---

## 2. Top-10 피처 비교

| 구분 | 피처 |
|------|------|
| 공통 (양쪽 Top 10) | `adr`, `country_grouped_PRT`, `customer_type_Transient`, `lead_time`, `market_segment_Groups`, `market_segment_Online TA`, `previous_cancellations`, `required_car_parking_spaces`, `total_of_special_requests` |
| XGBoost 전용 | `arrival_date_week_number` |
| LightGBM 전용 | `market_segment_Offline TA/TO` |

---

## 3. previous_cancellations B2B 신호 감시

| 모델 | 순위 |
|------|------|
| XGBoost | 9위 |
| LightGBM | 5위 |

✅ 상위 3위 밖 — 현재는 허용 범위 내. Phase 2에서 ablation 예정대로 진행.

---

## 4. 플롯 파일

| 파일 | 내용 |
|------|------|
| `shap_xgb_bar.png` | XGBoost global 중요도 (bar) |
| `shap_lgbm_bar.png` | LightGBM global 중요도 (bar) |
| `shap_xgb_beeswarm.png` | XGBoost beeswarm (방향성 포함) |
| `shap_lgbm_beeswarm.png` | LightGBM beeswarm (방향성 포함) |
| `shap_comparison.png` | 두 모델 나란히 비교 |
| `shap_waterfall.png` | 최고위험 예약 개별 설명 (LGBM, 앱 데모용) |

---

## 5. 액션 항목

- [ ] previous_cancellations 순위 확인 후 Phase 2 ablation 우선순위 결정 (미결 #6)
- [ ] SHAP top 피처 기반 ACTION 규칙 초안 작성 (미결 #5)
- [ ] 임계값 결정 시 beeswarm 방향성 참고 — 높은 값이 취소 위험 올리는 피처 파악 (미결 #4)
- [ ] 앱 탭1: `shap_lgbm_bar.png` 전역 중요도 패널로 활용
- [ ] 앱 탭2 Flexi: 개별 예약 waterfall → `shap_waterfall.png` 로직 재사용
