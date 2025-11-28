# agentops/eval_engine/engine.py

from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional

from core.aut_client import AUTClient
from core.aut_spec import AUTSpec
from agentops.eval_engine.models import EvalRecord, MetricResult
from agentops.eval_packs.base import EvalPack
from agentops.memory.best_practices import BestPracticesMemory
from infra.traces_store import log_trace


class EvalEngine:
    """
    General evaluation engine for ADK-based AUTs.

    Responsibilities:
      - Load golden testcases for this AUT (from AUTSpec.evaluation.extra["golden_path"])
      - Call AUTClient for each testcase
      - Run one or more EvalPacks (LLM + rule-based metrics)
      - Write trace events to traces.jsonl
      - Store eval outcomes into BestPracticesMemory
      - Return a summary + per-test EvalRecords
    """

    def __init__(
        self,
        aut_client: AUTClient,
        eval_packs: List[EvalPack],
        aut_spec: AUTSpec,
    ):
        self.aut_client = aut_client
        self.eval_packs = eval_packs
        self.aut_spec = aut_spec

        # Golden path from AUTSpec.evaluation.extra.golden_path
        self._golden_path_str: Optional[str] = None
        self._golden_path_resolved: Optional[Path] = None

        if (
            self.aut_spec.evaluation
            and self.aut_spec.evaluation.extra
            and "golden_path" in self.aut_spec.evaluation.extra
        ):
            self._golden_path_str = self.aut_spec.evaluation.extra["golden_path"]

        # AgentOps-wide memory of best practices / eval outcomes
        # For now, a simple JSONL-backed store.
        self.memory = BestPracticesMemory("data/best_practices.jsonl")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_golden_path(self) -> Optional[Path]:
        """
        Resolve the golden CSV path to an absolute Path.

        If the path in the spec is relative, we treat it as:
          Path.cwd() / self._golden_path_str
        assuming scripts are run from the repo root (which you are doing).
        """
        if not self._golden_path_str:
            return None

        path = Path(self._golden_path_str)
        if not path.is_absolute():
            path = Path.cwd() / path

        self._golden_path_resolved = path
        return path

    def _load_testcases(self) -> List[Dict[str, Any]]:
        """
        Load golden testcases from CSV.

        Expected columns:
          - id
          - input_json
          - judge_question
          - expected_behavior
        """
        path = self._resolve_golden_path()
        if not path:
            print("[EvalEngine] No golden_path specified in AUTSpec.evaluation.extra.")
            return []

        if not path.exists():
            print(f"[EvalEngine] Golden file does not exist at: {path}")
            return []

        rows: List[Dict[str, Any]] = []
        try:
            with path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Skip completely empty rows
                    if not row.get("id"):
                        continue
                    rows.append(row)
        except Exception as e:
            print(f"[EvalEngine] Error reading golden file {path}: {e}")
            return []

        print(f"[EvalEngine] Loaded {len(rows)} testcases from {path}")
        return rows

    def _build_request_payload(self, testcase: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a golden testcase row into the request payload for the AUT.

        For travel:
          - testcase["input_json"] is a JSON string for the request.
        """
        raw = testcase.get("input_json") or "{}"
        if isinstance(raw, dict):
            # Already parsed (future flexibility)
            return raw
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: empty request; better than crashing
            print(f"[EvalEngine] Failed to parse input_json for testcase {testcase.get('id')}")
            return {}

    # ------------------------------------------------------------------
    # Public entrypoint used by supervisor: run_full_eval
    # ------------------------------------------------------------------
    def run_full_eval(self, version_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the full evaluation suite for this AUT version.

        version_id:
          - For now, informational; AUTClient may use its own default_version
          - We still put it into EvalRecords + traces for metrics/compare.
        """
        target_version = version_id or self.aut_spec.version or "v1"
        testcases = self._load_testcases()

        if not testcases:
            # Surface the resolved path to help with debugging
            path_str = (
                str(self._golden_path_resolved)
                if self._golden_path_resolved is not None
                else str(self._golden_path_str)
            )
            return {
                "error": "No testcases loaded from golden set.",
                "golden_path": path_str,
            }

        all_records: List[EvalRecord] = []

        for tc in testcases:
            record = self._run_single_eval_case(
                testcase=tc,
                version_id=target_version,
            )
            all_records.append(record)

            # Persist eval outcome to AgentOps memory
            try:
                self.memory.record_eval_outcome(record)
            except Exception as e:
                print(f"[EvalEngine] WARNING: failed to record eval outcome to memory: {e}")

        # ---------------- Aggregated metrics ----------------
        judge_scores_all: List[float] = []
        latencies_all: List[float] = []
        task_success_all: List[bool] = []

        for r in all_records:
            # LLM judge scores
            for m in r.llm_metrics:
                if m.name == "judge_score":
                    try:
                        judge_scores_all.append(float(m.value))
                    except Exception:
                        pass

            # Latency
            latency = r.aut_response_meta.get("latency_ms")
            if isinstance(latency, (int, float)):
                latencies_all.append(float(latency))

            # Rule-based task_success
            for m in r.rule_metrics:
                if m.name == "task_success":
                    try:
                        task_success_all.append(bool(m.value))
                    except Exception:
                        pass

        avg_judge_score = mean(judge_scores_all) if judge_scores_all else None

        def _p95(values: List[float]) -> Optional[float]:
            if not values:
                return None
            vs = sorted(values)
            # simple nearest-rank p95
            idx = int(0.95 * (len(vs) - 1))
            return vs[idx]

        judge_score_p95 = _p95(judge_scores_all)
        latency_ms_p95 = _p95(latencies_all)
        task_success_rate: Optional[float]
        if task_success_all:
            task_success_rate = sum(1 for v in task_success_all if v) / float(len(task_success_all))
        else:
            task_success_rate = None

        summary: Dict[str, Any] = {
            "aut_id": self.aut_spec.aut_id,
            "version_id": target_version,
            "golden_path": str(self._golden_path_resolved) if self._golden_path_resolved else None,
            "num_testcases": len(all_records),
            "avg_judge_score": avg_judge_score,
            "aggregated_metrics": {
                "judge_score_avg": avg_judge_score,
                "judge_score_p95": judge_score_p95,
                "latency_ms_p95": latency_ms_p95,
                "task_success_rate": task_success_rate,
            },
            "records": [self._record_to_dict(r) for r in all_records],
        }
        return summary

    # ------------------------------------------------------------------
    # Single testcase execution
    # ------------------------------------------------------------------
    def _run_single_eval_case(
        self,
        testcase: Dict[str, Any],
        version_id: str,
    ) -> EvalRecord:
        """
        Run a single testcase:
          - Build input payload
          - Call AUTClient
          - Run all EvalPacks
          - Log trace
          - Return EvalRecord
        """
        request_payload = self._build_request_payload(testcase)

        # Call AUT
        aut_response = self.aut_client.run_query(request_payload)

        # Run all EvalPacks and collect MetricResults
        metric_results: List[MetricResult] = []
        for pack in self.eval_packs:
            pack_results = pack.evaluate(
                testcase=testcase,
                aut_response=aut_response,
                aut_spec=self.aut_spec,
            )
            metric_results.extend(pack_results or [])

        # Split into LLM + rule metrics
        llm_metrics = [m for m in metric_results if m.details.get("type") == "llm"]
        rule_metrics = [m for m in metric_results if m.details.get("type") == "rule"]

        # Build EvalRecord
        eval_id = f"{self.aut_spec.aut_id}:{version_id}:{testcase.get('id')}"
        record = EvalRecord(
            eval_id=eval_id,
            aut_id=self.aut_spec.aut_id,
            version_id=version_id,
            capability="create_itinerary",  # for travel; generalizable later
            input=testcase,
            output={"answer": aut_response.answer},
            aut_response_meta={
                "latency_ms": aut_response.latency_ms,
                "session_graph": aut_response.session_graph,
                "tool_calls": aut_response.tool_calls,
            },
            llm_metrics=llm_metrics,
            rule_metrics=rule_metrics,
        )

        # Also log to traces.jsonl for metrics/compare
        judge_scores = [m.value for m in llm_metrics if m.name == "judge_score"]
        score_for_trace = judge_scores[0] if judge_scores else None
        reasoning_for_trace = None
        for m in llm_metrics:
            if m.name == "judge_score" and "reasoning" in m.details:
                reasoning_for_trace = m.details["reasoning"]
                break

        trace_event: Dict[str, Any] = {
            "version_id": version_id,
            "aut_id": self.aut_spec.aut_id,
            "testcase_id": testcase.get("id"),
            "input_json": testcase.get("input_json"),
            "answer": aut_response.answer,
            "latency_ms": aut_response.latency_ms,
            "eval_score": score_for_trace,
            "eval_reasoning": reasoning_for_trace,
        }
        log_trace(trace_event)

        return record

    # ------------------------------------------------------------------
    # Utility: convert EvalRecord to plain dict for JSON
    # ------------------------------------------------------------------
    def _record_to_dict(self, r: EvalRecord) -> Dict[str, Any]:
        return {
            "eval_id": r.eval_id,
            "aut_id": r.aut_id,
            "version_id": r.version_id,
            "capability": r.capability,
            "input": r.input,
            "output": r.output,
            "aut_response_meta": r.aut_response_meta,
            "llm_metrics": [self._metric_to_dict(m) for m in r.llm_metrics],
            "rule_metrics": [self._metric_to_dict(m) for m in r.rule_metrics],
        }

    @staticmethod
    def _metric_to_dict(m: MetricResult) -> Dict[str, Any]:
        return {
            "name": m.name,
            "value": m.value,
            "details": m.details,
        }
