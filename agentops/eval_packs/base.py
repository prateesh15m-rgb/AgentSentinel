# agentops/eval_packs/base.py

from __future__ import annotations

from typing import Dict, Any, List

from core.aut_client import AUTResponse
from core.aut_spec import AUTSpec
from agentops.eval_engine.models import MetricResult


class EvalPack:
    """
    Base class for evaluation packs.

    Subclasses should implement `evaluate`.
    """

    name: str = "base_pack"

    def evaluate(
        self,
        testcase: Dict[str, Any],
        aut_response: AUTResponse,
        aut_spec: AUTSpec,
    ) -> List[MetricResult]:
        raise NotImplementedError("EvalPack subclasses must implement `evaluate`.")
