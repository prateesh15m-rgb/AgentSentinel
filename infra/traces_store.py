# infra/traces_store.py

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

TRACE_FILE = Path("data/traces.jsonl")


def _normalize_tool_calls(tool_calls: Optional[Union[list, dict]]) -> List[dict]:
    """
    Ensures tool calls are stored as a list of serializable dicts.
    """
    if tool_calls is None:
        return []

    if isinstance(tool_calls, dict):
        return [tool_calls]

    normalized = []
    for tc in tool_calls:
        if tc is None:
            continue
        if hasattr(tc, "__dict__"):
            normalized.append(dict(tc.__dict__))
        elif isinstance(tc, dict):
            normalized.append(tc)
        else:
            normalized.append({"repr": repr(tc)})
    return normalized


def _normalize_session_graph(graph: Any) -> Any:
    """
    Ensure session_graph is JSON serializable.
    If it's None or empty, return {}.
    """
    if not graph:
        return {}
    try:
        json.dumps(graph)  # check serializability
        return graph
    except Exception:
        # Fallback to repr
        return {"raw": repr(graph)}


def log_trace(event: Dict[str, Any]) -> str:
    """
    Appends a trace event to traces.jsonl.
    Enhancements:
      - Adds trace_id + timestamp
      - Normalizes tool calls
      - Normalizes session graph
      - Ensures JSON-serializable structure
    Returns trace_id.
    """
    trace_id = str(uuid.uuid4())

    event_with_ids = {
        "trace_id": trace_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **event,
    }

    # Normalize tool calls (ADK & our AUTClient variants)
    if "tool_calls" in event_with_ids:
        event_with_ids["tool_calls"] = _normalize_tool_calls(event_with_ids["tool_calls"])
    else:
        event_with_ids["tool_calls"] = []

    # Normalize session graph
    if "session_graph" in event_with_ids:
        event_with_ids["session_graph"] = _normalize_session_graph(
            event_with_ids["session_graph"]
        )
    else:
        event_with_ids["session_graph"] = {}

    # Write to disk
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with TRACE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event_with_ids) + "\n")

    return trace_id


def load_traces() -> List[Dict[str, Any]]:
    """
    Load all trace events from traces.jsonl.
    If file doesn't exist, returns empty list.
    """
    if not TRACE_FILE.exists():
        return []

    traces: List[Dict[str, Any]] = []
    with TRACE_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                traces.append(json.loads(line))
            except Exception:
                # Corrupted line fallback
                traces.append({"_raw_line": line, "error": "failed_to_parse_json"})
    return traces
