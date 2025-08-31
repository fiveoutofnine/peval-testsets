#!/usr/bin/env python3
"""
Select 200 puzzles from the Lichess puzzle database.
Random selection with 70/30 middle/endgame split.
"""

import csv
import os
import random
import sys
from typing import List, Dict

# Configuration
PUZZLE_CSV = "output/lichess_puzzles.csv"
OUTPUT_CSV = "output/puzzles.csv"

# Target: 200 puzzles total with 70/30 middlegame/endgame split
TOTAL_PUZZLES = 200
MIDDLEGAME_TARGET = 140
ENDGAME_TARGET = 60


def get_puzzle_phase(themes: str) -> str:
    """Determine if puzzle is middlegame or endgame based on themes."""
    if not themes:
        return "middlegame"

    theme_list = themes.strip().split()

    # If it has endgame theme, it's endgame
    if "endgame" in theme_list:
        return "endgame"

    # Otherwise it's middlegame
    return "middlegame"


def random_sample(puzzles: List[Dict], target_count: int, seed: int = 42) -> List[Dict]:
    """
    Select puzzles using pure random sampling.
    """
    if len(puzzles) <= target_count:
        return puzzles

    # Set random seed for reproducibility
    random.seed(seed)

    # Simple random sample without replacement
    return random.sample(puzzles, target_count)


def load_and_select_puzzles() -> List[Dict]:
    """Load puzzles and select 200 with random selection."""
    if not os.path.exists(PUZZLE_CSV):
        print(
            f"Error: {PUZZLE_CSV} not found. Run 05_fetch_puzzles.py first.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Loading puzzles from {PUZZLE_CSV}...")

    middlegame_puzzles = []
    endgame_puzzles = []

    total_count = 0

    with open(PUZZLE_CSV, encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)

        for row in reader:
            total_count += 1
            if total_count % 500000 == 0:
                print(f"  Processed {total_count:,} puzzles...")

            try:
                # Extract puzzle data
                puzzle_id = row["PuzzleId"]
                fen = row["FEN"]
                moves = row["Moves"]
                rating = int(row["Rating"])
                themes = row.get("Themes", "")

                # Skip puzzles without valid data
                if not fen or not moves:
                    continue

                # Determine phase
                phase = get_puzzle_phase(themes)

                # Store puzzle data
                puzzle_data = {
                    "puzzle_id": puzzle_id,
                    "fen": fen,
                    "moves": moves,
                    "rating": rating,
                    "themes": themes,
                    "phase": phase,
                    "game_url": row.get("GameUrl", ""),
                }

                if phase == "middlegame":
                    middlegame_puzzles.append(puzzle_data)
                else:
                    endgame_puzzles.append(puzzle_data)

            except (ValueError, KeyError):
                # Skip malformed rows
                continue

    print(f"\nLoaded {total_count:,} total puzzles")
    print(f"  Middlegame: {len(middlegame_puzzles):,}")
    print(f"  Endgame: {len(endgame_puzzles):,}")

    # Select puzzles using random sampling
    selected = []

    # Select middlegame puzzles
    selected_middlegame = random_sample(middlegame_puzzles, MIDDLEGAME_TARGET)
    selected.extend(selected_middlegame)

    if len(selected_middlegame) < MIDDLEGAME_TARGET:
        print(f"Warning: Only {len(selected_middlegame)} middlegame puzzles selected")

    # Select endgame puzzles
    remaining_slots = TOTAL_PUZZLES - len(selected)
    selected_endgame = random_sample(
        endgame_puzzles, min(ENDGAME_TARGET, remaining_slots)
    )
    selected.extend(selected_endgame)

    # If we still need more puzzles, take more from middlegame
    if len(selected) < TOTAL_PUZZLES and len(middlegame_puzzles) > len(
        selected_middlegame
    ):
        additional_needed = TOTAL_PUZZLES - len(selected)
        # Get puzzles that weren't already selected
        remaining_middlegame = [
            p for p in middlegame_puzzles if p not in selected_middlegame
        ]
        additional = random_sample(remaining_middlegame, additional_needed, seed=43)
        selected.extend(additional)

    print(f"\nSelected {len(selected)} puzzles")

    return selected


def get_side_to_move(fen: str) -> str:
    """Get side to move from FEN."""
    parts = fen.split()
    return "white" if parts[1] == "w" else "black"


def write_puzzles_csv(puzzles: List[Dict], output_path: str):
    """Write selected puzzles to CSV."""
    with open(output_path, "w", newline="") as f:
        fieldnames = [
            "puzzle_id",
            "fen",
            "moves",
            "rating",
            "phase",
            "color",
            "themes",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for puzzle in puzzles:
            writer.writerow(
                {
                    "puzzle_id": puzzle["puzzle_id"],
                    "fen": puzzle["fen"],
                    "moves": puzzle["moves"],
                    "rating": puzzle["rating"],
                    "phase": puzzle["phase"],
                    "color": get_side_to_move(puzzle["fen"]),
                    "themes": puzzle["themes"],
                }
            )


def main():
    """Select 200 puzzles from Lichess puzzle database."""
    print("Selecting 200 Lichess puzzles...")
    print("Using random selection")
    print(f"Target: {MIDDLEGAME_TARGET} middlegame, {ENDGAME_TARGET} endgame")

    # Load and select puzzles
    selected_puzzles = load_and_select_puzzles()

    # Sort by puzzle_id for consistent ordering
    selected_puzzles.sort(key=lambda p: p["puzzle_id"])

    # Write to CSV
    write_puzzles_csv(selected_puzzles, OUTPUT_CSV)

    print(f"\n{'=' * 60}")
    print(f"Successfully selected {len(selected_puzzles)} puzzles")
    print(f"Output written to: {OUTPUT_CSV}")

    # Final statistics
    total_middlegame = len([p for p in selected_puzzles if p["phase"] == "middlegame"])
    total_endgame = len(selected_puzzles) - total_middlegame
    print(f"\nPhase distribution:")
    print(
        f"  Middlegame: {total_middlegame} ({total_middlegame / len(selected_puzzles) * 100:.1f}%)"
    )
    print(
        f"  Endgame: {total_endgame} ({total_endgame / len(selected_puzzles) * 100:.1f}%)"
    )

    # Color distribution
    white_count = len(
        [p for p in selected_puzzles if get_side_to_move(p["fen"]) == "white"]
    )
    black_count = len(selected_puzzles) - white_count
    print(f"\nColor distribution:")
    print(
        f"  White to move: {white_count} ({white_count / len(selected_puzzles) * 100:.1f}%)"
    )
    print(
        f"  Black to move: {black_count} ({black_count / len(selected_puzzles) * 100:.1f}%)"
    )


if __name__ == "__main__":
    main()
