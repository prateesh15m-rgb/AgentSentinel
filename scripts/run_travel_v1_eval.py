# scripts/run_travel_v1_eval.py

from __future__ import annotations

import sys
from pathlib import Path

# --------------------------------------------------------------------
# Ensure repo root is on sys.path so `v2_adk` can be imported
# --------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]  # ../ (repo root)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2_adk.travel_planner.tests.eval.run_travel_v1_eval import main


if __name__ == "__main__":
    main()
