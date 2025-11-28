from __future__ import annotations

from pathlib import Path
import json
from typing import Dict, Any

# Paths to v1 and v2 configs
V1_CFG = Path("v2_adk/travel_planner/specs/travel_planner_config_v1.json")
V2_CFG = Path("v2_adk/travel_planner/specs/travel_planner_config_v2.json")


def compare_versions() -> Dict[str, Any]:
    """
    Compare v1 vs v2 travel planner configs at a high level.

    Returns a dict containing:
    - v1_config
    - v2_config
    - changed_top_level_keys: list of keys that differ between v1 and v2
    """
    if not V1_CFG.exists():
        return {"error": f"Missing config file: {V1_CFG}"}
    if not V2_CFG.exists():
        return {"error": f"Missing config file: {V2_CFG}"}

    v1 = json.loads(V1_CFG.read_text(encoding="utf-8"))
    v2 = json.loads(V2_CFG.read_text(encoding="utf-8"))

    changed_keys = []
    for key in sorted(set(v1.keys()) | set(v2.keys())):
        if v1.get(key) != v2.get(key):
            changed_keys.append(key)

    return {
        "v1_config": v1,
        "v2_config": v2,
        "changed_top_level_keys": changed_keys,
    }
