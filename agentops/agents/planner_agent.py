# agentops/agents/planner_agent.py

from __future__ import annotations

from typing import Any, Dict

from core.aut_spec import AUTSpec
from agentops.improvement.planner import PlannerEngine
from infra.memory_store import append_memory


class PlannerAgent:
    """
    PlannerAgent:

    Wraps PlannerEngine to:
      - propose a ChangeSet for a given version_id
      - log the config changes into long-term memory

    We intentionally keep this thin so we don't disturb your
    already-working PlannerEngine/improve flow.
    """

    def __init__(self, spec: AUTSpec, planner_engine: PlannerEngine):
        self.spec = spec
        self.planner_engine = planner_engine

    def run(
        self,
        version_id: str,
        eval_summary: Dict[str, Any] | None = None,
        memory_summary: Dict[str, Any] | None = None,
    ):
        """
        Propose a new ChangeSet for this AUT+version.

        We call into PlannerEngine.propose_changeset(version_id=...)
        (or your existing signature) and then persist the patches to
        the memory store as a 'config_change' memory entry.
        """
        # Note: assuming your PlannerEngine already accepts version_id
        # and knows how to load evals internally (from traces, etc.).
        changeset = self.planner_engine.propose_changeset(version_id=version_id)

        patches = []
        if hasattr(changeset, "config_patches"):
            for p in changeset.config_patches:
                if hasattr(p, "__dict__"):
                    patches.append(p.__dict__)
                else:
                    patches.append(p)
        else:
            # generic fallback
            patches = getattr(changeset, "patches", [])

        # Persist a high-level record of this config change
        append_memory(
            {
                "type": "config_change",
                "aut_id": getattr(self.spec, "aut_id", None),
                "version_id": version_id,
                "patch_count": len(patches),
                "patches": patches,
                "eval_context": {
                    "avg_judge_score": eval_summary.get("avg_judge_score")
                    if eval_summary
                    else None,
                    "num_testcases": eval_summary.get("num_testcases")
                    if eval_summary
                    else None,
                },
                "memory_context": memory_summary,
            }
        )

        return changeset
