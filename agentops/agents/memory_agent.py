# agentops/agents/memory_agent.py

from __future__ import annotations

from typing import Any, Dict, List

from core.aut_spec import AUTSpec
from infra.memory_store import append_memory


class MemoryAgent:
    """
    MemoryAgent:

    Consumes evaluation summaries and writes long-term memories
    that capture:
      - best practices (high judge_score)
      - failure patterns (low judge_score)
      - testcases & reasoning that led to changes

    These memories live in data/memory/bank.jsonl and can be reused
    across AUTs and versions in the future.
    """

    def __init__(self, spec: AUTSpec, score_threshold: float = 4.0):
        self.spec = spec
        self.score_threshold = score_threshold

    def _extract_judge_metric(self, record: Dict[str, Any]) -> Dict[str, Any] | None:
        for m in record.get("llm_metrics", []):
            if m.get("name") == "judge_score":
                return m
        return None

    def run(self, eval_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process eval_summary (from EvalAgent) and persist memories.

        eval_summary["records"] is expected to be a list of dicts like:
          {
            "aut_id": ...,
            "version_id": ...,
            "input": {...},
            "output": {...},
            "llm_metrics": [...],
            "rule_metrics": [...],
          }
        """
        aut_id = eval_summary.get("aut_id", getattr(self.spec, "aut_id", None))
        version_id = eval_summary.get("version_id", getattr(self.spec, "version", None))

        records: List[Dict[str, Any]] = eval_summary.get("records", [])

        best_practices = 0
        failures = 0

        for rec in records:
            tc = rec.get("input", {})
            judge = self._extract_judge_metric(rec)
            if not judge:
                continue

            try:
                score = float(judge.get("value", 0.0))
            except Exception:
                score = 0.0

            details = judge.get("details", {}) or {}
            reasoning = details.get("reasoning")
            rubric_id = details.get("rubric_id")

            base_entry = {
                "aut_id": rec.get("aut_id", aut_id),
                "version_id": rec.get("version_id", version_id),
                "testcase_id": tc.get("id"),
                "judge_score": score,
                "judge_reasoning": reasoning,
                "rubric_id": rubric_id,
                "judge_question": tc.get("judge_question"),
                "expected_behavior": tc.get("expected_behavior"),
            }

            if score >= self.score_threshold:
                append_memory(
                    {
                        "type": "best_practice",
                        **base_entry,
                    }
                )
                best_practices += 1
            else:
                append_memory(
                    {
                        "type": "failure_pattern",
                        **base_entry,
                    }
                )
                failures += 1

        return {
            "aut_id": aut_id,
            "version_id": version_id,
            "records_seen": len(records),
            "best_practices_written": best_practices,
            "failure_patterns_written": failures,
        }
