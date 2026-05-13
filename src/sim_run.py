"""
sim_run.py
메인 실행 오케스트레이터

1. LightGBM 모델 로드 + 테스트셋 취소 확률 계산
2. 고위험 예약 N건 샘플링 (cancel_prob >= min_prob)
3. vLLM 에이전트 배치 실행 (멀티스레드)
4. results/sim_responses.jsonl 저장

실행 예시 (학교 서버에서):
  python src/sim_run.py --n 500 --workers 16
  python src/sim_run.py --n 200 --dry-run   # LLM 없이 더미 응답으로 파이프라인 검증
"""

import argparse
import json
import pickle
import random
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from tqdm import tqdm

ROOT    = Path(__file__).resolve().parent.parent


def _compute_discount(cancel_prob: float) -> float:
    raw = 5.0 + (cancel_prob - 0.5) * 26.0
    return round(max(5.0, min(18.0, raw)), 1)
DATA    = ROOT / "data"
RESULTS = ROOT / "results"

CAT_COLS = [
    "hotel", "meal", "market_segment", "distribution_channel",
    "reserved_room_type", "customer_type", "country_grouped",
]


# ── 모델 + 데이터 로드 ────────────────────────────────────────────────────────
def load_model_and_data() -> pd.DataFrame:
    with open(RESULTS / "model_final.pkl", "rb") as f:
        model = pickle.load(f)

    raw       = pd.read_csv(DATA / "test.csv")
    processed = pd.read_csv(DATA / "test_processed.csv")
    train_p   = pd.read_csv(DATA / "train_processed.csv")

    # OHE (train 컬럼 기준으로 정렬 — leakage 방지)
    train_e = pd.get_dummies(train_p,   columns=CAT_COLS)
    test_e  = pd.get_dummies(processed, columns=CAT_COLS)
    test_e  = test_e.reindex(columns=train_e.columns, fill_value=0)

    X_te         = test_e.drop("is_canceled", axis=1)
    cancel_probs = model.predict_proba(X_te)[:, 1]

    # 원본 피처에 확률 병합 (페르소나 생성용)
    n = min(len(raw), len(cancel_probs))
    df = raw.iloc[:n].copy().reset_index(drop=True)
    df["cancel_prob"] = cancel_probs[:n]
    return df


# ── 고위험 샘플링 ─────────────────────────────────────────────────────────────
def sample_high_risk(df: pd.DataFrame, min_prob: float, n: int, seed: int = 42) -> pd.DataFrame:
    pool = df[df["cancel_prob"] >= min_prob]
    n    = min(n, len(pool))
    return pool.sample(n=n, random_state=seed).reset_index(drop=True)


# ── 더미 에이전트 (dry-run 전용) ──────────────────────────────────────────────
def _dummy_decide(row: dict, cancel_prob: float) -> dict:
    choices  = ["ACCEPT_FLEXI", "DECLINE_FLEXI", "CANCEL"]
    weights  = [0.45, 0.40, 0.15]
    decision = random.choices(choices, weights=weights, k=1)[0]
    return {
        "decision":    decision,
        "reason":      "dry-run dummy response",
        "cancel_prob": round(cancel_prob, 4),
        "discount":    _compute_discount(cancel_prob),
        "raw_text":    "[dry-run]",
    }


# ── 배치 실행 (멀티스레드) ────────────────────────────────────────────────────
def run_batch(
    sample:      pd.DataFrame,
    agent,                          # GuestAgent 또는 None(dry-run)
    max_workers: int = 8,
    dry_run:     bool = False,
) -> list[dict]:
    results = [None] * len(sample)

    def call(i: int, row: pd.Series):
        try:
            cp = float(row["cancel_prob"])
            if dry_run:
                res = _dummy_decide(row.to_dict(), cp)
            else:
                res = agent.decide(row.to_dict(), cp)
            res["_idx"] = i
            return i, res
        except Exception as e:
            cp = float(row.get("cancel_prob", 0))
            return i, {
                "_idx":        i,
                "decision":    "DECLINE_FLEXI",
                "reason":      f"error: {e}",
                "cancel_prob": cp,
                "discount":    _compute_discount(cp),
                "raw_text":    "",
            }

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(call, i, row): i
                   for i, row in sample.iterrows()}
        for fut in tqdm(as_completed(futures),
                        total=len(futures),
                        desc="에이전트 실행"):
            i, res = fut.result()
            results[i] = res

    return results


# ── 메인 ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Flexi LLM 에이전트 시뮬레이션")
    parser.add_argument("--n",        type=int,   default=99999,
                        help="시뮬레이션 에이전트 수 (기본: 고위험 풀 전체)")
    parser.add_argument("--min-prob", type=float, default=0.50,
                        help="샘플링 최소 취소 확률 (기본 0.50)")
    parser.add_argument("--workers",  type=int,   default=16,
                        help="병렬 스레드 수 (기본 16)")
    parser.add_argument("--base-url", type=str,
                        default="http://localhost:8000/v1")
    parser.add_argument("--model",    type=str,
                        default="Qwen/Qwen2.5-14B-Instruct")
    parser.add_argument("--seed",     type=int,   default=42)
    parser.add_argument("--out",      type=str,
                        default="results/sim_responses.jsonl")
    parser.add_argument("--dry-run",  action="store_true",
                        help="LLM 없이 더미 응답으로 파이프라인 검증")
    args = parser.parse_args()

    print("=" * 60)
    print("Flexi LLM 에이전트 시뮬레이션")
    print("=" * 60)

    # 1. 데이터 로드
    print("\n▶ 모델 + 데이터 로드...")
    df = load_model_and_data()
    n_high = (df["cancel_prob"] >= args.min_prob).sum()
    print(f"  테스트셋:    {len(df):,}행")
    print(f"  고위험 풀:   {n_high:,}건 (cancel_prob ≥ {args.min_prob})")

    # 2. 샘플링
    sample = sample_high_risk(df, args.min_prob, args.n, args.seed)
    print(f"  샘플:        {len(sample)}건")
    print(f"  cancel_prob: {sample['cancel_prob'].min():.3f} ~ "
          f"{sample['cancel_prob'].max():.3f}  "
          f"(mean {sample['cancel_prob'].mean():.3f})")

    # 3. 에이전트 초기화
    agent = None
    if not args.dry_run:
        from sim_agent import GuestAgent
        print(f"\n▶ vLLM 연결: {args.base_url}  모델: {args.model}")
        agent = GuestAgent(base_url=args.base_url, model=args.model)
    else:
        print("\n▶ [dry-run 모드] LLM 호출 없이 더미 응답 사용")

    # 4. 배치 실행
    print(f"\n▶ 에이전트 실행 ({args.workers} 스레드)...")
    t0      = time.time()
    raw_res = run_batch(sample, agent,
                        max_workers=args.workers,
                        dry_run=args.dry_run)
    elapsed = time.time() - t0
    n_done  = sum(1 for r in raw_res if r is not None)
    print(f"  완료: {elapsed:.1f}초 | {elapsed / n_done:.2f}s/건")

    # 5. 피처 병합 + 저장
    out_path = ROOT / args.out
    records  = []
    for i, res in enumerate(raw_res):
        if res is None:
            continue
        row = sample.iloc[i].to_dict()
        row.update(res)
        records.append(row)

    with open(out_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    print(f"\n▶ 저장: {out_path}  ({len(records)}건)")

    # 6. 요약
    decisions = [r["decision"] for r in raw_res if r]
    cnt       = Counter(decisions)
    print("\n결과 요약:")
    print(f"  {'결정':<18} {'건수':>5}  {'비율':>6}")
    print(f"  {'-'*32}")
    for k in ("ACCEPT_FLEXI", "DECLINE_FLEXI", "CANCEL"):
        v = cnt.get(k, 0)
        print(f"  {k:<18} {v:>5}건  {v / len(decisions) * 100:>5.1f}%")
    print(f"\n다음 단계: python src/sim_analyze.py")


if __name__ == "__main__":
    main()
