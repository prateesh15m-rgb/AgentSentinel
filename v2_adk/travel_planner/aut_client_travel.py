# v2_adk/travel_planner/aut_client_travel.py

from __future__ import annotations

from typing import Any, Dict, Optional

from core.aut_client import AUTClient, AUTResponse
from core.aut_spec import AUTSpec
from v2_adk.travel_planner.app.travel_runtime import TravelADKRuntime


class TravelAUTClient(AUTClient):
    """
    AUTClient implementation that wraps the ADK-based travel planner.

    Used by:
      - EvalEngine (via run_query)
      - Supervisor (via run_once for interactive runs)
    """

    def __init__(self, spec: AUTSpec, default_version: str):
        self.aut_id = spec.aut_id
        self.default_version = default_version
        self._runtime = TravelADKRuntime(spec, default_version=default_version)

    # ------------------------------------------------------------------
    # API used by EvalEngine
    # ------------------------------------------------------------------
    def run_query(
        self,
        input: Dict[str, Any],
        context: Optional[ Dict[str, Any] ] = None,
    ) -> AUTResponse:
        """
        Core interface for the EvalEngine.

        `context` may carry version_id or other flags in the future.
        """
        version_id = None
        if context:
            version_id = context.get("version_id") or context.get("version")

        if version_id is None:
            version_id = self.default_version

        return self._runtime.run_once(version_id=version_id, request=input)

    # ------------------------------------------------------------------
    # Convenience used by Supervisor CLI 'run' command
    # ------------------------------------------------------------------
    def run_once(
        self,
        version_id: Optional[str],
        request: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Helper for the CLI: returns a JSON-serializable dict with
        normalized fields for pretty-printing.
        """
        vid = version_id or self.default_version
        resp = self._runtime.run_once(version_id=vid, request=request)

        return {
            "answer": resp.answer,
            "latency_ms": resp.latency_ms,
            "session_graph": resp.session_graph,
            "tool_calls": resp.tool_calls,
            "raw": resp.raw,
        }
