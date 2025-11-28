from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Tuple, List

import google.generativeai as genai

from v2_adk.travel_planner.app.agents.travel_root_agent import (
    travel_root_agent,
    load_travel_config,
)
from v2_adk.travel_planner.app.tools.dest_info_tool import dest_info
from v2_adk.travel_planner.app.tools.weather_tool import seasonal_weather_profile
from v2_adk.travel_planner.app.tools.budget_tool import estimate_budget


# -------------------------------------------------------------
# ADK APP ENTRYPOINT (used by AUTClient)
# -------------------------------------------------------------
def create_app():
    """
    ADK "app entrypoint" – Supervisor/AUTClient calls this to get the root agent.

    In our v1, the ADK app is a single root agent (travel_root_agent) that
    encapsulates the travel planning behavior + config.
    """
    return travel_root_agent


# -------------------------------------------------------------
# GEMINI MODEL LOADER
# -------------------------------------------------------------
def _get_model(model_name: str):
    """
    Load a Gemini GenerativeModel using GOOGLE_API_KEY or GEMINI_API_KEY.
    """
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Please set GOOGLE_API_KEY or GEMINI_API_KEY in your environment."
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


# -------------------------------------------------------------------
# Helpers to build structured_plan fields
# -------------------------------------------------------------------
def build_itinerary_days(
    trip_request: Dict[str, Any],
    dest_profile: Dict[str, Any] | None = None,
    weather_profile: Dict[str, Any] | None = None,
    budget_profile: Dict[str, Any] | None = None,
) -> list[Dict[str, Any]]:
    """
    Build 'itinerary_days' in the exact shape expected by AUTSpec.outputs_schema.

    v1 implementation is intentionally generic:
      - Uses destination + duration_days + travel_style
      - Creates 2–4 activities per day with morning/afternoon/evening slots

    Later you can specialize per destination (Tokyo/Paris/Seattle) without
    changing the schema or the Supervisor.
    """
    destination = trip_request.get("destination", "your destination") or "your destination"
    num_days = int(trip_request.get("duration_days") or 3)
    style = (trip_request.get("travel_style") or "balanced").lower()

    # Rough guideline for how many activities per day based on style
    if style == "relaxed":
        activities_per_day = 2
    elif style == "packed":
        activities_per_day = 4
    else:  # balanced
        activities_per_day = 3

    # Time-of-day slots we'll use in order
    time_slots = ["morning", "afternoon", "evening", "night"]

    itinerary_days: list[Dict[str, Any]] = []

    for i in range(num_days):
        day_index = i + 1

        if day_index == 1:
            title = f"Arrival & First Impressions of {destination}"
            summary = f"Arrive, settle in, and get a gentle first taste of {destination}."
        else:
            title = f"Day {day_index} in {destination}"
            summary = (
                f"Explore more of {destination} with a mix of sightseeing and downtime, "
                f"tailored to a {style} travel style."
            )

        activities: list[Dict[str, Any]] = []
        for j in range(activities_per_day):
            slot = time_slots[j]

            activities.append(
                {
                    "time_of_day": slot,
                    "name": f"{destination} highlight {day_index}-{j+1}",
                    "description": (
                        f"Sample {slot} activity in {destination} for a {style} itinerary "
                        f"(e.g., a landmark, neighborhood walk, family-friendly park, or museum)."
                    ),
                    # Keep costs simple but valid; real logic can come in v2
                    "approx_cost": 0.0,
                    "booking_required": False,
                }
            )

        itinerary_days.append(
            {
                "day_index": day_index,
                "title": title,
                "summary": summary,
                "activities": activities,
            }
        )

    return itinerary_days


def build_budget_summary_from_profile(budget_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert your budget_tool output into the AUTSpec 'budget_summary' shape.

    AUTSpec requires:
      - currency
      - total_estimated
      - per_day_estimate
      - breakdown{lodging, food, local_transport, activities, misc}
    """
    breakdown = budget_profile.get("breakdown", {}) or {}

    return {
        "currency": budget_profile.get("currency", "USD"),
        "total_estimated": float(budget_profile.get("estimated_total", 0.0)),
        "per_day_estimate": float(budget_profile.get("estimated_per_day", 0.0)),
        "breakdown": {
            "lodging": float(breakdown.get("lodging", 0.0)),
            "food": float(breakdown.get("food", 0.0)),
            "local_transport": float(breakdown.get("local_transport", 0.0)),
            "activities": float(breakdown.get("activities", 0.0)),
            "misc": float(breakdown.get("misc", 0.0)),
        },
    }


def build_season_notes_from_profile(
    weather_profile: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Map weather_tool output into the optional 'season_notes' structure.
    """
    if not weather_profile:
        return {
            "season_label": "unknown",
            "weather_assumptions": "",
            "special_considerations": "",
        }

    # seasonal_weather_profile currently returns fields like:
    #   destination, season_label, typical_temp_range_c, rain_risk, notes
    typical_range = weather_profile.get("typical_temp_range_c")
    rain_risk = weather_profile.get("rain_risk")
    notes = weather_profile.get("notes", "")

    if notes:
        weather_assumptions = notes
    else:
        weather_assumptions = (
            f"Typical temperatures {typical_range}, rain risk: {rain_risk}."
        )

    return {
        "season_label": weather_profile.get("season_label", "typical"),
        "weather_assumptions": weather_assumptions,
        "special_considerations": "",
    }


# ---------- New helpers for assumptions & warnings ----------

def _extract_section_markdown(answer_text: str, heading: str) -> str:
    """
    Extract the markdown block under a given heading, e.g. "Assumptions & Warnings".

    Looks for lines like:
      ## Assumptions & Warnings
      ### Assumptions & Warnings
    and returns everything until the next line starting with '#'.
    """
    lines = answer_text.splitlines()
    pattern = rf"^#+\s*{re.escape(heading)}\s*$"

    start_idx: int | None = None
    for i, line in enumerate(lines):
        if re.match(pattern, line.strip(), flags=re.IGNORECASE):
            start_idx = i + 1
            break

    if start_idx is None:
        return ""

    collected: list[str] = []
    for line in lines[start_idx:]:
        if line.strip().startswith("#"):
            break
        collected.append(line)

    return "\n".join(collected).strip()


def _parse_bullet_items(block: str) -> list[str]:
    """
    Parse markdown bullet list items from a block into plain strings.
    """
    items: list[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith(("-", "*", "•")):
            item = stripped.lstrip("-*•").strip()
            if item:
                items.append(item)
    return items


def _split_assumptions_and_warnings(
    items: list[str],
) -> tuple[list[str], list[str]]:
    """
    Simple heuristic:
      - Lines mentioning risk/warning/avoid/etc → warnings
      - Everything else → assumptions
    """
    assumptions: list[str] = []
    warnings: list[str] = []

    warning_keywords = [
        "risk",
        "warning",
        "unsafe",
        "book in advance",
        "book tickets",
        "caution",
        "be aware",
        "avoid",
        "danger",
        "crowded",
        "limited availability",
        "typhoon",
        "heatwave",
        "storm",
    ]

    for item in items:
        lower = item.lower()
        if any(k in lower for k in warning_keywords):
            warnings.append(item)
        else:
            assumptions.append(item)

    return assumptions, warnings


def build_assumptions_and_warnings_from_answer(
    answer_text: str,
) -> tuple[list[str], list[str]]:
    """
    Fill assumptions[] and warnings[] from the LLM answer.

    Expects the prompt to include a section:
      "4. Assumptions & Warnings"

    And the model to emit a markdown heading:
      ## Assumptions & Warnings
         - bullet 1
         - bullet 2
    """
    section = _extract_section_markdown(answer_text, "Assumptions & Warnings")
    if not section:
        # No dedicated heading found; safe fallback: nothing
        return [], []

    bullet_items = _parse_bullet_items(section)
    if not bullet_items:
        return [], []

    return _split_assumptions_and_warnings(bullet_items)


# -------------------------------------------------------------
# MAIN RUNNER FOR TRAVEL PLANNER (called by AUTClient)
# -------------------------------------------------------------
def run_travel_planner_once(
    version_id: str,
    trip_request: Dict[str, Any],
    config_path: Path | str | None = None,
) -> Dict[str, Any]:
    """
    This is the main "AUT call" used by TravelAUTClient.

    It:
      - loads config
      - calls tools (dest_info, weather, budget)
      - builds a safe prompt
      - calls Gemini
      - returns both:
          * answer_markdown (human-facing)
          * structured_plan (machine-readable, matches AUTSpec)
    """

    # ---------------------------------------------------------
    # Load config + model
    # ---------------------------------------------------------
    config = load_travel_config(config_path)
    model_cfg = config["model"]
    model = _get_model(model_cfg["name"])

    destination = trip_request.get("destination", "")
    duration_days = trip_request.get("duration_days")
    start_date = trip_request.get("start_date")
    budget_total = trip_request.get("budget_total")
    travel_style = trip_request.get("travel_style", "balanced")

    travelers = trip_request.get("travelers_profile", {}) or {}
    num_adults = travelers.get("adults", 2)
    num_children = travelers.get("children", 0)
    num_travelers = max(num_adults + num_children, 1)

    # Month extraction from YYYY-MM-DD (if present)
    month = None
    if isinstance(start_date, str) and "-" in start_date:
        try:
            month = int(start_date.split("-")[1])
        except Exception:
            month = None

    # ---------------------------------------------------------
    # Tool calls (mocked/simulated for capstone)
    # ---------------------------------------------------------
    dest_profile = dest_info(destination)
    weather_profile = seasonal_weather_profile(destination, month)
    budget_profile = estimate_budget(
        destination=destination,
        duration_days=duration_days or 5,
        num_travelers=num_travelers,
        travel_style=travel_style,
        user_budget_total=budget_total,
    )

    tool_outputs = {
        "dest_profile": dest_profile,
        "weather_profile": weather_profile,
        "budget_profile": budget_profile,
    }

    # ---------------------------------------------------------
    # SAFE PROMPT TEMPLATE (NO F-STRING, NO BACKTICKS)
    # ---------------------------------------------------------
    PROMPT_TEMPLATE = """
{system_instruction}

You are planning the following trip request:

TRIP REQUEST JSON:
{trip_json}

DESTINATION INFO:
{dest_json}

SEASONAL WEATHER PROFILE:
{weather_json}

BUDGET ESTIMATE:
{budget_json}

Now produce a travel plan.

Requirements:
- Match the number of days requested.
- 2-3 realistic activities per day.
- Respect must_include / must_avoid / mobility / children.
- Use weather profile to adjust activities.
- Explain how the budget estimate relates to the user's budget.
- Use a {persona_tone} tone.

Output format (strict):
1. Summary section
2. Day-by-Day Itinerary
3. Budget Summary
4. Assumptions & Warnings

FINAL OUTPUT MUST BE MARKDOWN ONLY.
"""

    prompt = PROMPT_TEMPLATE.format(
        system_instruction=travel_root_agent.instruction,
        trip_json=json.dumps(trip_request, indent=2),
        dest_json=json.dumps(dest_profile, indent=2),
        weather_json=json.dumps(weather_profile, indent=2),
        budget_json=json.dumps(budget_profile, indent=2),
        persona_tone=config.get("persona", {}).get("tone", "friendly"),
    )

    # ---------------------------------------------------------
    # RUN MODEL
    # ---------------------------------------------------------
    start = time.time()
    response = model.generate_content(prompt)
    latency_ms = (time.time() - start) * 1000.0

    answer_text = getattr(response, "text", str(response))

    # ---------------------------------------------------------
    # STRUCTURED PLAN (wired to AUTSpec schema)
    # ---------------------------------------------------------
    itinerary_days = build_itinerary_days(
        trip_request=trip_request,
        dest_profile=dest_profile,
        weather_profile=weather_profile,
        budget_profile=budget_profile,
    )
    budget_summary = build_budget_summary_from_profile(budget_profile)
    season_notes = build_season_notes_from_profile(weather_profile)
    assumptions, warnings = build_assumptions_and_warnings_from_answer(answer_text)

    structured = {
        "itinerary_days": itinerary_days,
        "budget_summary": budget_summary,
        "season_notes": season_notes,
        "assumptions": assumptions,
        "warnings": warnings,
    }

    return {
        "version_id": version_id,
        "request": trip_request,
        "structured_plan": structured,
        "answer_markdown": answer_text,
        "latency_ms": latency_ms,
        "tool_outputs": tool_outputs,
    }
