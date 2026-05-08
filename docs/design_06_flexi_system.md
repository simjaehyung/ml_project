# Flexi Rate 시스템 설계 문서

> 작성: 심재형 (PM) | 기준일: 2026-05-06
> 목적: 취소 확률 기반 정밀 오버부킹 운영 시스템 설계 및 시뮬레이션 명세

---

## 1. 핵심 개념

### 기존 오버부킹 vs Flexi 오버부킹

호텔은 원래부터 오버부킹을 한다. 문제는 **블라인드 오버부킹**이라는 것이다.

```
기존 방식
  과거 평균 취소율 35% → 전체 예약의 35%를 일괄 초과 판매
  → 어느 예약이 취소될지 모르고 찍는 것

Flexi 방식
  모델이 "이 예약들은 취소될 가능성이 높다"고 예측
  → 그 자리에만 Flexi 예약 추가 판매
  → 정밀 오버부킹
```

**핵심 주장:** 취소 예측 정확도(PR-AUC)가 높을수록 walk 발생 없이 빈 방을 채우는 능력이 높아진다.

즉, 이 시스템에서 **모델 성능이 곧 운영 수익과 직결**된다.

---

## 2. 운영 구조

### 객실 인벤토리 분류

```
호텔 물리 객실 N실
  │
  ├─ Standard 풀
  │    Low/Med 위험 예약 → 정상 보장
  │    정가 청구, 즉시 확정
  │
  └─ Flexi 풀 (가상 인벤토리)
       High 위험 예약 자리 → 추가 예약 판매
       할인가 청구, D-1 확정
       초과 도착 시 보상 패키지 자동 발동
```

### Flexi 풀 크기 결정

```
Flexi_slots = Σ P(취소 | 예약_i)   for all i where P > threshold

예: threshold=0.65, 해당 예약 10건, 각 확률 0.70~0.90
  → Flexi_slots = 7.8 ≈ 8실 추가 판매 가능
```

Flexi 풀 크기는 고정값이 아니라 **매일 모델이 재계산**한다.

### 일일 운영 흐름

| 시각 | 동작 |
|------|------|
| 매일 10:00 | 익일 도착 예약 위험 점수 재계산 |
| 17:00 | Flexi 풀 최종 정산 시뮬레이션 |
| 17:00~17:30 | 매니저 대시보드 확인 — 경계 케이스 수동 검토 |
| 17:30 | 확정 / 이동 결정 |
| 18:00 | 손님 자동 통보 발송 |

---

## 3. 가격 정책

### 할인율 공식

```
할인율 = 5% + (위험점수 − 0.5) × 26%
         단, 5% ≤ 할인율 ≤ 18%
```

| 위험 점수 | 할인율 | 손님 입장 |
|----------|--------|----------|
| 0.60~0.69 | 7% | 소폭 저렴 |
| 0.70~0.79 | 11.5% | 매력적 |
| 0.80~0.89 | 14% | 가격 메리트 큼 |
| ≥ 0.90 | 18% | 명확한 트레이드오프 |

위험이 높을수록 취소 가능성이 높고, 그만큼 호텔의 기대 수익이 감소하므로 할인 여력도 커진다.

### 보상 패키지 (Walk 발생 시 자동 발동)

| 보상 항목 | 기준 |
|----------|------|
| 동급 인근 호텔 1박 | 호텔 부담 (협약가) |
| 이동 수단 | 택시 / 셔틀 제공 |
| 원 예약 1박 환불 | 100% |
| 향후 크레딧 | €30~50 |

**경제성 조건:** 보상 패키지 단가 < 취소로 잃는 ADR (빈 방 손실)

---

## 4. 커뮤니케이션 전략 — 파장 방지

### 핵심 문제

손님이 "이 방은 내가 취소할 가능성이 80%라서 파는 겁니다"라는 사실을 알면:
- 알고리즘에 의해 타깃팅되었다는 불쾌감
- "호텔이 나를 위험 손님으로 분류했다"는 낙인감
- SNS 확산 시 브랜드 직격

### 정보 분리 원칙

**호텔이 내부적으로 아는 것 → 손님에게 절대 노출하지 않는 것**

| 호텔 내부 정보 | 손님에게 보이는 것 |
|--------------|-----------------|
| 취소 확률 0.84 | 없음 |
| "이 예약은 High Risk" | 없음 |
| Flexi 풀 오버부킹 중 | 없음 |
| 모델이 이 예약을 선택 | 없음 |

**손님에게 보이는 것은 오직 상품의 조건 차이뿐이다.**

### 언어 설계 — 쓰면 안 되는 말 vs 써야 하는 말

| ❌ 쓰면 안 됨 | ✅ 대신 쓸 말 |
|-------------|-------------|
| "취소 가능성이 높아서" | 쓰지 않음 — 이유 언급 자체 금지 |
| "오버부킹 좌석입니다" | "유연한 요금제입니다" |
| "확정 예약이 아닙니다" | "객실은 체크인 전날 최종 배정됩니다" |
| "당신이 취소할 것 같아서" | 쓰지 않음 |
| "대기 예약" | "Flexi Rate" |

### 손님 관점에서의 프레이밍

Flexi Rate는 **손님에게 개인화된 제안이 아니라 호텔의 요금 상품 중 하나**다.

```
호텔 예약 페이지에 항상 두 옵션이 함께 노출:

  ┌─────────────────────────────────┐
  │  Standard Rate         €120/박  │
  │  ✓ 즉시 객실 확정               │
  │  ✓ 무료 취소 (정책 기준)         │
  └─────────────────────────────────┘

  ┌─────────────────────────────────┐
  │  Flexi Rate            €102/박  │  ← 15% 할인
  │  ✓ 동일 등급 객실               │
  │  ℹ 객실은 체크인 전날 최종 배정  │
  │  ✓ 미배정 시 전액 환불 + 보상    │
  └─────────────────────────────────┘
```

**포인트:** 고위험 예약으로 분류된 손님만 Flexi를 보는 게 아니다. 모든 예약에서 두 옵션이 보인다. 단, Flexi 풀의 실제 재고는 모델이 조정한다. 손님은 자신이 "선택됐다"는 사실을 알 수 없다.

### 자기선택 효과 (self-selection)

이 프레이밍의 부산물로 시스템이 더 안전해진다.

> 할인에 매력을 느껴 Flexi를 선택하는 손님 = 일정이 유동적인 손님일 가능성이 높다.

즉, 손님 스스로 "나는 일정이 바뀔 수 있다"는 신호를 보내면서 Flexi를 고른다. 모델이 예측한 고위험 + 손님의 자발적 선택이 겹치면 실제 취소율이 더 높아져 walk 위험이 줄어든다.

### 분쟁 발생 시 대응

Walk가 발생해도 손님이 "이건 계약 위반"이라고 주장할 수 있다. 사전 방어:

1. 예약 완료 화면에 명시: *"Flexi Rate 객실은 체크인 전날 오후 6시에 최종 배정됩니다"*
2. 예약 확인 이메일에 동일 문구 포함
3. 동의 로그 서버 보관 (GDPR 기준 7년)
4. Walk 발생 즉시 보상 패키지 자동 발동 — 매니저 재량 개입 없이

---

## 5. 손님 고지 및 동의

Flexi 예약의 핵심 원칙: **손님이 알고 동의한 위험**

```
예약 흐름
  1. 비교 화면: Standard €120 vs Flexi €102 (-15%)
  2. "Flexi란?" 안내 페이지
       - 객실 확정 시점: D-1 18:00
       - 미배정 시 보상 내용 명시
  3. 명시적 동의 (단순 체크박스 X → 안내 후 동의)
  4. 예약 완료

D-7: 리마인더 — "일정 변경 시 지금 취소 가능 (수수료 없음)"
D-1 18:00: 확정 또는 이동 통보
```

GDPR Art.22 준수: 자동화된 라우팅이지만 최종 결정은 매니저 승인 후 발송.

---

## 5. 시뮬레이션 설계

### 두 손님 풀 구조 (핵심)

이 시뮬레이션에는 **두 개의 독립된 손님 풀**이 있다.

```
Pool A — 기존 예약자 (고정, 실제 데이터)
  테스트셋 1000명. 실제로 400명이 취소할 것.
  이 결과는 이미 정해져 있다. 시뮬레이션이 바꿀 수 없다.
  모델은 이 중 누가 취소할지를 예측한다.

Pool B — 신규 Flexi 구매자 (외부 유입, 파라미터로 제어)
  Flexi 상품에 관심 있는 외부 손님들.
  슬롯이 생성되면 conversion_rate 비율만큼 구매한다.
  구매자 중 flexi_noshow_rate 비율은 실제 도착하지 않는다.
```

**Pool A와 Pool B는 완전히 별개다.**
Flexi 슬롯을 사는 사람은 기존 1000명이 아니다. 호텔이 새로 유치하는 외부 손님이다.

### 작동 원리

```
Pool A (기존 예약 1000명)
  ├─ 모델 확률 ≤ threshold → Standard 확정
  └─ 모델 확률 >  threshold → Flexi 슬롯 생성 대상
                                     │
                              slots_created
                        = round( Σ P(취소|예약_i) )
                          (확률합 = 예상 취소 수 = 판매 가능 슬롯)
                                     │
                                     ↓
                         Pool B 신규 손님에게 판매
                         slots_sold = slots_created × conversion_rate
                         flexi_new_arrivals = slots_sold × (1 - flexi_noshow_rate)
                                     │
                   ┌─────────────────┴──────────────────┐
                   ↓                                     ↓
     Pool A 실제 취소 ≥ Pool B 도착 수       Pool A 실제 취소 < Pool B 도착 수
     → 빈 방에 Pool B 입주, walk 0            → 방이 모자람 → walk 발생
     → 수익 증가                              → 보상 패키지 지급
```

### 시뮬레이션 코드

```python
def run_flexi_simulation(
    test_df, proba,
    threshold,
    conversion_rate=0.85,    # Pool B 수요 — 슬롯 중 몇 %가 실제로 팔리는가
    flexi_noshow_rate=0.05,  # Pool B — 구매자 중 실제 미도착 비율
    comp_multiplier=1.5      # walk 1건당 보상 = ADR × comp_multiplier
):
    # --- Pool A 분류 ---
    flexi_mask   = proba > threshold
    pool_a_flexi = test_df[flexi_mask]   # 고위험 예약 → Flexi 슬롯 생성 대상
    # pool_a_std = test_df[~flexi_mask]  # 저위험 예약 → Standard 그대로

    # Flexi 슬롯 생성량 — 확률합 기반 (예상 취소 수 = 판매 가능 슬롯 수)
    slots_created = round(proba[flexi_mask].sum())

    # --- Pool B 신규 손님 흐름 ---
    slots_sold         = round(slots_created * conversion_rate)
    flexi_new_arrivals = round(slots_sold * (1 - flexi_noshow_rate))

    # --- Pool A 현실: 실제 취소 수 = 비워지는 방 수 ---
    actual_cancels = pool_a_flexi['is_canceled'].sum()

    # --- Walk 계산: Pool B 도착 수 > Pool A 빈 방 수 ---
    walks                = max(0, flexi_new_arrivals - actual_cancels)
    flexi_new_checked_in = flexi_new_arrivals - walks

    # --- 수익 계산 ---
    avg_adr  = test_df['adr'].mean()
    discount = 0.05 + (proba[flexi_mask].mean() - 0.5) * 0.26
    discount = min(max(discount, 0.05), 0.18)

    flexi_new_rev = flexi_new_checked_in * avg_adr * (1 - discount)
    comp_cost     = walks * avg_adr * comp_multiplier

    return {
        'threshold':            threshold,
        'conversion_rate':      conversion_rate,
        'slots_created':        slots_created,       # 확률합 기반 생성 슬롯
        'slots_sold':           slots_sold,           # 실제 팔린 슬롯 (Pool B 구매)
        'flexi_new_arrivals':   flexi_new_arrivals,   # Pool B 실제 도착 수
        'actual_cancels':       actual_cancels,       # Pool A 실제 취소 수 (빈 방)
        'flexi_new_checked_in': flexi_new_checked_in, # Pool B 실제 입주 수
        'walks':                walks,
        'walk_rate':            walks / flexi_new_arrivals if flexi_new_arrivals > 0 else 0,
        'net_gain':             flexi_new_rev - comp_cost,
        'occupancy_gain':       flexi_new_checked_in,
        'baseline_empty_rooms': test_df['is_canceled'].sum(),
    }
```

### 파라미터 설명

| 파라미터 | 의미 | 기본값 | 범위 |
|---------|------|--------|------|
| `threshold` | Flexi 슬롯 생성 기준 확률 | — | 0.50~0.85 sweep |
| `conversion_rate` | Pool B 수요 — 슬롯 중 실제 팔리는 비율 | 0.85 | 0.60~0.95 |
| `flexi_noshow_rate` | Pool B 구매자 중 실제 미도착 비율 | 0.05 | 0.02~0.10 |
| `comp_multiplier` | walk 보상 단가 = ADR × 이 값 | 1.5 | 고정 |

`conversion_rate`와 `flexi_noshow_rate`는 실제 데이터가 없는 파라미터다. 발표 시 민감도 분석을 통해 "이 가정이 바뀌어도 결론이 유지되는가"를 보여준다.

### 평가 지표

**지표 1 — 점유율 (방이 얼마나 차는가)**
```
occupancy_gain = Pool B 실제 입주 수 (flexi_new_checked_in)

Flexi 없을 때: actual_cancels 만큼 그냥 빈 방
Flexi 있을 때: 그 중 flexi_new_checked_in 만큼 채움
```

**지표 2 — 수익성 (보상 주고도 남는가)**
```
net_gain = flexi_new_rev - comp_cost

net_gain > 0  → 운영 가능
net_gain >> 0 → 기존 블라인드 오버부킹 대비 우위
```

**지표 3 — 안정성**
```
walk_rate = walks / flexi_new_arrivals
목표: < 2%
```

### 결과 시각화 — Threshold Sweep 곡선

threshold 0.50~0.85를 sweep하면서 세 지표 변화를 한 그래프에 표시한다.

```
threshold →  0.50   0.55   0.60   0.65   0.70   0.75   0.80
─────────────────────────────────────────────────────────────
occupancy →  +15%   +12%   +10%   +7%    +5%    +3%    +2%
walk_rate →  5.8%   4.2%   3.1%   2.0%   1.3%   0.7%   0.3%
net_gain  →  높음   높음   보통   보통   낮음   낮음   낮음
─────────────────────────────────────────────────────────────
                                ↑
                         walk_rate = 2% 선
                         여기가 운영 가능 한계점 (최적 threshold)
```

**핵심 메시지:** PR-AUC가 높을수록 이 곡선이 오른쪽으로 밀린다. 같은 walk_rate에서 더 많은 방을 채우고 더 많은 수익을 낸다. PR-AUC가 단순 성능 수치가 아니라 실제 운영 수익과 직결된다는 것을 이 그래프로 증명한다.

### 베이스라인 3종 비교

| 시나리오 | Pool 구조 | walk_rate 예상 |
|---------|---------|--------------|
| **Baseline** | Pool A만. Pool B 없음. 취소 = 빈 방 손실 | 0% (내보내는 손님 없음, 대신 수익 손실) |
| **블라인드 오버부킹** | Pool A 전체 취소율(37%) 기반 일괄 Pool B 유치 | 3~6% (예측 없이 찍음) |
| **Flexi 시스템** | Pool A 모델 예측 기반 정밀 Pool B 유치 | < 2% (목표) |

---

## 6. 예상 결과 구조

발표에서 보여줄 최종 숫자 형태.

```
테스트셋 기간 (2017-03 ~ 2017-08)

[점유율]
  Baseline:          실제 투숙 X실 / 전체 N실 = A%
  Flexi 시스템:      실제 투숙 (X + new_guests_in)실 = B%
  개선:              +ΔB%p

[수익]
  Baseline:          $X (취소된 방은 수익 0)
  Flexi 시스템:      $X + net_gain
  net_gain:          $Y (보상 비용 차감 후)

[안정성]
  walk_rate:         Z% (< 2% 달성 여부)

[모델 기여]
  "PR-AUC가 0.01 오를 때 walk_rate가 몇 % 감소하는가"
  → 모델 성능 개선의 실제 가치를 금액으로 환산
```

---

## 7. 이 프로젝트에서 만드는 것 / 만들지 않는 것

| 항목 | 범위 | 주체 |
|------|------|------|
| 위험 예측 모델 (XGBoost/LightGBM) | ✓ 구현 | 이고은 |
| SHAP 위험 근거 출력 | ✓ 구현 | 심재형 |
| Flexi 라우팅 권장 UI (앱 탭 2) | ✓ 구현 | 심재형 |
| **Flexi 운영 시뮬레이션** | ✓ 구현 | 심재형 |
| 실제 PMS 연동 | 범위 외 | 호텔 인프라 |
| 실제 결제 / 카드 hold | 범위 외 | 호텔 인프라 |
| 협력 호텔 네트워크 | 범위 외 | 호텔 B2B |
| OTA 채널 연동 | 범위 외 | 단계적 확장 |

**발표 포지셔닝:**
> "저희는 두뇌를 만듭니다. 예측 엔진 + 운영 시뮬레이션으로 이 시스템이 실제로 작동하는지를 데이터로 증명합니다. PMS 연동은 호텔 인프라 영역입니다."

---

## 8. 타임라인

| 주차 | 작업 | 담당 |
|------|------|------|
| Week 3 | 최종 모델 확정 → 테스트셋 예측값 생성 | 
| Week 4 | 임계값 확정 + 시뮬레이션 코드 작성 | 
| Week 4 | RevPAR / walk_rate 결과 산출 |
| Week 5~6 | 결과 해석 + 발표 슬라이드 반영 | 팀 |

---

## 9. 미결 항목

| # | 항목 | 상태 |
|---|------|------|
| A | 임계값 확정 (0.65? 0.70?) | Week 4 PR curve 보고 결정 |
| B | N_rooms 설정 — 테스트셋에서 호텔별 실제 객실 수 추정 방법 | 논의 필요 |
| C | compensation_per_walk 단가 — ADR 기준 몇 배로 설정할지 | Week 4 |
| D | Flexi 슬롯 판매량 계산 방식 — `round(proba.sum())` vs 고정 비율 | Week 4 시뮬레이션 코드 시 결정 |
