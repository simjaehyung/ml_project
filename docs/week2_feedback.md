# Week 2 피드백 노트 — PM용

> 작성: 심재형 / 날짜: 2026-05-07
> 이 파일은 PM이 나중에 다시 읽고 결정하기 위한 메모. 기술적 판단보다 "왜 이게 문제인가"에 집중.

---

## 오늘 완료된 것

| 항목 | 담당 | 결과 |
|------|------|------|
| 전처리 파이프라인 (`preprocessing_pipeline.py`) | 심재형 | ✅ 완료. train/test_processed 생성 |
| Dummy Classifier baseline | 심재형 | ✅ PR-AUC 0.3870 (기준선 확정) |
| Streamlit 4패턴 + 앱 골격 | 이고은 | ✅ 완료. 탭1·탭2 구조 + 더미 예측값 구현 |
| 충돌 해결 + push | 심재형 | ✅ bf17d0d |

---

## Dummy PR-AUC 0.3870 — 이게 무슨 의미인가

모델을 하나도 안 쓰고 "전부 취소 안 한다"고 예측했을 때의 점수다.

이 점수보다 높아야 모델이 실제로 뭔가를 학습한 것이다.
LR·RF가 이걸 못 넘으면 그 모델은 의미가 없다는 뜻.

테스트셋 취소율 = 38.7% → Dummy PR-AUC도 약 0.387 (이론값). 정상.

---

## 이고은 Streamlit 앱 — 현재 상태

**잘 됨:**
- 탭1/탭2 구조 완성
- 할인율 공식을 PM 문서에서 직접 읽고 구현함 (`5% + (위험 - 0.5) × 26%`)
- `@st.cache_data` 같은 최적화도 스스로 적용
- 주석에 "Week 4에서 fake_risk 자리에 모델 예측값 들어감" 명시 — 나중 작업 흐름 파악하고 있음

**지금 한계 (예정된 것):**
- 취소 위험 78%는 하드코딩된 더미값. Week 4에서 모델로 교체.
- 탭1 데이터가 전처리 전 원본. STEP 2에서 processed 데이터로 교체 필요.

---

## 🔴 핵심 안건 — deposit_type "Non Refund" 이슈

### 뭘 발견했나

전처리하면서 데이터를 뜯어봤더니:

```
deposit_type = "No Deposit"   → 취소율 26.6%   (6만 8천건)   ← 정상
deposit_type = "Non Refund"   → 취소율 99.2%   (1만 461건)   ← 이상함
deposit_type = "Refundable"   → 취소율  7.4%   (135건)
```

"Non Refund"는 **환불 불가 요금제**다.
손님이 예약할 때 "싸지만 취소하면 환불 안 된다"는 조건으로 예약하는 것.

근데 이 사람들이 99.2%나 취소한다? 말이 안 된다.
환불도 못 받는데 왜 취소해?

### 두 가지 가설

**가설 A — B2B 여행사 allotment 계약 (채택)**

Non Refund의 61%가 "Groups"(단체), 37%가 "Offline TA/TO"(오프라인 여행사).

핵심 해석: 호텔-여행사 간 B2B allotment 계약에서 `Non Refund`는 **요금제 유형**을 나타낼 뿐이다.
개인 예약의 "환불불가(보증금 몰취)"와는 다르다.
B2B 계약에는 통상 **release date** 조항이 있어, 그 이전에 블록을 반납하면 패널티 없이 취소 가능.

즉, 여행사는 돈을 잃는 게 아니라 **미판매 블록을 반납**하는 것이다.
99.2% 취소율이 경제적으로 성립하는 이유가 여기에 있다.
(환불도 못 받으면서 99%를 취소한다는 건 경제적으로 불가능 → 가설 B의 약점)

**가설 B — 사후 기록 오염 (배제하지 않음)**

취소 이후 시스템이 deposit_type을 "Non Refund"로 업데이트.
타임스탬프가 없어 완전히 배제할 수 없지만, 가설 A가 경제 논리상 더 설득력 있음.

### 왜 구분을 못 하나

이 데이터셋에 deposit_type이 **언제 기록됐는지** 타임스탬프가 없다.
원본 논문(Antonio et al. 2019)도 이 부분을 명시하지 않음.

### 모델에서 이 컬럼을 쓰면 어떻게 되나

XGBoost·LightGBM 같은 트리 모델은 패턴을 매우 잘 잡는다.
"Non Refund → 취소" 신호가 너무 강해서 모델이 이 컬럼 하나에 과도하게 의존할 가능성이 높다.

Week 3에서 SHAP을 보면 deposit_type이 맨 위에 있을 것이다.
→ deposit_type 독식 여부를 SHAP에서 반드시 확인해야 한다.

### 결정: KEEP (2026-05-08 확정) — 가설 A 인지 하에 포함

**우리는 가설 A(B2B allotment 패턴)를 채택하고, 그 가정을 인지한 상태로 모델에 포함한다.**
발표 시 "Non Refund 99.2% 취소율은 여행사 블록 반납 패턴으로 해석했다"고 명시.

- Week 3 SHAP: deposit_type 기여도 1~2위 독식 여부 모니터링
- Phase 2(Week 5): deposit_type 제외 ablation 실험으로 영향 정량화

---

## 기타 전처리 발견 — 3개

### adr = 0 (1,504건, 2%)

평균 요금이 0원인 예약. 왜 0인지 불명확.
→ **MVP: 그냥 둔다.** 트리 모델에서 이상값 자체가 신호가 될 수 있음.

### adults = 0 (273건, 0.3%)

어른 없는 예약. 어린이·유아만 있거나 데이터 오류.
→ **MVP: 그냥 둔다.** 건수 적고 제거 시 오히려 편향.

### meal = "Undefined" (756건)

"SC"(식사 없음)와 의미가 같을 가능성 높음.
→ **MVP: SC로 통합.** 파이프라인에 한 줄 추가 예정.

---

## 전처리 파이프라인 최종 결과

```
원본 train: 78,703행 × 38컬럼
처리 후:   78,703행 × 34컬럼  (NaN 0건)

제거된 컬럼 4개:
  - temperature_2m_mean   (날씨 다중공선성)
  - wind_speed_10m_mean   (날씨 다중공선성)
  - rain_sum              (날씨 다중공선성)
  - arrival_date          (time_split 임시 컬럼, ML 불필요)

country_grouped Top10:
  PRT·GBR·FRA·ESP·DEU·ITA·IRL·BEL·NLD·BRA + Other
```

범주형 컬럼 (OHE는 각 모델 학습 시 처리):
`hotel / meal / market_segment / distribution_channel /
 reserved_room_type / deposit_type / customer_type / country_grouped`

---

## 이고은 STEP 2 — 지금 시작 가능

파이프라인 완성됐으니 이고은이 직접 실행해서 processed CSV 받으면 됨:
```
python src/preprocessing_pipeline.py
```

이후 `previous_cancellations` EDA 시작.
코드는 Week 2 업무 노션 페이지 코드 레퍼런스에 있음.

---

## 미결 사항 — 나중에 확인할 것

| # | 안건 | 결정 시점 | 핵심 질문 |
|---|------|----------|-----------|
| A | deposit_type | ✅ DROP 확정 (2026-05-08) | 파이프라인 반영 완료 |
| B | meal "Undefined" → SC 통합 | 다음 파이프라인 업데이트 시 | 한 줄 추가로 끝나는 작업 |
| C | previous_cancellations EDA 결과 | 이고은 STEP 2 완료 후 | is_repeated_guest 정의 어긋남 2,674건 해석 |
| D | precipitation 다중공선성 | 김나리 LR 완료 후 | 0.9 이상이면 하나 제거 검토 |
