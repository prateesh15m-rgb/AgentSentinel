# agentops/eval_agent.py

import json
import os
from typing import Dict, Any

import google.generativeai as genai

from agentops.prompts import EVAL_SYSTEM_PROMPT
from infra.env import ensure_env_loaded


def _get_eval_model(model_name: str = "gemini-2.0-flash"):
    """
    Configure Gemini client using API key from environment.

    Priority:
      - GOOGLE_API_KEY
      - GEMINI_API_KEY
    """
    # Make sure .env is loaded into os.environ
    ensure_env_loaded()

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Please set GOOGLE_API_KEY or GEMINI_API_KEY in your .env / environment "
            "for the eval agent."
        )

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def _strip_code_fences(text: str) -> str:
    """
    Remove ```json ... ``` or ``` ... ``` fences if the model wrapped JSON in a code block.
    """
    t = text.strip()
    if t.startswith("```"):
        # Remove first line (``` or ```json) and last line (```).
        lines = t.splitlines()
        # drop first and last lines if they start/end with ```
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def evaluate_answer(
    question: str,
    expected_behavior: str,
    model_answer: str,
    model_name: str = "gemini-2.0-flash",
) -> Dict[str, Any]:
    """
    Use Gemini as a judge to evaluate how good the model_answer is.

    Returns:
      {
        "score": int 1-5,
        "reasoning": str,
        "raw_response": str
      }
    """
    model = _get_eval_model(model_name)

    combined_prompt = f"""
{EVAL_SYSTEM_PROMPT.strip()}

Question:
{question}

Expected behavior:
{expected_behavior}

Model answer:
{model_answer}

Remember:
- Respond ONLY in JSON.
- Do NOT add commentary outside JSON.
- Do NOT wrap the JSON in quotes.
- If you use Markdown, make sure the JSON itself is still valid.
""".strip()

    response = model.generate_content(combined_prompt)
    raw_text = getattr(response, "text", str(response)).strip()

    # Strip possible ```json ... ``` fences
    cleaned = _strip_code_fences(raw_text)

    # Try to parse JSON safely
    try:
        parsed = json.loads(cleaned)
        score = int(parsed.get("score", 0))
        reasoning = parsed.get("reasoning", "")
    except Exception:
        score = 0
        reasoning = f"Failed to parse JSON from eval model. Raw response: {raw_text}"

    return {
        "score": score,
        "reasoning": reasoning,
        "raw_response": raw_text,
    }
