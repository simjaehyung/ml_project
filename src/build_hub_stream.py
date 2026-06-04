"""
src/build_hub_stream.py
DSS "데이터 인프라 허브" 실시간 수집 시각화용 스트림 데이터 생성.

다른 방(프론트)이 캐글 예약을 시간순으로 흘려보내며 수집·분류를 보여주려면
사전 계산된 위험점수 + 예약일 정렬 스트림이 필요하다. 이 스크립트가 그걸 만든다.

입력:
  data/train_processed.csv, data/test_processed.csv   (전처리 산출물)
  results/model_final.pkl                             (LightGBM 최종 모델)
출력:
  hotel-dss-app/public/hub_stream.json
    {
      "meta":   { disclaimer, n, date_range, test_split_note, growth_curve },
      "stream": [ {d, arr, wk, country, channel, hotel, lead, adr,
                   risk, color, canceled, split}, ... ]   # 예약일(d) 오름차순
    }

정직성(슬라이드 각주):
  - risk = 최종 모델로 사전 계산 → point-in-time 추론 재현 아님. "수집 시연"용.
  - country = country_grouped (top10 실제코드 + 'Other'). 원국적은 전처리에서 그룹핑됨.
  - booking_date(d) = arrival_date − lead_time.
  - split=='test'(2017-03~08)는 수집되나 평가용으로 학습 제외(고정 평가셋).

실행:
  python src/build_hub_stream.py                              # 기존 동작(풀버전)
  python src/build_hub_stream.py --from 2015-01-01 \
      --sample 40000 --out hotel-dss-app/public/hub_stream_lite.json

CLI 옵션(옵션 없으면 기존 동작 100% 동일):
  --sample N   stream을 균등 다운샘플 N건(시간순 보존). meta에 n_full·n_sample 기록.
  --from DATE  예약일(d) < DATE 레코드 제외(희소 초기연도 정리, 예 2015-01-01).
  --out PATH   출력 경로 지정(기본 hotel-dss-app/public/hub_stream.json).
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

import argparse
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
OUT = ROOT / "hotel-dss-app" / "public" / "hub_stream.json"

CAT_COLS = ["hotel", "meal", "market_segment", "distribution_channel",
            "reserved_room_type", "customer_type", "country_grouped"]


def load_processed() -> pd.DataFrame:
    tr_p, te_p = DATA / "train_processed.csv", DATA / "test_processed.csv"
    if not tr_p.exists() or not te_p.exists():
        raise SystemExit(
            f"✗ 전처리 산출물 없음: {tr_p} / {te_p}\n"
            f"  먼저 'python src/preprocessing_pipeline.py' 실행 (train/test.csv 필요)."
        )
    tr = pd.read_csv(tr_p); tr["split"] = "train"
    te = pd.read_csv(te_p); te["split"] = "test"
    return pd.concat([tr, te], ignore_index=True)


def compute_risk(df: pd.DataFrame) -> np.ndarray:
    mp = RESULTS / "model_final.pkl"
    if not mp.exists():
        raise SystemExit(f"✗ 모델 없음: {mp}")
    model = joblib.load(mp)

    X = pd.get_dummies(df.drop(columns=["split"], errors="ignore"), columns=CAT_COLS)
    # 모델 학습 시 피처 이름/순서에 정확히 맞춤 (is_canceled·_wk 등은 자동 제외)
    feats = getattr(model, "feature_name_", None)
    if feats is None and hasattr(model, "booster_"):
        feats = list(model.booster_.feature_name())
    if feats is not None:
        X = X.reindex(columns=feats, fill_value=0)
    else:  # 모델이 feature_name을 노출 안 하면 라벨만 제거하고 진행
        X = X.drop(columns=["is_canceled"], errors="ignore")
    return model.predict_proba(X)[:, 1]


def arrival_series(df: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(
        dict(year=df["arrival_date_year"],
             month=df["arrival_date_month"],
             day=df["arrival_date_day_of_month"]),
        errors="coerce",
    )


def parse_args():
    p = argparse.ArgumentParser(
        description="DSS 허브 수집 스트림(hub_stream.json) 생성. "
                    "옵션 없으면 기존 동작 100% 동일."
    )
    p.add_argument("--sample", type=int, default=None, metavar="N",
                   help="stream을 균등 다운샘플 N건(시간순 보존). meta에 n_full·n_sample 기록.")
    p.add_argument("--from", dest="from_date", type=str, default=None, metavar="DATE",
                   help="예약일(d) < DATE 레코드 제외(YYYY-MM-DD, 예 2015-01-01).")
    p.add_argument("--out", type=str, default=None, metavar="PATH",
                   help="출력 경로 지정(기본 hotel-dss-app/public/hub_stream.json).")
    return p.parse_args()


def main():
    args = parse_args()
    out_path = Path(args.out) if args.out else OUT

    df = load_processed()
    print(f"[로드] {len(df):,}행 (train+test)")

    risk = compute_risk(df)
    print(f"[risk] 계산 완료 — 평균 {risk.mean():.3f}")

    arr = arrival_series(df)
    book = arr - pd.to_timedelta(df["lead_time"].clip(lower=0), unit="D")
    y0 = int(df["arrival_date_year"].min())
    wk = (df["arrival_date_year"] - y0) * 53 + df["arrival_date_week_number"]

    out = pd.DataFrame({
        "d":        book.dt.strftime("%Y-%m-%d"),      # 예약일(수집 시점)
        "arr":      arr.dt.strftime("%Y-%m-%d"),       # 도착일
        "wk":       wk.astype("Int64"),                # 절대주차(성장곡선 동기용)
        "country":  df["country_grouped"].astype(str),
        "channel":  df["distribution_channel"].astype(str),
        "hotel":    df["hotel"].astype(str),
        "lead":     df["lead_time"].astype(int),
        "adr":      df["adr"].round(0).astype(int),
        "risk":     np.round(risk, 3),
        "canceled": df["is_canceled"].astype(int),
        "split":    df["split"],
    }).dropna(subset=["d"]).sort_values("d", kind="stable").reset_index(drop=True)

    out["color"] = pd.cut(out["risk"], [-0.01, 0.4, 0.7, 1.01],
                          labels=["low", "med", "high"]).astype(str)

    # ── CLI 필터/샘플 (옵션 없으면 무변화) ──────────────────────────
    # --from: 예약일(d) < DATE 레코드 제외 (희소 초기연도 정리)
    if args.from_date:
        before = len(out)
        out = out[out["d"] >= args.from_date].reset_index(drop=True)
        print(f"[--from {args.from_date}] {before:,} → {len(out):,}건 "
              f"({before - len(out):,}건 제외)")

    n_full = int(len(out))  # 필터 적용 후·샘플 적용 전 전체 건수

    # --sample: 시간순 보존 균등 다운샘플 N건
    sampled = False
    if args.sample is not None and args.sample < n_full:
        idx = np.linspace(0, n_full - 1, num=args.sample).round().astype(int)
        idx = np.unique(idx)  # 반올림 충돌 제거(드물게 N보다 소폭 작아질 수 있음)
        out = out.iloc[idx].reset_index(drop=True)
        sampled = True
        print(f"[--sample {args.sample}] 균등 다운샘플(시간순 보존) → {len(out):,}건")
    elif args.sample is not None:
        print(f"[--sample {args.sample}] 전체({n_full:,}) 이하 — 다운샘플 생략")

    meta = {
        "disclaimer": "risk는 최종 LightGBM 모델로 사전 계산(point-in-time 아님). 수집 시연용.",
        "n": int(len(out)),
        "date_range": [out["d"].min(), out["d"].max()],
        "test_split_note": "split=='test'(2017-03~08)는 수집되나 평가용으로 학습 제외(고정 평가셋).",
        "growth_curve": "results/growth_curve_agg.csv 와 'wk'로 동기화",
        "fields": "d=예약일 arr=도착일 wk=절대주차 risk=0~1 color=low/med/high canceled=실제라벨 split=train|test",
    }
    # 정직성 meta — 필터/샘플 시 원본수·샘플수 명시
    if args.from_date:
        meta["from_date_filter"] = args.from_date
    if sampled:
        meta["n_full"] = n_full          # 필터 적용 후 전체 건수(샘플 전)
        meta["n_sample"] = int(len(out))  # 실제 샘플 건수
        meta["sampling"] = (
            f"시간순 보존 균등 다운샘플: 전체 {n_full:,}건에서 약 {args.sample:,}건 "
            f"(np.linspace 균등 인덱스). 표시·렌더 부담 경감용, 분포 근사."
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "stream": out.to_dict("records")},
                  f, ensure_ascii=False, separators=(",", ":"))

    size_mb = out_path.stat().st_size / 1e6
    print(f"[완료] {out_path}  ({len(out):,}건, {size_mb:.1f}MB)")
    print(f"  기간 {meta['date_range'][0]} ~ {meta['date_range'][1]}")
    print(f"  위험 분포 — high {(out.color=='high').sum():,} / med {(out.color=='med').sum():,} / low {(out.color=='low').sum():,}")
    if size_mb > 15:
        print("  ⚠️ 15MB 초과 — 필요시 stride 샘플링 고려(프론트 렌더 부담).")


if __name__ == "__main__":
    main()
