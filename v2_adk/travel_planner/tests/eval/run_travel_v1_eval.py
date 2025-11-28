# v2_adk/travel_planner/tests/eval/run_travel_v1_eval.py

from __future__ import annotations

import csv
import json
from pathlib import Path

from infra.traces_store import log_trace
from agentops.eval_agent import evaluate_answer
from v2_adk.travel_planner.app.main import run_travel_planner_once

GOLDEN_PATH = (
    Path(__file__)
    .resolve()
    .parents[1]  # up from eval/ -> tests/
    / "golden"
    / "travel_golden_v1.csv"
)


def load_golden() -> list[dict]:
    if not GOLDEN_PATH.exists():
        raise FileNotFoundError(f"Golden set not found at {GOLDEN_PATH}")
    rows: list[dict] = []
    with GOLDEN_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def main():
    golden = load_golden()
    if not golden:
        print("Golden set is empty.")
        return

    scores: list[float] = []

    print(f"Running Travel Planner v1 evaluation on {len(golden)} test cases...\n")

    for row in golden:
        test_id = row["id"]
        input_json = row["input_json"]
        judge_question = row["judge_question"]
        expected_behavior = row["expected_behavior"]

        print(f"--- Travel Test Case {test_id} ---")
        print("Input JSON:", input_json)
        print("Judge question:", judge_question)

        trip_request = json.loads(input_json)

        # Run Travel Planner v1
        result = run_travel_planner_once(
            version_id="travel_v1",
            trip_request=trip_request,
        )

        answer_markdown = result["answer_markdown"]

        print("\nModel Answer (markdown):")
        print(answer_markdown)

        # Use existing eval agent as judge
        eval_result = evaluate_answer(
            question=judge_question,
            expected_behavior=expected_behavior,
            model_answer=answer_markdown,
        )

        score = eval_result["score"]
        scores.append(score)

        print("\nEval Score:", score)
        print("Reasoning:", eval_result["reasoning"])

        # Log a trace compatible with your existing metrics tooling
        trace_event = {
            "version_id": result["version_id"],  # "travel_v1"
            "trip_request": result["request"],
            "answer_markdown": answer_markdown,
            "tool_outputs": result["tool_outputs"],
            "latency_ms": result["latency_ms"],
            "eval_score": score,
            "eval_reasoning": eval_result["reasoning"],
        }
        trace_id = log_trace(trace_event)

        print("Trace ID:", trace_id)
        print("\n")

    avg_score = sum(scores) / len(scores)
    print("=============================")
    print(" Travel Planner v1 Evaluation Complete")
    print("=============================")
    print(f"Average Score: {avg_score:.2f} out of 5")
    print(f"Scores: {scores}")


if __name__ == "__main__":
    main()
