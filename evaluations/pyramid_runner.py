"""
Agentic AI Testing Pyramid Orchestrator.
Executes testing layers hierarchically with an early-exit gatekeeper:
Layer 1 (Pytest Unit Tests) -> Layer 2 (Single-Turn Evals) -> Layer 3 (Multi-Turn Evals) -> Layer 4 (Observability)
If Layer 1 fails, execution aborts immediately to protect LLM API balances.
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure root directory is discoverable
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def print_pyramid_banner():
    banner = """
===========================================================================
               🛡️  AGENTIC AI TESTING PYRAMID RUNNER
===========================================================================
                         / \\
                        /   \\   Layer 4: Observability & Audit
                       /-----\\  (Audit tables, Streamlit glass box, logs)
                      /       \\  Layer 3: Multi-Turn Trajectory Evals
                     /---------\\ (ConversationalTestCase, context retention)
                    /           \\  Layer 2: Single-Turn Component Evals
                   /-------------\\ (ToolCorrectness, ArgumentCorrectness, GEval)
                  /               \\  Layer 1: Deterministic Unit Tests
                 /-----------------\\ (Pytest, DB transactions, idempotency - $0)
===========================================================================
"""
    print(banner)


def run_layer_1() -> bool:
    """
    Layer 1: Deterministic Unit Tests with Pytest ($0 cost, sub-second).
    Gatekeeper rule: If Layer 1 fails, higher layers MUST NOT execute.
    """
    print("\n" + "=" * 75)
    print(" [LAYER 1] Deterministic Unit Tests (Pytest - $0 Cost)")
    print("=" * 75)
    print("Target: SQLite schema, relative dates, idempotency, tool contracts...")
    
    start_time = time.time()
    res = subprocess.run([sys.executable, "-m", "pytest", "-v", "tests/"])
    elapsed = time.time() - start_time
    
    if res.returncode == 0:
        print(f"✅ Layer 1 PASSED in {elapsed:.2f}s ($0.00 API cost)")
        return True
    else:
        print(f"❌ Layer 1 FAILED in {elapsed:.2f}s.")
        print("🚨 EARLY-EXIT GATEKEEPER TRIGGERED: Aborting higher layers to prevent unnecessary LLM costs!")
        return False


def run_layer_2(dry_run: bool = True) -> bool:
    """
    Layer 2: Single-Turn LLM Component Evals (Tool selection, schema validation, GEval).
    """
    print("\n" + "=" * 75)
    mode_str = "DRY-RUN ($0 Cost)" if dry_run else "LIVE EVALUATION"
    print(f" [LAYER 2] Single-Turn Component Evals ({mode_str})")
    print("=" * 75)
    print("Target: Tool correctness, parameter precision, answer correctness...")

    cmd = [sys.executable, "evaluations/eval_all.py"]
    if dry_run:
        cmd.append("--dry-run")
    else:
        cmd.extend(["--category", "smoke"])

    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("✅ Layer 2 PASSED")
        return True
    else:
        print("❌ Layer 2 FAILED")
        return False


def run_layer_3(dry_run: bool = True) -> bool:
    """
    Layer 3: Multi-Turn Conversational Trajectory Evals (ConversationalTestCase, slot-filling).
    """
    print("\n" + "=" * 75)
    mode_str = "DRY-RUN ($0 Cost)" if dry_run else "LIVE EVALUATION"
    print(f" [LAYER 3] Multi-Turn Trajectory Evals ({mode_str})")
    print("=" * 75)
    print("Target: Conversational slot-filling, context memory across turns, policy shifts...")

    cmd = [sys.executable, "evaluations/eval_multiturn.py"]
    if dry_run:
        cmd.append("--dry-run")
    else:
        cmd.extend(["--scenario", "MT-01"])

    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("✅ Layer 3 PASSED")
        return True
    else:
        print("❌ Layer 3 FAILED")
        return False


def run_layer_4() -> bool:
    """
    Layer 4: Production Observability & Database Audit Check ($0 cost).
    """
    print("\n" + "=" * 75)
    print(" [LAYER 4] Production Observability & Audit Integrity Check ($0 Cost)")
    print("=" * 75)
    print("Target: Database audit ticket accessibility and supervisor escalation logs...")

    try:
        from agent.db import get_all_tickets, get_all_purchases
        tickets = get_all_tickets()
        purchases = get_all_purchases()
        print(f"   * Total Tracked Purchases in SQLite: {len(purchases)}")
        print(f"   * Total Issued/Escalated Tickets: {len(tickets)}")
        print("   * Streamlit Glass-Box Inspector: Ready (uv run python main.py --ui)")
        print("✅ Layer 4 Audit Verification PASSED ($0.00 API cost)")
        return True
    except Exception as e:
        print(f"❌ Layer 4 Verification Failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Agentic AI Testing Pyramid Runner")
    parser.add_argument(
        "--layer",
        choices=["1", "2", "3", "4", "all"],
        default="all",
        help="Specific pyramid tier to execute (default: all)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Execute live LLM calls for Layer 2/3 (default is safe dry-run mode)",
    )
    args = parser.parse_args()

    print_pyramid_banner()
    is_dry_run = not args.live

    if is_dry_run:
        print("ℹ️ Running in SAFE DRY-RUN mode: Validates all layers with $0.00 LLM costs.")
    else:
        print("⚠️ Running in LIVE mode: Layer 2 & 3 will make live LLM API calls.")

    results = {}

    # Layer 1 Execution (Always runs first in 'all' mode)
    if args.layer in ["1", "all"]:
        l1_passed = run_layer_1()
        results["Layer 1 (Pytest Unit Tests)"] = "PASSED" if l1_passed else "FAILED"
        if not l1_passed and args.layer == "all":
            print("\n❌ Pyramid execution aborted due to Layer 1 failure.")
            sys.exit(1)

    # Layer 2 Execution
    if args.layer in ["2", "all"]:
        l2_passed = run_layer_2(dry_run=is_dry_run)
        results["Layer 2 (Single-Turn Component Evals)"] = "PASSED" if l2_passed else "FAILED"

    # Layer 3 Execution
    if args.layer in ["3", "all"]:
        l3_passed = run_layer_3(dry_run=is_dry_run)
        results["Layer 3 (Multi-Turn Trajectory Evals)"] = "PASSED" if l3_passed else "FAILED"

    # Layer 4 Execution
    if args.layer in ["4", "all"]:
        l4_passed = run_layer_4()
        results["Layer 4 (Observability & Audit Check)"] = "PASSED" if l4_passed else "FAILED"

    # Final Summary Table
    print("\n" + "=" * 75)
    print(" 📊 TESTING PYRAMID EXECUTION SUMMARY")
    print("=" * 75)
    for layer_name, status in results.items():
        icon = "✅" if status == "PASSED" else "❌"
        print(f" {icon} {layer_name:<45} : {status}")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
