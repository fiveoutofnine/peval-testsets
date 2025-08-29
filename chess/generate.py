#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

def run_step(step_name: str, script: str, check_files: list) -> bool:
    """Run a step if its output files don't exist."""
    # Check if all output files exist
    all_exist = all(os.path.exists(f) for f in check_files)
    
    if all_exist:
        print(f"✓ {step_name} - already complete (found {', '.join(check_files)})")
        return True
    
    print(f"\n→ Running {step_name}...")
    try:
        # Use the virtual environment's Python
        python_cmd = sys.executable if hasattr(sys, 'real_prefix') or hasattr(sys, 'base_prefix') else "python3"
        result = subprocess.run([python_cmd, script], check=True)
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
        subprocess.run(["stockfish", "quit"], capture_output=True, text=True, input="quit\n")
        print("✓ Stockfish found")
    except FileNotFoundError:
        print("✗ Stockfish not found. Please install it:")
        print("  macOS: brew install stockfish")
        print("  Ubuntu: sudo apt install stockfish")
        print("  Or download from https://stockfishchess.org/download/")
        return False
    
    return True


def main():
    print("Chess Position Selection Pipeline")
    print("=" * 50)
    
    # Change to the chess directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    print("\nRunning pipeline steps...")
    
    # Step 1: Fetch games (if needed)
    if os.path.exists("01_fetch.py"):
        if not run_step("Step 1: Fetch games", "01_fetch.py", ["games.pgn"]):
            print("\nPipeline stopped at Step 1")
            sys.exit(1)
    else:
        # Check if games.pgn exists
        if not os.path.exists("games.pgn"):
            print("✗ games.pgn not found and no fetch script available")
            sys.exit(1)
        print("✓ Step 1: Fetch games - games.pgn already exists")
    
    # Step 2: Process and filter games
    if not run_step("Step 2: Process games", "02_process.py", ["output/games.db"]):
        print("\nPipeline stopped at Step 2")
        sys.exit(1)
    
    # Step 3: Select positions
    if not run_step("Step 3: Select positions", "03_select.py", ["output/positions.csv"]):
        print("\nPipeline stopped at Step 3")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✓ Pipeline complete!")
    print("\nOutput files:")
    print("  - output/games.db: Filtered games database")
    print("  - output/positions.csv: Selected chess positions (intermediate format)")
    
    # Show summary statistics
    if os.path.exists("output/positions.csv"):
        with open("output/positions.csv") as f:
            line_count = sum(1 for _ in f) - 1  # Subtract header
        print(f"\nTotal positions selected: {line_count}")
        
        # Note about puzzles
        if line_count < 1000:
            print(f"\nNote: {1000 - line_count} Lichess puzzle positions still need to be added")


if __name__ == "__main__":
    main()
