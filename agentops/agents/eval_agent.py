# agentops/agents/eval_agent.py

from __future__ import annotations

from typing import Any, Dict

from core.aut_spec import AUTSpec
from agentops.eval_engine.engine import EvalEngine


class EvalAgent:
    """
    EvalAgent:

    Orchestrates evaluation for a given AUT+version by delegating
    to EvalEngine (which already wires in EvalPacks, judge, tooling).

    This agent is what the supervisor pipeline uses for "run eval".
    """

    def __init__(self, spec: AUTSpec, eval_engine: EvalEngine):
        self.spec = spec
        self.eval_engine = eval_engine

    def run(self, version_id: str) -> Dict[str, Any]:
        """
        Execute the full evaluation for a particular version_id.

        Returns the EvalEngine summary dict, which includes:
          - aut_id
          - version_id
          - golden_path
          - num_testcases
          - avg_judge_score
          - records: List[EvalRecord-like dicts]
        """
        summary: Dict[str, Any] = self.eval_engine.run_full_eval(
            version_id=version_id
        )
        return summary
