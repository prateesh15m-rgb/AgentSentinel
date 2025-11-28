# agentops/memory/__init__.py
"""
AgentOps memory subsystem.

This package provides utilities for storing and querying long-lived
"best practices" and experience across AUTs and versions.

Key concepts:
  - BestPracticesMemory: append-only JSONL-backed store of events
  - Events: eval outcomes, budget overrun patterns, prompt tweaks,
            human labels, etc.

The memory is intentionally generic and lightweight so it can be used
by:
  - EvalEngine (to record eval outcomes)
  - PlannerEngine (to discover patterns & inform improvements)
  - Supervisor CLI (for human-in-the-loop annotations)
"""
