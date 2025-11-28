# core/common/change_set.py

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal

PatchOp = Literal["set"]


@dataclass
class ConfigPatch:
    """A single config update operation on a JSON config using dot-path syntax."""
    path: str              # e.g. "planning.clarification.enabled"
    op: PatchOp            # currently only "set"
    value: Any             # JSON-serializable value


@dataclass
class NewTestCase:
    """Optional new golden test row to add to the travel_golden CSV."""
    id: str
    input_json: str
    judge_question: str
    expected_behavior: str


@dataclass
class ChangeSet:
    """
    Represents a version upgrade proposal:
    - base_config -> new_config via patches
    - optional new tests to append to golden set
    """
    base_config_path: str
    new_config_path: str
    config_patches: List[ConfigPatch] = field(default_factory=list)
    new_tests: List[NewTestCase] = field(default_factory=list)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ChangeSet":
        patches = [
            ConfigPatch(
                path=p["path"],
                op=p.get("op", "set"),
                value=p.get("value"),
            )
            for p in data.get("config_patches", [])
        ]
        new_tests = [
            NewTestCase(
                id=str(t["id"]),
                input_json=t["input_json"],
                judge_question=t["judge_question"],
                expected_behavior=t["expected_behavior"],
            )
            for t in data.get("new_tests", [])
        ]
        return ChangeSet(
            base_config_path=data["base_config_path"],
            new_config_path=data["new_config_path"],
            config_patches=patches,
            new_tests=new_tests,
        )


# ----------------- helpers to apply patches -----------------


def _set_by_path(obj: Dict[str, Any], path: str, value: Any) -> None:
    """
    Set obj[parts[0]]...[parts[-1]] = value for dot-separated path.
    Creates intermediate dicts if needed.
    """
    parts = path.split(".")
    cur = obj
    for key in parts[:-1]:
        if key not in cur or not isinstance(cur[key], dict):
            cur[key] = {}
        cur = cur[key]
    cur[parts[-1]] = value


def apply_config_patches(config: Dict[str, Any], patches: List[ConfigPatch]) -> Dict[str, Any]:
    """
    Return a new config dict with all patches applied.
    """
    updated = copy.deepcopy(config)
    for patch in patches:
        if patch.op == "set":
            _set_by_path(updated, patch.path, patch.value)
        else:
            raise ValueError(f"Unsupported patch op: {patch.op}")
    return updated


def save_new_config(base_path: str | Path, new_path: str | Path, patches: List[ConfigPatch]) -> None:
    base = Path(base_path)
    new = Path(new_path)

    if not base.exists():
        raise FileNotFoundError(f"Base config not found: {base}")

    with base.open("r", encoding="utf-8") as f:
        cfg = json.load(f)

    updated = apply_config_patches(cfg, patches)

    new.parent.mkdir(parents=True, exist_ok=True)
    with new.open("w", encoding="utf-8") as f:
        json.dump(updated, f, indent=2, ensure_ascii=False)

    print(f"Saved new config to {new}")
