"""
Main Entrypoint for Refund Agent with Evaluation System.
Provides command-line shortcuts to launch the Streamlit UI, run evaluation suites
(single-turn & multi-turn), run deterministic pytest unit tests, test via CLI,
or reset the SQLite database.
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
        "--pytest",
        action="store_true",
        help="Run Layer 1 deterministic unit tests with pytest ($0 cost)",
    )
    parser.add_argument(
        "--eval",
        choices=["dry-run", "smoke", "boundary", "guardrails", "all"],
        default=None,
        help="Run DeepEval single-turn evaluation test suite",
    )
    parser.add_argument(
        "--multiturn",
        choices=["dry-run", "live"],
        default=None,
        help="Run DeepEval multi-turn conversational evaluation suite",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Reset and re-seed the SQLite database with dynamic relative dates",
    )
    args = parser.parse_args()

    if args.seed:
        from agent.db import seed_db
        seed_db()
        print("Successfully re-seeded SQLite database with relative dates.")
        return

    if args.pytest:
        subprocess.run([sys.executable, "-m", "pytest", "-v"])
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

    if args.multiturn:
        if args.multiturn == "dry-run":
            subprocess.run([sys.executable, "evaluations/eval_multiturn.py", "--dry-run"])
        else:
            subprocess.run([sys.executable, "evaluations/eval_multiturn.py"])
        return

    # Default: Show helpful usage banner
    print("\n" + "=" * 70)
    print(" 🛡️  Refund Customer Support Agent & Evaluation System")
    print("=" * 70)
    print(" Available Commands:")
    print("   1. Layer 1 Unit Tests ($0):  uv run python main.py --pytest")
    print("   2. Single-Turn Dry-Run ($0): uv run python main.py --eval dry-run")
    print("   3. Multi-Turn Dry-Run ($0):  uv run python main.py --multiturn dry-run")
    print("   4. Single-Turn Smoke Gate:   uv run python main.py --eval smoke")
    print("   5. Multi-Turn Live Gate:     uv run python main.py --multiturn live")
    print("   6. Launch Web UI:            uv run python main.py --ui")
    print("   7. Interactive CLI Chat:     uv run python main.py --cli")
    print("   8. Re-seed Database:         uv run python main.py --seed")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
