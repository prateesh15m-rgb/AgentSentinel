# infra/memory_store.py

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

MEMORY_FILE = Path("data/memory/bank.jsonl")


def _ensure_dir():
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def append_memory(entry: Dict[str, Any]) -> str:
    """
    Append a memory entry to data/memory/bank.jsonl.

    We add:
      - memory_id
      - timestamp
    and keep all provided fields as-is.

    Returns the generated memory_id.
    """
    _ensure_dir()
    memory_id = str(uuid.uuid4())
    record = {
        "memory_id": memory_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **entry,
    }

    with MEMORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return memory_id


def load_memories(
    memory_type: Optional[str] = None,
    aut_id: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Load memory entries from data/memory/bank.jsonl.

    Filters:
      - memory_type (e.g. "best_practice", "failure_pattern", "config_change")
      - aut_id

    If limit is provided, only the last N entries are returned.
    """
    if not MEMORY_FILE.exists():
        return []

    entries: List[Dict[str, Any]] = []
    with MEMORY_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            if memory_type and rec.get("type") != memory_type:
                continue
            if aut_id and rec.get("aut_id") != aut_id:
                continue

            entries.append(rec)

    if limit is not None and len(entries) > limit:
        return entries[-limit:]
    return entries
