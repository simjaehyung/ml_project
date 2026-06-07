"""
src/build_demo_snapshot.py
발표용 "현재 장부(as-of)" 스냅샷 생성 — 테스트셋 기간의 실제 예약을 모델로 채점해
대시보드(현황·예약목록·Flexi·도메인 인박스)가 빈약한 20건 랜덤 대신
'특정 시점에 잡혀 있는 실제 예약'을 보여주도록 한다.

정직성:
  - 예약 필드(호텔·국적·도착일·숙박·인원·ADR·lead_time)는 캐글 test.csv 실제값.
  - risk = results/model_final.pkl(LightGBM) 사전 채점값 (point-in-time 재현 아님 — 'as-of' 시연용).
  - created_at(예약일) = arrival_date − lead_time (실제). → lead time이 '지금'과 무관하게 정확.
  - 표시용 균등 샘플(window 내 전체에서 N건). meta에 window 전체 수(n_window)도 기록.

입력:  data/test.csv(표시 필드+arrival_date), data/test_processed.csv(모델 피처), results/model_final.pkl
출력:  data/demo_snapshot.json

실행:  python src/build_demo_snapshot.py [--as-of 2017-06-01] [--horizon 14] [--n 100]
"""
import argparse
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

import numpy as np
import pandas as pd
import joblib

THRESHOLD = 0.65  # api/main.py CURRENT_THRESHOLD와 동일


def discount_for(risk: float) -> float | None:
    if risk < THRESHOLD:
        return None
    raw = 0.05 + (risk - 0.5) * 0.26
    return round(max(0.05, min(0.18, raw)), 4)


def status_for(risk: float, flexi: bool) -> str:
    if risk >= 0.7:
        return "high-risk"
    if flexi:
        return "flexi-routed"
    return "confirmed"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default="2017-06-01")
    ap.add_argument("--horizon", type=int, default=14)  # as-of 기준 향후 N일 도착 = '현재 장부'
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--out", default="data/demo_snapshot.json")
    args = ap.parse_args()

    model = joblib.load("results/model_final.pkl")
    raw = pd.read_csv("data/test.csv")
    proc = pd.read_csv("data/test_processed.csv")
    assert len(raw) == len(proc), "test.csv 와 test_processed.csv 행 수 불일치"

    # 모델 채점 (학습과 동일한 OHE → 모델 피처 순서로 정렬)
    X = pd.get_dummies(proc.drop(columns=["is_canceled"]))
    X = X.reindex(columns=model.feature_name_, fill_value=0)
    risk = model.predict_proba(X)[:, 1]

    df = raw.copy()
    df["risk"] = risk
    df["arr"] = pd.to_datetime(df["arrival_date"])

    as_of = pd.Timestamp(args.as_of)
    end = as_of + pd.Timedelta(days=args.horizon)
    window = df[(df["arr"] >= as_of) & (df["arr"] < end)].copy()
    n_window = len(window)
    if n_window == 0:
        raise SystemExit(f"window [{as_of.date()}, {end.date()}) 에 예약 없음")

    # 위험대 균형 샘플 — 저/중/고가 모두 잘 보이게('적절히 잘 분류된' 시연용). 결정적.
    # (실제 테스트셋은 저위험 다수라 균등 샘플 시 고위험에 시선이 쏠림 → 의도적 균형)
    rng = np.random.default_rng(42)
    target = {"low": 50, "med": 25, "high": 25}
    bands = {
        "low": window[window["risk"] < 0.4],
        "med": window[(window["risk"] >= 0.4) & (window["risk"] < 0.7)],
        "high": window[window["risk"] >= 0.7],
    }
    picks = []
    for band, t in target.items():
        pool = bands[band]
        k = min(t, len(pool))
        if k > 0:
            sel = rng.choice(len(pool), size=k, replace=False)
            picks.append(pool.iloc[sel])
    sample = pd.concat(picks).sort_values("arr").reset_index(drop=True)

    records = []
    for i, r in sample.iterrows():
        risk_v = round(float(r["risk"]), 4)
        flexi = risk_v >= THRESHOLD
        disc = discount_for(risk_v)
        nights = int(r["stays_in_weekend_nights"]) + int(r["stays_in_week_nights"])
        nights = max(1, nights)
        adults = max(1, int(r["adults"]))
        arr = r["arr"]
        lead = int(r["lead_time"])
        created = arr - pd.Timedelta(days=lead)
        country = str(r["country"]) if pd.notna(r["country"]) else "Other"
        records.append({
            "booking_id": f"BK-{(i + 1):03d}{str(country)[:2].upper()}",
            "hotel": str(r["hotel"]),
            "country": country,
            "arrival_date": arr.strftime("%Y-%m-%d"),
            "nights": nights,
            "adults": adults,
            "risk_score": risk_v,
            "flexi_recommended": flexi,
            "discount_rate": disc,
            "status": status_for(risk_v, flexi),
            "created_at": created.strftime("%Y-%m-%dT%H:%M:%S"),
            "lead_time": lead,
            "adr": round(float(r["adr"]), 2),
        })

    hi = sum(1 for x in records if x["risk_score"] >= 0.7)
    md = sum(1 for x in records if 0.4 <= x["risk_score"] < 0.7)
    lo = sum(1 for x in records if x["risk_score"] < 0.4)
    flexi_n = sum(1 for x in records if x["flexi_recommended"])
    out = {
        "meta": {
            "as_of": args.as_of,
            "horizon_days": args.horizon,
            "n": len(records),
            "n_window": int(n_window),
            "high_risk": hi,
            "med_risk": md,
            "low_risk": lo,
            "flexi_routed": flexi_n,
            "threshold": THRESHOLD,
            "source": "data/test.csv (캐글 test split) + results/model_final.pkl(LightGBM) 사전 채점",
            "note": "위험대 균형 시연 샘플(저/중/고). risk는 사전계산(point-in-time 재현 아님). created_at=arrival-lead_time(실제).",
        },
        "bookings": records,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"OK → {args.out}")
    print(f"as-of {args.as_of} +{args.horizon}d · window {n_window} → 샘플 {len(records)}건 "
          f"(고위험 {hi} / Flexi {flexi_n})")


if __name__ == "__main__":
    main()
