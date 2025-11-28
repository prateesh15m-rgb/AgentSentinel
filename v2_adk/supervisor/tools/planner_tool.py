from __future__ import annotations

import subprocess
from typing import Dict, Any


def propose_improvements() -> Dict[str, Any]:
    """
    Calls your planner (ChangeSet generator) for travel_v1 -> travel_v2.
    """
    cmd = ["python", "scripts/propose_travel_v2_config.py"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }
