# v2_adk/travel_planner/app/tools/dest_info_tool.py

from __future__ import annotations

from typing import Dict, List


def dest_info(destination: str) -> Dict:
    """
    Tool: dest_info

    Return a mock "destination profile" for the given city/region.

    This is intentionally simple and deterministic so that:
    - Discovery can see that the agent *has* this tool.
    - Evaluations are stable across runs (no live APIs).

    Args:
        destination: Name of the destination city/region.

    Returns:
        {
          "destination": str,
          "region_type": "city" | "coastal" | "mixed",
          "typical_daily_cost_per_person": float,
          "main_areas": [str],
          "tags": [str]
        }
    """
    dest = destination.lower().strip()

    if "tokyo" in dest:
        return {
            "destination": destination,
            "region_type": "city",
            "typical_daily_cost_per_person": 180.0,
            "main_areas": ["Shinjuku", "Shibuya", "Asakusa"],
            "tags": ["food", "shopping", "culture", "tech"],
        }
    if "paris" in dest:
        return {
            "destination": destination,
            "region_type": "city",
            "typical_daily_cost_per_person": 200.0,
            "main_areas": ["Latin Quarter", "Le Marais", "Montmartre"],
            "tags": ["museums", "romantic", "cafes"],
        }
    if "seattle" in dest:
        return {
            "destination": destination,
            "region_type": "mixed",
            "typical_daily_cost_per_person": 160.0,
            "main_areas": ["Downtown", "Capitol Hill", "Ballard"],
            "tags": ["coffee", "waterfront", "family"],
        }

    # Generic fallback
    return {
        "destination": destination,
        "region_type": "mixed",
        "typical_daily_cost_per_person": 150.0,
        "main_areas": [],
        "tags": ["general"],
    }
