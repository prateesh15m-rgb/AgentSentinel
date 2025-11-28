# agentops/eval_engine/models.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class MetricResult:
    """
    Single metric output from an evaluator (EvalPack).

    Examples:
      - name="judge_score", value=4.5,
        details={"type": "llm", "reasoning": "...", "model": "gemini-2.5-pro"}

      - name="task_success", value=True,
        details={"type": "rule", "reason": "non_empty_answer"}
    """
    name: str
    value: Any
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalRecord:
    """
    Full evaluation record for a single testcase.

    Used by:
      - EvalEngine (producer)
      - PlannerEngine (consumer for improvements)
      - Supervisor (for JSON summaries, comparisons, dashboards, etc.)

    One EvalRecord corresponds to:
      - a single golden testcase row
      - one AUT invocation
      - all metrics computed for that run
    """
    eval_id: str
    aut_id: str
    version_id: str
    capability: str

    # Golden testcase input row
    # (id, input_json, judge_question, expected_behavior, etc.)
    input: Dict[str, Any]

    # Normalized AUT output
    # e.g. {"answer": "...markdown..."} or richer in future
    output: Dict[str, Any]

    # Metadata about the AUT run (latency, tools, session graph, etc.)
    aut_response_meta: Dict[str, Any] = field(default_factory=dict)

    # Metrics
    llm_metrics: List[MetricResult] = field(default_factory=list)
    rule_metrics: List[MetricResult] = field(default_factory=list)
