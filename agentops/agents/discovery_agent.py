# agentops/agents/discovery_agent.py

from __future__ import annotations

from typing import Any, Dict

from core.aut_spec import AUTSpec


class DiscoveryAgent:
    """
    DiscoveryAgent:

    Given an AUTSpec, produces a structured capability profile
    that can be used by other agents (EvalAgent, PlannerAgent, etc.).
    """

    def __init__(self, spec: AUTSpec):
        self.spec = spec

    def run(self) -> Dict[str, Any]:
        """
        Return a high-level profile of the AUT.

        Mirrors the behavior of the 'discover' CLI command, but in
        agent form so it can participate in A2A flows.
        """
        spec = self.spec

        profile: Dict[str, Any] = {
            "aut_id": getattr(spec, "aut_id", None),
            "name": getattr(spec, "name", None),
            "version": getattr(spec, "version", None),
            "description": getattr(spec, "description", None),
            "adk": getattr(spec, "adk", None),
            "inputs_schema": getattr(spec, "inputs", None),
            "outputs_schema": getattr(spec, "outputs", None),
            "tools": getattr(spec, "tools", None),
            "flows": getattr(spec, "flows", None),
            "capabilities": getattr(spec, "capabilities", None),
            "risk_profile": getattr(spec, "risk_profile", None),
            "evaluation": getattr(spec, "evaluation", None),
        }

        return profile
