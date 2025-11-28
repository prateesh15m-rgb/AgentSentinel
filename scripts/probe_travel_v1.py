from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2_adk.travel_planner.app.main import run_travel_planner_once


def main():
    probes = [
        {
            "id": "probe_1",
            "request": {
                "destination": "Bali",
                "duration_days": 3,
                "budget_total": 800,
                "travel_style": "relaxed",
                "travelers_profile": {"adults": 2, "children": 0}
            }
        }
    ]

    print("Running dynamic probes...\n")

    for p in probes:
        result = run_travel_planner_once("travel_v1", p["request"])
        print(f"Probe {p['id']} result:")
        print(result["answer_markdown"])
        print("\n---\n")


if __name__ == "__main__":
    main()
