# agentops/memory/best_practices.py

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


@dataclass
class BestPractice:
    """
    Represents a single best practice or planned improvement related to
    agent design, prompts, evals, or config tweaks.

    This ties into the *Memory & Context Engineering* concept from the course:
    a persistent store of "what good looks like" and "what we changed".
    """
    id: str
    title: str
    description: str
    category: str = "general"  # e.g. "evals", "planning", "latency"
    source: Optional[str] = None  # e.g. "Day 2 - Evals", "Internal experiment"


@dataclass
class PromptTweakImprovement:
    """
    Represents a planned improvement to an AUT's behavior, so we can later
    correlate config/prompt changes with eval outcomes.
    """
    aut_id: str
    base_version: str
    new_version: str
    description: str
    expected_impact: str


class BestPracticesMemory:
    """
    File-backed memory for best practices, planned improvements, and eval outcomes.

    This is NOT user chat history; it's a curated knowledge base
    the Supervisor / PlannerEngine / EvalEngine can use to:
      - inject best practices into prompts,
      - track which changes we *intended* to make,
      - log eval outcomes for later correlation with changes.

    For the capstone, a simple JSONL file is enough.
    """

    def __init__(self, path: Optional[str] = None) -> None:
        # Example path used by PlannerEngine: "data/best_practices.jsonl"
        self.path = Path(path) if path else None
        self._best_practices: Dict[str, BestPractice] = {}
        self._prompt_tweaks: List[PromptTweakImprovement] = []
        self._eval_outcomes: List[Dict[str, Any]] = []

        # Best effort load from disk if a path is provided.
        if self.path and self.path.exists():
            self._load_from_file()

    # ------------------------------------------------------------------
    # Internal persistence helpers
    # ------------------------------------------------------------------
    def _load_from_file(self) -> None:
        try:
            with self.path.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    if obj.get("type") == "best_practice":
                        bp = BestPractice(
                            id=obj["id"],
                            title=obj["title"],
                            description=obj["description"],
                            category=obj.get("category", "general"),
                            source=obj.get("source"),
                        )
                        self._best_practices[bp.id] = bp
                    elif obj.get("type") == "prompt_tweak":
                        pt = PromptTweakImprovement(
                            aut_id=obj["aut_id"],
                            base_version=obj["base_version"],
                            new_version=obj["new_version"],
                            description=obj["description"],
                            expected_impact=obj["expected_impact"],
                        )
                        self._prompt_tweaks.append(pt)
                    elif obj.get("type") == "eval_outcome":
                        # Eval outcomes are stored as raw dicts.
                        self._eval_outcomes.append(obj)
        except Exception as e:
            print(f"[BestPracticesMemory] WARNING: failed to load from {self.path}: {e}")

    def _append_to_file(self, record: Dict[str, Any]) -> None:
        if not self.path:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as f:
                # default=str ensures objects like EvalRecord become strings
                f.write(json.dumps(record, default=str) + "\n")
        except Exception as e:
            print(f"[BestPracticesMemory] WARNING: failed to append to {self.path}: {e}")

    # ------------------------------------------------------------------
    # Public API for best practices
    # ------------------------------------------------------------------
    def upsert_best_practice(self, bp: BestPractice) -> None:
        self._best_practices[bp.id] = bp
        self._append_to_file({"type": "best_practice", **asdict(bp)})

    def list_best_practices(self, category: Optional[str] = None) -> List[BestPractice]:
        items = list(self._best_practices.values())
        if category:
            items = [bp for bp in items if bp.category == category]
        return items

    def best_practices_prompt_block(self, category: Optional[str] = None) -> str:
        """
        Render best practices as a text block for use in prompts
        (Context Engineering).
        """
        items = self.list_best_practices(category)
        if not items:
            return ""
        lines = ["Best practices to consider:"]
        for bp in items:
            lines.append(f"- {bp.title}: {bp.description}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Public API for planned improvements (used by PlannerEngine)
    # ------------------------------------------------------------------
    def record_prompt_tweak_improvement(
        self,
        aut_id: str,
        base_version: str,
        new_version: str,
        description: str,
        expected_impact: str,
    ) -> None:
        """
        Called by PlannerEngine when we *plan* a config/prompt/test change.
        This is how we create a longitudinal "memory" of changes.

        This maps directly to the course concept of:
          - Memory & eval correlation,
          - Governance / audit trail of changes.
        """
        pt = PromptTweakImprovement(
            aut_id=aut_id,
            base_version=base_version,
            new_version=new_version,
            description=description,
            expected_impact=expected_impact,
        )
        self._prompt_tweaks.append(pt)
        record = {"type": "prompt_tweak", **asdict(pt)}
        self._append_to_file(record)

    def list_prompt_tweaks(self) -> List[PromptTweakImprovement]:
        return list(self._prompt_tweaks)

    # ------------------------------------------------------------------
    # Public API for eval outcomes (used by EvalEngine)
    # ------------------------------------------------------------------
    def record_eval_outcome(self, *args: Any, **kwargs: Any) -> None:
        """
        Called by EvalEngine after an eval run.

        We keep this intentionally flexible (args/kwargs) so it won't
        break if the EvalEngine changes its signature. We just persist
        whatever it sends as an 'eval_outcome' record.

        This supports:
          - Memory linked to evals,
          - Governance & audit trail of model performance over time.
        """
        record: Dict[str, Any] = {"type": "eval_outcome"}

        # If EvalEngine passes positional data, store it under 'args'.
        if args:
            # Objects like EvalRecord will be made JSON-safe by default=str in _append_to_file
            record["args"] = list(args)

        # Any keyword fields from EvalEngine get merged in.
        record.update(kwargs)

        self._eval_outcomes.append(record)
        self._append_to_file(record)

    def list_eval_outcomes(self) -> List[Dict[str, Any]]:
        """
        Return all eval outcome records currently in memory.
        """
        return list(self._eval_outcomes)
