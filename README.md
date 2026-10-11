# WordBattle (WordGrid)

> An adversarial, two-player turn-based word construction game and Artificial Intelligence search laboratory.

Players take turns placing letters on an $N \times N$ grid to construct valid English words horizontally and vertically, maximizing their score while strategically denying opportunities to their opponent.

---

## Features

- **Adversarial AI Search**:
  - **Random Agent**: Uniform random baseline.
  - **Heuristic Minimax**: Depth-limited search with multi-feature evaluation.
  - **Alpha-Beta Pruning**: Branch-pruning search with candidate move ordering.
  - **Monte Carlo Tree Search (MCTS)**: Genuine UCT selection, expansion, biased rollouts, and backpropagation.
- **Authoritative Game Engine**: Single source of truth for rules, legal moves, state transitions, and scoring.
- **Physical Occurrence Tracking**: Each word occurrence is tracked by coordinates and orientation; words score once upon completion without duplicate points.
- **Offline English Dictionary**: Preprocessed prefix Trie with morphological plural exclusion and singular preservation (`BUS`, `ANALYSIS`, `GAS`, etc.).
- **Rich Interfaces**:
  - **Pygame GUI**: Responsive dark-themed interface with non-blocking threaded AI search, live metrics, and board visualization.
  - **CLI / Tournament Mode**: Head-to-head matches and automated round-robin benchmarks with JSON/CSV export.
- **Comprehensive Test Suite**: 38 automated unit tests covering engine rules, dictionary filtering, and AI search equivalence.

---

## Game Rules

1. **Board & Turns**: Played on an $N \times N$ grid (default $5 \times 5$, configurable to $3 \times 3$, $4 \times 4$). Players alternate placing one uppercase letter (A–Z) in an empty cell.
2. **Word Completion**: Contiguous horizontal (left-to-right) and vertical (top-to-bottom) sequences passing through the placed cell are evaluated against the offline dictionary.
3. **Scoring**:
   - The move awards the length of the **longest eligible newly formed word**:
     $$\text{move\_score} = \max(\text{eligible\_new\_word\_lengths}, \text{default}=0)$$
   - Extending a word (e.g. `CAT` $\to$ `CATS`) awards points for the new word without rescoring the original word.
   - An existing word left unchanged does not award repeated points.
   - If horizontal and vertical words form simultaneously, only the longest word scores.
4. **Game Modes**:
   - `UNTIL_BOARD_FULL`: Play until all cells are filled.
   - `REACH_GOAL_SCORE`: Play until a player reaches a goal score (e.g., 30 points).
   - `MOVE_LIMIT`: Play for a fixed number of turns (e.g., 20 moves).

---

## Project Structure

```
WordBattle/
├── main.py                  # Entry point launcher
├── requirements.txt         # Project dependencies
├── wordgrid/
│   ├── config.py            # Global configuration & heuristic weights
│   ├── main.py              # CLI & GUI launcher
│   ├── game/                # Authoritative engine, board, state & scoring
│   ├── dictionary/          # Prefix Trie, loader & morphological cleaner
│   ├── ai/                  # Random, Minimax, Alpha-Beta & MCTS agents
│   ├── ui/                  # Pygame GUI screens, renderer & controls
│   └── experiments/         # Tournament runner, metrics & exporters
├── data/
│   ├── cleaned_words.txt    # Preprocessed offline dictionary
│   └── raw_words.txt        # Full vocabulary source
└── tests/                   # 38 unit tests for engine, AI, and dictionary
```

---

## Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/<your-username>/WordBattle.git
   cd WordBattle
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## Quickstart

### Launch Pygame GUI
```bash
python main.py
```
*Select game mode (Human vs AI, AI vs AI, Human vs Human, Tournament), choose algorithms, and configure search depth or simulation budgets.*

### Run CLI Tournament Benchmark
```bash
python main.py --cli --mode tournament --board-size 3 --depth 2 --sims 50 --games 2
```
*Exports match records and aggregated statistics to `data/tournament_results/`.*

### Play Head-to-Head CLI Match
```bash
python main.py --cli --mode play --p1 Human --p2 AlphaBeta --board-size 3
```

---

## Running Tests

Run the full automated test suite:
```bash
pytest -v
```

All 38 tests cover:
- Board initialization, legal moves, boundary enforcement, and state immutability.
- Dictionary normalization, prefix queries, plural exclusion, and singular preservation.
- Authoritative scoring, occurrence tracking, word extension, and max-length rule.
- Minimax vs Alpha-Beta optimal value equivalence and branch pruning.
- MCTS simulation budgets, rollout policies, and reward backpropagation.

---

## License

This project is licensed under the MIT License.
