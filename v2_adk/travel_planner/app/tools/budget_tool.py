# v2_adk/travel_planner/app/tools/budget_tool.py

from __future__ import annotations

from typing import Dict, Literal, Optional

TravelStyle = Literal["relaxed", "balanced", "packed"]


def estimate_budget(
    destination: str,
    duration_days: int,
    num_travelers: int = 2,
    travel_style: TravelStyle = "balanced",
    user_budget_total: Optional[float] = None,
) -> Dict:
    """
    Tool: estimate_budget

    Compute a rough budget breakdown given destination, duration, and style.

    This is intentionally simple and deterministic. It is not meant to be accurate,
    just consistent for evaluation.

    Args:
        destination: Destination city/region.
        duration_days: Number of days for the trip.
        num_travelers: How many travelers.
        travel_style: relaxed | balanced | packed (affects activity/food budget).
        user_budget_total: Optional user-stated budget to compare against.

    Returns:
        {
          "destination": str,
          "duration_days": int,
          "num_travelers": int,
          "style": str,
          "currency": "USD",
          "estimated_total": float,
          "estimated_per_day": float,
          "breakdown": {
             "lodging": float,
             "food": float,
             "local_transport": float,
             "activities": float,
             "misc": float
          },
          "within_user_budget": bool | None
        }
    """
    dest = destination.lower().strip()

    # Base per-day cost per person (very rough)
    if "tokyo" in dest or "paris" in dest:
        base_per_person = 200.0
    elif "seattle" in dest:
        base_per_person = 170.0
    else:
        base_per_person = 150.0

    # Style multipliers
    if travel_style == "relaxed":
        style_mult = 0.9
    elif travel_style == "packed":
        style_mult = 1.1
    else:  # balanced
        style_mult = 1.0

    per_person_per_day = base_per_person * style_mult
    total = per_person_per_day * duration_days * max(num_travelers, 1)
    per_day = total / max(duration_days, 1)

    # Simple breakdown heuristics
    lodging = total * 0.4
    food = total * 0.25
    local_transport = total * 0.15
    activities = total * 0.15
    misc = total - (lodging + food + local_transport + activities)

    within_budget: Optional[bool]
    if user_budget_total is None:
        within_budget = None
    else:
        within_budget = total <= user_budget_total * 1.15  # 15% cushion

    return {
        "destination": destination,
        "duration_days": duration_days,
        "num_travelers": num_travelers,
        "style": travel_style,
        "currency": "USD",
        "estimated_total": round(total, 2),
        "estimated_per_day": round(per_day, 2),
        "breakdown": {
            "lodging": round(lodging, 2),
            "food": round(food, 2),
            "local_transport": round(local_transport, 2),
            "activities": round(activities, 2),
            "misc": round(misc, 2),
        },
        "within_user_budget": within_budget,
    }
