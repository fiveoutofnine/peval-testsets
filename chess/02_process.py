#!/usr/bin/env python3
import os
import sys
import sqlite3
import chess.pgn
import hashlib
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

class TimeControl(Enum):
    ULTRAFAST = "ultrafast"
    BULLET = "bullet"
    BLITZ = "blitz"
    RAPID = "rapid"
    CLASSICAL = "classical"
    CORRESPONDENCE = "correspondence"
    
    @classmethod
    def from_seconds(cls, base_time: int, increment: int = 0) -> 'TimeControl':
        """Classify time control based on Lichess categories."""
        estimated_game_time = base_time + 40 * increment
        
        if estimated_game_time < 29:
            return cls.ULTRAFAST
        elif estimated_game_time < 179:
            return cls.BULLET
        elif estimated_game_time < 479:
            return cls.BLITZ
        elif estimated_game_time < 1499:
            return cls.RAPID
        else:
            return cls.CLASSICAL


@dataclass
class GameInfo:
    """Filtered game information."""
    game_id: str
    pgn_offset: int
    white_elo: Optional[int]
    black_elo: Optional[int]
    avg_elo: Optional[float]
    time_control: TimeControl
    eco: Optional[str]
    opening: Optional[str]
    result: str
    ply_count: int
    moves_uci: str


def parse_time_control(tc_string: str) -> Optional[tuple[int, int]]:
    """Parse time control string like '300+3' to (base_seconds, increment)."""
    if not tc_string or tc_string == '-':
        return None
        
    parts = tc_string.split('+')
    try:
        base_time = int(parts[0])
        increment = int(parts[1]) if len(parts) > 1 else 0
        return base_time, increment
    except (ValueError, IndexError):
        return None


def should_keep_game(game: chess.pgn.Game) -> bool:
    """Apply game-level filters."""
    headers = game.headers
    
    # Check if it's a standard rated game
    if headers.get("Variant", "Standard").lower() != "standard":
        return False
    
    if headers.get("Event", "").lower() == "casual":
        return False
        
    # Check time control
    tc_string = headers.get("TimeControl", "")
    tc_parsed = parse_time_control(tc_string)
    if not tc_parsed:
        return False
        
    time_control = TimeControl.from_seconds(*tc_parsed)
    if time_control in (TimeControl.ULTRAFAST, TimeControl.BULLET):
        return False
        
    # Must have both player ratings
    if not headers.get("WhiteElo") or not headers.get("BlackElo"):
        return False
        
    return True


def extract_game_info(game: chess.pgn.Game, game_id: str, pgn_offset: int) -> GameInfo:
    """Extract relevant game information."""
    headers = game.headers
    
    white_elo = int(headers.get("WhiteElo", 0)) or None
    black_elo = int(headers.get("BlackElo", 0)) or None
    avg_elo = (white_elo + black_elo) / 2 if white_elo and black_elo else None
    
    tc_parsed = parse_time_control(headers.get("TimeControl", ""))
    time_control = TimeControl.from_seconds(*tc_parsed) if tc_parsed else TimeControl.CLASSICAL
    
    # Extract moves and count plies
    moves_uci = []
    ply_count = 0
    board = game.board()
    node = game
    
    while node.variations:
        move = node.variation(0).move
        moves_uci.append(move.uci())
        board.push(move)
        ply_count += 1
        node = node.variation(0)
    
    return GameInfo(
        game_id=game_id,
        pgn_offset=pgn_offset,
        white_elo=white_elo,
        black_elo=black_elo,
        avg_elo=avg_elo,
        time_control=time_control,
        eco=headers.get("ECO"),
        opening=headers.get("Opening"),
        result=headers.get("Result", "*"),
        ply_count=ply_count,
        moves_uci=" ".join(moves_uci)
    )


def create_database(db_path: str):
    """Create SQLite database with appropriate schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Games table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            pgn_offset INTEGER,
            white_elo INTEGER,
            black_elo INTEGER,
            avg_elo REAL,
            time_control TEXT,
            eco TEXT,
            opening TEXT,
            result TEXT,
            ply_count INTEGER,
            moves_uci TEXT,
            processed BOOLEAN DEFAULT FALSE,
            rand_key REAL
        )
    ''')
    
    # Positions table (for future use when we sample positions)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            pos_id TEXT PRIMARY KEY,
            game_id TEXT,
            ply INTEGER,
            fen TEXT,
            fen4 TEXT,
            phase TEXT,
            side_to_move TEXT,
            legal_move_count INTEGER,
            castling_rights TEXT,
            hash_bucket INTEGER,
            FOREIGN KEY (game_id) REFERENCES games(game_id)
        )
    ''')
    
    # Create indices
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_avg_elo ON games(avg_elo)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_games_processed ON games(processed)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_game_id ON positions(game_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_positions_hash_bucket ON positions(hash_bucket)')
    
    conn.commit()
    return conn


def main():
    pgn_file = "games.pgn"  # Keep source file in root
    db_file = "output/games.db"
    
    # Check if PGN file exists
    if not os.path.exists(pgn_file):
        print(f"Error: {pgn_file} does not exist!", file=sys.stderr)
        sys.exit(1)
    
    # Create database
    conn = create_database(db_file)
    cursor = conn.cursor()
    
    # Process games
    game_count = 0
    filtered_count = 0
    
    print("Processing games...")
    
    with open(pgn_file) as pgn:
        while True:
            # Record offset before reading
            pgn_offset = pgn.tell()
            game = chess.pgn.read_game(pgn)
            if game is None:
                break
                
            game_count += 1
            if game_count % 1000 == 0:
                print(f"Processed {game_count} games, kept {filtered_count}...")
            
            # Apply filters
            if not should_keep_game(game):
                continue
                
            # Extract game info
            game_id = f"game_{filtered_count:06d}"
            game_info = extract_game_info(game, game_id, pgn_offset)
            
            # Generate deterministic random key based on game_id
            rand_key = int(hashlib.sha256(f"rand_{game_id}".encode()).hexdigest()[:16], 16) / float(2**64)
            
            # Store in database
            cursor.execute('''
                INSERT INTO games (
                    game_id, pgn_offset, white_elo, black_elo, avg_elo, time_control,
                    eco, opening, result, ply_count, moves_uci, rand_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                game_info.game_id,
                game_info.pgn_offset,
                game_info.white_elo,
                game_info.black_elo,
                game_info.avg_elo,
                game_info.time_control.value,
                game_info.eco,
                game_info.opening,
                game_info.result,
                game_info.ply_count,
                game_info.moves_uci,
                rand_key
            ))
            
            filtered_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"\nProcessing complete!")
    print(f"Total games processed: {game_count}")
    print(f"Games kept after filtering: {filtered_count}")
    print(f"Database saved to: {db_file}")


if __name__ == "__main__":
    main()
