# Chess | Peval Competition

[**Link**](https://peval.io/competition/chess) / [`questions.csv`](https://github.com/fiveoutofnine/peval-testsets/blob/main/chess/questions.csv)

## Test-set design

The test-set evaluates LLMs' chess playing ability across a comprehensive range of positions, combining 800 real game positions from [Lichess Open Database](https://database.lichess.org) and 200 tactical puzzles. The dataset is strategically balanced across:

- **ELO ranges**: From beginner (<1400) to super-GM (>2600) level positions
- **Game phases**: Opening (20%), Middlegame (60%), and Endgame (20%)
- **Position types**: Tactical (requiring precise calculation) and Quiet (positional understanding)
- **Colors**: Equal distribution between White and Black to move
- **Complexity**: From simple 1-move tactics to deep positional evaluations

### Distribution breakdown

The 1000 test cases follow this precise distribution:

- **800 Game Positions**: Sampled from real games with the following ELO distribution:
  - 40 positions from <1400 ELO games (beginner level)
  - 160 positions from 1400-1800 ELO games (intermediate level)
  - 280 positions from 1800-2200 ELO games (advanced level)
  - 200 positions from 2200-2600 ELO games (master level)
  - 120 positions from >2600 ELO games (super-GM level)

- **200 Puzzle Positions**: Tactical puzzles with guaranteed best moves:
  - 10 puzzles rated <1400 (beginner tactics)
  - 40 puzzles rated 1400-1800 (intermediate tactics)
  - 70 puzzles rated 1800-2200 (advanced tactics)
  - 50 puzzles rated 2200-2600 (master tactics)
  - 30 puzzles rated >2600 (super-GM tactics)

Each position is evaluated using Stockfish (depth 25) to provide objective scores for all legal moves, enabling precise measurement of move quality.

## Generating

To generate an equivalent sample test-set, run the complete pipeline:

```bash
python generate.py [options]
```

### Options

- `--force`: Force re-run all pipeline steps even if outputs exist
- `--skip-eval`: Skip the Stockfish evaluation step (useful for testing)

### Examples

```bash
# Run the complete pipeline (skips completed steps)
python generate.py

# Force regenerate everything from scratch
python generate.py --force

# Generate positions without evaluation (faster for testing)
python generate.py --skip-eval

# View detailed statistics about the generated dataset
python print.py
```

## Pipeline details

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
Selects 800 positions following the exact distribution requirements:
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
Randomly selects 200 puzzles matching the target distribution:
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
- `output/positions.csv` - 800 selected game positions with labels
- `output/lichess_puzzles.csv` - Complete puzzle database
- `output/puzzles.csv` - 200 selected puzzles
- `questions.csv` - Final competition dataset with the following columns:
  - `index`: Test case index (0-999)
  - `input`: Chess position in FEN notation
  - `expected_output`: JSON object containing all legal moves with their evaluations
  - `private`: "false" for first 100 positions (public), "true" for remaining 900 (private)

## Requirements

- Python 3.8+
- Stockfish chess engine (install via package manager or download from [stockfishchess.org](https://stockfishchess.org))
- ~2GB free disk space for puzzle database
- Dependencies (install via `pip install -r requirements.txt`):
  - `python-chess`: Chess library for move generation and board manipulation
  - `requests`: For downloading Lichess data
  - `tqdm`: Progress bars for long-running operations

## Technical notes

### Position selection criteria

- **Legal & non-terminal**: All positions must have at least one legal move
- **Halfmove clock < 80**: Avoids positions close to 50-move rule draws
- **En passant normalization**: Only includes en passant square when capture is actually possible
- **Canonical FEN**: Uses first 4 fields only (pieces, turn, castling, en passant)

### Tactical vs Quiet classification

Positions are classified using Stockfish analysis (depth ~12):
- **Tactical**: Positions with forcing moves, large evaluation gaps between best and second-best moves, or positions requiring precise calculation
- **Quiet**: Positions with multiple reasonable moves, small evaluation differences, requiring positional understanding

### Reproducibility

The pipeline uses deterministic selection with fixed random seeds to ensure reproducible dataset generation. The exact same 1000 positions can be regenerated by running the pipeline with the same input data.