# scripts/propose_travel_v2_config.py

from __future__ import annotations

import sys
from pathlib import Path
import json

# ----------------------------------------------------
# Ensure repo root is on sys.path so `agentops` imports work
# ----------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]  # ../ (repo root)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentops.travel_planner_planner import propose_travel_changeset
from core.common.change_set import ChangeSet, save_new_config


def main():
    proposal_dict = propose_travel_changeset(
        base_config_path="v2_adk/travel_planner/specs/travel_planner_config_v1.json",
        new_config_path="v2_adk/travel_planner/specs/travel_planner_config_v2.json",
        version_id="travel_v1",
        min_score=4.0,
    )

    print("=== Raw Planner Proposal (JSON) ===")
    print(json.dumps(proposal_dict, indent=2))

    cs = ChangeSet.from_dict(proposal_dict)

    save_new_config(
        base_path=cs.base_config_path,
        new_path=cs.new_config_path,
        patches=cs.config_patches,
    )

    print("\nNew config saved at:", cs.new_config_path)
    if cs.new_tests:
        print("\nSuggested new tests (append manually to travel_golden_v1.csv):")
        for t in cs.new_tests:
            print(json.dumps(t.__dict__, indent=2))


if __name__ == "__main__":
    main()
