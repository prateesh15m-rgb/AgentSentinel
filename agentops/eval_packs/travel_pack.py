# agentops/eval_packs/travel_pack.py

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from core.aut_spec import AUTSpec
from agentops.eval_engine.models import MetricResult


class TravelEvalPack:
    """
    Evaluation pack for the travel_planner AUT.

    CONTRACT with EvalEngine:
      - EvalEngine calls:
          pack.evaluate(testcase=..., aut_response=..., aut_spec=...)
      - This method MUST return: List[MetricResult]

    Responsibilities:
      - For each testcase + aut_response:
          * Run rule-based checks (e.g., non-empty answer -> task_success)
          * Optionally run LLM judge (Gemini) to score response 1–5
      - It does NOT:
          * Load golden CSV (EvalEngine does that)
          * Call the AUT (EvalEngine already did that)
          * Build EvalRecord (EvalEngine builds records)
    """

    RULE_TASK_SUCCESS_NAME = "task_success"
    LLM_JUDGE_METRIC_NAME = "judge_score"

    def __init__(self, aut_spec: AUTSpec):
        self.aut_spec = aut_spec
        self.aut_id = aut_spec.aut_id

        eval_cfg = aut_spec.evaluation

        # Metrics configuration from AUT spec
        self.metrics_cfg: List[str] = list(eval_cfg.metrics or [])

        # Extra config (judge model, rubric, etc.)
        extra = eval_cfg.extra or {}

        self.llm_model_name: str = (
            extra.get("judge_model")
            or os.getenv("AGENTOPS_LLM_MODEL")
            or "gemini-2.5-pro"
        )
        self.llm_rubric_id: str = extra.get("judge_rubric_id", "travel_itinerary_v1")

        # Optional kill switch for LLM judge via env
        self.disable_llm_judge_env: bool = (
            os.getenv("AGENTOPS_DISABLE_LLM_JUDGE", "").strip().lower()
            in {"1", "true", "yes", "on"}
        )

        print(
            f"[TravelEvalPack] init: aut_id={self.aut_id}, "
            f"metrics_cfg={self.metrics_cfg}, "
            f"llm_model={self.llm_model_name}, "
            f"rubric={self.llm_rubric_id}, "
            f"disable_llm_judge_env={self.disable_llm_judge_env}"
        )

    # ------------------------------------------------------------------
    # Public API used by EvalEngine
    # ------------------------------------------------------------------
    def evaluate(
        self,
        testcase: Dict[str, Any],
        aut_response: Any,
        aut_spec: Optional[AUTSpec] = None,
        **kwargs: Any,
    ) -> List[MetricResult]:
        """
        Compute metrics for a single testcase + AUT response.

        Args (as passed by EvalEngine._run_single_eval_case):
          - testcase: golden row (id, input_json, judge_question, expected_behavior, ...)
          - aut_response: object returned by AUTClient.run_query(...)
          - aut_spec: AUTSpec (not strictly needed here)

        Returns:
          List[MetricResult]
        """
        # Normalize output
        answer = getattr(aut_response, "answer", "") or ""
        output = {"answer": answer}

        metrics: List[MetricResult] = []

        # 1) Rule metrics
        if self._wants_metric(self.RULE_TASK_SUCCESS_NAME):
            metrics.extend(self._rule_non_empty_answer(output))

        # 2) LLM judge metric (Gemini)
        if self._wants_metric(self.LLM_JUDGE_METRIC_NAME) and not self.disable_llm_judge_env:
            try:
                judge_metric = self._run_llm_judge(
                    row=testcase,
                    output=output,
                )
                if judge_metric is not None:
                    metrics.append(judge_metric)
            except Exception as e:
                print(
                    f"[TravelEvalPack] ERROR: LLM judge failed for testcase {testcase.get('id')}: {e}"
                )
        else:
            if self._wants_metric(self.LLM_JUDGE_METRIC_NAME):
                print(
                    f"[TravelEvalPack] Skipping LLM judge for testcase {testcase.get('id')} "
                    f"(AGENTOPS_DISABLE_LLM_JUDGE={self.disable_llm_judge_env})"
                )

        return metrics

    # ------------------------------------------------------------------
    # Metric selection
    # ------------------------------------------------------------------
    def _wants_metric(self, metric_name: str) -> bool:
        """
        Returns True if this per-case metric should be computed, based on the
        `metrics` list in AUTSpec.evaluation.

        Example metrics config in AUTSpec:
          ["task_success", "judge_score_avg", "judge_score_p95", "latency_ms_p95"]

        We treat:
          - "task_success" -> compute rule metric task_success
          - any "judge_score*" -> compute base judge_score metric
        """
        if not self.metrics_cfg:
            # If no metrics are declared, compute everything by default.
            return True

        if metric_name == self.RULE_TASK_SUCCESS_NAME:
            return self.RULE_TASK_SUCCESS_NAME in self.metrics_cfg

        if metric_name == self.LLM_JUDGE_METRIC_NAME:
            # If they reference judge_score or any aggregate of it, compute base metric
            return any(m.startswith("judge_score") for m in self.metrics_cfg)

        # Default: off
        return False

    # ------------------------------------------------------------------
    # Rule metrics
    # ------------------------------------------------------------------
    def _rule_non_empty_answer(self, output: Dict[str, Any]) -> List[MetricResult]:
        """
        Simple rule metric:
          - task_success = True if answer is non-empty string
        """
        answer = (output.get("answer") or "").strip()
        success = bool(answer)

        metric = MetricResult(
            name=self.RULE_TASK_SUCCESS_NAME,
            value=success,
            details={
                "type": "rule",
                "reason": "non_empty_answer" if success else "empty_answer",
            },
        )
        return [metric]

    # ------------------------------------------------------------------
    # LLM judge metric (Gemini)
    # ------------------------------------------------------------------
    def _run_llm_judge(
        self,
        row: Dict[str, Any],
        output: Dict[str, Any],
    ) -> Optional[MetricResult]:
        """
        Call Gemini to judge the quality of the AUT answer for this testcase.

        Returns:
          MetricResult(name="judge_score", value=<1–5>, details=...) or None.
        """
        print("[TravelEvalPack] _run_llm_judge: starting Gemini call")

        try:
            import google.generativeai as genai  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "google.generativeai is not installed. "
                "Install it or disable LLM judge via metrics or AGENTOPS_DISABLE_LLM_JUDGE."
            ) from e

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY or GOOGLE_API_KEY is not set in the environment. "
                "Set one of them or disable LLM judge."
            )

        genai.configure(api_key=api_key)

        judge_question = row.get("judge_question") or ""
        expected_behavior = row.get("expected_behavior") or ""
        answer = (output.get("answer") or "").strip()
        rubric = self.llm_rubric_id

        prompt = f"""
You are an expert travel itinerary evaluator.

Rubric ID: {rubric}

GOLDEN TESTCASE:
- Judge question: {judge_question}
- Expected behavior: {expected_behavior}

MODEL ANSWER:
{answer}

Score the answer on a scale of 1 to 5, where:
1 = Very poor
2 = Weak
3 = Acceptable
4 = Good
5 = Excellent

Return ONLY a JSON object with:
- "score": number (1–5)
- "rationale": short explanation
"""

        model = genai.GenerativeModel(self.llm_model_name)
        resp = model.generate_content(prompt)

        # Try to extract text content robustly
        text = getattr(resp, "text", None)
        if not text:
            try:
                candidate = resp.candidates[0]
                content = getattr(candidate, "content", candidate)
                parts = getattr(content, "parts", [])
                text = "".join(getattr(p, "text", "") for p in parts)
            except Exception:
                text = ""

        text_stripped = (text or "").strip()
        print(f"[TravelEvalPack] Gemini raw response: {text_stripped[:200]}")

        # Parse JSON
        score: float
        rationale: str
        try:
            parsed = json.loads(text_stripped)
            score = float(parsed.get("score", 0))
            rationale = parsed.get("rationale", text_stripped)
        except Exception:
            # Fallback: extract first 1–5 in the text
            import re

            m = re.search(r"\b([1-5])\b", text_stripped)
            if m:
                score = float(m.group(1))
            else:
                score = 0.0
            rationale = text_stripped

        metric = MetricResult(
            name=self.LLM_JUDGE_METRIC_NAME,
            value=score,
            details={
                "type": "llm",
                "reasoning": rationale,
                "model": self.llm_model_name,
                "rubric_id": rubric,
            },
        )
        print(f"[TravelEvalPack] Created judge_score metric: {score}")
        return metric
