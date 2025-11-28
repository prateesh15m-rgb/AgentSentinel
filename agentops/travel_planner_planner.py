# agentops/travel_planner_planner.py

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import google.generativeai as genai

from infra.traces_store import load_traces


def _get_planner_model(model_name: str = "gemini-2.0-flash"):
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Please set GOOGLE_API_KEY or GEMINI_API_KEY for planner agent.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def get_low_scoring_travel_traces(
    version_id: str = "travel_v1",
    min_score: float = 4.0,
) -> List[Dict[str, Any]]:
    traces = load_traces()
    low: List[Dict[str, Any]] = []
    for t in traces:
        if t.get("version_id") != version_id:
            continue
        score = t.get("eval_score")
        if score is None:
            continue
        try:
            score_val = float(score)
        except Exception:
            continue
        if score_val < min_score:
            low.append(t)
    return low


def build_travel_failure_report(traces: List[Dict[str, Any]]) -> str:
    if not traces:
        return "No low-scoring travel traces. All eval scores meet or exceed the threshold."

    parts = []
    for t in traces:
        req = t.get("trip_request", {})
        parts.append(
            "Trip request: "
            + json.dumps(req, ensure_ascii=False)
            + "\n"
            + f"Answer markdown (truncated): {t.get('answer_markdown', '')[:500]}...\n"
            + f"Eval score: {t.get('eval_score')}\n"
            + f"Eval reasoning: {t.get('eval_reasoning')}\n"
        )
    return "\n---\n".join(parts)


def propose_travel_changeset(
    base_config_path: str = "v2_adk/travel_planner/specs/travel_planner_config_v1.json",
    new_config_path: str = "v2_adk/travel_planner/specs/travel_planner_config_v2.json",
    version_id: str = "travel_v1",
    min_score: float = 4.0,
) -> Dict[str, Any]:
    """
    Ask Gemini to propose a ChangeSet to go from v1 -> v2.
    """
    low_traces = get_low_scoring_travel_traces(version_id=version_id, min_score=min_score)
    failure_report = build_travel_failure_report(low_traces)

    model = _get_planner_model()

    planner_prompt = f"""
You are a senior AI agent designer improving a travel itinerary planner.

The planner:
- Generates day-by-day itineraries with budgets and season-aware activities.
- Is currently version_id = "{version_id}" with config at: {base_config_path}

You will be given low-scoring evaluation traces (if any) for this version.
Each trace includes:
- trip_request (destination, days, budget, style, etc.)
- answer_markdown (truncated)
- eval_score and eval_reasoning.

Your task:
1. Analyze failure patterns (if there are any).
2. Propose config changes that could improve behavior in future versions.
   Focus on:
   - planning.clarification (whether to ask clarification questions)
   - budgeting.budget_strictness, allow_over_budget_pct
   - ux.verbosity, ux.include_warnings_section, ux.include_assumptions_section
   - seasonality.seasonal_intensity
3. Optionally propose new evaluation test cases (goldens) to add.

You MUST respond in this exact JSON shape (no extra fields):

{{
  "base_config_path": "{base_config_path}",
  "new_config_path": "{new_config_path}",
  "config_patches": [
    {{
      "path": "planning.clarification.enabled",
      "op": "set",
      "value": true
    }}
  ],
  "new_tests": [
    {{
      "id": "4",
      "input_json": "{{\\"destination\\": \\"Tokyo\\", \\"duration_days\\": 3}}",
      "judge_question": "Does the itinerary ...?",
      "expected_behavior": "The answer should ..."
    }}
  ]
}}

Rules:
- Use "op": "set" for all patches.
- Use dot-separated path syntax for "path" (e.g., "planning.clarification.enabled").
- new_tests can be an empty list if you have no suggestions.
- If there are no low-scoring traces, still propose small robustness improvements
  (e.g., enable clarifications, stronger assumptions section) but keep patches minimal.

Low-scoring travel traces (if any):

{failure_report}
""".strip()

    response = model.generate_content(planner_prompt)
    raw_text = getattr(response, "text", str(response)).strip()
    cleaned = _strip_code_fences(raw_text)

    try:
        data = json.loads(cleaned)
    except Exception:
        # Fallback minimal ChangeSet if parsing fails
        data = {
            "base_config_path": base_config_path,
            "new_config_path": new_config_path,
            "config_patches": [
                {
                    "path": "planning.clarification.enabled",
                    "op": "set",
                    "value": True,
                }
            ],
            "new_tests": [],
            "error": f"Failed to parse planner JSON. Raw response: {raw_text}",
        }

    # Ensure required keys exist
    data.setdefault("base_config_path", base_config_path)
    data.setdefault("new_config_path", new_config_path)
    data.setdefault("config_patches", [])
    data.setdefault("new_tests", [])

    return data
