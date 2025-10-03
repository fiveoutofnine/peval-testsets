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

Downloads recent Lichess game data in PGN format. By default fetches games from the most recent complete month available.

### 2. Process games (`02_process_games.py`)

Filters and processes raw PGN data into a SQLite database:

- Filters for standard rated games (Blitz/Rapid/Classical time controls)
- Excludes bullet games, variants, and incomplete games
- Extracts positions with proper FEN normalization
- Labels game phase (opening/middlegame/endgame) based on move number and material
- Performs light Stockfish analysis to classify positions as tactical or quiet

### 3. Select game positions (`03_select_games.py`)

Selects 200 positions following the exact distribution requirements:

- Stratified sampling across ELO ranges, game phases, and position types
- Ensures 50/50 color balance
- Deduplicates positions to avoid repetition
- Uses deterministic selection for reproducibility

### 4. Fetch puzzles (`04_fetch_puzzles.py`)

Downloads the complete Lichess puzzle database (~1GB compressed):

- Contains millions of tactical puzzles from real games
- Includes puzzle ratings and themes
- Pre-validated for having clear best moves

### 5. Select puzzles (`05_select_puzzles.py`)

Randomly selects 50 puzzles matching the target distribution:

- Filters for standard chess puzzles (no variants)
- Stratifies by rating ranges
- Balances game phases and colors
- Validates puzzle solutions

### 6. Create questions (`06_create_questions.py`)

Evaluates all positions to create the final dataset:

- Uses Stockfish at depth 25 for objective evaluation
- Scores ALL legal moves for each position
- Outputs in competition format with move evaluations
- Creates both public and private test splits

## Output files

The pipeline generates the following files:

- `output/games.pgn` - Raw Lichess game data
- `output/games.db` - Processed games in SQLite format with metadata
- `output/positions.csv` - 200 selected game positions with labels
- `output/lichess_puzzles.csv` - Complete puzzle database
- `output/puzzles.csv` - 50 selected puzzles
- `questions.csv` - Final competition dataset with the following columns:
  - `index`: Test case index (0-249)
  - `input`: Chess position in FEN notation
  - `expected_output`: JSON object containing all legal moves with their evaluations
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
