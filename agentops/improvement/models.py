from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ConfigPatch:
    path: str         # e.g. "planning.clarification.enabled"
    op: str           # "set"
    value: Any


@dataclass
class NewTestcase:
    id: str
    input_json: str
    judge_question: str
    expected_behavior: str


@dataclass
class ChangeSet:
    aut_id: str
    base_config_path: str
    new_config_path: str
    config_patches: List[ConfigPatch] = field(default_factory=list)
    new_tests: List[NewTestcase] = field(default_factory=list)
    notes: str = ""
