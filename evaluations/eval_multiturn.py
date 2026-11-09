"""
Multi-Turn Conversational Evaluation Runner for Refund Customer Support Agent.
Tests memory, slot filling, policy negotiation, and state retention across
multiple conversational turns using DeepEval's ConversationalTestCase.
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from deepeval import evaluate
from deepeval.evaluate import CacheConfig, DisplayConfig
from deepeval.metrics import (
    ConversationCompletenessMetric,
    ConversationalGEval,
)
from deepeval.test_case import ConversationalTestCase, Turn

# Ensure agent directory is discoverable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.agent import invoke_agent
from evaluations.dataset_multiturn import MULTITURN_SCENARIOS, MultiTurnScenario
from evaluations.model import eval_model


def build_multiturn_metrics():
    """Build multi-turn conversational metrics."""
    metrics = [
        ConversationCompletenessMetric(
            threshold=0.7,
            model=eval_model,
            include_reason=True,
        ),
        ConversationalGEval(
            name="Multi-Turn Context & Policy Adherence",
            criteria=(
                "Evaluate whether the agent correctly retains context from earlier turns (e.g., username, requested items), "
                "strictly adheres to the 30-day return policy and duplicate refund rules, "
                "and does not issue refund tickets prematurely before obtaining customer identity."
            ),
            evaluation_steps=[
                "Check that the agent does NOT issue a refund ticket if the customer username is missing in earlier turns.",
                "Verify that the agent remembers user information provided in subsequent turns.",
                "Verify that the agent correctly applies policies (30-day window, already refunded) across all turns.",
                "Confirm that final responses accurately address customer questions or refund actions.",
            ],
            threshold=0.75,
            model=eval_model,
            verbose_mode=True,
        ),
    ]
    return metrics


def run_dry_run(scenarios: list):
    """Dry-run inspection of multi-turn scenarios with zero LLM API costs."""
    print("\n" + "=" * 75)
    print(" [DRY RUN] Multi-Turn Conversational Suite Inspection (Zero Cost)")
    print("=" * 75)
    print(f"Total Multi-Turn Scenarios: {len(scenarios)}")
    print(f"Evaluator Model: {eval_model}")
    print("-" * 75)

    for sc in scenarios:
        print(f"\n[{sc.id}] {sc.title}")
        print(f"Scenario: {sc.scenario_description}")
        print(f"Expected Outcome: {sc.expected_outcome}")
        print(f"Dialogue Flow ({len(sc.turns)} Turns):")
        for turn_data in sc.turns:
            turn_no = turn_data["turn"]
            user_in = turn_data["user_input"]
            expected_beh = turn_data["expected_agent_behavior"]
            tools = turn_data.get("expected_tools", [])
            print(f"   Turn {turn_no} [User]: {user_in}")
            print(f"   Turn {turn_no} [Expected]: {expected_beh}")
            print(f"   Turn {turn_no} [Tools]: {', '.join(tools) if tools else 'None'}")
        print("-" * 75)

    print("\n" + "=" * 75)
    print("Dry run completed successfully. No LLM calls were made.")
    print("=" * 75 + "\n")


def generate_multiturn_report(records: list, report_path: Path):
    """Generates Markdown report of multi-turn dialogues."""
    lines = [
        "# Multi-Turn Conversational Agent Evaluation Report",
        f"\n**Generated At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Evaluator Model:** `{eval_model}`",
        f"**Total Scenarios Evaluated:** {len(records)}\n",
        "## Evaluated Dialogue Transcripts\n",
    ]

    for item in records:
        lines.append(f"### {item['id']}: {item['title']}")
        lines.append(f"**Scenario:** {item['scenario']}")
        lines.append(f"**Expected Outcome:** {item['expected_outcome']}\n")
        lines.append("| Turn | Role | Content |")
        lines.append("|---|---|---|")
        for t in item["turns"]:
            clean_content = t["content"].replace("\n", " ")
            lines.append(f"| {t['turn']} | **{t['role']}** | {clean_content} |")
        lines.append("\n---\n")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSaved multi-turn evaluation report to: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Multi-Turn Evaluation Runner")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect multi-turn scenarios without calling LLMs (zero cost)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Run a specific scenario ID (e.g. MT-01)",
    )
    parser.add_argument(
        "--report",
        type=str,
        default="eval_multiturn_report.md",
        help="Path to save markdown report",
    )
    args = parser.parse_args()

    load_dotenv()
    target_scenarios = MULTITURN_SCENARIOS
    if args.scenario:
        target_scenarios = [s for s in MULTITURN_SCENARIOS if s.id == args.scenario]

    if args.dry_run:
        run_dry_run(target_scenarios)
        return

    print(f"\nStarting multi-turn evaluation for {len(target_scenarios)} scenario(s)...")
    metrics = build_multiturn_metrics()
    cache_config = CacheConfig(use_cache=False, write_cache=False)
    display_config = DisplayConfig(inspect_after_run=False)

    conversational_test_cases = []
    report_records = []

    for sc in target_scenarios:
        print(f"\nExecuting Scenario {sc.id}: {sc.title}...")
        thread_id = str(uuid4())  # Persistent LangGraph session across turns
        dialogue_turns = []
        turn_records = []

        for turn_data in sc.turns:
            user_input = turn_data["user_input"]
            dialogue_turns.append(Turn(role="user", content=user_input))
            turn_records.append({
                "turn": turn_data["turn"],
                "role": "User",
                "content": user_input,
            })

            # Invoke agent across the same thread_id
            response = invoke_agent(user_message=user_input, thread_id=thread_id)
            assistant_reply = response["answer"]

            dialogue_turns.append(Turn(role="assistant", content=assistant_reply))
            turn_records.append({
                "turn": turn_data["turn"],
                "role": "Agent",
                "content": assistant_reply,
            })

        conversational_test_cases.append(
            ConversationalTestCase(
                turns=dialogue_turns,
                scenario=sc.scenario_description,
                expected_outcome=sc.expected_outcome,
            )
        )
        report_records.append({
            "id": sc.id,
            "title": sc.title,
            "scenario": sc.scenario_description,
            "expected_outcome": sc.expected_outcome,
            "turns": turn_records,
        })

    evaluate(
        test_cases=conversational_test_cases,
        metrics=metrics,
        cache_config=cache_config,
        display_config=display_config,
    )

    generate_multiturn_report(report_records, Path(args.report))
    print(f"\nCompleted multi-turn evaluation across {len(conversational_test_cases)} scenarios.")


if __name__ == "__main__":
    main()

