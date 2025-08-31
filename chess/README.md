# Chess | Peval Competition

[**Link**](https://peval.io/competition/chess) / [`questions.csv`](https://github.com/fiveoutofnine/peval-testsets/blob/main/chess/questions.csv)

## Test-set design

To get a comprehensive evaluation of an LLM&apos;s chess ability, the test-set selects 800 random positions from the most recent month in [Lichess&apos;s Open Database](https://database.lichess.org) game data and 200 random puzzles with the following distribution:

```
All (1000)
|-- Games (800)
|   |-- (0, 1400) ELO (40)
|   |   |-- Opening (8)
|   |   |   |-- Tactical (2)
|   |   |   |   |-- White (1)
|   |   |   |   `-- Black (1)
|   |   |   `-- Quiet (6)
|   |   |       |-- White (3)
|   |   |       `-- Black (3)
|   |   |-- Middlegame (24)
|   |   |   |-- Tactical (7)
|   |   |   |   |-- White (4)
|   |   |   |   `-- Black (3)
|   |   |   `-- Quiet (17)
|   |   |       |-- White (8)
|   |   |       `-- Black (9)
|   |   `-- Endgame (8)
|   |       |-- Tactical (3)
|   |       |   |-- White (1)
|   |       |   `-- Black (2)
|   |       `-- Quiet (5)
|   |           |-- White (2)
|   |           `-- Black (3)
|   |-- [1400, 1800) ELO (160)
|   |   |-- Opening (32)
|   |   |   |-- Tactical (9)
|   |   |   |   |-- White (5)
|   |   |   |   `-- Black (4)
|   |   |   `-- Quiet (23)
|   |   |       |-- White (11)
|   |   |       `-- Black (12)
|   |   |-- Middlegame (96)
|   |   |   |-- Tactical (28)
|   |   |   |   |-- White (14)
|   |   |   |   `-- Black (14)
|   |   |   `-- Quiet (68)
|   |   |       |-- White (34)
|   |   |       `-- Black (34)
|   |   `-- Endgame (32)
|   |       |-- Tactical (9)
|   |       |   |-- White (5)
|   |       |   `-- Black (4)
|   |       `-- Quiet (23)
|   |           |-- White (12)
|   |           `-- Black (11)
|   |-- [1800, 2200) ELO (280)
|   |   |-- Opening (56)
|   |   |   |-- Tactical (16)
|   |   |   |   |-- White (8)
|   |   |   |   `-- Black (8)
|   |   |   `-- Quiet (40)
|   |   |       |-- White (20)
|   |   |       `-- Black (20)
|   |   |-- Middlegame (168)
|   |   |   |-- Tactical (48)
|   |   |   |   |-- White (24)
|   |   |   |   `-- Black (24)
|   |   |   `-- Quiet (120)
|   |   |       |-- White (60)
|   |   |       `-- Black (60)
|   |   `-- Endgame (56)
|   |       |-- Tactical (16)
|   |       |   |-- White (8)
|   |       |   `-- Black (8)
|   |       `-- Quiet (40)
|   |           |-- White (20)
|   |           `-- Black (20)
|   |-- [2200, 2600) ELO (200)
|   |   |-- Opening (40)
|   |   |   |-- Tactical (11)
|   |   |   |   |-- White (6)
|   |   |   |   `-- Black (5)
|   |   |   `-- Quiet (29)
|   |   |       |-- White (15)
|   |   |       `-- Black (14)
|   |   |-- Middlegame (120)
|   |   |   |-- Tactical (34)
|   |   |   |   |-- White (17)
|   |   |   |   `-- Black (17)
|   |   |   `-- Quiet (86)
|   |   |       |-- White (43)
|   |   |       `-- Black (43)
|   |   `-- Endgame (40)
|   |       |-- Tactical (11)
|   |       |   |-- White (6)
|   |       |   `-- Black (5)
|   |       `-- Quiet (29)
|   |           |-- White (14)
|   |           `-- Black (15)
|   `-- [2600, ∞) ELO (120)
|       |-- Opening (24)
|       |   |-- Tactical (7)
|       |   |   |-- White (3)
|       |   |   `-- Black (4)
|       |   `-- Quiet (17)
|       |       |-- White (9)
|       |       `-- Black (8)
|       |-- Middlegame (72)
|       |   |-- Tactical (21)
|       |   |   |-- White (11)
|       |   |   `-- Black (10)
|       |   `-- Quiet (51)
|       |       |-- White (25)
|       |       `-- Black (26)
|       `-- Endgame (24)
|           |-- Tactical (7)
|           |   |-- White (4)
|           |   `-- Black (3)
|           `-- Quiet (17)
|               |-- White (9)
|               `-- Black (8)
`-- Puzzles (200)
    |-- (0, 1400) ELO (10)
    |   |-- Opening (2)
    |   |   |-- Tactical (2)
    |   |   |   |-- White (1)
    |   |   |   `-- Black (1)
    |   |   `-- Quiet (0)
    |   |       |-- White (0)
    |   |       `-- Black (0)
    |   |-- Middlegame (6)
    |   |   |-- Tactical (5)
    |   |   |   |-- White (3)
    |   |   |   `-- Black (2)
    |   |   `-- Quiet (1)
    |   |       |-- White (1)
    |   |       `-- Black (0)
    |   `-- Endgame (2)
    |       |-- Tactical (2)
    |       |   |-- White (1)
    |       |   `-- Black (1)
    |       `-- Quiet (0)
    |           |-- White (0)
    |           `-- Black (0)
    |-- [1400, 1800) ELO (40)
    |   |-- Opening (8)
    |   |   |-- Tactical (7)
    |   |   |   |-- White (4)
    |   |   |   `-- Black (3)
    |   |   `-- Quiet (1)
    |   |       |-- White (1)
    |   |       `-- Black (0)
    |   |-- Middlegame (24)
    |   |   |-- Tactical (20)
    |   |   |   |-- White (10)
    |   |   |   `-- Black (10)
    |   |   `-- Quiet (4)
    |   |       |-- White (2)
    |   |       `-- Black (2)
    |   `-- Endgame (8)
    |       |-- Tactical (7)
    |       |   |-- White (3)
    |       |   `-- Black (4)
    |       `-- Quiet (1)
    |           |-- White (1)
    |           `-- Black (0)
    |-- [1800, 2200) ELO (70)
    |   |-- Opening (14)
    |   |   |-- Tactical (12)
    |   |   |   |-- White (6)
    |   |   |   `-- Black (6)
    |   |   `-- Quiet (2)
    |   |       |-- White (1)
    |   |       `-- Black (1)
    |   |-- Middlegame (42)
    |   |   |-- Tactical (36)
    |   |   |   |-- White (18)
    |   |   |   `-- Black (18)
    |   |   `-- Quiet (6)
    |   |       |-- White (3)
    |   |       `-- Black (3)
    |   `-- Endgame (14)
    |       |-- Tactical (12)
    |       |   |-- White (6)
    |       |   `-- Black (6)
    |       `-- Quiet (2)
    |           |-- White (1)
    |           `-- Black (1)
    |-- [2200, 2600) ELO (50)
    |   |-- Opening (10)
    |   |   |-- Tactical (9)
    |   |   |   |-- White (5)
    |   |   |   `-- Black (4)
    |   |   `-- Quiet (1)
    |   |       |-- White (1)
    |   |       `-- Black (0)
    |   |-- Middlegame (30)
    |   |   |-- Tactical (26)
    |   |   |   |-- White (13)
    |   |   |   `-- Black (13)
    |   |   `-- Quiet (4)
    |   |       |-- White (2)
    |   |       `-- Black (2)
    |   `-- Endgame (10)
    |       |-- Tactical (9)
    |       |   |-- White (4)
    |       |   `-- Black (5)
    |       `-- Quiet (1)
    |           |-- White (1)
    |           `-- Black (0)
    `-- [2600, ∞) ELO (30)
        |-- Opening (6)
        |   |-- Tactical (5)
        |   |   |-- White (3)
        |   |   `-- Black (2)
        |   `-- Quiet (1)
        |       |-- White (0)
        |       `-- Black (1)
        |-- Middlegame (18)
        |   |-- Tactical (15)
        |   |   |-- White (8)
        |   |   `-- Black (7)
        |   `-- Quiet (3)
        |       |-- White (2)
        |       `-- Black (1)
        `-- Endgame (6)
            |-- Tactical (5)
            |   |-- White (2)
            |   `-- Black (3)
            `-- Quiet (1)
                |-- White (0)
                `-- Black (1)
```

### Filters & labeling (copy/paste checklist)

**Game-level (PGNs)**

- Keep: **Standard**, **rated**; time control = **Blitz/Rapid/Classical**.
- Drop: **Bullet/Ultrabullet**, variants (Chess960, etc.), corrupt/partial PGNs, missing ratings.
- Sample **≤1 position per game** (use reservoir sampling over eligible plies).

**Position-level (from games)**

- Must be **legal & non-terminal** (not mate/stalemate; ≥1 legal move).
- **Halfmove clock < 80** (avoid 50-move rule artifacts).
- **Normalize en passant**: only set EP if an EP capture is actually legal; else `-`.
- **Canonicalize FEN**: store first 4 fields (`pieces turn castling ep`).
- **Phase detection** (heuristic):
  Opening = ply ≤ 20 & queens present & non-king material ≥ 26;
  Endgame = non-king material ≤ 14; otherwise Middlegame.
- **Deduplicate & split**: `pos_id = SHA256(SALT || fen4)`; `hash_bucket = int(SHA256(fen4)[:8],16)%100` → preview vs hidden.
- Record: **side to move** (W/B), **avg ELO** bucket, legal move count, castling rights, etc.

**Tactical vs Quiet labeling (light engine probe)**

- Probe with Stockfish **depth ≈ 12**, `MultiPV=3–5`.
- Let `gap = eval(top1) − eval(top2)` (centipawns, POV side-to-move); `good_move_count` = # moves within **≤50 cp** of best.
- **Tactical if any**: mate in PV1, or `gap ≥ 100 cp` (opening/mid) / `≥ 60 cp` (end), or PV1 is check/capture with **SEE ≥ +100 cp**, or `good_move_count ≤ 2`.
- **Quiet if all**: `gap ≤ 30 cp` (opening/mid) / `≤ 20 cp` (end) **and** PV1 not check/capture **and** `good_move_count ≥ 3`.

**Puzzle-level (Lichess puzzles CSV)**

- Keep: Standard puzzles; verify first move is **best** (or wins by **≥100 cp**) at your **grading** depth.
- Drop: malformed FEN, variants, **near-ties** at grading depth, severely overrepresented single motifs.
- Default label: **tactical**; cap **mate** content to ≤4% of all cases.

**Randomness & reproducibility**

- Salted IDs for splits (`SALT`), and a separate `SELECT_SEED` (or precomputed `rand_key`) for deterministic shuffles—**avoid** `ORDER BY RANDOM()`.
- **50/50 color** and distribution totals enforced at selection time (as shown above).

If you want, I can patch your canvas script to (a) add a deterministic `rand_key` column and (b) emit this exact slice (SQL) so you can regenerate the same tree on demand.

## Pipeline

The chess position selection pipeline consists of 6 steps:

1. **01_fetch_games.py** - Downloads a chunk of Lichess game data
2. **02_process_games.py** - Filters and processes games into a SQLite database
3. **03_select_games.py** - Selects 800 positions from games based on ELO, phase, and type distribution
4. **04_fetch_puzzles.py** - Downloads the Lichess puzzle database (~1GB uncompressed)
5. **05_select_puzzles.py** - Randomly selects 200 puzzles (70% middlegame, 30% endgame)
6. **06_create_questions.py** - Evaluates all legal moves for both game positions and puzzles using Stockfish

### Running the Pipeline

```bash
# Run the entire pipeline (skips completed steps)
python generate.py

# Force re-run all steps
python generate.py --force

# Skip the evaluation step (useful for testing)
python generate.py --skip-eval

# Show detailed statistics
python print.py
```

The pipeline will produce:
- `output/games.pgn` - Raw game data from Lichess
- `output/games.db` - Filtered games in SQLite format
- `output/positions.csv` - 800 selected game positions
- `output/lichess_puzzles.csv` - Full Lichess puzzle database
- `output/puzzles.csv` - 200 selected puzzles
- `questions.csv` - Final dataset with all 1000 positions and their move evaluations
