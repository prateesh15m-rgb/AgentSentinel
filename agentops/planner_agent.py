# agentops/planner_agent.py

import json
import os
from typing import Dict, Any, List

import google.generativeai as genai

from infra.traces_store import load_traces
from infra.env import ensure_env_loaded


def _get_planner_model(model_name: str = "gemini-2.0-flash"):
    """
    Configure Gemini client using API key from environment.

    Priority:
      - GOOGLE_API_KEY
      - GEMINI_API_KEY
    """
    ensure_env_loaded()

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Please set GOOGLE_API_KEY or GEMINI_API_KEY in your .env / environment "
            "for the planner agent."
        )

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` style fences if present."""
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def get_low_scoring_traces(min_score: int = 4) -> List[Dict[str, Any]]:
    """
    Load traces and return only those with eval_score < min_score.
    """
    traces = load_traces()
    low = []
    for t in traces:
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


def build_failure_report(traces: List[Dict[str, Any]]) -> str:
    """
    Turn low-scoring traces into a human-readable failure report string.
    """
    if not traces:
        return "No low-scoring traces. All eval scores meet or exceed the threshold."

    parts = []
    for t in traces:
        parts.append(
            f"- Question: {t.get('question')}\n"
            f"  Answer: {t.get('answer')}\n"
            f"  Eval score: {t.get('eval_score')}\n"
            f"  Eval reasoning: {t.get('eval_reasoning')}\n"
        )
    return "\n".join(parts)


def propose_new_config(
    base_version_id: str = "v1",
    new_version_id: str = "v2",
    min_score: int = 4,
) -> Dict[str, Any]:
    """
    Use a planner-style LLM to propose a new agent configuration
    based on low-scoring traces.

    Returns a dict like:
      {
        "new_version_id": "v2",
        "system_prompt": "...",
        "retrieval_top_k": 3
      }
    """
    low_traces = get_low_scoring_traces(min_score=min_score)
    failure_report = build_failure_report(low_traces)

    model = _get_planner_model()

    planner_prompt = f"""
You are a senior AI agent designer.

You are improving a Q&A support agent that answers questions using company docs.

You will be given:
- A base agent version id: {base_version_id}
- A desired new version id: {new_version_id}
- A list of low-scoring evaluation traces with:
  - question
  - answer
  - eval_score
  - eval_reasoning

Your job:
1. Analyze the failure patterns.
2. Suggest how to improve the agent's behavior, especially via:
   - Better system prompt (more cautious, more explicit, more complete).
   - Slight adjustments to retrieval if needed (retrieval_top_k).
3. Produce a NEW config for the agent, as JSON, with this exact shape:

{{
  "new_version_id": "{new_version_id}",
  "system_prompt": "<new system prompt text>",
  "retrieval_top_k": <integer, e.g., 3 or 5>
}}

Do NOT include comments. Do NOT add other fields.
Do NOT wrap JSON in additional text.

Here are the low-scoring traces (if any):

{failure_report}
""".strip()

    response = model.generate_content(planner_prompt)
    raw_text = getattr(response, "text", str(response)).strip()
    cleaned = _strip_code_fences(raw_text)

    try:
        proposal = json.loads(cleaned)
    except Exception:
        proposal = {
            "new_version_id": new_version_id,
            "system_prompt": (
                "You are a careful Q&A support assistant. Always answer ONLY from the docs. "
                "If something is not explicitly mentioned in the docs, do not guess or invent details. "
                "If you are not sure, say that the information is not available."
            ),
            "retrieval_top_k": 3,
            "error": f"Failed to parse planner JSON. Raw response: {raw_text}",
        }

    return proposal
