#!/usr/bin/env python3
"""
Chess position selection pipeline orchestrator.
Runs all steps to create a chess evaluation dataset.
"""

import csv
import json
import os
import subprocess
import sys
from pathlib import Path


def run_step(
    step_name: str, script: str, check_files: list = None, force: bool = False
) -> bool:
    """
    Run a pipeline step.

    Args:
        step_name: Display name for the step
        script: Python script to run
        check_files: List of files that should exist if step is complete
        force: Force re-run even if output files exist
    """
    # Check if all output files exist
    if check_files and not force:
        all_exist = all(os.path.exists(f) for f in check_files)
        if all_exist:
            print(f"✓ {step_name} - already complete")
            return True

    print(f"\n→ Running {step_name}...")
    try:
        # Use the virtual environment's Python
        if os.path.exists(".venv/bin/python"):
            python_cmd = ".venv/bin/python"
        else:
            python_cmd = sys.executable

        subprocess.run([python_cmd, script], check=True)
        print(f"✓ {step_name} complete")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {step_name} failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"✗ {step_name} failed: {e}")
        return False


def check_dependencies():
    """Check if required dependencies are available."""
    print("Checking dependencies...")

    # Check for virtual environment
    venv_path = Path(".venv")
    if not venv_path.exists():
        print("✗ Virtual environment not found. Creating one...")
        subprocess.run(["uv", "venv"], check=True)
        subprocess.run(["uv", "pip", "install", "python-chess"], check=True)
    else:
        print("✓ Virtual environment found")

    # Check for Stockfish
    try:
        subprocess.run(
            ["stockfish", "quit"], capture_output=True, text=True, input="quit\n"
        )
        print("✓ Stockfish found")
    except FileNotFoundError:
        print("✗ Stockfish not found. Please install it:")
        print("  macOS: brew install stockfish")
        print("  Ubuntu: sudo apt install stockfish")
        print("  Or download from https://stockfishchess.org/download/")
        return False

    return True


def check_questions_status():
    """Check if questions.csv exists and has evaluations."""
    if not os.path.exists("questions.csv"):
        return False, 0

    try:
        with open("questions.csv") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if not rows:
                return False, 0

            # Check if evaluations exist
            first_row = rows[0]
            if (
                first_row.get("expected_output")
                and first_row["expected_output"] != "{}"
            ):
                # Parse JSON to check if it's a valid array
                try:
                    data = json.loads(first_row["expected_output"])
                    if isinstance(data, list) and len(data) > 0:
                        return True, len(rows)
                except Exception:
                    pass
            return False, len(rows)
    except Exception:
        return False, 0


def show_statistics():
    """Display pipeline statistics."""
    stats = []

    # Check games.pgn
    if os.path.exists("output/games.pgn"):
        size = os.path.getsize("output/games.pgn") / (1024 * 1024)
        stats.append(f"  output/games.pgn: {size:.1f} MB")

    # Check games.db
    if os.path.exists("output/games.db"):
        size = os.path.getsize("output/games.db") / (1024 * 1024)
        stats.append(f"  output/games.db: {size:.1f} MB (filtered games)")

    # Check positions.csv
    if os.path.exists("output/positions.csv"):
        with open("output/positions.csv") as f:
            count = sum(1 for _ in f) - 1
        stats.append(f"  output/positions.csv: {count} positions selected")

    # Check questions.csv
    has_evals, count = check_questions_status()
    if count > 0:
        eval_status = "with evaluations" if has_evals else "without evaluations"
        stats.append(f"  questions.csv: {count} questions ({eval_status})")

    if stats:
        print("\nCurrent status:")
        for stat in stats:
            print(stat)


def main():
    """Run the chess position selection pipeline."""
    print("\n" + "=" * 60)
    print("Chess Position Selection Pipeline")
    print("=" * 60)

    # Change to the chess directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    # Show current status
    show_statistics()

    # Check dependencies
    print("\nChecking dependencies...")
    if not check_dependencies():
        sys.exit(1)

    # Parse command line arguments
    force_all = "--force" in sys.argv
    skip_eval = "--skip-eval" in sys.argv

    if force_all:
        print("\nForce mode: Re-running all steps")

    print("\n" + "-" * 60)
    print("Starting pipeline...")
    print("-" * 60)

    # Step 1: Fetch games
    if not os.path.exists("output/games.pgn"):
        if os.path.exists("01_fetch_games.py"):
            if not run_step("Step 1: Fetch games", "01_fetch_games.py"):
                print("\n✗ Pipeline failed at Step 1")
                sys.exit(1)
        else:
            print("\n✗ Error: output/games.pgn not found")
            print("  Please download from https://database.lichess.org/")
            print("  or create 01_fetch_games.py to download automatically")
            sys.exit(1)
    else:
        print("✓ Step 1: Fetch games - already complete")

    # Step 2: Process and filter games
    if not run_step(
        "Step 2: Process games",
        "02_process_games.py",
        ["output/games.db"],
        force=force_all,
    ):
        print("\n✗ Pipeline failed at Step 2")
        sys.exit(1)

    # Step 3: Select positions
    if not run_step(
        "Step 3: Select positions",
        "03_select_games.py",
        ["output/positions.csv"],
        force=force_all,
    ):
        print("\n✗ Pipeline failed at Step 3")
        sys.exit(1)

    # Step 4: Create questions with evaluations
    has_evals, question_count = check_questions_status()

    if has_evals and not force_all:
        print("✓ Step 4: Create questions - already complete")
    elif skip_eval:
        print("⚠ Step 4: Create questions - skipped (--skip-eval flag)")
    else:
        print("\n" + "-" * 60)
        print("Step 4: Create questions with evaluations")
        print("-" * 60)
        print("This step will evaluate ALL legal moves for each position.")
        print("Estimated time: 20-40 minutes for ~750 positions")
        print("\nEngine configuration:")
        print("  - Depth: 20")
        print("  - Time per position: 2 seconds")
        print("  - Output: All moves with evaluation scores")

        if not force_all and question_count > 0:
            print(f"\nWarning: questions.csv exists with {question_count} positions")
            print("This will overwrite the existing file.")

        response = input("\nContinue with evaluation? (y/n): ")
        if response.lower() == "y":
            if not run_step("Step 4: Create questions", "04_create_questions_games.py"):
                print("\n✗ Pipeline failed at Step 4")
                sys.exit(1)
        else:
            print("⚠ Evaluation skipped")

    # Final summary
    print("\n" + "=" * 60)
    print("✓ Pipeline Complete!")
    print("=" * 60)

    show_statistics()

    # Check if we have the full dataset
    if os.path.exists("output/positions.csv"):
        with open("output/positions.csv") as f:
            position_count = sum(1 for _ in f) - 1

        if position_count < 800:
            print(f"\n⚠ Note: Only {position_count}/800 game positions selected")
            print(
                f"  Missing {800 - position_count} positions (likely due to limited 2600+ ELO games)"
            )

        print(
            f"\n⚠ Reminder: {1000 - position_count} Lichess puzzle positions still need to be added"
        )
        print("  to reach the target of 1000 total positions")

    print("\nUsage:")
    print("  python generate.py          # Run pipeline (skip completed steps)")
    print("  python generate.py --force  # Re-run all steps")
    print("  python generate.py --skip-eval  # Skip evaluation step")
    print("  python print.py            # Show detailed statistics")


if __name__ == "__main__":
    main()
