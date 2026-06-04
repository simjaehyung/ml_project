"""
Hotel DSS LLM 시뮬레이션 실행 스크립트

5명의 페르소나 에이전트가 PMS를 통해 예약을 생성한다.
각 에이전트의 예약은 자동으로 DSS에 연동되어 위험도가 분석된다.

사용법:
    python -m llm_sim.run_simulation
    python -m llm_sim.run_simulation --agents ana james  (특정 에이전트만)
    python -m llm_sim.run_simulation --rounds 2          (각 에이전트 2번씩)

준비 사항:
    1. FastAPI DSS 실행:  uvicorn api.main:app --port 8001 --reload
    2. PMS 서버 실행:     uvicorn app_pms.pms_mock:app --port 3001 --reload
    3. ANTHROPIC_API_KEY 환경 변수 설정
"""

import argparse
import os
import sys
import time
from pathlib import Path

# ── .env 자동 로드 (의존성 없는 최소 파서) ──────────────────────────────
#    프로젝트 루트의 .env 에 ANTHROPIC_API_KEY 를 넣어두면 자동으로 환경변수에 올린다.
#    .env 는 .gitignore 로 막혀 있어 키가 git에 노출되지 않는다.
_ENV_FILE = Path(__file__).parent.parent / ".env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _val = _line.split("=", 1)
            _val = _val.strip().strip('"').strip("'")
            if _val:
                os.environ.setdefault(_key.strip(), _val)

from llm_sim.agents import run_agent
from llm_sim.personas import PERSONAS, PERSONA_BY_ID


def check_servers() -> bool:
    """DSS, PMS 서버 상태 확인"""
    import httpx
    servers = [
        ("FastAPI DSS", "http://localhost:8001/api/v1/dashboard/summary"),
        ("PMS 서버",    "http://localhost:3001/admin/stats"),
    ]
    all_ok = True
    for name, url in servers:
        try:
            r = httpx.get(url, timeout=3.0)
            status = "✓ OK" if r.status_code == 200 else f"✗ {r.status_code}"
            print(f"  {name}: {status} ({url})")
            if r.status_code != 200:
                all_ok = False
        except Exception as e:
            print(f"  {name}: ✗ 연결 실패 — {e}")
            all_ok = False
    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Hotel DSS LLM 에이전트 시뮬레이션")
    parser.add_argument(
        "--agents",
        nargs="+",
        choices=["ana", "james", "marie", "thomas", "paulo", "all"],
        default=["all"],
        help="실행할 에이전트 (기본: all)"
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=1,
        help="각 에이전트 반복 횟수 (기본: 1)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="에이전트 간 대기 시간 초 (기본: 2.0)"
    )
    args = parser.parse_args()

    # API 키 확인
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("✗ ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    print("\n" + "="*60)
    print("  Hotel DSS — LLM 에이전트 시뮬레이션")
    print("="*60)

    # 서버 상태 확인
    print("\n서버 상태 확인...")
    if not check_servers():
        print("\n⚠️  일부 서버가 실행되지 않았습니다.")
        print("   계속 진행하시겠습니까? (y/N): ", end="")
        if input().strip().lower() != "y":
            sys.exit(1)

    # 실행할 에이전트 선택
    if "all" in args.agents:
        selected_personas = PERSONAS
    else:
        id_map = {
            "ana": "guest-ana",
            "james": "guest-james",
            "marie": "guest-marie",
            "thomas": "guest-thomas",
            "paulo": "guest-paulo",
        }
        selected_personas = [PERSONA_BY_ID[id_map[a]] for a in args.agents if id_map[a] in PERSONA_BY_ID]

    total = len(selected_personas) * args.rounds
    print(f"\n실행 계획: {len(selected_personas)}명 × {args.rounds}회 = {total}건")
    print(f"모델: claude-haiku-4-5-20251001 (빠른 실행, 비용 최소화)")
    print(f"PMS UI: http://localhost:3000/pms")
    print(f"DSS UI: http://localhost:3000/dashboard\n")

    results = []
    for round_i in range(args.rounds):
        if args.rounds > 1:
            print(f"\n{'─'*60}")
            print(f"  Round {round_i + 1} / {args.rounds}")
            print(f"{'─'*60}")

        for persona in selected_personas:
            try:
                result = run_agent(persona)
                if result:
                    results.append({
                        "persona": persona["name"],
                        "confirmation": result.get("confirmation_number"),
                        "pricing": result.get("pricing_type"),
                        "total": result.get("total_amount"),
                    })
            except Exception as e:
                print(f"\n  ✗ {persona['name']} 에이전트 오류: {e}")

            if args.delay > 0:
                time.sleep(args.delay)

    # 최종 요약
    print(f"\n\n{'='*60}")
    print(f"  시뮬레이션 완료 — {len(results)}/{total}건 성공")
    print(f"{'='*60}")
    for r in results:
        disc_label = "Flexi ✓" if r["pricing"] == "Flexi Rate" else "Standard"
        print(f"  {r['persona']:<18} {r['confirmation']:<14} {disc_label}  €{r['total']:.0f}")

    flexi_count = sum(1 for r in results if r["pricing"] == "Flexi Rate")
    print(f"\n  Flexi 라우팅: {flexi_count}/{len(results)}건")
    print(f"  DSS 대시보드에서 위험도 분석 확인: http://localhost:3000/dashboard")
    print(f"  PMS 예약 현황 확인: http://localhost:3000/pms")


if __name__ == "__main__":
    main()
