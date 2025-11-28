#!/usr/bin/env python
"""
Build city_cost_baselines.json using Google Places price_level.

Usage:
  source .venv/bin/activate
  export GOOGLE_MAPS_API_KEY=...
  python scripts/build_city_cost_baselines_from_google.py
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Dict, List

from v2_adk.travel_planner.tools.google_maps_client import get_gmaps_client

OUTPUT_PATH = Path("data/travel_cost_baselines.json")

# Seed cities you care about (used in your tests + demo)
CITIES = [
    "Tokyo, Japan",
    "Paris, France",
    "Seattle, USA",
    # add more if you want
]


def _price_level_to_usd_nightly(price_level: int) -> float:
    """
    Very rough mapping from Google price_level (0–4) to nightly hotel cost.
    These are assumptions, but grounded in the price_level signal.
    """
    mapping = {
        0: 80.0,   # free/cheap → hostels/basic
        1: 120.0,  # budget
        2: 180.0,  # mid-range
        3: 260.0,  # upper-mid
        4: 350.0,  # luxury
    }
    return mapping.get(price_level, 180.0)


def _price_level_to_usd_meal(price_level: int) -> float:
    """
    Rough mapping from price_level to per-person meal cost.
    """
    mapping = {
        0: 8.0,
        1: 15.0,
        2: 25.0,
        3: 40.0,
        4: 70.0,
    }
    return mapping.get(price_level, 25.0)


def _collect_price_levels_for_type(city: str, place_type: str, max_results: int = 20) -> List[int]:
    gmaps = get_gmaps_client()
    resp = gmaps.places(query=f"{place_type} in {city}")
    results = resp.get("results", [])[:max_results]
    levels: List[int] = []
    for r in results:
        pl = r.get("price_level")
        if pl is not None:
            levels.append(int(pl))
    return levels


def build_baselines() -> Dict[str, Dict[str, float]]:
    baselines: Dict[str, Dict[str, float]] = {}

    for city in CITIES:
        lodging_levels = _collect_price_levels_for_type(city, "hotel")
        food_levels = _collect_price_levels_for_type(city, "restaurant")

        if lodging_levels:
            avg_lodging_level = mean(lodging_levels)
        else:
            avg_lodging_level = 2  # mid-range default

        if food_levels:
            avg_food_level = mean(food_levels)
        else:
            avg_food_level = 2

        lodging_per_night = _price_level_to_usd_nightly(round(avg_lodging_level))
        food_per_person_per_day = _price_level_to_usd_meal(round(avg_food_level))

        baselines[city] = {
            "lodging_per_night": round(lodging_per_night, 2),
            "food_per_person_per_day": round(food_per_person_per_day, 2),
            # simple fixed assumptions; could refine if you like
            "transport_per_person_per_day": 30.0,
            "activities_per_person_per_day": 35.0,
        }

    # Provide a generic default entry
    baselines["__default__"] = {
        "lodging_per_night": 180.0,
        "food_per_person_per_day": 25.0,
        "transport_per_person_per_day": 30.0,
        "activities_per_person_per_day": 35.0,
    }

    return baselines


def main():
    baselines = build_baselines()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(baselines, f, indent=2)
    print(f"Saved baselines to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
