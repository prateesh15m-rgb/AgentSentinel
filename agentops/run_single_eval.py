# agentops/run_single_eval.py

from agent_app.agent_core import run_agent_once
from infra.datasets import load_golden_set
from agentops.eval_agent import evaluate_answer


def main():
    golden = load_golden_set()
    if not golden:
        print("Golden set is empty.")
        return

    row = golden[0]
    question = row["question"]
    expected_behavior = row["expected_behavior"]

    print("=== Golden Test Case ===")
    print("Question:", question)
    print("Expected behavior:", expected_behavior)

    # Run the reference agent
    result = run_agent_once("v1", question)
    answer = result["answer"]

    print("\n=== Model Answer ===")
    print(answer)

    # Evaluate the answer
    eval_result = evaluate_answer(
        question=question,
        expected_behavior=expected_behavior,
        model_answer=answer,
    )

    print("\n=== Eval Result ===")
    print("Score:", eval_result["score"])
    print("Reasoning:", eval_result["reasoning"])


if __name__ == "__main__":
    main()
