# agentops/run_full_eval.py

from typing import Dict, Any

from infra.datasets import load_golden_set
from infra.traces_store import log_trace
from agentops.eval_agent import evaluate_answer
from agent_app.qna_aut_client import QnAAUTClient


def _trace_event_from_aut_response(
    aut_resp,
    eval_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Normalize what we log for each test case so it works for both
    the legacy Q&A agent and future ADK agents.
    """
    tool_calls_dicts = []
    for tc in getattr(aut_resp, "tool_calls", []) or []:
        if hasattr(tc, "__dict__"):
            tool_calls_dicts.append(dict(tc.__dict__))
        elif isinstance(tc, dict):
            tool_calls_dicts.append(tc)
        else:
            tool_calls_dicts.append({"repr": repr(tc)})

    metadata = aut_resp.metadata or {}
    return {
        "aut_id": metadata.get("aut_id", "qna_support"),
        "version_id": metadata.get("version_id"),
        "question": aut_resp.question,
        "answer": aut_resp.answer,
        "retrieved_docs": metadata.get("retrieved_docs", []),
        "latency_ms": aut_resp.latency_ms,
        "eval_score": eval_result["score"],
        "eval_reasoning": eval_result["reasoning"],
        "tool_calls": tool_calls_dicts,
        "session_graph": getattr(aut_resp, "session_graph", {}),
    }


def main():
    golden = load_golden_set()
    if not golden:
        print("Golden set is empty.")
        return

    # Fixed to v1 (baseline) like your original script
    aut_client = QnAAUTClient(version_id="v1")

    scores = []
    print(f"Running full evaluation on {len(golden)} test cases...\n")

    for row in golden:
        qid = row["id"]
        question = row["question"]
        expected = row["expected_behavior"]

        print(f"--- Test Case {qid} ---")
        print(f"Question: {question}")

        aut_resp = aut_client.run_query({"question": question})
        answer = aut_resp.answer

        print("\nModel Answer:")
        print(answer)

        eval_result = evaluate_answer(
            question=question,
            expected_behavior=expected,
            model_answer=answer,
        )

        score = eval_result["score"]
        scores.append(score)

        print("\nEval Score:", score)
        print("Reasoning:", eval_result["reasoning"])

        trace_event = _trace_event_from_aut_response(aut_resp, eval_result)
        trace_id = log_trace(trace_event)

        print("Trace ID:", trace_id)
        print("\n")

    avg_score = sum(scores) / len(scores)
    print("=============================")
    print(" Full Evaluation Complete")
    print("=============================")
    print(f"Average Score: {avg_score:.2f} out of 5")
    print(f"Scores: {scores}")


if __name__ == "__main__":
    main()
