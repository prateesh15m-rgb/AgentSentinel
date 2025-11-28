#!/usr/bin/env python
from __future__ import annotations

"""
AgentOps Autopilot — Universal ADK Supervisor (CLI)

Multi-agent framing (for capstone narrative):

- Supervisor Agent (this CLI)
    Orchestrates everything: discover, run, eval, improve, metrics, compare.
- Eval Agent
    Implemented as EvalEngine + one or more EvalPacks (here: TravelEvalPack).
    Calls the AUT, runs rule metrics + Gemini LLM judge, logs traces.
- Planner / Critic Agents
    Implemented inside PlannerEngine:
      * PlannerAgent: reads eval history + best-practices memory, proposes config
        patches + new golden testcases.
      * CriticAgent: reviews those proposals against goals/constraints and
        returns a refined “changeset” for the human + AUT.

This file is the HUMAN interface to that multi-agent loop.
"""

import argparse
import json
import sys
from dataclasses import is_dataclass, asdict
from pathlib import Path
from typing import Any, Dict

# --------------------------------------------------------------------
# Ensure repo root on sys.path
# --------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --------------------------------------------------------------------
# Core imports
# --------------------------------------------------------------------
from core.aut_spec import AUTSpec
from infra.traces_store import load_traces

# Eval + Improvement engines
from agentops.eval_engine.engine import EvalEngine
from agentops.eval_packs.travel_pack import TravelEvalPack
from agentops.improvement.planner import PlannerEngine

# AUT Clients
from v2_adk.travel_planner.aut_client_travel import TravelAUTClient

# Optional metrics summary tool (reads traces.jsonl)
from agentops.run_metrics_summary import main as metrics_summary_main


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------
def _json_fallback(o: Any) -> Any:
    """
    Fallback serializer for pretty():
      - If object has .to_dict(), use that
      - If it's a dataclass, use asdict()
      - Otherwise, use str()
    """
    if hasattr(o, "to_dict") and callable(getattr(o, "to_dict")):
        return o.to_dict()
    if is_dataclass(o):
        return asdict(o)
    return str(o)


def pretty(obj: Any) -> None:
    """Pretty-print a Python object as JSON, robust to custom types."""
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=_json_fallback))


def load_aut_spec(path: Path) -> AUTSpec:
    """Load an AUTSpec from YAML or JSON."""
    if not path.exists():
        raise FileNotFoundError(f"AUT spec not found: {path}")
    return AUTSpec.load_from_file(path)


# --------------------------------------------------------------------
# Factory: Build runtime (AUTClient, EvalEngine, PlannerEngine)
# --------------------------------------------------------------------
def build_runtime_for_aut(spec: AUTSpec, default_version: str):
    """
    Creates runtime triplet (AUTClient, EvalEngine, PlannerEngine)
    depending on the AUT type.

    Conceptual mapping to agents (for capstone):

      - AUTClient        → The underlying task agent / AUT
      - EvalEngine       → Eval Agent (calls AUT + eval packs)
      - PlannerEngine    → Planner + Critic Agents (propose_changeset)

    Easily extendable for future AUTs:
      - qna_bot
      - analytics_assistant
      - custom multi-agent systems
    """
    aut_id = spec.aut_id

    if aut_id == "travel_planner":
        # AUT client (wraps the ADK travel app)
        aut_client = TravelAUTClient(spec=spec, default_version=default_version)

        # Eval pack(s) for this AUT
        eval_pack = TravelEvalPack(aut_spec=spec)

        # General Evaluation Engine (Eval Agent)
        eval_engine = EvalEngine(
            aut_spec=spec,
            aut_client=aut_client,
            eval_packs=[eval_pack],
        )

        # Planner engine (Planner + Critic multi-agent)
        planner_engine = PlannerEngine(spec=spec)

        return aut_client, eval_engine, planner_engine

    # -----------------------------
    # Unknown AUT case
    # -----------------------------
    raise ValueError(
        f"Unsupported AUT '{aut_id}'. "
        "Please extend build_runtime_for_aut() to support this AUT."
    )


# --------------------------------------------------------------------
# Lightweight Discover
# --------------------------------------------------------------------
def run_discover(spec: AUTSpec) -> Dict[str, Any]:
    """
    Return high-level profile of the AUT.

    This is intentionally defensive: many fields (tools, flows, etc.)
    are optional in the AUTSpec and may not exist for all AUTs.
    """
    evaluation = getattr(spec, "evaluation", None)
    if hasattr(evaluation, "to_dict"):
        evaluation = evaluation.to_dict()

    return {
        "aut_id": getattr(spec, "aut_id", None),
        "name": getattr(spec, "name", None),
        "version": getattr(spec, "version", None),
        "description": getattr(spec, "description", None),
        "adk": getattr(spec, "adk", None),
        "inputs_schema": getattr(spec, "inputs", None),
        "outputs_schema": getattr(spec, "outputs", None),
        "tools": getattr(spec, "tools", None),
        "flows": getattr(spec, "flows", None),
        "capabilities": getattr(spec, "capabilities", None),
        "risk_profile": getattr(spec, "risk_profile", None),
        "evaluation": evaluation,
    }


# --------------------------------------------------------------------
# Interactive Supervisor Loop (Supervisor Agent)
# --------------------------------------------------------------------
def supervisor_loop(aut_spec_path: Path) -> None:
    # Load AUT spec (single source of truth for this AUT)
    spec = load_aut_spec(aut_spec_path)
    default_version = getattr(spec, "version", None) or "v1"

    # Build runtime agents (AUTClient + EvalAgent + Planner/CriticAgents)
    aut_client, eval_engine, planner_engine = build_runtime_for_aut(
        spec, default_version=default_version
    )

    # --------------------------------------------------------------
    # Banner
    # --------------------------------------------------------------
    print("===========================================================")
    print("   AgentOps Autopilot — Universal ADK Supervisor (CLI)     ")
    print("===========================================================")
    print(f"Loaded AUT spec: {aut_spec_path}")
    print(f"AUT ID: {spec.aut_id} | Version: {spec.version}")
    print("\nType 'help' for all commands.")
    print("-----------------------------------------------------------")

    # --------------------------------------------------------------
    # Main Loop
    # --------------------------------------------------------------
    while True:
        try:
            raw = input("\nSupervisor > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting supervisor.")
            break

        if not raw:
            continue

        parts = raw.split()
        cmd = parts[0].lower()
        args = parts[1:]

        # ----------------------------
        # Exit
        # ----------------------------
        if cmd in {"exit", "quit"}:
            print("Goodbye.")
            break

        # ----------------------------
        # Help
        # ----------------------------
        elif cmd == "help":
            print("Commands:")
            print("  discover                 - Show AUT spec structure")
            print("  profile                  - High-level profile + config file")
            print("  eval [version]           - Run evaluation for version")
            print("  improve [version]        - Suggest config/test improvements")
            print("  metrics                  - Summary from traces.jsonl")
            print("  compare v1 v2            - Compare version metrics (avg score)")
            print("  run                      - Run AUT once with JSON input")
            print("  exit                     - Quit")

        # ----------------------------
        # Discover (full spec)
        # ----------------------------
        elif cmd == "discover":
            try:
                info = run_discover(spec)
                pretty(info)
            except Exception as e:
                print(f"❌ Discover failed: {e}")

        # ----------------------------
        # Profile (shorter summary)
        # ----------------------------
        elif cmd == "profile":
            evaluation = getattr(spec, "evaluation", None)
            if hasattr(evaluation, "to_dict"):
                evaluation = evaluation.to_dict()

            profile = {
                "aut_id": getattr(spec, "aut_id", None),
                "name": getattr(spec, "name", None),
                "version": getattr(spec, "version", None),
                "description": getattr(spec, "description", None),
                "config_file": (
                    getattr(spec, "adk", {}) or {}
                ).get("config_file"),
                "evaluation": evaluation,
            }
            pretty(profile)

        # ----------------------------
        # Eval (multi-test eval with LLM judge + rule metrics)
        # ----------------------------
        elif cmd == "eval":
            version_id = args[0] if args else default_version
            try:
                summary = eval_engine.run_full_eval(version_id=version_id)
                # summary typically includes:
                #   - aut_id, version_id, golden_path, num_testcases
                #   - avg_judge_score (legacy)
                #   - aggregated_metrics: {judge_score_avg, judge_score_p95, latency_ms_p95, task_success_rate}
                #   - records: [EvalRecord...]
                pretty(summary)
            except Exception as e:
                print(f"❌ Eval failed: {e}")

        # ----------------------------
        # Improve (Planner / Critic loop)
        # ----------------------------
        elif cmd == "improve":
            version_id = args[0] if args else default_version
            try:
                # PlannerEngine implements multi-agent planning:
                #   - PlannerAgent: proposes config_patch + new_testcases
                #   - CriticAgent: reviews/refines into a changeset
                changeset = planner_engine.propose_changeset(version_id=version_id)
                if hasattr(changeset, "to_dict"):
                    pretty(changeset.to_dict())
                else:
                    pretty(changeset.__dict__)
            except Exception as e:
                print(f"❌ Improvement failed: {e}")

        # ----------------------------
        # Metrics Summary (from traces.jsonl)
        # ----------------------------
        elif cmd == "metrics":
            print("\n=== Metrics Summary (from traces.jsonl) ===\n")
            try:
                metrics_summary_main()
            except Exception as e:
                print(f"❌ Metrics summary failed: {e}")

        # ----------------------------
        # Compare Versions (using traces)
        # ----------------------------
        elif cmd == "compare":
            if len(args) != 2:
                print("Usage: compare v1 v2")
                continue
            v1, v2 = args
            traces = load_traces()

            from collections import defaultdict
            from statistics import mean

            by_version = defaultdict(list)
            for t in traces:
                vid = t.get("version_id", "unknown")
                by_version[vid].append(t)

            def avg_for(v: str):
                scores = []
                for e in by_version.get(v, []):
                    s = e.get("eval_score")
                    if s is not None:
                        try:
                            scores.append(float(s))
                        except Exception:
                            pass
                return mean(scores) if scores else None

            s1 = avg_for(v1)
            s2 = avg_for(v2)

            result = {
                "version_1": v1,
                "version_2": v2,
                "avg_score_v1": s1,
                "avg_score_v2": s2,
                "delta": (s2 - s1) if (s1 is not None and s2 is not None) else None,
            }
            pretty(result)

        # ----------------------------
        # Run Once (single AUT call)
        # ----------------------------
        elif cmd == "run":
            print(
                "Enter a JSON request.\n"
                'Example: {"destination": "Tokyo", "duration_days": 3, "budget_total": 1500}\n'
            )
            raw_json = input("JSON > ").strip()
            try:
                req = json.loads(raw_json)
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON: {e}")
                continue

            try:
                # TravelAUTClient.run_once(version_id=..., request=...)
                result = aut_client.run_once(
                    version_id=default_version,
                    request=req,
                )
                pretty(result)
            except Exception as e:
                print(f"❌ AUT run failed: {e}")

        # ----------------------------
        # Unknown command
        # ----------------------------
        else:
            print("Unknown command. Type 'help' for list.")


# --------------------------------------------------------------------
# Entry Point
# --------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Universal ADK Supervisor CLI")
    parser.add_argument(
        "--aut-spec",
        type=str,
        default=str(ROOT / "v2_adk/travel_planner/specs/travel_planner_v1.aut.yaml"),
        help="Path to AUT spec YAML file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    supervisor_loop(Path(args.aut_spec))


if __name__ == "__main__":
    main()
