"""
Main Entrypoint for Refund Agent with Evaluation System.
Provides command-line shortcuts to launch the Streamlit UI, run evaluation suites,
test the agent via CLI, or reset the SQLite database.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Refund Customer Support Agent & LLMOps Evaluation System")
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Launch the interactive Streamlit dual-pane app",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Start an interactive terminal conversation session",
    )
    parser.add_argument(
        "--eval",
        choices=["dry-run", "smoke", "boundary", "guardrails", "all"],
        default=None,
        help="Run DeepEval evaluation test suite",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Reset and re-seed the SQLite database with dynamic relative dates",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent

    if args.seed:
        from agent.db import seed_db
        seed_db()
        print("Successfully re-seeded SQLite database with relative dates.")
        return

    if args.ui:
        print("Launching Streamlit UI...")
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
        return

    if args.cli:
        from agent.agent import run_conversation_cli
        run_conversation_cli()
        return

    if args.eval:
        if args.eval == "dry-run":
            subprocess.run([sys.executable, "evaluations/eval_all.py", "--dry-run"])
        else:
            subprocess.run([sys.executable, "evaluations/eval_all.py", "--category", args.eval])
        return

    # Default: Show helpful usage banner
    print("\n" + "=" * 65)
    print(" 🛡️  Refund Customer Support Agent & Evaluation System")
    print("=" * 65)
    print(" Available Commands:")
    print("   1. Launch Web UI:         uv run python main.py --ui")
    print("   2. Interactive CLI Chat:  uv run python main.py --cli")
    print("   3. Dry-Run Eval ($0):     uv run python main.py --eval dry-run")
    print("   4. Smoke Test Gate:       uv run python main.py --eval smoke")
    print("   5. Re-seed Database:      uv run python main.py --seed")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
