# agentops/agents/human_agent.py

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict


class HumanReviewAgent:
    """
    HumanReviewAgent:

    Implements a simple Human-in-the-Loop (HITL) pattern by:
      - writing proposed ChangeSets into a review queue file
      - returning metadata that the supervisor can surface

    This is intentionally simple (JSONL file) but demonstrates
    how HITL fits into the AgentOps loop.
    """

    REVIEW_QUEUE_FILE = Path("data/hitl/review_queue.jsonl")

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def _ensure_dir(self):
        self.REVIEW_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _serialize_changeset(self, changeset: Any) -> Dict[str, Any]:
        if hasattr(changeset, "to_dict"):
            return changeset.to_dict()
        if is_dataclass(changeset):
            return asdict(changeset)
        if hasattr(changeset, "__dict__"):
            return dict(changeset.__dict__)
        return {"raw": repr(changeset)}

    def run(self, changeset: Any, require_review: bool = True) -> Dict[str, Any]:
        """
        If HITL is enabled and review is required, enqueue the ChangeSet
        to the review queue and return a handle.

        Otherwise, indicate auto-approval.
        """
        if not self.enabled or not require_review:
            return {
                "hitl_enabled": self.enabled,
                "review_required": False,
                "status": "auto_approved",
            }

        self._ensure_dir()
        record = {
            "status": "pending",
            "changeset": self._serialize_changeset(changeset),
        }

        with self.REVIEW_QUEUE_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        return {
            "hitl_enabled": True,
            "review_required": True,
            "status": "queued_for_review",
            "queue_file": str(self.REVIEW_QUEUE_FILE),
        }
