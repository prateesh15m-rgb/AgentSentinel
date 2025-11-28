# scripts/discover_travel_v1.py

from __future__ import annotations

import json
import sys
from pathlib import Path

# --------------------------------------------------------------------
# Ensure repo root is on sys.path so `core` imports work
# --------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]  # ../ (repo root)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.aut_spec import AUTSpec  # ADK AUT spec loader


AUT_SPEC_PATH = ROOT / "v2_adk/travel_planner/specs/travel_planner_v1.aut.yaml"
CONFIG_PATH = ROOT / "v2_adk/travel_planner/specs/travel_planner_config_v1.json"
OUTPUT_PROFILE = ROOT / "v2_adk/travel_planner/specs/agent_profile_travel_v1.json"


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    # 1) Load AUT spec (YAML) via our shared core.aut_spec
    spec = AUTSpec.load_from_file(AUT_SPEC_PATH)

    # 2) Load current config JSON for this version
    cfg = _load_json(CONFIG_PATH)

    # 3) Build a normalized "agent profile" that the supervisor / UI can use
    profile = {
        "aut_id": spec.aut_id,
        "name": spec.name,
        "version": spec.version,
        "description": spec.description,

        # ADK wiring (entrypoint, root agent, config file, etc.)
        "adk": spec.adk,

        # I/O contracts
        "inputs_schema": spec.inputs,
        "outputs_schema": spec.outputs,

        # Capabilities, tools, risk, eval config
        "capabilities": spec.capabilities,
        "tools": spec.tools,
        "risk_profile": spec.risk_profile,
        "evaluation": spec.evaluation,

        # Current runtime config + "knob" surfaces
        "config_file": spec.adk.get("config_file") if spec.adk else None,
        "current_config": cfg,
        "config_knobs": {
            # These sections match our travel_planner_config_v1.json structure.
            # If you add more sections later, you can extend this dict.
            "planning": list(cfg.get("planning", {}).keys()),
            "budgeting": list(cfg.get("budgeting", {}).keys()),
            "seasonality": list(cfg.get("seasonality", {}).keys()),
            "ux": list(cfg.get("ux", {}).keys()),
        },
    }

    # 4) Write profile to JSON for downstream tooling (supervisor, UI, docs)
    OUTPUT_PROFILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PROFILE.write_text(json.dumps(profile, indent=2), encoding="utf-8")

    print("Wrote agent profile to:", OUTPUT_PROFILE)


if __name__ == "__main__":
    main()
