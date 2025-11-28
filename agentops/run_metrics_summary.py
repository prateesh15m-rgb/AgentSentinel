# agentops/run_metrics_summary.py

from collections import defaultdict
from statistics import mean
from typing import List, Dict, Any
import numpy as np

from infra.traces_store import load_traces


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return None
    return float(np.percentile(values, p))


def main():
    traces = load_traces()
    if not traces:
        print("No traces found. Run some evals first.")
        return

    # Group by version_id
    by_version: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for t in traces:
        version = t.get("version_id") or t.get("aut_version") or "unknown"
        by_version[version].append(t)

    print("\n===============================")
    print("      METRICS SUMMARY")
    print("===============================\n")

    for version, events in by_version.items():
        scores = []
        latencies = []
        tool_call_counts = []
        judge_models = defaultdict(int)
        session_graph_sizes = []

        for e in events:
            # Scores
            score = e.get("eval_score")
            if score is not None:
                try:
                    scores.append(float(score))
                except Exception:
                    pass

            # Latency
            latency = e.get("latency_ms")
            if latency is not None:
                try:
                    latencies.append(float(latency))
                except Exception:
                    pass

            # Tool calls
            tc = e.get("tool_calls", [])
            if isinstance(tc, list):
                tool_call_counts.append(len(tc))

            # Judge model usage
            jm = e.get("eval_judge_model") or e.get("judge_model")
            if jm:
                judge_models[jm] += 1

            # Session graph breadth
            sg = e.get("session_graph", {})
            if isinstance(sg, dict):
                session_graph_sizes.append(len(sg))

        # Aggregate
        avg_score = mean(scores) if scores else None
        avg_latency = mean(latencies) if latencies else None
        p50_latency = _percentile(latencies, 50)
        p95_latency = _percentile(latencies, 95)

        avg_tool_calls = mean(tool_call_counts) if tool_call_counts else None
        avg_session_graph = mean(session_graph_sizes) if session_graph_sizes else None

        fail_count = sum(1 for s in scores if s < 4)
        total = len(scores)

        print(f"=== Version: {version} ===")
        print(f"  Test cases: {total}")
        print(
            f"  Average score: {avg_score:.2f}"
            if avg_score is not None
            else "  Average score: N/A"
        )
        print(
            f"  Average latency: {avg_latency:.1f} ms"
            if avg_latency is not None
            else "  Average latency: N/A"
        )
        print(
            f"  p50 latency: {p50_latency:.1f} ms" if p50_latency is not None else "  p50 latency: N/A"
        )
        print(
            f"  p95 latency: {p95_latency:.1f} ms" if p95_latency is not None else "  p95 latency: N/A"
        )
        print(
            f"  Avg tool calls: {avg_tool_calls:.2f}"
            if avg_tool_calls is not None
            else "  Avg tool calls: N/A"
        )
        print(
            f"  Avg session graph nodes: {avg_session_graph:.2f}"
            if avg_session_graph is not None
            else "  Avg session graph nodes: N/A"
        )
        print(f"  Failing (<4): {fail_count}")
        if total:
            print(f"  Pass rate: {(total - fail_count) / total * 100:.1f}%")

        if judge_models:
            print("  Judge model usage:")
            for jm, count in judge_models.items():
                print(f"    - {jm}: {count} evals")

        print()

    print("===============================")
    print("         END OF REPORT")
    print("===============================")


if __name__ == "__main__":
    main()
