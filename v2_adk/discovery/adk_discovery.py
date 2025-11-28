# v2_adk/discovery/adk_discovery.py
from pathlib import Path
from typing import Optional
import json
import yaml

from core.aut_spec import AUTSpec, ModelSpec, ToolSpec, FlowSpec, SessionConfig, MemoryConfig, EvaluationConfig


def discover_adk_agent(project_path: str | Path) -> AUTSpec:
    """
    Inspect an ADK agent project directory and construct an AUTSpec.
    Assumes ADK configs live under `specs/` in JSON or YAML format.
    """
    root = Path(project_path)
    # 1) Find ADK config files
    # 2) Load root agent + tools + model name
    # 3) Infer flows (sequential / loop)
    # 4) Build AUTSpec object
    # 5) Optionally dump to YAML beside configs

    # Skeleton structure:
    model_specs: list[ModelSpec] = [...]
    tool_specs: list[ToolSpec] = [...]
    flow_spec = FlowSpec(type="sequential", allow_iterations=True)
    session_cfg = SessionConfig(enabled=True, service_class="InMemorySessionService")
    memory_cfg = MemoryConfig(enabled=False, kind="none")
    eval_cfg = EvaluationConfig(default_pack="generic_adk", metrics=["correctness", "latency"])

    aut_spec = AUTSpec(
        aut_id="travel_planner",
        version="travel_v1",
        root_agent="travel_root",
        models=model_specs,
        tools=tool_specs,
        flows=flow_spec,
        capabilities=["itinerary_planning"],
        sessions=session_cfg,
        memory=memory_cfg,
        evaluation=eval_cfg,
    )

    return aut_spec


def save_aut_spec(aut_spec: AUTSpec, output_path: str | Path) -> None:
    data = _aut_spec_to_dict(aut_spec)
    with open(output_path, "w") as f:
        yaml.safe_dump(data, f)


def load_aut_spec(path: str | Path) -> AUTSpec:
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    # reconstruct AUTSpec from dict...
    ...
