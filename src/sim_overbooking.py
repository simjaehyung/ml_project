"""
sim_overbooking.py
오버부킹 Walk 보상 협상 시뮬레이션 (design_12 v3 / design_13 v2)

구조:
  Hotel Agent (규칙 기반, LLM 없음) × Customer Agent (LLM)
  5 아키타입 × 5 보상 구간 × 40회 = 1,000회

실행 예시:
  # 파이프라인 검증 (LLM 없음)
  python src/sim_overbooking.py --dry-run

  # 파일럿 60회 (A·D 아키타입 × 3구간 × 10회)
  python src/sim_overbooking.py --pilot --dry-run
  python src/sim_overbooking.py --pilot --model vllm

  # 전체 1,000회 — Qwen2.5-14B 로컬 (학교 서버, 권장)
  python src/sim_overbooking.py --model vllm --workers 8

  # 전체 1,000회 — Claude Sonnet 4.6 API (폴백)
  python src/sim_overbooking.py --model anthropic --workers 2
"""

import argparse
import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from tqdm import tqdm

ROOT    = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)


# ── 아키타입 정의 (design_12 v3 Table) ───────────────────────────────────────
# 모든 피처는 표준 PMS / Kaggle 예약 데이터에서 직접 수집 가능.
ARCHETYPES: dict[str, dict] = {
    "A": {
        "label": "Business Solo",
        "description": (
            "A business traveler on a corporate account, traveling alone. "
            "Stays 1-2 nights. Values reliability and efficiency over price. "
            "Accustomed to last-minute plan changes."
        ),
        "adr": 120.0,
        "nights": 2,
        "adults": 1,
        "children": 0,
        "meal": "BB",
        "market_segment": "Corporate",
        "special_requests": 0,
        "walk_difficulty": "low",
    },
    "B": {
        "label": "Leisure Couple",
        "description": (
            "A couple on a leisure trip booked via an online travel agency. "
            "Weekend stay at a mid-range rate. Values the experience but is price-aware."
        ),
        "adr": 95.0,
        "nights": 2,
        "adults": 2,
        "children": 0,
        "meal": "BB",
        "market_segment": "Online TA",
        "special_requests": 1,
        "walk_difficulty": "medium",
    },
    "C": {
        "label": "Family",
        "description": (
            "A family with two children on a planned vacation. Half-board meal plan, "
            "long stay of 5 nights, 3 special requests (cot, connecting rooms, etc.). "
            "Changing hotels with children at check-in is extremely disruptive."
        ),
        "adr": 110.0,
        "nights": 5,
        "adults": 2,
        "children": 2,
        "meal": "HB",
        "market_segment": "Direct",
        "special_requests": 3,
        "walk_difficulty": "high",
    },
    "D": {
        "label": "Budget OTA",
        "description": (
            "A price-conscious solo traveler who booked via an online travel agency "
            "at a low nightly rate. No special requests. Primarily motivated by price — "
            "a higher compensation offer is likely to be accepted."
        ),
        "adr": 55.0,
        "nights": 2,
        "adults": 1,
        "children": 0,
        "meal": "SC",
        "market_segment": "Online TA",
        "special_requests": 0,
        "walk_difficulty": "low",
    },
    "E": {
        "label": "Group",
        "description": (
            "A group booking coordinator managing 12 guests. "
            "Changing hotels means coordinating transport and communication for everyone. "
            "Negotiates on behalf of the group — requires a substantial offer."
        ),
        "adr": 85.0,
        "nights": 3,
        "adults": 12,
        "children": 0,
        "meal": "BB",
        "market_segment": "Groups",
        "special_requests": 2,
        "walk_difficulty": "very_high",
    },
}

# 보상 구간: ADR × nights 기준 배수 (design_12: 구간1~5)
OFFER_MULTIPLIERS = [0.26, 0.42, 0.60, 0.74, 0.90]

# ── Hotel Agent 규칙 (LLM 없음) ──────────────────────────────────────────────
INITIAL_OFFER_RATIO  = 0.30   # 초기 오퍼 = ADR × nights × 0.30
BUDGET_CEILING_RATIO = 0.60   # 예산 상한 = ADR × nights × 0.60
ROUND2_ADJUST        = 0.85   # Round2 = min(counter × 0.85, 예산 상한)


def hotel_initial_offer(adr: float, nights: int) -> float:
    return round(adr * nights * INITIAL_OFFER_RATIO, 0)


def hotel_round2_offer(counter: float, adr: float, nights: int) -> float:
    ceiling = adr * nights * BUDGET_CEILING_RATIO
    return round(min(counter * ROUND2_ADJUST, ceiling), 0)


# ── Customer Agent 프롬프트 빌더 (design_13 v2) ───────────────────────────────

def _party_str(a: dict) -> str:
    s = f"{a['adults']} adult(s)"
    if a["children"] > 0:
        s += f" + {a['children']} child(ren)"
    return s


def build_round1_prompt(arch: dict, offer_amount: float) -> tuple[str, str]:
    """Round 1: ACCEPT / COUNTER / REJECT"""
    total = arch["adr"] * arch["nights"]

    system = (
        "You are simulating a real hotel guest responding to an overbooking situation. "
        "Respond ONLY in valid JSON. No other text."
    )
    user = f"""\
## WHO YOU ARE
{arch['description']}
Party: {_party_str(arch)}
Booking channel: {arch['market_segment']}
Nights: {arch['nights']} × €{arch['adr']:.0f}/night = €{total:.0f} total
Meal plan: {arch['meal']}
Special requests on record: {arch['special_requests']}

## SITUATION
You have just arrived at the hotel after travelling.
The hotel informs you that your room is unavailable due to overbooking.

## THE HOTEL'S OFFER
The hotel offers €{offer_amount:.0f} compensation and will arrange
a comparable room (same star rating) at a nearby hotel, including transfer.

## YOUR DECISION
Respond ONLY in JSON. No other text.
{{"decision": "ACCEPT" or "COUNTER" or "REJECT", "counter_amount": number or null, "reason": "one sentence"}}"""

    return system, user


def build_round2_prompt(
    arch: dict,
    prev_offer: float,
    prev_counter: float | None,
    current_offer: float,
) -> tuple[str, str]:
    """Round 2: ACCEPT / REJECT only"""
    counter_line = (
        f"  Your counter-offer: €{prev_counter:.0f}" if prev_counter else ""
    )

    system = (
        "You are simulating a real hotel guest responding to an overbooking situation. "
        "Respond ONLY in valid JSON. No other text."
    )
    user = f"""\
## WHO YOU ARE
{arch['description']}
Party: {_party_str(arch)}
Nights: {arch['nights']} × €{arch['adr']:.0f}/night

## NEGOTIATION HISTORY
  Hotel's first offer: €{prev_offer:.0f}
  Your response: COUNTER{counter_line}
  Hotel's revised offer: €{current_offer:.0f}

## YOUR FINAL DECISION (accept or walk away)
Respond ONLY in JSON. No other text.
{{"decision": "ACCEPT" or "REJECT", "reason": "one sentence"}}"""

    return system, user


# ── JSON パーサー ─────────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict | None:
    m = re.search(r'\{[^{}]+\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return None


def parse_round1(text: str) -> dict:
    data = _extract_json(text)
    if data:
        dec = str(data.get("decision", "REJECT")).upper().strip()
        if dec not in ("ACCEPT", "COUNTER", "REJECT"):
            dec = "REJECT"
        counter = data.get("counter_amount")
        try:
            counter = float(counter) if counter is not None else None
        except (ValueError, TypeError):
            counter = None
        return {
            "decision":      dec,
            "counter_amount": counter,
            "reason":        str(data.get("reason", ""))[:200],
            "parse_ok":      True,
        }
    # 키워드 폴백
    t = text.upper()
    if "COUNTER" in t:
        return {"decision": "COUNTER", "counter_amount": None, "reason": "keyword-fallback", "parse_ok": False}
    if "ACCEPT" in t:
        return {"decision": "ACCEPT",  "counter_amount": None, "reason": "keyword-fallback", "parse_ok": False}
    return     {"decision": "REJECT",  "counter_amount": None, "reason": "parse-failed",     "parse_ok": False}


def parse_round2(text: str) -> dict:
    data = _extract_json(text)
    if data:
        dec = str(data.get("decision", "REJECT")).upper().strip()
        if dec not in ("ACCEPT", "REJECT"):
            dec = "REJECT"
        return {"decision": dec, "reason": str(data.get("reason", ""))[:200], "parse_ok": True}
    t = text.upper()
    if "ACCEPT" in t:
        return {"decision": "ACCEPT", "reason": "keyword-fallback", "parse_ok": False}
    return     {"decision": "REJECT", "reason": "parse-failed",     "parse_ok": False}


# ── LLM 클라이언트 팩토리 ─────────────────────────────────────────────────────
# 반환값: (system: str, user: str) -> str 형태의 callable

def make_llm_client(model_type: str, base_url: str, model_name: str | None):
    if model_type == "anthropic":
        import anthropic
        _client = anthropic.Anthropic()
        _model  = model_name or "claude-sonnet-4-6"

        def _call(system: str, user: str) -> str:
            # rate limit 발생 시 지수 백오프 재시도 (최대 3회)
            for attempt in range(4):
                try:
                    msg = _client.messages.create(
                        model=_model,
                        max_tokens=150,
                        temperature=0.3,
                        system=system,
                        messages=[{"role": "user", "content": user}],
                    )
                    return msg.content[0].text
                except anthropic.RateLimitError:
                    if attempt == 3:
                        raise
                    time.sleep(2 ** (attempt + 3))  # 8, 16, 32초
            return ""

        return _call

    else:  # vllm (default: Qwen2.5-14B)
        from openai import OpenAI
        _client = OpenAI(base_url=base_url, api_key="not-needed")
        _model  = model_name or "Qwen/Qwen2.5-14B-Instruct"

        def _call(system: str, user: str) -> str:
            resp = _client.chat.completions.create(
                model=_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                temperature=0.3,
                max_tokens=150,
            )
            return resp.choices[0].message.content or ""

        return _call


def _dry_run_call(_system: str, _user: str) -> str:
    """dry-run 전용 더미 응답 — LLM 없이 파이프라인 검증용"""
    choices = [
        '{"decision": "ACCEPT", "counter_amount": null, "reason": "dry-run accept"}',
        '{"decision": "COUNTER", "counter_amount": 120, "reason": "dry-run counter"}',
        '{"decision": "REJECT", "counter_amount": null, "reason": "dry-run reject"}',
    ]
    return random.choice(choices)


# ── 단일 협상 (2-round) ───────────────────────────────────────────────────────

def run_negotiation(
    arch_key:     str,
    arch:         dict,
    offer_amount: float,
    llm_call,
) -> dict:
    record = {
        "archetype":       arch_key,
        "archetype_label": arch["label"],
        "walk_difficulty": arch["walk_difficulty"],
        "adr":             arch["adr"],
        "nights":          arch["nights"],
        "initial_offer":   offer_amount,
    }

    # Round 1
    sys1, usr1 = build_round1_prompt(arch, offer_amount)
    raw1 = llm_call(sys1, usr1)
    r1   = parse_round1(raw1)

    record.update({
        "r1_decision":     r1["decision"],
        "r1_counter":      r1["counter_amount"],
        "r1_reason":       r1["reason"],
        "r1_parse_ok":     r1["parse_ok"],
        "r1_raw":          raw1[:400],
    })

    if r1["decision"] in ("ACCEPT", "REJECT"):
        record.update({
            "final_decision": r1["decision"],
            "final_offer":    offer_amount,
            "rounds":         1,
        })
        return record

    # Round 2 (COUNTER 진입)
    counter  = r1["counter_amount"] or round(offer_amount * 1.5, 0)
    r2_offer = hotel_round2_offer(counter, arch["adr"], arch["nights"])

    sys2, usr2 = build_round2_prompt(arch, offer_amount, r1["counter_amount"], r2_offer)
    raw2 = llm_call(sys2, usr2)
    r2   = parse_round2(raw2)

    record.update({
        "r2_offer":       r2_offer,
        "r2_decision":    r2["decision"],
        "r2_reason":      r2["reason"],
        "r2_parse_ok":    r2["parse_ok"],
        "r2_raw":         raw2[:400],
        "final_decision": r2["decision"],
        "final_offer":    r2_offer,
        "rounds":         2,
    })
    return record


# ── 실험 매트릭스 생성 ────────────────────────────────────────────────────────

def build_tasks(
    arch_keys:    list[str],
    offer_mults:  list[float],
    n_repeats:    int,
) -> list[tuple[str, float]]:
    tasks = []
    for key in arch_keys:
        a = ARCHETYPES[key]
        base = a["adr"] * a["nights"]
        for mult in offer_mults:
            offer = round(base * mult, 0)
            tasks.extend([(key, offer)] * n_repeats)
    return tasks


# ── 배치 실행 ─────────────────────────────────────────────────────────────────

def run_batch(
    tasks:       list[tuple[str, float]],
    llm_call,
    max_workers: int,
) -> list[dict]:
    results: list[dict] = []

    def worker(args: tuple[str, float]) -> dict:
        key, offer = args
        return run_negotiation(key, ARCHETYPES[key], offer, llm_call)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(worker, t): t for t in tasks}
        for fut in tqdm(as_completed(futures), total=len(futures), desc="협상 시뮬레이션"):
            try:
                results.append(fut.result())
            except Exception as e:
                key, offer = futures[fut]
                results.append({
                    "archetype": key, "initial_offer": offer,
                    "final_decision": "ERROR", "error": str(e),
                })
    return results


# ── 요약 분석 ─────────────────────────────────────────────────────────────────

def make_summary(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)

    # ERROR 행 제외 — rate limit/네트워크 오류는 수락률 계산에서 배제
    n_errors = (df["final_decision"] == "ERROR").sum()
    if n_errors > 0:
        print(f"\n[주의] ERROR {n_errors}건 제외 후 요약 계산 (유효 {len(df) - n_errors}건 기준)")
    valid = df[df["final_decision"] != "ERROR"].copy()

    if valid.empty:
        return pd.DataFrame(columns=[
            "archetype", "archetype_label", "walk_difficulty",
            "initial_offer", "n_runs", "accept_rate", "counter_mean", "r1_parse_ok",
        ])

    valid["accepted"] = (valid["final_decision"] == "ACCEPT").astype(int)

    summary = (
        valid.groupby(["archetype", "archetype_label", "walk_difficulty", "initial_offer"])
        .agg(
            n_runs        = ("accepted",    "count"),
            accept_rate   = ("accepted",    "mean"),
            counter_mean  = ("r1_counter",  "mean"),
            r1_parse_ok   = ("r1_parse_ok", "mean"),
        )
        .reset_index()
    )
    summary["accept_rate"]  = summary["accept_rate"].round(3)
    summary["counter_mean"] = summary["counter_mean"].round(0)
    summary["r1_parse_ok"]  = summary["r1_parse_ok"].round(3)
    return summary.sort_values(["archetype", "initial_offer"])


def print_report(records: list[dict], summary: pd.DataFrame):
    df = pd.DataFrame(records)
    total    = len(df)
    n_errors = (df["final_decision"] == "ERROR").sum()
    valid_df = df[df["final_decision"] != "ERROR"]
    parse_ok = valid_df.get("r1_parse_ok", pd.Series([True] * len(valid_df))).mean()

    print("\n" + "=" * 72)
    print("Walk 보상 협상 시뮬레이션 - 결과 리포트")
    print("=" * 72)
    print(f"총 협상 횟수 : {total:,}회")
    print(f"  유효 건수 : {len(valid_df):,}회")
    print(f"  ERROR     : {n_errors:,}건 ({n_errors/max(total,1):.1%})")
    print(f"JSON 파싱 성공률 (R1, 유효 기준) : {parse_ok:.1%}  (목표 95%+)")

    print(f"\n{'아키타입':<6} {'이름':<22} {'오퍼(€)':<10} {'건수':>5} {'수락률':>8}")
    print("-" * 60)
    for _, row in summary.iterrows():
        print(
            f"{row['archetype']:<6} {row['archetype_label']:<22} "
            f"€{row['initial_offer']:<9.0f} {row['n_runs']:>5} "
            f"{row['accept_rate']:>7.1%}"
        )

    print("\n[Claim 2 핵심 - 아키타입별 평균 수락률]")
    arch_avg = summary.groupby(["archetype", "archetype_label"])["accept_rate"].mean()
    for (key, label), rate in arch_avg.items():
        print(f"  {key}  {label:<22} : {rate:.1%}")

    # Claim 2: 가족(C)은 거부감이 높아 수락률이 낮고, Budget OTA(D)는 가격 민감 → 수락률 높아야 함
    # C_rate < D_rate = Claim 2 방어 가능
    print("\n방향성 확인 (Family < Budget OTA 이면 Claim 2 방어 가능):")
    rates = arch_avg.to_dict()
    for low_arch, high_arch in [
        (("C", "Family"), ("D", "Budget OTA")),
        (("C", "Family"), ("A", "Business Solo")),
    ]:
        low_rate  = rates.get(low_arch,  float("nan"))
        high_rate = rates.get(high_arch, float("nan"))
        direction = "[OK]" if low_rate < high_rate else "[NG]"
        print(f"  {direction}  {low_arch[1]} ({low_rate:.1%}) < {high_arch[1]} ({high_rate:.1%})")

    print("=" * 72)


# ── 서버 상태 점검 ───────────────────────────────────────────────────────────

def check_server(base_url: str = "http://localhost:8000") -> dict:
    """
    GPU / vLLM / 디스크 상태를 점검하고 권장 실행 파라미터를 출력한다.
    반환값을 main() 에서도 참조할 수 있도록 dict로 리턴.
    """
    import shutil
    import subprocess
    import urllib.request

    sep = "=" * 64
    print(sep)
    print("서버 환경 점검 (sim_overbooking.py --check)")
    print(sep)

    result = {
        "gpu_free_count":  0,
        "gpu_recommended": None,   # "0,1" 형식 또는 None
        "vllm_ready":      False,
        "vllm_model":      None,
        "disk_free_gb":    0,
        "recommended_cmd": None,
    }

    # ── GPU ──────────────────────────────────────────────────────────────────
    print("\n[GPU 상태]")
    try:
        out = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=index,name,memory.used,memory.free,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()

        free_indices = []
        for line in out.splitlines():
            idx, name, used, free, util = [x.strip() for x in line.split(",")]
            status = "FREE" if int(util) < 15 else "BUSY"
            tag    = " <-- 사용 가능" if status == "FREE" else ""
            print(f"  GPU {idx}: {name}  {used}MB/{int(used)+int(free)}MB  util={util}%  [{status}]{tag}")
            if status == "FREE":
                free_indices.append(idx)

        result["gpu_free_count"] = len(free_indices)
        if len(free_indices) >= 2:
            result["gpu_recommended"] = f"{free_indices[0]},{free_indices[1]}"
            print(f"\n  -> 권장 GPU: {result['gpu_recommended']} (2장 확보됨)")
        elif len(free_indices) == 1:
            print(f"\n  -> 주의: 여유 GPU 1장 ({free_indices[0]}) — tensor-parallel=1 필요 또는 대기")
        else:
            print("\n  -> 경고: 여유 GPU 없음 — 다른 작업 종료 후 재시도")

    except FileNotFoundError:
        print("  nvidia-smi 없음 (CPU 환경 또는 드라이버 미설치)")
    except Exception as e:
        print(f"  GPU 점검 오류: {e}")

    # ── vLLM 서버 ─────────────────────────────────────────────────────────────
    print("\n[vLLM 서버]")
    try:
        with urllib.request.urlopen(f"{base_url}/health", timeout=3) as resp:
            print(f"  /health -> HTTP {resp.status}  [정상]")
            result["vllm_ready"] = True
    except Exception:
        print(f"  {base_url}/health -> 응답 없음  [미실행]")

    if result["vllm_ready"]:
        try:
            with urllib.request.urlopen(f"{base_url}/v1/models", timeout=3) as resp:
                data = json.loads(resp.read())
                models = [m["id"] for m in data.get("data", [])]
                result["vllm_model"] = models[0] if models else None
                print(f"  로드된 모델: {models}")
        except Exception:
            pass

    # ── 디스크 ────────────────────────────────────────────────────────────────
    print("\n[디스크]")
    total, _, free = shutil.disk_usage(ROOT)
    result["disk_free_gb"] = free // (1024 ** 3)
    print(f"  {ROOT}  여유 {result['disk_free_gb']}GB / 전체 {total // (1024**3)}GB")
    if result["disk_free_gb"] < 2:
        print("  -> 경고: 디스크 여유 2GB 미만 — 결과 저장 실패 위험")

    # ── 패키지 ────────────────────────────────────────────────────────────────
    print("\n[패키지]")
    for pkg in ["vllm", "openai", "anthropic", "tqdm", "pandas"]:
        try:
            __import__(pkg)
            print(f"  {pkg:<12} OK")
        except ImportError:
            print(f"  {pkg:<12} 없음 -- pip install {pkg}")

    # ── 권장 명령 ──────────────────────────────────────────────────────────────
    print("\n[권장 실행 순서]")
    if not result["vllm_ready"]:
        result["recommended_cmd"] = (
            "nohup bash start_vllm.sh > logs/vllm.log 2>&1 &\n"
            "sleep 90 && python src/sim_overbooking.py --check"
        )
        print("  1. vLLM 서버가 꺼져있습니다.")
        print("     nohup bash start_vllm.sh > logs/vllm.log 2>&1 &")
        print("  2. 90초 대기 후 다시 --check 실행해서 서버 확인")
        print("     python src/sim_overbooking.py --check")
    elif result["gpu_free_count"] < 2:
        result["recommended_cmd"] = (
            "# GPU 부족 — Anthropic API 폴백\n"
            "python src/sim_overbooking.py --pilot --model anthropic"
        )
        print("  GPU 여유 부족 -> Anthropic API 폴백 권장:")
        print("    python src/sim_overbooking.py --pilot --model anthropic")
    else:
        workers = min(8, result["gpu_free_count"] * 4)
        result["recommended_cmd"] = (
            f"python src/sim_overbooking.py --pilot --model vllm --workers {workers}\n"
            f"# 파일럿 [OK] 확인 후:\n"
            f"python src/sim_overbooking.py --model vllm --workers {workers}"
        )
        print(f"  vLLM 준비됨 + GPU {result['gpu_free_count']}장 여유")
        print(f"  파일럿(60회):")
        print(f"    python src/sim_overbooking.py --pilot --model vllm --workers {workers}")
        print(f"  전체(1,000회):")
        print(f"    python src/sim_overbooking.py --model vllm --workers {workers}")

    print(sep)
    return result


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="오버부킹 Walk 보상 협상 시뮬레이션")
    parser.add_argument(
        "--pilot", action="store_true",
        help="파일럿 모드: 아키타입 A·D × 구간 3개 × 10회 = 60회",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="LLM 없이 더미 응답으로 파이프라인 검증",
    )
    parser.add_argument(
        "--model", type=str, default="vllm",
        choices=["vllm", "anthropic"],
        help="vllm (Qwen2.5-14B 로컬, 기본값 / 학교 서버 권장) 또는 anthropic (Claude Sonnet 4.6 API)",
    )
    parser.add_argument(
        "--base-url", type=str, default="http://localhost:8000/v1",
        help="vLLM 서버 URL (--model vllm 시)",
    )
    parser.add_argument(
        "--model-name", type=str, default=None,
        help="모델 명칭 오버라이드 (예: Qwen/Qwen2.5-14B-Instruct)",
    )
    parser.add_argument(
        "--workers", type=int, default=4,
        help="병렬 스레드 수 (기본 4)",
    )
    parser.add_argument(
        "--repeats", type=int, default=40,
        help="조합당 반복 횟수 (기본 40)",
    )
    parser.add_argument(
        "--out", type=str, default="results/walk_sim_results.jsonl",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--check", action="store_true",
        help="서버 환경 점검 후 종료 (GPU / vLLM / 디스크 / 권장 명령 출력)",
    )
    args = parser.parse_args()

    # 서버 상태 점검 모드
    if args.check:
        check_server(base_url=args.base_url.replace("/v1", ""))
        return

    random.seed(args.seed)

    # 실험 범위 결정
    if args.pilot:
        arch_keys   = ["A", "D"]
        offer_mults = OFFER_MULTIPLIERS[:3]
        n_repeats   = 10
        tag         = "파일럿"
    else:
        arch_keys   = list(ARCHETYPES.keys())
        offer_mults = OFFER_MULTIPLIERS
        n_repeats   = args.repeats
        tag         = "전체"

    tasks = build_tasks(arch_keys, offer_mults, n_repeats)
    total = len(tasks)

    print("=" * 60)
    print(f"Walk 보상 협상 시뮬레이션 [{tag}]")
    print("=" * 60)
    print(f"  아키타입 : {arch_keys}")
    print(f"  보상 구간 : {len(offer_mults)}개")
    print(f"  반복     : {n_repeats}회/조합")
    print(f"  총 협상  : {total}회")
    print(f"  모델     : {'dry-run' if args.dry_run else args.model}")
    print(f"  스레드   : {args.workers}")

    # LLM 클라이언트
    if args.dry_run:
        llm_call = _dry_run_call
        print("\n> [dry-run] LLM 호출 없이 더미 응답 사용")
    else:
        print(f"\n> LLM 초기화: {args.model}")
        if args.model == "vllm":
            import urllib.request as _ur
            try:
                _ur.urlopen(args.base_url.replace("/v1", "") + "/health", timeout=3)
            except Exception:
                print(f"  [오류] vLLM 서버 미응답 ({args.base_url})")
                print("  먼저: nohup bash start_vllm.sh > logs/vllm.log 2>&1 &")
                print("  확인: python src/sim_overbooking.py --check")
                return
        llm_call = make_llm_client(args.model, args.base_url, args.model_name)

    # 실행
    t0      = time.time()
    records = run_batch(tasks, llm_call, max_workers=args.workers)
    elapsed = time.time() - t0
    print(f"\n  완료: {elapsed:.1f}초  ({elapsed / max(len(records), 1):.2f}s/건)")

    # 저장 — JSONL (gitignore 제외, 대용량)
    out_path = ROOT / args.out
    with open(out_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    print(f"> 원본 저장: {out_path}  ({len(records)}건)")

    # 요약 CSV (gitignore 미포함 → 추적됨)
    summary     = make_summary(records)
    summary_out = out_path.with_suffix("").with_name(
        out_path.stem + "_summary.csv"
    )
    summary.to_csv(summary_out, index=False)
    print(f"> 요약 CSV : {summary_out}")

    print_report(records, summary)
    print("\n다음: python src/sim_walk_analyze.py  (시각화 예정)")


if __name__ == "__main__":
    main()
