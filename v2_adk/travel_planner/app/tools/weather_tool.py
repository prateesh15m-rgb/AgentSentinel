# v2_adk/travel_planner/app/tools/weather_tool.py

from __future__ import annotations

from typing import Dict, Optional


def seasonal_weather_profile(destination: str, month: Optional[int] = None) -> Dict:
    """
    Tool: seasonal_weather_profile

    Return a simple seasonal weather profile for the destination.

    Args:
        destination: Destination city/region.
        month: Month as integer 1–12. If None, assume 'typical' season.

    Returns:
        {
          "destination": str,
          "season_label": str,
          "typical_temp_range_c": str,
          "rain_risk": "low" | "medium" | "high",
          "notes": str
        }
    """
    dest = destination.lower().strip()

    # Very rough seasonal mapping; enough for demos/evals.
    if month is None:
        return {
            "destination": destination,
            "season_label": "typical",
            "typical_temp_range_c": "10–25",
            "rain_risk": "medium",
            "notes": "Assuming mild conditions; adjust activities if user clarifies dates.",
        }

    # Heuristic by month
    if month in (12, 1, 2):
        season = "winter"
    elif month in (3, 4, 5):
        season = "spring"
    elif month in (6, 7, 8):
        season = "summer"
    else:
        season = "autumn"

    # Simple destination-dependent tweaks
    if "tokyo" in dest:
        if season == "summer":
            temp = "25–32"
            rain = "high"
            notes = "Hot and humid with rainy season; favor indoor activities and evening walks."
        elif season == "winter":
            temp = "0–10"
            rain = "low"
            notes = "Cool to cold; mix indoor attractions with short outdoor walks."
        else:
            temp = "10–25"
            rain = "medium"
            notes = "Pleasant weather; balanced indoor/outdoor plans."
    elif "paris" in dest:
        if season == "summer":
            temp = "20–30"
            rain = "medium"
            notes = "Warm and lively; great for outdoor cafes and evening walks."
        elif season == "winter":
            temp = "0–8"
            rain = "medium"
            notes = "Chilly and sometimes rainy; favor museums and indoor activities."
        else:
            temp = "10–20"
            rain = "medium"
            notes = "Mild shoulder seasons; mix indoor and outdoor activities."
    else:
        temp = "10–25"
        rain = "medium"
        notes = "Assuming moderate conditions; adjust based on actual weather if known."

    return {
        "destination": destination,
        "season_label": season,
        "typical_temp_range_c": temp,
        "rain_risk": rain,
        "notes": notes,
    }
