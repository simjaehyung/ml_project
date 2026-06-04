"""
Hotel DSS — LLM 에이전트 구현

각 게스트 페르소나는 Claude claude-haiku-4-5-20251001 모델로 구동.
anthropic tool_use API를 통해 PMS 예약 도구를 호출.

사용법:
    from llm_sim.agents import run_agent
    result = run_agent(persona)
"""

import os
import httpx
import anthropic
from datetime import date, timedelta
from typing import Optional

from llm_sim.personas import PERSONAS

PMS_BASE_URL = "http://localhost:3001"
PMS_API_KEY = "pms-guest-key-2026"
MODEL = "claude-haiku-4-5-20251001"

# ── 예약 도구 정의 ─────────────────────────────────────────────
BOOKING_TOOL = {
    "name": "create_hotel_booking",
    "description": (
        "Create a hotel room booking through the hotel PMS system. "
        "Use this tool to make your reservation. "
        "The system will confirm your booking and tell you the pricing type."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "hotel": {
                "type": "string",
                "enum": ["City Hotel", "Resort Hotel"],
                "description": "Which hotel to book"
            },
            "arrival_date": {
                "type": "string",
                "description": "Check-in date in YYYY-MM-DD format"
            },
            "departure_date": {
                "type": "string",
                "description": "Check-out date in YYYY-MM-DD format (must be after arrival_date)"
            },
            "adults": {
                "type": "integer",
                "minimum": 1,
                "maximum": 4,
                "description": "Number of adult guests"
            },
            "children": {
                "type": "integer",
                "minimum": 0,
                "maximum": 4,
                "default": 0,
                "description": "Number of children"
            },
            "room_type_preference": {
                "type": "string",
                "enum": ["Single", "Double", "Twin", "Suite", "No Preference"],
                "description": "Preferred room type"
            },
            "meal_plan": {
                "type": "string",
                "enum": ["Bed & Breakfast", "Half Board", "Full Board", "Room Only"],
                "description": "Meal plan preference"
            },
            "nationality": {
                "type": "string",
                "description": "Guest nationality as ISO alpha-3 code (e.g. GBR, PRT, DEU, FRA, BRA)"
            },
            "special_requests": {
                "type": "string",
                "description": "Any special requests or notes (can be empty)"
            }
        },
        "required": ["hotel", "arrival_date", "departure_date", "adults", "nationality"]
    }
}


def _call_pms_api(tool_input: dict, agent_id: str, persona_description: str) -> dict:
    """도구 호출 결과 → PMS API 실제 호출"""
    payload = {
        "hotel": tool_input["hotel"],
        "arrival_date": tool_input["arrival_date"],
        "departure_date": tool_input["departure_date"],
        "adults": tool_input.get("adults", 1),
        "children": tool_input.get("children", 0),
        "room_type_preference": tool_input.get("room_type_preference", "No Preference"),
        "meal_plan": tool_input.get("meal_plan", "Bed & Breakfast"),
        "nationality": tool_input["nationality"],
        "special_requests": tool_input.get("special_requests", ""),
        "agent_id": agent_id,
        "persona_description": persona_description,
    }

    with httpx.Client(timeout=20.0) as client:
        resp = client.post(
            f"{PMS_BASE_URL}/api/bookings",
            json=payload,
            headers={
                "Authorization": f"Bearer {PMS_API_KEY}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        return resp.json()


def run_agent(persona: dict, print_fn=print) -> Optional[dict]:
    """
    단일 페르소나 에이전트를 실행하고 예약 결과를 반환.

    Args:
        persona: personas.py의 PERSONAS 항목
        print_fn: 출력 함수 (기본: print, UI 연동 시 custom 사용)

    Returns:
        예약 확인 결과 dict or None (실패 시)
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")

    client = anthropic.Anthropic(api_key=api_key)

    today_str = date.today().isoformat()
    user_message = (
        f"Today is {today_str}. "
        f"You are {persona['name']}, a {persona['persona_type']} from {persona['nationality']}. "
        "Please book a hotel room that fits your persona and travel style. "
        "Use the create_hotel_booking tool to complete your reservation."
    )

    print_fn(f"\n{'='*60}")
    print_fn(f"  에이전트: {persona['name']} ({persona['nationality']}) [{persona['persona_type']}]")
    print_fn(f"  {persona['description']}")
    print_fn(f"{'='*60}")

    messages = [{"role": "user", "content": user_message}]
    booking_result = None

    # 최대 3턴 (thinking → tool use → reaction)
    for turn in range(3):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=persona["system_prompt"],
            tools=[BOOKING_TOOL],
            messages=messages,
        )

        # 에이전트 생각 출력
        for block in response.content:
            if hasattr(block, "text") and block.text:
                print_fn(f"\n  💬 {persona['name']}: {block.text[:300]}")

        # 도구 호출 처리
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        if not tool_uses:
            # 도구 호출 없이 응답 종료
            if response.stop_reason == "end_turn":
                print_fn(f"\n  ⚠️  도구 호출 없이 종료 (stop_reason=end_turn)")
            break

        # 도구 결과 처리
        tool_results = []
        for tool_use in tool_uses:
            if tool_use.name == "create_hotel_booking":
                print_fn(f"\n  → 예약 요청: {tool_use.input.get('hotel')} "
                         f"{tool_use.input.get('arrival_date')} ~ {tool_use.input.get('departure_date')}, "
                         f"{tool_use.input.get('adults')}명")
                try:
                    result = _call_pms_api(
                        tool_use.input,
                        persona["id"],
                        persona["description"],
                    )
                    booking_result = result
                    pricing = result.get("pricing_type", "Unknown")
                    conf = result.get("confirmation_number", "?")
                    disc = result.get("discount_applied")
                    disc_str = f" (-{round(disc*100,1)}%)" if disc else ""
                    print_fn(f"\n  ✓ 확정: {conf} | {pricing}{disc_str} | €{result.get('total_amount', 0):.0f}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": (
                            f"Booking confirmed!\n"
                            f"Confirmation: {conf}\n"
                            f"Hotel: {result.get('hotel')}\n"
                            f"Check-in: {result.get('arrival_date')}, Check-out: {result.get('departure_date')}\n"
                            f"Pricing: {pricing}{disc_str}\n"
                            f"Total: €{result.get('total_amount', 0):.2f}\n"
                            f"Message: {result.get('message', '')}"
                        ),
                    })
                except Exception as e:
                    print_fn(f"\n  ✗ 예약 실패: {e}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "is_error": True,
                        "content": f"Booking failed: {str(e)}",
                    })

        if not tool_results:
            break

        # 다음 턴을 위해 messages 업데이트
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        if booking_result:
            # 예약 완료 → 에이전트 반응 한 번 더 받고 종료
            final = client.messages.create(
                model=MODEL,
                max_tokens=256,
                system=persona["system_prompt"],
                tools=[BOOKING_TOOL],
                messages=messages,
            )
            for block in final.content:
                if hasattr(block, "text") and block.text:
                    print_fn(f"\n  💬 {persona['name']} (반응): {block.text[:200]}")
            break

    return booking_result
