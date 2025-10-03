# Chess | Peval Competition

[**Link**](https://peval.io/competition/chess) / [`questions.csv`](https://github.com/fiveoutofnine/peval-testsets/blob/main/chess/questions.csv)

## Test set design

The test set was designed to holistically assess LLMs' chess playing ability.
It consists of 200 real game positions and 50 puzzles randomly sampled from [Lichess' Open Database](https://database.lichess.org) with the following characteristics and distribution:

- 200 positions:
  - ELO ranges:
    - `[0, 1400)`: 20 (10%)
    - `[1400, 1800)`: 50 (25%)
    - `[1800, 2200)`: 70 (35%)
    - `[2200, 2600]`: 40 (20%)
    - `[2600, ∞)`: 20 (10%)
  - Game phases:
    - Opening: 40 (20%)
    - Middlegame: 120 (60%)
    - Endgame: 40 (20%)
  - Position types:
    - Tactical: 56 (28%)
    - Quiet: 144 (72%)
  - Side-to-move:
    - White: 100 (50%)
    - Black: 100 (50%)
- 50 puzzles:
  - 35 middlegame (70%)
  - 15 endgame (30%)

> [!INFO]
> The game positions for the competition's test set were sampled from a 4GB (uncompressed) slice of the [August 2025 Lichess database dump](https://database.lichess.org/standard/lichess_db_standard_rated_2025-08.pgn.zst).

## Generating

First, set up the Python environment using [`uv`](https://github.com/astral-sh/uv):

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

Then, to generate an equivalent sample test set, run each step of the pipeline or use the orchestrator to run them sequentially:

```bash
uv run 01_fetch_games.py
uv run 02_process_games.py
uv run 03_select_games.py
uv run 04_fetch_puzzles.py
uv run 05_select_puzzles.py
uv run 06_create_questions.py

# Or use the orchestrator
uv run generate.py
```

## Additional details

The generation pipeline consists of 6 sequential steps:

### 1. Fetch games (`01_fetch_games.py`)

Downloads and extracts a 4GB chunk from the August 2025 Lichess database dump. The script downloads the compressed file and extracts a specific slice (starting at offset 15.5GB) after decompression.

### 2. Process games (`02_process_games.py`)

Filters and processes raw PGN data into a SQLite database:

- Filters for standard rated games (Blitz/Rapid/Classical time controls)
- Excludes bullet/ultrafast games, variants, and incomplete games
- Stores game metadata (ELO ratings, time control, result)
- Creates a searchable database for position selection

### 3. Select game positions (`03_select_games.py`)

Selects 200 positions following the exact distribution requirements:

- Stratified sampling across ELO ranges, game phases, and position types
- Extracts positions from games and analyzes with Stockfish (depth 12)
- Labels positions as tactical or quiet based on evaluation gaps
- Ensures 50/50 color balance
- Deduplicates positions to avoid repetition
- Uses deterministic selection for reproducibility

### 4. Fetch puzzles (`04_fetch_puzzles.py`)

Downloads the complete Lichess puzzle database:

- Downloads ~250MB compressed file (expands to ~1GB)
- Contains millions of tactical puzzles from real games
- Includes puzzle ratings, themes, and solutions
- Pre-validated for having clear best moves

### 5. Select puzzles (`05_select_puzzles.py`)

Randomly selects 50 puzzles matching the target distribution:

- 35 middlegame puzzles (70%)
- 15 endgame puzzles (30%)
- Filters based on puzzle themes
- Uses random sampling with fixed seed for reproducibility

### 6. Create questions (`06_create_questions.py`)

Evaluates all positions to create the final dataset:

- Combines 200 game positions and 50 puzzles
- Uses Stockfish at depth 25 for comprehensive evaluation
- Analyzes ALL legal moves for each position (up to 500 moves with MultiPV)
- Outputs JSON with move evaluations in centipawns
- Creates public (first 50) and private (remaining 200) test splits

## Output files

The pipeline generates the following files:

- `output/games.pgn` - 4GB slice of Lichess game data in PGN format
- `output/games.db` - SQLite database with filtered games and metadata
- `output/positions.csv` - 200 selected game positions with ELO, phase, and type labels
- `output/lichess_puzzles.csv` - Complete Lichess puzzle database (~1GB)
- `output/puzzles.csv` - 50 selected puzzles with themes and solutions
- `questions.csv` - Final competition dataset with the following columns:
  - `index`: Test case index (0-249)
  - `input`: Chess position in FEN notation
  - `expected_output`: JSON object mapping each legal move (UCI format) to its evaluation in centipawns
  - `private`: "false" for first 50 positions (public), "true" for remaining 200 (private)

### Requirements

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) for Python package management
- Stockfish chess engine (install via package manager or download from [stockfishchess.org](https://stockfishchess.org))
- ~2GB free disk space for puzzle database
- Dependencies (managed via `uv`):
  - `python-chess`: Chess library for move generation and board manipulation
  - `requests`: For downloading Lichess data
  - `tqdm`: Progress bars for long-running operations
  - `ruff`: Python linter and formatter (for development)

### Position selection criteria

- **Legal & non-terminal**: All positions must have at least one legal move
- **Halfmove clock < 80**: Avoids positions close to 50-move rule draws
- **En passant normalization**: Only includes en passant square when capture is actually possible
- **Canonical FEN**: Uses first 4 fields only (pieces, turn, castling, en passant)

### Tactical vs Quiet classification

Positions are classified using Stockfish analysis (depth ~12):

- **Tactical**: Positions with forcing moves, large evaluation gaps between best and second-best moves, or positions requiring precise calculation
- **Quiet**: Positions with multiple reasonable moves, small evaluation differences, requiring positional understanding
