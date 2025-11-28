# agentops/eval_packs/generic_adk_pack.py
from typing import Dict, Any, List
from agentops.eval_packs.base import EvalPack
from core.aut_client import AUTResponse
from core.aut_spec import AUTSpec
from agentops.eval_engine.models import MetricResult
from agentops.eval_agent import evaluate_answer  # your existing LLM judge


class GenericADKEvalPack(EvalPack):
    name = "generic_adk"

    def evaluate(
        self,
        testcase: Dict[str, Any],
        aut_response: AUTResponse,
        aut_spec: AUTSpec,
    ) -> List[MetricResult]:
        # generic instruction following + quality check
        judge_result = evaluate_answer(
            question=testcase["question"],
            expected_behavior=testcase.get("expected_behavior", ""),
            model_answer=aut_response.answer,
        )
        return [
            MetricResult(
                name="generic_quality",
                score=judge_result["score"],
                details={"type": "llm", "reason": judge_result["reasoning"]},
            )
        ]
