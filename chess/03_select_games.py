#!/usr/bin/env python3
import csv
import hashlib
import os
import random
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import chess
import chess.engine
import chess.pgn

# Configuration
STOCKFISH_PATH = "stockfish"  # Assumes stockfish is in PATH
STOCKFISH_DEPTH = 12  # Reduced for faster testing
MULTI_PV = 4
SALT = "chess_position_salt_v1"
OUTPUT_CSV = "output/positions.csv"

# ELO buckets: [0, 1400), [1400, 1800), [1800, 2200), [2200, 2600), [2600, inf)
ELO_RANGES = [(0, 1400), (1400, 1800), (1800, 2200), (2200, 2600), (2600, 9999)]
ELO_BUCKET_NAMES = ["0-1400", "1400-1800", "1800-2200", "2200-2600", "2600+"]

# Target distribution for 800 games positions
GAME_DISTRIBUTION = {
    "0-1400": 20,
    "1400-1800": 50,
    "1800-2200": 70,
    "2200-2600": 40,
    "2600+": 20,
}

# Phase ratios within each ELO bucket
PHASE_RATIOS = {"opening": 0.2, "middlegame": 0.6, "endgame": 0.2}

# Tactical ratio for each phase
TACTICAL_RATIOS = {"opening": 0.28, "middlegame": 0.29, "endgame": 0.28}


@dataclass
class Position:
    pos_id: str
    fen: str
    fen4: str  # First 4 fields of FEN
    game_id: str
    ply: int
    phase: str
    side_to_move: str
    legal_move_count: int
    castling_rights: str
    avg_elo: float
    elo_bucket: str
    is_tactical: bool
    is_mate: bool
    hash_bucket: int


def get_elo_bucket(avg_elo: float) -> str:
    """Return the ELO bucket name for a given average ELO."""
    for i, (min_elo, max_elo) in enumerate(ELO_RANGES):
        if min_elo <= avg_elo < max_elo:
            return ELO_BUCKET_NAMES[i]
    return ELO_BUCKET_NAMES[-1]


def get_material_count(board: chess.Board) -> int:
    """Count non-king material on the board."""
    material = 0
    piece_values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
    }

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece and piece.piece_type != chess.KING:
            material += piece_values.get(piece.piece_type, 0)

    return material


def get_phase(board: chess.Board, ply: int) -> str:
    """Determine game phase based on position and ply count."""
    material = get_material_count(board)
    has_queens = bool(
        board.pieces(chess.QUEEN, chess.WHITE) or board.pieces(chess.QUEEN, chess.BLACK)
    )

    # Opening: ply ≤ 20 & queens present & material ≥ 26
    if ply <= 20 and has_queens and material >= 26:
        return "opening"

    # Endgame: material ≤ 14
    if material <= 14:
        return "endgame"

    # Otherwise middlegame
    return "middlegame"


def normalize_en_passant(board: chess.Board) -> str:
    """Return en passant square only if an en passant capture is actually legal."""
    if not board.ep_square:
        return "-"

    # Check if any pawn can actually capture en passant
    if board.turn == chess.WHITE:
        capturing_pawns = board.pieces(chess.PAWN, chess.WHITE)
        for square in capturing_pawns:
            if square + 7 == board.ep_square or square + 9 == board.ep_square:
                move = chess.Move(square, board.ep_square)
                if move in board.legal_moves:
                    return chess.square_name(board.ep_square)
    else:
        capturing_pawns = board.pieces(chess.PAWN, chess.BLACK)
        for square in capturing_pawns:
            if square - 7 == board.ep_square or square - 9 == board.ep_square:
                move = chess.Move(square, board.ep_square)
                if move in board.legal_moves:
                    return chess.square_name(board.ep_square)

    return "-"


def get_fen4(board: chess.Board) -> str:
    """Get canonicalized FEN (first 4 fields only)."""
    fen_parts = board.fen().split()
    # Normalize en passant
    fen_parts[3] = normalize_en_passant(board)
    return " ".join(fen_parts[:4])


def calculate_pos_id(fen4: str) -> Tuple[str, int]:
    """Calculate position ID and hash bucket."""
    pos_id = hashlib.sha256(f"{SALT}{fen4}".encode()).hexdigest()
    hash_bucket = int(hashlib.sha256(fen4.encode()).hexdigest()[:8], 16) % 100
    return pos_id, hash_bucket


def is_capture_or_check(board: chess.Board, move: chess.Move) -> bool:
    """Check if a move is a capture or gives check."""
    if board.is_capture(move):
        return True
    board.push(move)
    in_check = board.is_check()
    board.pop()
    return in_check


def classify_position(
    board: chess.Board, engine: chess.engine.SimpleEngine, phase: str
) -> tuple[bool, bool]:
    """
    Classify position as tactical or quiet using Stockfish.
    Returns (is_tactical, is_mate) tuple.
    """
    # Run multi-PV analysis
    info = engine.analyse(
        board, chess.engine.Limit(depth=STOCKFISH_DEPTH), multipv=MULTI_PV
    )

    if not info:
        return True, False  # Default to tactical, not mate if analysis fails

    # Get top moves and evaluations
    top_moves = []
    for pv_info in info[: min(len(info), MULTI_PV)]:
        if "score" in pv_info and "pv" in pv_info and pv_info["pv"]:
            score = pv_info["score"]
            move = pv_info["pv"][0]

            # Convert score to centipawns from current player's perspective
            if score.is_mate():
                # Get mate distance
                if hasattr(score, "mate"):
                    mate_dist = score.mate()
                else:
                    mate_dist = score.relative.mate()
                cp_score = 10000 if mate_dist > 0 else -10000
            else:
                # PovScore needs to be converted to relative score
                cp_score = score.relative.score()

            # Score is already from current player's POV

            top_moves.append((move, cp_score))

    if not top_moves:
        return True, False  # Default to tactical, not mate if no moves found

    best_move, best_eval = top_moves[0]

    # Calculate gap between best and second-best move
    gap = 0
    if len(top_moves) > 1:
        gap = abs(best_eval - top_moves[1][1])

    # Count good moves (within 50 cp of best)
    good_move_count = sum(
        1 for _, eval_score in top_moves if abs(eval_score - best_eval) <= 50
    )

    # Check if best move is check or capture
    is_check_capture = is_capture_or_check(board, best_move)

    # Tactical classification criteria
    is_tactical = False
    is_mate = False

    # Mate in PV
    if abs(best_eval) >= 10000:
        is_tactical = True
        is_mate = True
    # Large evaluation gap
    elif (
        (phase in ["opening", "middlegame"] and gap >= 100)
        or (phase == "endgame" and gap >= 60)
        or is_check_capture
        and best_eval > 100
        or good_move_count <= 2
    ):
        is_tactical = True

    # Quiet classification (must satisfy all conditions)
    if (
        not is_tactical
        and (
            (phase in ["opening", "middlegame"] and gap <= 30)
            or (phase == "endgame" and gap <= 20)
        )
        and not is_check_capture
        and good_move_count >= 3
    ):
        is_tactical = False  # Confirmed quiet
    elif not is_tactical:
        # Neither clearly tactical nor quiet - default to tactical
        is_tactical = True

    return is_tactical, is_mate


def sample_position_from_game(
    conn: sqlite3.Connection,
    game_id: str,
    moves_uci: str,
    avg_elo: float,
    engine: chess.engine.SimpleEngine,
) -> Optional[Position]:
    """Sample a single position from a game."""
    moves = moves_uci.split() if moves_uci else []
    if not moves:
        return None

    board = chess.Board()

    # Reservoir sampling - select one position from eligible moves
    selected_ply = None
    selected_board = None
    eligible_count = 0

    for ply, move_uci in enumerate(moves):
        move = chess.Move.from_uci(move_uci)
        board.push(move)

        # Check position eligibility
        if (
            board.is_checkmate()
            or board.is_stalemate()
            or board.is_insufficient_material()
            or board.halfmove_clock >= 80
        ):
            continue

        # Reservoir sampling
        eligible_count += 1
        if random.randint(1, eligible_count) == 1:
            selected_ply = ply + 1
            selected_board = board.copy()

    if not selected_board:
        return None

    # Analyze selected position
    phase = get_phase(selected_board, selected_ply)
    fen4 = get_fen4(selected_board)
    pos_id, hash_bucket = calculate_pos_id(fen4)

    # Position deduplication is handled by the caller checking existing_pos_ids
    # No need to check database here since we track in memory

    # Classify position
    is_tactical, is_mate = classify_position(selected_board, engine, phase)

    return Position(
        pos_id=pos_id,
        fen=selected_board.fen(),
        fen4=fen4,
        game_id=game_id,
        ply=selected_ply,
        phase=phase,
        side_to_move="white" if selected_board.turn else "black",
        legal_move_count=len(list(selected_board.legal_moves)),
        castling_rights=selected_board.castling_xfen(),
        avg_elo=avg_elo,
        elo_bucket=get_elo_bucket(avg_elo),
        is_tactical=is_tactical,
        is_mate=is_mate,
        hash_bucket=hash_bucket,
    )


def load_existing_positions(
    csv_path: str,
) -> Tuple[set, Dict[str, Dict[str, Dict[str, Dict[str, List[Position]]]]]]:
    """Load existing positions from CSV and rebuild the selected data structure."""
    existing_pos_ids = set()  # Changed to track position IDs, not game IDs
    selected = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )

    if not os.path.exists(csv_path):
        return existing_pos_ids, selected

    print(f"Loading existing positions from {csv_path}...")
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Track position IDs to avoid duplicates (not game IDs)
            # We need to reconstruct the pos_id from the FEN
            fen4 = " ".join(row["fen"].split()[:4])  # Get first 4 fields
            pos_id = hashlib.sha256(f"{SALT}{fen4}".encode()).hexdigest()
            existing_pos_ids.add(pos_id)

            # Rebuild the nested structure for counting
            elo_bucket = row["elo_bucket"]
            phase = row["phase"]
            type_key = row["type"]
            color = row["color"]

            # Create a minimal Position object for counting
            pos = Position(
                pos_id="",  # Not needed for counting
                fen=row["fen"],
                fen4="",  # Not needed
                game_id=row.get("game_id", ""),
                ply=0,  # Not needed
                phase=phase,
                side_to_move=color,
                legal_move_count=int(row["legal_moves"]),
                castling_rights="",  # Not needed
                avg_elo=0,  # Not needed
                elo_bucket=elo_bucket,
                is_tactical=(type_key == "tactical"),
                is_mate=False,  # Not tracked in existing CSV
                hash_bucket=int(row["hash_bucket"]),
            )
            selected[elo_bucket][phase][type_key][color].append(pos)

    total_loaded = sum(
        len(positions)
        for elo in selected.values()
        for phase in elo.values()
        for type_pos in phase.values()
        for positions in type_pos.values()
    )
    print(
        f"Loaded {total_loaded} existing positions ({len(existing_pos_ids)} unique positions)"
    )

    return existing_pos_ids, selected


def write_positions_incremental(selected: Dict, csv_path: str, append: bool = False):
    """Write positions to CSV, optionally appending."""
    mode = "a" if append else "w"
    write_header = not append or not os.path.exists(csv_path)

    with open(csv_path, mode, newline="") as csvfile:
        fieldnames = [
            "game_id",
            "fen",
            "elo_bucket",
            "phase",
            "type",
            "color",
            "legal_moves",
            "hash_bucket",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if write_header:
            writer.writeheader()

        count = 0
        for elo_bucket in selected:
            for phase in selected[elo_bucket]:
                for type_key in selected[elo_bucket][phase]:
                    for color in selected[elo_bucket][phase][type_key]:
                        for position in selected[elo_bucket][phase][type_key][color]:
                            writer.writerow(
                                {
                                    "game_id": position.game_id,
                                    "fen": position.fen,
                                    "elo_bucket": position.elo_bucket,
                                    "phase": position.phase,
                                    "type": type_key,
                                    "color": position.side_to_move,
                                    "legal_moves": position.legal_move_count,
                                    "hash_bucket": position.hash_bucket,
                                }
                            )
                            count += 1
        return count


def main():
    if not os.path.exists("output/games.db"):
        print(
            "Error: output/games.db not found. Run 02_process_games.py first.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Initialize engine
    try:
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    except Exception as e:
        print(
            f"Error: Could not initialize Stockfish at '{STOCKFISH_PATH}': {e}",
            file=sys.stderr,
        )
        print(
            "Make sure Stockfish is installed and in your PATH, or update STOCKFISH_PATH.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load existing positions if any
    existing_pos_ids, selected = load_existing_positions(OUTPUT_CSV)

    # Track mate positions globally (max 4% of total = 28 positions for 700 total)
    mate_positions_count = 0
    MAX_MATE_POSITIONS = int(sum(GAME_DISTRIBUTION.values()) * 0.04)  # 4% cap

    conn = sqlite3.connect("output/games.db")
    cursor = conn.cursor()

    # Check overall progress
    total_positions = sum(
        len(positions)
        for elo in selected.values()
        for phase in elo.values()
        for type_pos in phase.values()
        for positions in type_pos.values()
    )
    total_target = sum(GAME_DISTRIBUTION.values())

    if total_positions >= total_target:
        print(
            f"\nAlready have {total_positions} positions (target: {total_target}). Nothing to do."
        )
        conn.close()
        engine.quit()
        return

    print(f"\nStarting from {total_positions}/{total_target} positions...")

    # Debug: Show breakdown by bucket
    print("\nCurrent position counts by bucket:")
    for bucket in ELO_BUCKET_NAMES:
        bucket_count = sum(
            len(positions)
            for phase in selected.get(bucket, {}).values()
            for type_pos in phase.values()
            for positions in type_pos.values()
        )
        print(f"  {bucket}: {bucket_count}/{GAME_DISTRIBUTION.get(bucket, 0)}")

    for elo_bucket, target_count in GAME_DISTRIBUTION.items():
        min_elo, max_elo = ELO_RANGES[ELO_BUCKET_NAMES.index(elo_bucket)]

        # Calculate targets for each phase and tactical/quiet split
        phase_targets = {}
        for phase, phase_ratio in PHASE_RATIOS.items():
            phase_count = int(target_count * phase_ratio)
            tactical_count = int(phase_count * TACTICAL_RATIOS[phase])
            quiet_count = phase_count - tactical_count
            phase_targets[phase] = {
                "tactical": {
                    "white": tactical_count // 2,
                    "black": (tactical_count + 1) // 2,
                },
                "quiet": {"white": quiet_count // 2, "black": (quiet_count + 1) // 2},
            }

        # Count existing positions for this bucket
        bucket_current = sum(
            len(positions)
            for phase_positions in selected[elo_bucket].values()
            for type_positions in phase_positions.values()
            for positions in type_positions.values()
        )

        if bucket_current >= target_count:
            print(
                f"\n{elo_bucket} ELO bucket already complete ({bucket_current}/{target_count} positions)"
            )
            continue

        print(
            f"\nProcessing {elo_bucket} ELO bucket (current: {bucket_current}, target: {target_count})..."
        )

        # Get all games in this ELO range, ordered by deterministic rand_key
        cursor.execute(
            """
            SELECT game_id, moves_uci, avg_elo 
            FROM games 
            WHERE avg_elo >= ? AND avg_elo < ? AND moves_uci IS NOT NULL
            ORDER BY rand_key
        """,
            (min_elo, max_elo),
        )

        games = cursor.fetchall()
        game_idx = 0

        # Track newly added positions for this bucket
        new_positions = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        while game_idx < len(games) and bucket_current < target_count:
            game_id, moves_uci, avg_elo = games[game_idx]
            game_idx += 1

            # Note: We can sample multiple positions from the same game
            # Only duplicate FENs (pos_id) are avoided

            # Sample position from game
            if game_idx % 50 == 0:
                print(f"    Checking game {game_idx}/{len(games)}...")
            position = sample_position_from_game(
                conn, game_id, moves_uci, avg_elo, engine
            )
            if not position:
                continue

            # Check if this position already exists
            if position.pos_id in existing_pos_ids:
                continue

            # Check mate position cap
            if position.is_mate and mate_positions_count >= MAX_MATE_POSITIONS:
                continue  # Skip mate positions if we've reached the cap

            # Check if we need this type of position
            type_key = "tactical" if position.is_tactical else "quiet"
            current_count = len(
                selected[elo_bucket][position.phase][type_key][position.side_to_move]
            )
            target = phase_targets[position.phase][type_key][position.side_to_move]

            if current_count < target:
                # Add to both tracking structures (no database insert needed)
                selected[elo_bucket][position.phase][type_key][
                    position.side_to_move
                ].append(position)
                new_positions[position.phase][type_key][position.side_to_move].append(
                    position
                )
                existing_pos_ids.add(position.pos_id)
                bucket_current += 1

                # Track mate positions
                if position.is_mate:
                    mate_positions_count += 1

                # Write incrementally every 10 positions or when done
                if (
                    len(
                        [
                            p
                            for phase in new_positions.values()
                            for type_pos in phase.values()
                            for positions in type_pos.values()
                            for p in positions
                        ]
                    )
                    % 10
                    == 0
                ):
                    # Write the new positions
                    temp_selected = {elo_bucket: new_positions}
                    write_positions_incremental(temp_selected, OUTPUT_CSV, append=True)
                    # Clear the buffer
                    new_positions = defaultdict(
                        lambda: defaultdict(lambda: defaultdict(list))
                    )
                    print(f"  Selected {bucket_current}/{target_count} positions...")

        # Write any remaining positions for this bucket
        if any(
            positions
            for phase in new_positions.values()
            for type_pos in phase.values()
            for positions in type_pos.values()
        ):
            temp_selected = {elo_bucket: new_positions}
            write_positions_incremental(temp_selected, OUTPUT_CSV, append=True)
            print(
                f"  Final count for {elo_bucket}: {bucket_current}/{target_count} positions"
            )

    engine.quit()

    # Count final total
    final_total = sum(
        len(positions)
        for elo in selected.values()
        for phase in elo.values()
        for type_pos in phase.values()
        for positions in type_pos.values()
    )

    print(f"\nSuccessfully selected {final_total} positions total")
    print(
        f"Mate positions: {mate_positions_count}/{MAX_MATE_POSITIONS} (cap: {MAX_MATE_POSITIONS})"
    )

    # Also include puzzles (200 positions) - placeholder for now
    print("\nNote: Lichess puzzles (200 positions) need to be added separately")

    conn.close()


if __name__ == "__main__":
    main()
