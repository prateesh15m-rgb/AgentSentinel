from __future__ import annotations

import subprocess
from typing import Dict, Any


def run_travel_eval(version: str) -> Dict[str, Any]:
    """
    Calls your eval scripts (v1 or v2).
    Captures output from the process and returns it as a dict.
    """
    if version == "v1":
        cmd = ["python", "scripts/run_travel_v1_eval.py"]
    elif version == "v2":
        cmd = ["python", "scripts/run_travel_v2_eval.py"]
    else:
        return {"error": f"Unknown travel version: {version}"}

    result = subprocess.run(cmd, capture_output=True, text=True)

    return {
        "version": version,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }
