#!/usr/bin/env python3
"""
Create questions.csv from positions.csv with full move evaluations.
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
    "hash": 256,  # Hash table size in MB
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

    move_scores = []

    # Method 1: Use MultiPV to get multiple lines at once
    # This is faster than analyzing each move separately
    try:
        # Analyze position with high MultiPV
        info = engine.analyse(
            board,
            chess.engine.Limit(
                depth=ENGINE_CONFIG["depth"], time=ENGINE_CONFIG["time_limit"]
            ),
            multipv=min(len(legal_moves), ENGINE_CONFIG["multipv"]),
        )

        # Extract scores for each PV
        pv_moves = {}
        for pv_info in info:
            if "pv" in pv_info and pv_info["pv"] and "score" in pv_info:
                move = pv_info["pv"][0]
                score = pv_info["score"]

                # Convert score to centipawns from the moving side's perspective
                if score.is_mate():
                    # Mate score
                    mate_distance = score.relative.mate()
                    # Positive mate distance = we're mating, negative = we're being mated
                    if mate_distance > 0:
                        cp_score = 30000 - mate_distance  # Mate in N: very high score
                    else:
                        cp_score = -30000 - mate_distance  # Mated in N: very low score
                else:
                    cp_score = score.relative.score()

                pv_moves[move.uci()] = cp_score

        # For moves not in the PV list, we need to analyze them separately
        # This happens when there are more legal moves than MultiPV lines
        analyzed_moves = set(pv_moves.keys())
        remaining_moves = [m for m in legal_moves if m.uci() not in analyzed_moves]

        if remaining_moves:
            # These are likely bad moves not in top MultiPV
            # We can either analyze them individually or assign a default bad score
            # For efficiency, let's analyze them with reduced depth
            reduced_depth = max(10, ENGINE_CONFIG["depth"] // 2)

            for move in remaining_moves:
                board.push(move)
                try:
                    # Analyze resulting position (with negated score since it's opponent's turn)
                    result = engine.analyse(
                        board, chess.engine.Limit(depth=reduced_depth, time=0.1)
                    )
                    if "score" in result:
                        score = result["score"]
                        if score.is_mate():
                            mate_distance = score.relative.mate()
                            if mate_distance > 0:
                                cp_score = -(30000 - mate_distance)
                            else:
                                cp_score = -(-30000 - mate_distance)
                        else:
                            cp_score = -score.relative.score()
                        pv_moves[move.uci()] = cp_score
                except Exception:
                    # If analysis fails, assign a very bad score
                    pv_moves[move.uci()] = -10000
                finally:
                    board.pop()

        # Convert to list of tuples
        for move in legal_moves:
            move_uci = move.uci()
            if move_uci in pv_moves:
                move_scores.append((move_uci, pv_moves[move_uci]))
            else:
                # Shouldn't happen, but just in case
                move_scores.append((move_uci, -10000))

    except Exception as e:
        print(f"\nError during analysis: {e}")
        # Fallback: analyze each move individually
        for move in legal_moves:
            board.push(move)
            try:
                result = engine.analyse(board, chess.engine.Limit(depth=10, time=0.1))
                if "score" in result:
                    score = result["score"]
                    if score.is_mate():
                        mate_distance = score.relative.mate()
                        if mate_distance > 0:
                            cp_score = -(30000 - mate_distance)
                        else:
                            cp_score = -(-30000 - mate_distance)
                    else:
                        cp_score = -score.relative.score()
                    move_scores.append((move.uci(), cp_score))
                else:
                    move_scores.append((move.uci(), -10000))
            except Exception:
                move_scores.append((move.uci(), -10000))
            finally:
                board.pop()

    # Sort by score (best first)
    move_scores.sort(key=lambda x: x[1], reverse=True)

    return move_scores


def format_expected_output(move_scores: List[Tuple[str, int]]) -> str:
    """
    Format the move scores as a JSON string for the expected_output field.
    Format: [{"uci": "e2e4", "score": 25}, ...]
    """
    moves_data = [{"uci": move, "score": score} for move, score in move_scores]
    return json.dumps(moves_data, separators=(",", ":"))


def check_existing_progress(output_file: str) -> Dict[int, str]:
    """Load already evaluated positions to resume progress."""
    evaluated = {}
    if os.path.exists(output_file):
        with open(output_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["expected_output"] and row["expected_output"] != "{}":
                    evaluated[int(row["index"])] = row["expected_output"]
    return evaluated


def main():
    """Process positions.csv and create questions.csv with full evaluations."""
    if not os.path.exists("output/positions.csv"):
        print(
            "Error: output/positions.csv not found. Run 03_select_games.py first.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Initialize engine
    print(f"Initializing Stockfish at: {STOCKFISH_PATH}")
    print(
        f"Engine configuration: depth={ENGINE_CONFIG['depth']}, time={ENGINE_CONFIG['time_limit']}s"
    )

    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        print("Stockfish initialized successfully")
    except Exception as e:
        print(
            f"Error: Could not initialize Stockfish at '{STOCKFISH_PATH}': {e}",
            file=sys.stderr,
        )
        print("Make sure Stockfish is installed and in your PATH.", file=sys.stderr)
        sys.exit(1)

    # Read positions
    positions = []
    with open("output/positions.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            positions.append(row)

    if not positions:
        print("No positions found in positions.csv")
        engine.quit()
        return

    # Apply test mode limit if enabled
    if TEST_MODE:
        positions = positions[:TEST_POSITIONS]
        print(f"\nTEST MODE: Processing only first {len(positions)} positions")

    print(f"\nFound {len(positions)} positions to process")

    # Check for existing evaluations
    evaluated = check_existing_progress("questions.csv")
    remaining = len(positions) - len(evaluated)

    if remaining == 0:
        print("All positions already evaluated!")
        engine.quit()
        return

    print(f"Already evaluated: {len(evaluated)}")
    print(f"Remaining: {remaining}")
    estimated_time = remaining * (ENGINE_CONFIG["time_limit"] + 0.5) / 60
    print(f"Estimated time: {estimated_time:.1f} - {estimated_time * 2:.1f} minutes")
    print("\nStarting evaluation...")

    # Process positions
    start_time = time.time()
    evaluated_count = len(evaluated)

    # Write to CSV
    output_file = "questions.csv"
    temp_file = "questions_temp.csv"

    with open(temp_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["index", "input", "expected_output", "private"]
        )
        writer.writeheader()

        for i, pos in enumerate(positions):
            # Create question entry
            fen = pos["fen"]
            # Use hash_bucket for private flag (>=80 is private)
            private = int(pos["hash_bucket"]) >= 80

            # Check if already evaluated
            if i in evaluated:
                writer.writerow(
                    {
                        "index": i,
                        "input": fen,
                        "expected_output": evaluated[i],
                        "private": str(private),
                    }
                )
                continue

            # Parse and evaluate position
            try:
                board = chess.Board(fen)
                legal_moves_count = len(list(board.legal_moves))

                # Show position info
                print(f"\nPosition {i + 1}/{len(positions)}")
                print(f"  FEN: {fen}")
                print(f"  Side to move: {'White' if board.turn else 'Black'}")
                print(f"  Legal moves: {legal_moves_count}")
                print("  Evaluating all moves...", end="", flush=True)

                # Evaluate all moves
                move_scores = evaluate_all_moves(board, engine)

                if move_scores:
                    # Format output
                    expected_output = format_expected_output(move_scores)
                    evaluated_count += 1

                    # Show best move
                    best_move, best_score = move_scores[0]
                    score_str = (
                        f"{best_score / 100:.2f}" if abs(best_score) < 20000 else "Mate"
                    )
                    print(f" Done! Best: {best_move} ({score_str})")
                else:
                    print(" No legal moves!")
                    expected_output = json.dumps([])

            except Exception as e:
                print(f" Error: {e}")
                expected_output = json.dumps([])

            # Write row
            writer.writerow(
                {
                    "index": i,
                    "input": fen,
                    "expected_output": expected_output,
                    "private": str(private),
                }
            )

            # Progress update
            if (i + 1 - len(evaluated)) % 5 == 0 and i + 1 > len(evaluated):
                elapsed = time.time() - start_time
                positions_done = i + 1 - len(evaluated)
                rate = positions_done / elapsed if elapsed > 0 else 0
                eta = (len(positions) - i - 1) / rate if rate > 0 else 0
                print(
                    f"\nProgress: {evaluated_count}/{len(positions)}, "
                    f"Rate: {rate * 60:.1f} pos/min, ETA: {eta / 60:.1f} min"
                )

    engine.quit()

    # Replace original file
    os.replace(temp_file, output_file)

    # Final statistics
    total_time = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"Evaluation complete in {total_time / 60:.1f} minutes!")
    print(f"Successfully evaluated: {evaluated_count}/{len(positions)}")

    # Count public/private
    public_count = sum(1 for p in positions if int(p["hash_bucket"]) < 80)
    private_count = len(positions) - public_count
    print("\nDataset split:")
    print(f"  Public:  {public_count} ({public_count / len(positions) * 100:.1f}%)")
    print(f"  Private: {private_count} ({private_count / len(positions) * 100:.1f}%)")

    if TEST_MODE:
        print(f"\nTEST MODE: Only processed {len(positions)} positions")
        print("Set TEST_MODE = False to process all positions")


if __name__ == "__main__":
    # For testing, you can enable test mode
    # TEST_MODE = True
    main()
