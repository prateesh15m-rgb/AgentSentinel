# core/aut_client.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class AUTToolCall:
    """
    Lightweight representation of a single tool call.
    """
    name: str
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class AUTResponse:
    """
    Normalized response from any AUT (Agent Under Test).
    """
    answer: str
    raw: Any
    latency_ms: Optional[float] = None
    session_graph: Optional[Dict[str, Any]] = None
    tool_calls: List[AUTToolCall] = field(default_factory=list)


class AUTClient(Protocol):
    """
    Protocol (interface) that all AUT clients must implement.
    """

    aut_id: str
    default_version: str

    def run_query(
        self,
        request: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> AUTResponse:
        ...
