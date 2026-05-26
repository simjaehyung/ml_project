"""
src/sim_extra.py
보완 실험 2종 — 추가 API 비용 최소화 설계

[실험 1] D 아키타입 임계값 정밀화
  기존: €29(0%) → €46(100%)  ← 갭 너무 큼, 로지스틱 추정에만 의존
  추가: €33, €37, €42  (×40회 = 120 calls)
  목적: 50% 수락 임계값 실측값으로 확인

[실험 2] B 아키타입 Ceiling Artifact 검증
  기존: €80(100%) → €114(0%)  ← €114 = R2 예산 상한과 동일, 구조적 블록
  추가: €91, €99, €106 (×40회 = 120 calls)  ← 천장(€114) 아래 구간만
  목적: 0%가 진짜 거절인지 Ceiling 버그인지 구분

비용 추정: ~$0.8 / 시간: ~15분
총 API 호출: 240회 (×평균 1.3라운드)

실행:
  python src/sim_extra.py --exp all   # 둘 다
  python src/sim_extra.py --exp d     # D 임계값만 (~$0.3)
  python src/sim_extra.py --exp b     # B 검증만  (~$0.3)
"""

import argparse
import json
import time
from pathlib import Path

from tqdm import tqdm

# sim_overbooking에서 핵심 함수 재사용
from sim_overbooking import (
    ARCHETYPES,
    build_tasks,
    make_llm_client,
    make_summary,
    print_report,
    run_batch,
)

ROOT    = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

# ── 실험별 설정 ───────────────────────────────────────────────────────────────
# D: adr=55, nights=2 → room_cost=110
#   기존 포인트: 0.26(€29), 0.42(€46), 0.60(€66), 0.74(€81), 0.90(€99)
#   새 포인트:  0.30(€33), 0.34(€37), 0.38(€42)  ← €29↔€46 사이
EXP_D = {
    "arch_keys":  ["D"],
    "mults":      [0.30, 0.34, 0.38],
    "n_repeats":  40,
    "out_stem":   "walk_sim_D_threshold",
    "label":      "D 임계값 정밀화 (€29-€46 사이 3포인트)",
}

# B: adr=95, nights=2 → room_cost=190, 천장=190×0.60=€114
#   기존 포인트: €49(65%), €80(100%), €114(0%)←천장, €141(0%), €171(0%)
#   새 포인트:  0.48(€91), 0.52(€99), 0.56(€106) ← 모두 €114 미만
EXP_B = {
    "arch_keys":  ["B"],
    "mults":      [0.48, 0.52, 0.56],
    "n_repeats":  40,
    "out_stem":   "walk_sim_B_fixed",
    "label":      "B Ceiling Artifact 검증 (€80-€114 사이, 천장 이하만)",
}


def run_experiment(exp: dict, llm_call, workers: int):
    print(f"\n{'='*60}")
    print(f"실험: {exp['label']}")
    print(f"  아키타입: {exp['arch_keys']}")

    # 실제 오퍼 금액 미리 계산해서 출력
    arch_key = exp["arch_keys"][0]
    arch = ARCHETYPES[arch_key]
    base = arch["adr"] * arch["nights"]
    offers = [round(base * m, 0) for m in exp["mults"]]
    print(f"  오퍼 구간: {[f'€{o:.0f}' for o in offers]}")
    print(f"  반복: {exp['n_repeats']}회/구간  총 {len(offers)*exp['n_repeats']}회")
    print(f"{'='*60}")

    tasks = build_tasks(exp["arch_keys"], exp["mults"], exp["n_repeats"])

    t0 = time.time()
    records = run_batch(tasks, llm_call, max_workers=workers)
    elapsed = time.time() - t0
    print(f"\n  완료: {elapsed:.1f}초 ({elapsed/max(len(records),1):.2f}s/건)")

    # 저장
    out_jsonl = RESULTS / f"{exp['out_stem']}.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    print(f"> 원본 저장: {out_jsonl}")

    summary = make_summary(records)
    out_csv = RESULTS / f"{exp['out_stem']}_summary.csv"
    summary.to_csv(out_csv, index=False)
    print(f"> 요약 CSV : {out_csv}")

    print_report(records, summary)
    return records, summary


def main():
    parser = argparse.ArgumentParser(description="Walk 시뮬레이션 보완 실험")
    parser.add_argument(
        "--exp", choices=["all", "d", "b"], default="all",
        help="실험 선택: all(기본) / d(D 임계값) / b(B 검증)",
    )
    parser.add_argument(
        "--model", choices=["anthropic", "vllm"], default="anthropic",
        help="LLM 모델 (기본: anthropic = Sonnet 4.6)",
    )
    parser.add_argument(
        "--workers", type=int, default=2,
        help="병렬 스레드 수 (Anthropic API rate limit 고려, 기본 2)",
    )
    parser.add_argument(
        "--base-url", type=str, default="http://localhost:8000/v1",
    )
    args = parser.parse_args()

    print(f"\n모델: {args.model}  스레드: {args.workers}")
    llm_call = make_llm_client(args.model, args.base_url, model_name=None)

    if args.exp in ("all", "d"):
        run_experiment(EXP_D, llm_call, args.workers)

    if args.exp in ("all", "b"):
        run_experiment(EXP_B, llm_call, args.workers)

    print("\n\n다음 단계:")
    print("  python src/sim_walk_visualize_v2.py  (그래프 업데이트)")


if __name__ == "__main__":
    main()
