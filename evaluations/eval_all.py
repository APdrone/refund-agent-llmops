"""
Comprehensive LLM Evaluation Runner for Refund Customer Support Agent.
Supports DeepEval trace metrics, single-turn metrics, category filtering,
dry-run inspection (0 cost), and structured markdown report generation.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from deepeval import evaluate
from deepeval.evaluate import CacheConfig, DisplayConfig
from deepeval.integrations.langchain import CallbackHandler
from deepeval.metrics import (
    ArgumentCorrectnessMetric,
    GEval,
    PlanAdherenceMetric,
    PlanQualityMetric,
    StepEfficiencyMetric,
    TaskCompletionMetric,
    ToolCorrectnessMetric,
)
from deepeval.test_case import LLMTestCase, SingleTurnParams, ToolCall, ToolCallParams

# Ensure agent directory is discoverable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.agent import agent
from evaluations.dataset import ALL_GOLDENS, get_dataset_by_category
from evaluations.model import eval_model

SUCCESSFUL_TASK_DESCRIPTION = """
If the username is missing, ask the user to provide it.
For a refund request, identify the customer and the requested purchases, and
check that each purchase is no more than 30 days old and is not in the future.
Refund only the items requested by the user. If the customer or requested item
cannot be found, or was already refunded, do not issue a refund ticket and explain why.
If a refund exceeds $100, flag it for supervisor review.
Once the necessary information is available, tell the user whether a refund
ticket was issued and its amount, or explain why no refund was issued.
For an information-only request, answer the question without issuing a ticket.
"""


def build_metrics():
    """Build trace-based and single-turn evaluation metrics."""
    trace_metrics = [
        TaskCompletionMetric(
            threshold=0.8,
            model=eval_model,
            task=SUCCESSFUL_TASK_DESCRIPTION,
            include_reason=True,
        ),
        StepEfficiencyMetric(
            threshold=0.8,
            model=eval_model,
            include_reason=True,
        ),
        PlanQualityMetric(
            threshold=0.8,
            model=eval_model,
            include_reason=True,
        ),
        PlanAdherenceMetric(
            threshold=0.8,
            model=eval_model,
            include_reason=True,
        ),
    ]

    single_turn_metrics = [
        ArgumentCorrectnessMetric(
            threshold=None,
            model=eval_model,
            include_reason=True,
        ),
        ToolCorrectnessMetric(
            threshold=0.85,
            model=eval_model,
            include_reason=True,
            evaluation_params=[ToolCallParams.INPUT_PARAMETERS],
        ),
        GEval(
            name="Answer Correctness",
            evaluation_params=[
                SingleTurnParams.INPUT,
                SingleTurnParams.ACTUAL_OUTPUT,
                SingleTurnParams.EXPECTED_OUTPUT,
            ],
            evaluation_steps=[
                "Check that the actual output and expected output have the same "
                "logical conclusion about the user's refund request and policy justification.",
            ],
            threshold=0.8,
            model=eval_model,
            verbose_mode=True,
        ),
    ]

    return trace_metrics, single_turn_metrics


def run_dry_run(goldens: list):
    """
    Dry-run mode: prints evaluation dataset structure and test cases
    without invoking any LLMs, incurring zero API costs.
    """
    print("\n" + "=" * 70)
    print(" [DRY RUN] Evaluation Suite Inspection (Zero Cost)")
    print("=" * 70)
    print(f"Total Test Cases Loaded: {len(goldens)}")
    print(f"Evaluator Model Target: {eval_model}")
    print("-" * 70)

    for idx, golden in enumerate(goldens, 1):
        tools = [t.name for t in (golden.expected_tools or [])]
        print(f"[{idx:02d}] Input: {golden.input}")
        print(f"     Expected: {golden.expected_output}")
        print(f"     Tools ({len(tools)}): {', '.join(tools) if tools else 'None'}\n")

    print("=" * 70)
    print("Dry run completed successfully. No LLM calls were made.")
    print("=" * 70)


def generate_markdown_report(results: list, report_path: Path):
    """Generates a clean Markdown summary report of evaluation runs."""
    lines = [
        "# Agent Evaluation Benchmark Report",
        f"\n**Generated At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Evaluator Model:** `{eval_model}`",
        f"**Total Test Cases Evaluated:** {len(results)}\n",
        "## Summary Table",
        "| # | Input Snippet | Actual Output | Status |",
        "|---|---|---|---|",
    ]
    for idx, item in enumerate(results, 1):
        snippet = (item["input"][:45] + "...") if len(item["input"]) > 45 else item["input"]
        out_snippet = (item["actual_output"][:45] + "...") if len(item["actual_output"]) > 45 else item["actual_output"]
        lines.append(f"| {idx} | `{snippet}` | {out_snippet} | Completed |")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSaved evaluation report to: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Refund Agent Evaluation Runner")
    parser.add_argument(
        "--category",
        choices=["all", "happy", "boundary", "guardrails", "validation", "smoke"],
        default="all",
        help="Run a specific test category (default: all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of test cases to run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect dataset and expected tools without invoking LLMs (zero cost)",
    )
    parser.add_argument(
        "--report",
        type=str,
        default="eval_report.md",
        help="Path to save markdown report",
    )
    args = parser.parse_args()

    load_dotenv()
    target_dataset = get_dataset_by_category(args.category)
    goldens = target_dataset.goldens

    if args.limit:
        goldens = goldens[:args.limit]

    if args.dry_run:
        run_dry_run(goldens)
        return

    print(f"\nStarting evaluation of {len(goldens)} test cases with model: {eval_model}...")
    trace_metrics, single_turn_metrics = build_metrics()
    cache_config = CacheConfig(use_cache=False, write_cache=False)
    display_config = DisplayConfig(inspect_after_run=False)

    test_cases = []
    run_records = []

    for golden in target_dataset.evals_iterator(
        metrics=trace_metrics,
        cache_config=cache_config,
        display_config=display_config,
    ):
        response = agent.invoke(
            {"messages": [{"role": "user", "content": golden.input}]},
            config={
                "configurable": {"thread_id": str(uuid4())},
                "callbacks": [CallbackHandler()],
            },
        )

        tools_called = []
        for message in response.get("messages", []):
            for tool_call in getattr(message, "tool_calls", []) or []:
                tools_called.append(
                    ToolCall(
                        name=tool_call["name"],
                        input_parameters=tool_call["args"],
                    )
                )

        actual_output = response["structured_response"].answer
        test_cases.append(
            LLMTestCase(
                input=golden.input,
                actual_output=actual_output,
                expected_output=golden.expected_output,
                tools_called=tools_called,
                expected_tools=golden.expected_tools,
            )
        )
        run_records.append({
            "input": golden.input,
            "actual_output": actual_output,
            "tools_called": [t.name for t in tools_called],
        })

    evaluate(
        test_cases=test_cases,
        metrics=single_turn_metrics,
        cache_config=cache_config,
        display_config=display_config,
    )

    generate_markdown_report(run_records, Path(args.report))
    print(f"\nCompleted all 7 metrics across {len(test_cases)} test cases.")


if __name__ == "__main__":
    main()
