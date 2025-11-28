# v2_adk/travel_planner/app/travel_runtime.py

from __future__ import annotations

import time
from typing import Any, Dict, Optional, List

from core.aut_spec import AUTSpec
from core.aut_client import AUTResponse

# Your existing ADK entrypoint helper
from v2_adk.travel_planner.app.main import run_travel_planner_once


class TravelADKRuntime:
    """
    Thin wrapper around your ADK travel planner runtime.

    Responsibilities:
      - Call the ADK root agent (run_travel_planner_once)
      - Measure latency
      - Normalize the response into AUTResponse
    """

    def __init__(self, spec: AUTSpec, default_version: str):
        self.spec = spec
        self.default_version = default_version

    def run_once(self, version_id: Optional[str], request: Dict[str, Any]) -> AUTResponse:
        """
        Run the ADK-based travel planner once and normalize the result.
        """
        vid = version_id or self.default_version

        start = time.time()
        # This should call into your ADK graph for the given version.
        result = run_travel_planner_once(vid, request)
        latency_ms = (time.time() - start) * 1000.0

        # Normalize answer text
        if isinstance(result, dict):
            answer_text = (
                result.get("answer_markdown")
                or result.get("answer")
                or result.get("output")
                or str(result)
            )
            session_graph = result.get("session_graph")
            tool_calls: List[Dict[str, Any]] = result.get("tool_calls") or []
        else:
            answer_text = str(result)
            session_graph = None
            tool_calls = []

        return AUTResponse(
            answer=answer_text,
            raw=result,
            latency_ms=latency_ms,
            session_graph=session_graph,
            tool_calls=tool_calls,
        )
