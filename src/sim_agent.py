"""
sim_agent.py
LLM 게스트 에이전트 — 예약 피처 → 심리 기반 페르소나 → Flexi 오퍼 반응

프롬프트 설계 참고:
  - LLM-Based Multi-Agent System for Simulating Consumer Behavior (arXiv 2510.18155)
    → Need Detection, internal trigger, price strategy embedding, JSON structured output
  - AgentSociety (arXiv 2502.08691)
    → Emotions × Needs × Cognition 3층 심리 모델, Profile + Status 분리,
       mind-behavior coupling (Needs → Plan → Behavioral Sequence)
"""

import json
import re
from openai import OpenAI

VLLM_BASE_URL = "http://localhost:8000/v1"
VLLM_MODEL    = "Qwen/Qwen2.5-14B-Instruct"

COUNTRY_NAMES = {
    "PRT": "Portuguese", "GBR": "British",  "FRA": "French",
    "ESP": "Spanish",    "DEU": "German",   "ITA": "Italian",
    "IRL": "Irish",      "BRA": "Brazilian","NLD": "Dutch",
    "USA": "American",   "CHN": "Chinese",  "BEL": "Belgian",
    "POL": "Polish",     "ROU": "Romanian", "AUT": "Austrian",
    "CHE": "Swiss",      "RUS": "Russian",  "SWE": "Swedish",
    "NOR": "Norwegian",  "DNK": "Danish",
}

MARKET_LABELS = {
    "Online TA":      "online travel agency (Booking.com / Expedia)",
    "Offline TA/TO":  "travel agent (offline)",
    "Direct":         "direct booking with the hotel",
    "Corporate":      "corporate account",
    "Groups":         "group booking coordinator",
    "Complementary":  "complimentary stay",
    "Aviation":       "airline crew booking",
}

MEAL_LABELS = {
    "BB": "breakfast included",
    "HB": "half board (breakfast + dinner)",
    "FB": "full board (all meals)",
    "SC": "no meal plan",
    "Undefined": "no meal plan",
}


# ── 할인율 공식 (CLAUDE.md 확정) ──────────────────────────────────────────────
def compute_discount(cancel_prob: float) -> float:
    raw = 5.0 + (cancel_prob - 0.5) * 26.0
    return round(max(5.0, min(18.0, raw)), 1)


# ── 심리 지표 파생 (데이터 → 행동 신호) ───────────────────────────────────────
# AgentSociety의 "Needs × Cognition" 레이어에 해당
# 2510.18155의 "heterogeneous traits enabling differential responses"

def derive_commitment(row: dict) -> tuple[str, str]:
    """특별 요청 + 주차 수요 → 여행 헌신도 (투자 수준)"""
    special = int(row.get("total_of_special_requests", 0))
    parking = int(row.get("required_car_parking_spaces", 0)) > 0

    score = special + (2 if parking else 0)
    if score == 0:
        return "LOW", "No special requests or parking — likely a convenience/price-driven booking with low personal investment."
    elif score <= 2:
        return "MEDIUM", f"{special} special request(s){'+ parking space needed' if parking else ''} — moderate trip investment."
    else:
        return "HIGH", f"{special} specific requests + {'parking needed' if parking else ''} — highly invested: has planned this trip carefully."


def derive_price_sensitivity(row: dict) -> str:
    """시장 세그먼트 + ADR → 가격 민감도"""
    segment = str(row.get("market_segment", ""))
    adr     = float(row.get("adr", 80))

    if segment in ("Online TA", "Offline TA/TO") and adr > 100:
        return "HIGH — booked via OTA at premium rate, likely comparison-shopping and responsive to discounts"
    elif segment == "Direct":
        return "LOW — booked directly, values relationship and certainty over price"
    elif segment == "Corporate":
        return "LOW — corporate account; cost is secondary to reliability and policy compliance"
    elif segment == "Groups":
        return "MEDIUM — group coordinator balancing cost and logistics"
    elif adr < 60:
        return "HIGH — budget booking, every euro matters"
    else:
        return "MEDIUM — moderate price sensitivity"


def derive_certainty_need(row: dict) -> str:
    """어린이 동반 + 주차 + 특별 요청 → 확실성(room guarantee) 욕구"""
    children = int(row.get("children", 0))
    parking  = int(row.get("required_car_parking_spaces", 0)) > 0
    special  = int(row.get("total_of_special_requests", 0))
    ctype    = str(row.get("customer_type", ""))

    if children > 0 or (parking and special >= 2) or "Group" in ctype:
        return "HIGH — family/group trip or specific room needs; cannot risk room reassignment"
    elif parking or special >= 1:
        return "MEDIUM — some room preferences; reassignment could be inconvenient"
    else:
        return "LOW — no specific room requirements; flexible on assignment"


def derive_flexibility_attitude(row: dict) -> str:
    """고객 유형 + 리드타임 → 유연성에 대한 태도 (AgentSociety Cognition 레이어)"""
    ctype     = str(row.get("customer_type", "Transient"))
    lead_time = int(row.get("lead_time", 30))
    prev_c    = int(row.get("previous_cancellations", 0))

    if ctype == "Contract":
        return "RIGID — contract booking with fixed terms; flexibility is not valued"
    elif "Group" in ctype:
        return "RIGID — coordinating for multiple people; cannot change plans easily"
    elif lead_time > 120 and prev_c > 0:
        return "FLEXIBLE — booked far in advance with history of changing plans; Flexi aligns with behavior"
    elif lead_time > 60:
        return "SOMEWHAT FLEXIBLE — long horizon means plans may still change"
    else:
        return "COMMITTED — close-in booking signals firm travel plans"


def derive_emotional_state(row: dict, cancel_prob: float) -> str:
    """예약 상황 → 현재 감정 상태 (AgentSociety Emotions 레이어)"""
    lead_time = int(row.get("lead_time", 30))
    prev_c    = int(row.get("previous_cancellations", 0))

    # 높은 취소 확률 = 내부적으로 불확실성 존재 (의식적이든 무의식적이든)
    if cancel_prob > 0.80 and lead_time > 90:
        return "UNCERTAIN — booked speculatively far in advance; genuine uncertainty about travel plans"
    elif prev_c > 1:
        return "HABIT OF CANCELLING — has cancelled before; may be booking as a placeholder"
    elif lead_time < 14:
        return "COMMITTED — last-minute booking signals definite travel intention"
    else:
        return "NEUTRAL — normal booking psychology"


# ── 페르소나 빌더 ─────────────────────────────────────────────────────────────
def build_persona(row: dict, cancel_prob: float) -> dict:
    total_nights = int(row.get("stays_in_weekend_nights", 0) +
                       row.get("stays_in_week_nights", 0))
    total_nights = max(1, total_nights)

    country_code = str(row.get("country", "Unknown"))
    nationality  = COUNTRY_NAMES.get(country_code, f"{country_code} national")

    channel   = MARKET_LABELS.get(str(row.get("market_segment", "")),
                                  str(row.get("market_segment", "")))
    meal_text = MEAL_LABELS.get(str(row.get("meal", "SC")), "no meal plan")

    adults   = int(row.get("adults", 1))
    children = int(row.get("children", 0))
    party    = f"{adults} adult(s)" + (f" + {children} child(ren)" if children > 0 else "")

    ctype = str(row.get("customer_type", "Transient"))
    if "Party" in ctype:
        trip_type = "leisure group trip with friends/family"
    elif ctype == "Contract":
        trip_type = "corporate / contract stay"
    elif ctype == "Group":
        trip_type = "organized group tour"
    else:
        trip_type = "individual trip (leisure or business)"

    hotel      = str(row.get("hotel", "hotel"))
    hotel_text = "city hotel in Lisbon" if "City" in hotel else "resort hotel in Algarve"
    lead_time  = int(row.get("lead_time", 30))
    adr        = float(row.get("adr", 80.0))

    prev_c = int(row.get("previous_cancellations", 0))
    if prev_c == 0:
        cancel_history = "No previous cancellations — tends to follow through on bookings."
    elif prev_c == 1:
        cancel_history = "1 previous cancellation — has some history of changing travel plans."
    else:
        cancel_history = f"{prev_c} previous cancellations — pattern of booking and cancelling."

    # 심리 지표 (AgentSociety: Needs × Cognition × Emotions)
    commit_level, commit_text     = derive_commitment(row)
    price_sensitivity             = derive_price_sensitivity(row)
    certainty_need                = derive_certainty_need(row)
    flexibility_attitude          = derive_flexibility_attitude(row)
    emotional_state               = derive_emotional_state(row, cancel_prob)

    return {
        "nationality":         nationality,
        "party":               party,
        "trip_type":           trip_type,
        "hotel":               hotel_text,
        "channel":             channel,
        "lead_time":           lead_time,
        "adr":                 adr,
        "total_nights":        total_nights,
        "total_cost":          round(adr * total_nights, 0),
        "meal":                meal_text,
        "cancel_history":      cancel_history,
        # 심리 지표
        "commit_level":        commit_level,
        "commit_text":         commit_text,
        "price_sensitivity":   price_sensitivity,
        "certainty_need":      certainty_need,
        "flexibility_attitude":flexibility_attitude,
        "emotional_state":     emotional_state,
    }


# ── 시스템 프롬프트 ────────────────────────────────────────────────────────────
# AgentSociety: "mind-behavior coupling" — 심리 상태가 행동으로 연결
_SYSTEM = """\
You are simulating a real hotel guest making a genuine booking decision.
Your response must reflect your specific psychological profile — not a generic answer.
Think carefully through your situation before deciding.\
"""

# ── 메인 프롬프트 ─────────────────────────────────────────────────────────────
# 2510.18155: Profile → Internal State → Offer → Reasoning → Decision
# AgentSociety: Emotions × Needs × Cognition → Behavioral Sequence
_PROMPT = """\
## STATIC PROFILE (who you are)
- Nationality: {nationality}
- Party: {party}
- Trip type: {trip_type}
- Destination: {hotel}
- Booked via: {channel}

## CURRENT BOOKING STATUS (your situation)
- Days until arrival: {lead_time} days
- Rate: €{adr:.0f}/night × {total_nights} nights = €{total_cost:.0f} total
- Meal plan: {meal}
- Booking history: {cancel_history}

## YOUR PSYCHOLOGICAL STATE (internal triggers)
Commitment to this trip:
  → {commit_text}

Price sensitivity:
  → {price_sensitivity}

Need for room certainty:
  → {certainty_need}

Attitude toward flexibility:
  → {flexibility_attitude}

Current emotional state:
  → {emotional_state}

---

## THE OFFER (environmental stimulus)
The hotel sends you this message:

  "We are offering you a Flexi upgrade: pay {discount:.0f}% less (€{discounted_rate:.0f}/night instead of €{adr:.0f}/night),
   saving you €{savings:.0f} in total. In return, your room type may be reassigned to
   an equivalent category, and we may contact you 24 hours before arrival to confirm.
   Your current booking has no free cancellation."

---

## REASON THROUGH YOUR DECISION
(Address each point from your profile — do not skip)

1. Given your emotional state and commitment level, how certain are you about this trip?
2. Does the €{savings:.0f} saving matter to you, given your price sensitivity?
3. Does room reassignment conflict with your certainty need or special requests?
4. Does the refund option add value, given your flexibility attitude?

Then respond with ONLY this JSON (no other text, no markdown):
{{"reasoning": "2-3 sentences covering the above", "decision": "ACCEPT_FLEXI" or "DECLINE_FLEXI" or "CANCEL"}}\
"""


def make_prompt(row: dict, cancel_prob: float) -> tuple[str, str]:
    """(system_prompt, user_prompt) 반환"""
    persona         = build_persona(row, cancel_prob)
    discount        = compute_discount(cancel_prob)
    discounted_rate = round(persona["adr"] * (1 - discount / 100), 0)
    savings         = round((persona["adr"] - discounted_rate) * persona["total_nights"], 0)
    user_prompt     = _PROMPT.format(
        **persona,
        discount=discount,
        discounted_rate=discounted_rate,
        savings=savings,
    )
    return _SYSTEM, user_prompt


# ── 응답 파서 ─────────────────────────────────────────────────────────────────
def parse_response(text: str) -> dict:
    try:
        m = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if m:
            data     = json.loads(m.group())
            decision = str(data.get("decision", "DECLINE_FLEXI")).upper().strip()
            if decision not in ("ACCEPT_FLEXI", "DECLINE_FLEXI", "CANCEL"):
                decision = "DECLINE_FLEXI"
            return {
                "decision": decision,
                "reason":   str(data.get("reasoning", data.get("reason", "")))[:300],
            }
    except Exception:
        pass
    t = text.upper()
    if "ACCEPT_FLEXI" in t:
        return {"decision": "ACCEPT_FLEXI",  "reason": "keyword-parsed"}
    if "CANCEL" in t and "DECLINE" not in t:
        return {"decision": "CANCEL",         "reason": "keyword-parsed"}
    return {"decision": "DECLINE_FLEXI",  "reason": "fallback"}


# ── GuestAgent ────────────────────────────────────────────────────────────────
class GuestAgent:
    def __init__(
        self,
        base_url:    str   = VLLM_BASE_URL,
        model:       str   = VLLM_MODEL,
        temperature: float = 0.75,
    ):
        self.client      = OpenAI(base_url=base_url, api_key="not-needed")
        self.model       = model
        self.temperature = temperature

    def decide(self, row: dict, cancel_prob: float) -> dict:
        system, user = make_prompt(row, cancel_prob)
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=self.temperature,
            max_tokens=200,
        )
        raw_text = resp.choices[0].message.content or ""
        result   = parse_response(raw_text)
        result.update({
            "cancel_prob": round(cancel_prob, 4),
            "discount":    compute_discount(cancel_prob),
            "raw_text":    raw_text[:600],
        })
        return result
