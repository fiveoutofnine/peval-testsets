#!/usr/bin/env python3
"""Print overview statistics for the chess position selection pipeline."""

import csv
import os
import sqlite3
from collections import defaultdict
from pathlib import Path


def format_table(headers, rows, col_widths=None):
    """Format data as a pretty ASCII table."""
    if not col_widths:
        col_widths = [
            max(len(str(row[i])) for row in [headers] + rows)
            for i in range(len(headers))
        ]

    # Create separator line
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

    # Format header
    header_line = (
        "|"
        + "|".join(f" {headers[i]:<{col_widths[i]}} " for i in range(len(headers)))
        + "|"
    )

    # Format rows
    lines = [separator, header_line, separator]
    for row in rows:
        row_line = (
            "|"
            + "|".join(f" {str(row[i]):<{col_widths[i]}} " for i in range(len(row)))
            + "|"
        )
        lines.append(row_line)
    lines.append(separator)

    return "\n".join(lines)


def get_database_stats():
    """Get statistics from games.db."""
    db_path = "output/games.db"
    if not os.path.exists(db_path):
        return None

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Total games
        cursor.execute("SELECT COUNT(*) FROM games")
        total_games = cursor.fetchone()[0]

        # Games by ELO bucket
        elo_stats = []
        elo_ranges = [(0, 1400), (1400, 1800), (1800, 2200), (2200, 2600), (2600, 9999)]
        elo_names = ["0-1400", "1400-1800", "1800-2200", "2200-2600", "2600+"]

        for i, (min_elo, max_elo) in enumerate(elo_ranges):
            cursor.execute(
                """
                SELECT COUNT(*) FROM games 
                WHERE avg_elo >= ? AND avg_elo < ?
            """,
                (min_elo, max_elo),
            )
            count = cursor.fetchone()[0]
            elo_stats.append((elo_names[i], count))

        # Time control distribution
        cursor.execute("""
            SELECT time_control, COUNT(*) as count 
            FROM games 
            GROUP BY time_control 
            ORDER BY count DESC
        """)
        time_controls = cursor.fetchall()

        conn.close()
        return {
            "total_games": total_games,
            "elo_distribution": elo_stats,
            "time_controls": time_controls[:5],  # Top 5
        }
    except Exception:
        return None


def get_position_stats():
    """Get statistics from positions.csv."""
    csv_path = "output/positions.csv"
    if not os.path.exists(csv_path):
        return None

    try:
        stats = {
            "total": 0,
            "by_elo": defaultdict(int),
            "by_phase": defaultdict(int),
            "by_type": defaultdict(int),
            "by_color": defaultdict(int),
            "by_elo_phase_type": defaultdict(
                lambda: defaultdict(lambda: defaultdict(int))
            ),
            "mate_positions": 0,
        }

        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats["total"] += 1
                stats["by_elo"][row["elo_bucket"]] += 1
                stats["by_phase"][row["phase"]] += 1
                stats["by_type"][row["type"]] += 1
                stats["by_color"][row["color"]] += 1
                stats["by_elo_phase_type"][row["elo_bucket"]][row["phase"]][
                    row["type"]
                ] += 1

        return stats
    except Exception:
        return None


def get_puzzle_stats():
    """Get statistics from puzzles.csv."""
    csv_path = "output/puzzles.csv"
    if not os.path.exists(csv_path):
        return None

    try:
        stats = {
            "total": 0,
            "by_phase": defaultdict(int),
            "by_color": defaultdict(int),
            "rating_range": [float("inf"), 0],
        }

        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats["total"] += 1
                stats["by_phase"][row["phase"]] += 1
                stats["by_color"][row["color"]] += 1
                rating = int(row["rating"])
                stats["rating_range"][0] = min(stats["rating_range"][0], rating)
                stats["rating_range"][1] = max(stats["rating_range"][1], rating)

        return stats
    except Exception:
        return None


def get_questions_stats():
    """Get statistics from questions.csv."""
    csv_path = "questions.csv"
    if not os.path.exists(csv_path):
        return None

    try:
        public_count = 0
        private_count = 0
        total = 0

        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                total += 1
                if row["private"].lower() == "true":
                    private_count += 1
                else:
                    public_count += 1

        return {"total": total, "public": public_count, "private": private_count}
    except Exception:
        return None


def main():
    """Print overview statistics."""
    print("\nChess Position Selection Pipeline Statistics")
    print("=" * 60)

    # Change to chess directory if we're not already there
    if os.path.basename(os.getcwd()) != "chess":
        chess_dir = Path(__file__).parent
        os.chdir(chess_dir)

    # Check if files exist
    files_status = [
        ("output/games.pgn", os.path.exists("output/games.pgn")),
        ("output/games.db", os.path.exists("output/games.db")),
        ("output/positions.csv", os.path.exists("output/positions.csv")),
        ("output/lichess_puzzles.csv", os.path.exists("output/lichess_puzzles.csv")),
        ("output/puzzles.csv", os.path.exists("output/puzzles.csv")),
        ("questions.csv", os.path.exists("questions.csv")),
    ]

    print("\nFile Status:")
    headers = ["File", "Status", "Size"]
    rows = []
    for filename, exists in files_status:
        if exists:
            size = os.path.getsize(filename)
            if size > 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"
            rows.append([filename, "✓ Exists", size_str])
        else:
            rows.append([filename, "✗ Missing", "0"])
    print(format_table(headers, rows))

    # Database statistics
    db_stats = get_database_stats()
    if db_stats:
        print("\n\nDatabase Statistics (games.db):")
        print(f"Total games: {db_stats['total_games']:,}")

        print("\nGames by ELO Bucket:")
        headers = ["ELO Range", "Count", "Percentage"]
        rows = []
        for elo_range, count in db_stats["elo_distribution"]:
            percentage = (
                (count / db_stats["total_games"] * 100)
                if db_stats["total_games"] > 0
                else 0
            )
            rows.append([elo_range, f"{count:,}", f"{percentage:.1f}%"])
        print(format_table(headers, rows))

        if db_stats["time_controls"]:
            print("\nTop Time Controls:")
            headers = ["Time Control", "Count"]
            rows = [[tc, f"{count:,}"] for tc, count in db_stats["time_controls"]]
            print(format_table(headers, rows))

        print("\nDatabase Features:")
        print("- Deterministic ordering: ✓ (rand_key column)")
        print("- Reproducible selection: ✓")
    else:
        print("\n\nDatabase Statistics: No data (games.db not found)")

    # Position statistics
    pos_stats = get_position_stats()
    if pos_stats:
        print("\n\nPosition Statistics (positions.csv):")
        print(f"Total positions: {pos_stats['total']:,}")

        # Distribution by ELO
        print("\nPositions by ELO Bucket:")
        headers = ["ELO Range", "Selected", "Target", "Progress"]
        targets = {
            "0-1400": 20,
            "1400-1800": 50,
            "1800-2200": 70,
            "2200-2600": 40,
            "2600+": 20,
        }
        rows = []
        for elo in ["0-1400", "1400-1800", "1800-2200", "2200-2600", "2600+"]:
            count = pos_stats["by_elo"].get(elo, 0)
            target = targets.get(elo, 0)
            progress = (count / target * 100) if target > 0 else 0
            rows.append([elo, str(count), str(target), f"{progress:.1f}%"])
        print(format_table(headers, rows))

        # Distribution by phase
        print("\nPositions by Phase:")
        headers = ["Phase", "Count", "Percentage", "Target %"]
        phase_targets = {"opening": 20, "middlegame": 60, "endgame": 20}
        rows = []
        for phase in ["opening", "middlegame", "endgame"]:
            count = pos_stats["by_phase"].get(phase, 0)
            percentage = (
                (count / pos_stats["total"] * 100) if pos_stats["total"] > 0 else 0
            )
            target = phase_targets.get(phase, 0)
            rows.append(
                [phase.capitalize(), str(count), f"{percentage:.1f}%", f"{target}%"]
            )
        print(format_table(headers, rows))

        # Distribution by type
        print("\nPositions by Type:")
        headers = ["Type", "Count", "Percentage", "Target %"]
        rows = []
        for pos_type in ["tactical", "quiet"]:
            count = pos_stats["by_type"].get(pos_type, 0)
            percentage = (
                (count / pos_stats["total"] * 100) if pos_stats["total"] > 0 else 0
            )
            target = 28 if pos_type == "tactical" else 72
            rows.append(
                [pos_type.capitalize(), str(count), f"{percentage:.1f}%", f"{target}%"]
            )
        print(format_table(headers, rows))

        # Mate positions (if tracked)
        if "mate_positions" in pos_stats:
            mate_cap = int(200 * 0.04)  # 4% of 200
            mate_percentage = (
                (pos_stats["mate_positions"] / pos_stats["total"] * 100)
                if pos_stats["total"] > 0
                else 0
            )
            print(
                f"\nMate positions: {pos_stats['mate_positions']}/{mate_cap} ({mate_percentage:.1f}% of total, cap: 4.0%)"
            )

        # Distribution by color
        print("\nPositions by Side to Move:")
        headers = ["Color", "Count", "Percentage"]
        rows = []
        for color in ["white", "black"]:
            count = pos_stats["by_color"].get(color, 0)
            percentage = (
                (count / pos_stats["total"] * 100) if pos_stats["total"] > 0 else 0
            )
            rows.append([color.capitalize(), str(count), f"{percentage:.1f}%"])
        print(format_table(headers, rows))
    else:
        print("\n\nPosition Statistics: No data (positions.csv not found)")

    # Puzzle statistics
    puzzle_stats = get_puzzle_stats()
    if puzzle_stats:
        print("\n\nPuzzle Statistics (puzzles.csv):")
        print(f"Total puzzles: {puzzle_stats['total']:,}")

        # Distribution by phase
        print("\nPuzzles by Phase:")
        headers = ["Phase", "Count", "Percentage", "Target"]
        rows = []
        phase_targets = {"middlegame": 35, "endgame": 15}
        for phase in ["middlegame", "endgame"]:
            count = puzzle_stats["by_phase"].get(phase, 0)
            percentage = (
                (count / puzzle_stats["total"] * 100)
                if puzzle_stats["total"] > 0
                else 0
            )
            target = phase_targets.get(phase, 0)
            rows.append(
                [phase.capitalize(), str(count), f"{percentage:.1f}%", str(target)]
            )
        print(format_table(headers, rows))

        # Distribution by color
        print("\nPuzzles by Side to Move:")
        headers = ["Color", "Count", "Percentage"]
        rows = []
        for color in ["white", "black"]:
            count = puzzle_stats["by_color"].get(color, 0)
            percentage = (
                (count / puzzle_stats["total"] * 100)
                if puzzle_stats["total"] > 0
                else 0
            )
            rows.append([color.capitalize(), str(count), f"{percentage:.1f}%"])
        print(format_table(headers, rows))

        # Rating range
        if puzzle_stats["rating_range"][0] != float("inf"):
            print(
                f"\nCommunity rating range: {puzzle_stats['rating_range'][0]} - {puzzle_stats['rating_range'][1]}"
            )
    else:
        print("\n\nPuzzle Statistics: No data (puzzles.csv not found)")

    # Questions statistics
    q_stats = get_questions_stats()
    if q_stats:
        print("\n\nQuestions Statistics (questions.csv):")
        headers = ["Type", "Count", "Percentage"]
        rows = [
            [
                "Public",
                str(q_stats["public"]),
                f"{q_stats['public'] / q_stats['total'] * 100:.1f}%",
            ],
            [
                "Private",
                str(q_stats["private"]),
                f"{q_stats['private'] / q_stats['total'] * 100:.1f}%",
            ],
            ["Total", str(q_stats["total"]), "100.0%"],
        ]
        print(format_table(headers, rows))
    else:
        print("\n\nQuestions Statistics: No data (questions.csv not found)")

    # Total summary
    print("\n\nTotal Summary:")
    print("=" * 40)
    game_positions = pos_stats["total"] if pos_stats else 0
    puzzle_positions = puzzle_stats["total"] if puzzle_stats else 0
    total_positions = game_positions + puzzle_positions

    print(
        f"Game positions:   {game_positions:4d} / 200  ({game_positions / 200 * 100:5.1f}%)"
    )
    print(
        f"Puzzle positions: {puzzle_positions:4d} / 50  ({puzzle_positions / 50 * 100:5.1f}%)"
    )
    print(
        f"Total positions:  {total_positions:4d} / 250 ({total_positions / 250 * 100:5.1f}%)"
    )

    print("\n" + "=" * 60)
    print("Note: Run generate.py to create missing files")
    print()


if __name__ == "__main__":
    main()
