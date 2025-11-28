# agentops/run_planner_once.py

from __future__ import annotations

import sys
from pathlib import Path
from pprint import pprint

# -------------------------------------------------------------
# Ensure repo root on sys.path (same pattern as run_supervisor)
# -------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# -------------------------------------------------------------
# Core imports
# -------------------------------------------------------------
from core.aut_spec import AUTSpec
from agentops.improvement.planner import PlannerEngine


# Default AUT spec for the travel planner
DEFAULT_AUT_SPEC = ROOT / "v2_adk/travel_planner/specs/travel_planner_v1.aut.yaml"


def main() -> None:
    # ---------------------------------------------------------
    # 1. Load AUT spec (single source of truth for this AUT)
    # ---------------------------------------------------------
    spec = AUTSpec.load_from_file(DEFAULT_AUT_SPEC)
    base_version_id = spec.version or "travel_v1"

    # ---------------------------------------------------------
    # 2. Instantiate PlannerEngine (Planner + Critic agents)
    # ---------------------------------------------------------
    planner_engine = PlannerEngine(spec=spec)

    # ---------------------------------------------------------
    # 3. Ask PlannerEngine for a changeset proposal
    #    This reads eval history + best practices and returns:
    #      - config_patch      (how to tweak model/tools/config)
    #      - new_testcases     (golden rows to add)
    #      - rationale         (LLM explanation)
    #      - metadata          (current metrics, targets, etc.)
    # ---------------------------------------------------------
    changeset = planner_engine.propose_changeset(version_id=base_version_id)

    if hasattr(changeset, "to_dict"):
        proposal_dict = changeset.to_dict()
    elif isinstance(changeset, dict):
        proposal_dict = changeset
    else:
        proposal_dict = changeset.__dict__

    print("=== Planner Changeset Proposal ===")
    pprint(proposal_dict)

    # ---------------------------------------------------------
    # 4. Human next steps (for capstone narrative)
    # ---------------------------------------------------------
    print(
        "\nNext steps:\n"
        "  1) Use this proposal to create a NEW version config, e.g.:\n"
        "       v2_adk/travel_planner/specs/travel_planner_config_v2.json\n"
        "     by applying the suggested `config_patch`.\n"
        "  2) Append any `new_testcases` to your golden CSV, e.g.:\n"
        "       v2_adk/travel_planner/tests/golden/travel_golden_v2.csv\n"
        "  3) Update your AUT spec (travel_planner_v2.aut.yaml) to point\n"
        "     to the new config + golden path.\n"
        "  4) Run eval again for the new version via Supervisor:\n"
        "       Supervisor > eval travel_v2\n"
    )


if __name__ == "__main__":
    main()
