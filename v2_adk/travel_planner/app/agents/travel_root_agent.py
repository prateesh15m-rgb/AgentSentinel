# v2_adk/travel_planner/app/agents/travel_root_agent.py

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

try:
    from google.adk.agents import Agent
except ImportError as e:  # pragma: no cover - helpful error for local runs
    raise ImportError(
        "google-adk is not installed. Install it with:\n"
        "  pip install google-adk\n"
        f"Original error: {e}"
    )

from v2_adk.travel_planner.app.tools.dest_info_tool import dest_info
from v2_adk.travel_planner.app.tools.weather_tool import seasonal_weather_profile
from v2_adk.travel_planner.app.tools.budget_tool import estimate_budget

# Path to default config (v1)
CONFIG_PATH = (
    Path(__file__)
    .resolve()
    .parents[2]  # up from agents/ → app/ → travel_planner/
    / "specs"
    / "travel_planner_config_v1.json"
)


def load_travel_config(path: Path | str | None = None) -> Dict[str, Any]:
    """Load the travel planner behavior config JSON."""
    cfg_path = Path(path) if path else CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(f"Travel planner config not found at: {cfg_path}")
    with cfg_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_instruction(config: Dict[str, Any]) -> str:
    """Build the root agent instruction string from config persona + knobs."""
    persona = config.get("persona", {})
    planning = config.get("planning", {})
    budgeting = config.get("budgeting", {})
    seasonality = config.get("seasonality", {})
    ux = config.get("ux", {})
    safety = config.get("safety", {})

    style_guidelines: List[str] = persona.get("style_guidelines", [])
    style_bullets = "\n".join(f"- {g}" for g in style_guidelines)

    clarification_cfg = planning.get("clarification", {})
    clarification_enabled = clarification_cfg.get("enabled", False)

    instruction = f"""
You are a travel itinerary planning assistant.

Your job:
- Take a destination, dates or duration, budget, and travel style.
- Produce a realistic day-by-day itinerary with 2–3 key activities per day.
- Provide a rough budget breakdown.
- Consider seasonality and typical weather for the destination and dates.
- Respect explicit constraints (must_include / must_avoid, mobility, children).

Persona:
- Role: {persona.get('role', 'A pragmatic travel planner')}
- Tone: {persona.get('tone', 'friendly-practical')}

Style guidelines:
{style_bullets or '- Use common sense and be concise.'}

Planning knobs:
- Max days you should plan for: {planning.get('max_days', 14)}
- You can assume the agent has up to {planning.get('max_tool_calls', 5)} tool calls available.
- Clarification questions enabled: {clarification_enabled}

Budgeting behavior:
- Default currency: {budgeting.get('default_currency', 'USD')}
- Budget strictness: {budgeting.get('budget_strictness', 'medium')}
- Allow going over budget by up to {int(budgeting.get('allow_over_budget_pct', 0.15) * 100)}%.

Seasonality:
- Season-aware planning is enabled: {seasonality.get('enabled', True)}

Output & UX:
- Format: {ux.get('output_format', 'markdown')}
- Include summary first: {ux.get('include_summary_first', True)}
- Verbosity: {ux.get('verbosity', 'normal')}

Safety:
- Child-friendly by default: {safety.get('child_friendly_default', True)}
- Disallowed activities: {', '.join(safety.get('disallowed_activities', []))}

Core rules:
- Be realistic about time and energy per day.
- Do not invent precise prices; give approximate ranges when needed.
- If information is uncertain, state your assumptions explicitly.
- Avoid unsafe or illegal activities. If user explicitly asks, explain safety trade-offs and suggest safer alternatives.
    """.strip()

    return instruction


# Load config once at import-time for the ADK Agent definition
_CONFIG = load_travel_config()
_INSTRUCTION = build_instruction(_CONFIG)

travel_root_agent = Agent(
    name="travel_planner_root",
    model=_CONFIG["model"]["name"],
    description="Generates day-by-day travel itineraries with rough budgets and season-aware activities.",
    instruction=_INSTRUCTION,
    # NOTE: These are Python functions exposed as tools for future ADK tool-calling.
    # Even if we orchestrate calls manually at first, having them here helps discovery.
    tools=[dest_info, seasonal_weather_profile, estimate_budget],
)
