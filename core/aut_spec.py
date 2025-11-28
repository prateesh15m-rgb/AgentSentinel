# core/aut_spec.py
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json
from pathlib import Path

# -------- Runtime + Tools + Eval helpers --------

@dataclass
class RuntimeConfig:
    """
    General runtime description.

    For now we mostly use:
      type = "adk"
      config["app_entrypoint"], config["root_agent"], config["config_file"]

    Later:
      type = "rest", "langgraph", "crew", "python", ...
    """
    type: str = "adk"                 # "adk" | "rest" | "python" | ...
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolSpec:
    id: str
    description: str = ""
    kind: str = "adk_tool"            # "adk_tool", "rest_tool", "mcp_tool", ...
    module: Optional[str] = None      # for Python/ADK tools
    endpoint: Optional[str] = None    # for REST tools
    mcp_server: Optional[str] = None  # for MCP tools
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HumanEvalConfig:
    """
    Optional human-in-the-loop settings for this AUT.
    """
    enabled: bool = False
    # e.g. "label_schema_id": "travel_task_success_v1"
    label_schema: Dict[str, Any] = field(default_factory=dict)
    # e.g. routing rules: when to ask humans
    routing_rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationConfig:
    """
    Evaluation configuration for this AUT.
    """
    default_pack: str = "generic_adk"      # name of eval pack
    metrics: List[str] = field(default_factory=list)
    llm_judge: Dict[str, Any] = field(default_factory=dict)
    human: HumanEvalConfig = field(default_factory=HumanEvalConfig)
    extra: Dict[str, Any] = field(default_factory=dict)


# -------- Main AUTSpec --------

@dataclass
class AUTSpec:
    aut_id: str
    name: str
    version: str
    description: str = ""

    # NEW: runtime info (general)
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)

    # Keep these to stay compatible with your current YAML + code
    adk: Dict[str, Any] = field(default_factory=dict)

    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    tools: List[ToolSpec] = field(default_factory=list)
    capabilities: Dict[str, Any] = field(default_factory=dict)
    risk_profile: Dict[str, Any] = field(default_factory=dict)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)

    # Entire raw YAML/JSON in case you need framework-specific details later
    raw: Dict[str, Any] = field(default_factory=dict)

    # ---------- Convenience helpers for ADK today ----------

    @property
    def app_entrypoint(self) -> Optional[str]:
        """
        For ADK: the Python path to the app factory, if present.
        """
        # Prefer runtime.config, fall back to old 'adk' section
        return (
            self.runtime.config.get("app_entrypoint")
            or self.adk.get("app_entrypoint")
        )

    @property
    def root_agent(self) -> Optional[str]:
        return (
            self.runtime.config.get("root_agent")
            or self.adk.get("root_agent")
        )

    @property
    def config_file(self) -> Optional[str]:
        return (
            self.runtime.config.get("config_file")
            or self.adk.get("config_file")
        )

    # ---------- Loader from YAML/JSON spec ----------

    @staticmethod
    def load_from_file(path: Path) -> "AUTSpec":
        """
        Load an AUTSpec from YAML or JSON file.
        Supports your current travel_planner_v1.aut.yaml format.
        """
        import yaml  # type: ignore

        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(text)
        else:
            data = json.loads(text)

        # Core required fields
        aut_id = data["aut_id"]
        name = data.get("name", aut_id)
        version = data.get("version", "v1")
        description = data.get("description", "")

        # Runtime + ADK (backwards-compatible)
        adk_section = data.get("adk", {}) or {}
        runtime_section = data.get("runtime", {}) or {}

        runtime_type = runtime_section.get("type", "adk")
        runtime_config = runtime_section.get("config", {})

        # For ADK, make sure key fields are present in runtime.config
        for key in ("app_entrypoint", "root_agent", "config_file"):
            if key in adk_section and key not in runtime_config:
                runtime_config[key] = adk_section[key]

        runtime = RuntimeConfig(
            type=runtime_type,
            config=runtime_config,
        )

        # Tools
        tools_raw = data.get("tools", []) or []
        tools: List[ToolSpec] = []
        for t in tools_raw:
            known_keys = {
                "id",
                "name",
                "description",
                "kind",
                "module",
                "endpoint",
                "mcp_server",
            }
            tools.append(
                ToolSpec(
                    id=t.get("id") or t.get("name"),
                    description=t.get("description", ""),
                    kind=t.get("kind", "adk_tool"),
                    module=t.get("module"),
                    endpoint=t.get("endpoint"),
                    mcp_server=t.get("mcp_server"),
                    extra={k: v for k, v in t.items() if k not in known_keys},
                )
            )

        # Evaluation + human-in-the-loop
        eval_raw = data.get("evaluation", {}) or {}
        human_raw = eval_raw.get("human_review", {}) or {}

        evaluation = EvaluationConfig(
            default_pack=eval_raw.get("default_pack", eval_raw.get("default_golden_set", "generic_adk")),
            metrics=eval_raw.get("metrics", []),
            llm_judge=eval_raw.get("judge", {}),
            human=HumanEvalConfig(
                enabled=bool(human_raw.get("enabled", False)),
                label_schema=human_raw.get("label_schema", {}),
                routing_rules=human_raw.get("routing_rules", {}),
            ),
            extra={k: v for k, v in eval_raw.items() if k not in {"default_pack", "default_golden_set", "metrics", "judge", "human_review"}},
        )

        return AUTSpec(
            aut_id=aut_id,
            name=name,
            version=version,
            description=description,
            runtime=runtime,
            adk=adk_section,  # keep for now
            inputs=data.get("inputs", {}),
            outputs=data.get("outputs", {}),
            tools=tools,
            capabilities=data.get("capabilities", {}),
            risk_profile=data.get("risk_profile", {}),
            evaluation=evaluation,
            raw=data,
        )
