from __future__ import annotations
import json
from pathlib import Path

AUT_SPEC_PATH = Path("v2_adk/travel_planner/specs/travel_planner_v1.aut.json")
PROFILE_PATH = Path("v2_adk/travel_planner/specs/agent_profile_travel_v1.json")


def discover_travel_app():
    """
    Returns AUT spec + discovered profile as a single JSON dictionary.
    This is what the Supervisor will show as the 'discovery' result.
    """
    aut = json.loads(AUT_SPEC_PATH.read_text())
    profile = json.loads(PROFILE_PATH.read_text())

    return {
        "aut_spec": aut,
        "agent_profile": profile,
        "status": "ok",
    }
