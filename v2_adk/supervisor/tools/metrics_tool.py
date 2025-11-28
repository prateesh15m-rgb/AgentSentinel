from __future__ import annotations

import subprocess
from typing import Dict, Any


def show_metrics() -> Dict[str, Any]:
    """
    Runs metrics summary using your existing metrics script.
    """
    cmd = ["python", "-m", "agentops.run_metrics_summary"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }
