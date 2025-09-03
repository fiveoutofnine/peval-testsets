#!/usr/bin/env python3
"""
Create questions.csv from both positions.csv and puzzles.csv with full move evaluations.
Each position is evaluated to get scores for ALL legal moves.
"""

import csv
import json
import os
import sys
import time
from typing import Dict, List, Tuple

import chess
import chess.engine

# Configuration
STOCKFISH_PATH = "stockfish"

# Engine settings - can be adjusted for testing
ENGINE_CONFIG = {
    "depth": 20,  # Search depth
    "time_limit": 2.0,  # Time limit per position in seconds
    "multipv": 500,  # Max number of lines to analyze (set high to get all moves)
    "threads": 1,  # Number of threads
    "hash": 512,  # Hash table size in MB
}

# Testing configuration
TEST_MODE = False  # Set to True for testing with subset
TEST_POSITIONS = 10  # Number of positions to process in test mode


def evaluate_all_moves(
    board: chess.Board, engine: chess.engine.SimpleEngine
) -> List[Tuple[str, int]]:
    """
    Evaluate all legal moves in a position and return them sorted by score.
    Returns list of (move_uci, score_cp) tuples.
    """
    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return []

    # Configure engine
    engine.configure(
        {
            "Threads": ENGINE_CONFIG["threads"],
            "Hash": ENGINE_CONFIG["hash"],
        }
    )

    # Use multipv to analyze all moves at once (up to 500)
    multipv = min(len(legal_moves), ENGINE_CONFIG["multipv"])

    try:
        # Analyze position with multiple PVs
        info = engine.analyse(
            board,
            chess.engine.Limit(
                depth=ENGINE_CONFIG["depth"],
                time=ENGINE_CONFIG["time_limit"],
            ),
            multipv=multipv,
        )

        # Extract scores for each move
        move_scores = []
        analyzed_moves = set()

        # Get scores from multipv analysis
        for pv_info in info:
            if "pv" in pv_info and pv_info["pv"]:
                move = pv_info["pv"][0]
                if "score" in pv_info and move not in analyzed_moves:
                    score = pv_info["score"].white()
                    if score.is_mate():
                        # Convert mate scores to centipawns
                        mate_in = score.mate()
                        # Use large values for mate scores
                        cp_score = (
                            30000 - abs(mate_in) * 100
                            if mate_in > 0
                            else -30000 + abs(mate_in) * 100
                        )
                    else:
                        cp_score = score.score()

                    if cp_score is not None:
                        # Adjust score for side to move
                        if board.turn == chess.BLACK:
                            cp_score = -cp_score

                        move_scores.append((move.uci(), cp_score))
                        analyzed_moves.add(move)

        # For any remaining moves not analyzed, do individual analysis
        for move in legal_moves:
            if move not in analyzed_moves:
                board.push(move)
                try:
                    # Quick evaluation for remaining moves
                    info = engine.analyse(
                        board,
                        chess.engine.Limit(depth=10, time=0.1),
                    )
                    if "score" in info:
                        score = info["score"].white()
                        if score.is_mate():
                            mate_in = score.mate()
                            cp_score = (
                                30000 - abs(mate_in) * 100
                                if mate_in > 0
                                else -30000 + abs(mate_in) * 100
                            )
                        else:
                            cp_score = score.score()

                        if cp_score is not None:
                            # Negate because we pushed the move
                            cp_score = -cp_score
                            # Adjust for original side to move
                            if board.turn == chess.WHITE:  # We're now on opposite side
                                cp_score = -cp_score

                            move_scores.append((move.uci(), cp_score))
                finally:
                    board.pop()

        # Sort by score (best first)
        move_scores.sort(key=lambda x: x[1], reverse=True)
        return move_scores

    except Exception as e:
        print(f"Error evaluating position: {e}", file=sys.stderr)
        return []


def format_expected_output(move_scores: List[Tuple[str, int]]) -> str:
    """
    Format move scores as JSON array for expected_output field.
    """
    # Create array of [move, score] pairs
    output = [[move, score] for move, score in move_scores]
    return json.dumps(output, separators=(",", ":"))


def process_game_positions() -> List[Dict]:
    """Process game positions from positions.csv."""
    positions_file = "output/positions.csv"
    if not os.path.exists(positions_file):
        print(
            f"Warning: {positions_file} not found, skipping game positions",
            file=sys.stderr,
        )
        return []

    questions = []
    with open(positions_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append(
                {
                    "prompt": row["fen"],
                    "fen": row["fen"],
                    "source": "game",
                    "elo_bucket": row.get("elo_bucket", ""),
                    "phase": row.get("phase", ""),
                    "type": row.get("type", ""),
                    "color": row.get("color", ""),
                    "castle_rights": row.get("castle_rights", ""),
                    "en_passant": row.get("en_passant", ""),
                    "legal_moves": row.get("legal_moves", ""),
                    "hash_bucket": row.get("hash_bucket", "0"),
                }
            )

    return questions


def process_puzzle_positions() -> List[Dict]:
    """Process puzzle positions from puzzles.csv."""
    puzzles_file = "output/puzzles.csv"
    if not os.path.exists(puzzles_file):
        print(
            f"Warning: {puzzles_file} not found, skipping puzzle positions",
            file=sys.stderr,
        )
        return []

    questions = []
    with open(puzzles_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # For puzzles, use the FEN after the first move is played
            # The "moves" field contains the solution moves
            fen = row["fen"]
            moves = row["moves"].split()

            # Apply the first move to get the puzzle position
            try:
                board = chess.Board(fen)
                if moves:
                    first_move = chess.Move.from_uci(moves[0])
                    board.push(first_move)
                    puzzle_fen = board.fen()
                else:
                    puzzle_fen = fen
            except Exception as e:
                print(
                    f"Error processing puzzle {row['puzzle_id']}: {e}", file=sys.stderr
                )
                puzzle_fen = fen

            # Calculate hash bucket for private/public split
            import hashlib

            hash_value = int(hashlib.sha256(puzzle_fen.encode()).hexdigest()[:8], 16)
            hash_bucket = hash_value % 100

            questions.append(
                {
                    "prompt": puzzle_fen,
                    "fen": puzzle_fen,
                    "source": "puzzle",
                    "puzzle_id": row["puzzle_id"],
                    "rating": row["rating"],
                    "phase": row["phase"],
                    "color": row["color"],
                    "themes": row["themes"],
                    "hash_bucket": str(hash_bucket),
                }
            )

    return questions


def main():
    """Create questions.csv with evaluations from both game and puzzle positions."""
    # Check if Stockfish is available
    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    except Exception as e:
        print(
            f"Error: Could not start Stockfish engine at '{STOCKFISH_PATH}'",
            file=sys.stderr,
        )
        print(f"Details: {e}", file=sys.stderr)
        print("\nPlease ensure Stockfish is installed:", file=sys.stderr)
        print("  macOS: brew install stockfish", file=sys.stderr)
        print("  Ubuntu: sudo apt install stockfish", file=sys.stderr)
        sys.exit(1)

    # Gather all positions
    print("Loading positions...")
    all_questions = []

    # Load game positions
    game_questions = process_game_positions()
    print(f"  Loaded {len(game_questions)} game positions")
    all_questions.extend(game_questions)

    # Load puzzle positions
    puzzle_questions = process_puzzle_positions()
    print(f"  Loaded {len(puzzle_questions)} puzzle positions")
    all_questions.extend(puzzle_questions)

    if not all_questions:
        print("Error: No positions found to evaluate!", file=sys.stderr)
        engine.quit()
        sys.exit(1)

    print(f"\nTotal positions to evaluate: {len(all_questions)}")

    # Test mode handling
    if TEST_MODE:
        print(
            f"\n*** TEST MODE: Processing only first {TEST_POSITIONS} positions ***\n"
        )
        all_questions = all_questions[:TEST_POSITIONS]

    # Process positions
    start_time = time.time()
    processed = 0

    # Open output file
    with open("questions.csv", "w", newline="") as f:
        # Define fieldnames based on all possible fields
        fieldnames = [
            "prompt",
            "expected_output",
            "private",
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, question in enumerate(all_questions):
            # Show progress
            if i % 10 == 0:
                elapsed = time.time() - start_time
                if i > 0:
                    per_position = elapsed / i
                    remaining = (len(all_questions) - i) * per_position
                    print(
                        f"Progress: {i}/{len(all_questions)} positions "
                        f"({i / len(all_questions) * 100:.1f}%) - "
                        f"Est. remaining: {remaining / 60:.1f} min"
                    )

            try:
                # Create board from FEN
                board = chess.Board(question["prompt"])

                # Evaluate all moves
                move_scores = evaluate_all_moves(board, engine)

                if move_scores:
                    # Format output
                    expected_output = format_expected_output(move_scores)

                    # Determine if position should be private (20% of positions)
                    # Use hash_bucket: 0-19 are private, 20-99 are public
                    is_private = int(question["hash_bucket"]) < 20

                    # Create output row
                    output_row = {
                        "prompt": question["prompt"],
                        "expected_output": expected_output,
                        "private": str(is_private).lower(),
                    }

                    # Add all other fields from the question
                    for field in question:
                        if (
                            field not in ["prompt", "hash_bucket"]
                            and field in fieldnames
                        ):
                            output_row[field] = question[field]

                    writer.writerow(output_row)
                    processed += 1

            except Exception as e:
                print(f"\nError processing position {i}: {e}", file=sys.stderr)
                print(f"FEN: {question['prompt']}", file=sys.stderr)
                continue

    # Clean up
    engine.quit()

    # Summary
    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"Evaluation complete!")
    print(f"Processed {processed}/{len(all_questions)} positions")
    print(f"Time elapsed: {elapsed / 60:.1f} minutes")
    print(f"Average time per position: {elapsed / processed:.2f} seconds")
    print(f"Output written to: questions.csv")

    # Show split statistics
    with open("questions.csv") as f:
        reader = csv.DictReader(f)
        private_count = sum(1 for row in reader if row["private"] == "true")
        public_count = processed - private_count

    print(f"\nDataset split:")
    print(f"  Public: {public_count} ({public_count / processed * 100:.1f}%)")
    print(f"  Private: {private_count} ({private_count / processed * 100:.1f}%)")


if __name__ == "__main__":
    main()
