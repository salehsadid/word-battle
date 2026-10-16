# WordBattle — Strategic Word Grid Game with AI

Two players take turns placing letters (A–Z) on an N × N grid to form English words. Every move
is about two things: scoring as much as you can, and not handing your opponent a bigger word.
You can play against a friend, against an AI (Heuristic Minimax or MCTS, four difficulty levels),
or watch the two AIs play each other.

---

## Setup

Requirements: Python 3.10+.

```bash
pip install -r requirements.txt
python main.py                     # graphical game (pygame)
pytest -q                          # 89 automated tests
```

The game is fully offline. The dictionary lives in `data/cleaned_words.txt`.

### Command line (optional)

```bash
# Play in the terminal (Human, Minimax, MCTS or Random for each side)
python main.py --cli --mode play --p1 Human --p2 MCTS --difficulty Hard --board-size 5

# AI vs AI with a move limit of 10 moves per player, player 2 starting, fixed seed
python main.py --cli --mode play --p1 Minimax --p2 MCTS --game-mode MOVE_LIMIT --move-limit 10 --start 2 --seed 7

# Round-robin benchmark (Random, Minimax, Alpha-Beta, MCTS); results go to data/tournament_results/
python main.py --cli --mode tournament --board-size 4 --games 4
```

Run `python main.py --help` for every option (`--min-len`, `--dict`, `--goal-score`, `--depth`, `--k`, `--sims`, `--c`, ...).

---

## How to play (GUI)

1. **Choose how to play.** Pick a card: *Play vs Computer*, *Two Players* or *Watch AI vs AI*.
   Then set the opponent (**Strategist** = Minimax, **Explorer** = MCTS), difficulty, who goes
   first, board size, and how the match ends (fill the board, reach a score, or a move limit).
   Every choice is a visible button with a one-line hint. Numbers use − / + steppers, so they
   can't be out of range. Start stays disabled, with a plain-language message, until the setup
   is valid.
2. **Advanced options (optional).** A separate sheet with tabs:
   - *Rules*: minimum word length, dictionary, random seed.
   - *Strategist AI*: custom depth, breadth, pruning and playing-style sliders (the heuristic weights).
   - *Explorer AI*: custom simulations, playout length, breadth, exploration constant.
   - *Display*: AI explanations, technical details, pause between AI moves.
   - *Reset to recommended* restores the defaults.
3. **Your turn.** Click an empty square and a letter picker appears next to it. Click a letter,
   or just type it. Arrow keys move the selection and Esc cancels.
4. **During the match:**
   - The **turn banner** says whose turn it is and what to do next.
   - **Score cards** show points, moves (or "x of N moves") and a progress bar in target mode.
   - **Pills** show the rule, squares left and the move number.
   - The **move panel** explains the last move in plain words, e.g. "Strategist played P at
     row 4, col 4, making DAMP for +4. You can answer with up to +3". Technical search details
     are one click away.
   - **Match history** has *Words* (word, points, player, square, direction) and *All moves*
     (including moves that score nothing). Hover an entry to light it up on the board.
   - Scored words glow green. A "+4 DAMP" or "No word formed" toast confirms each move. Hover
     a square for its row and column.
5. **Controls:** **Restart** and **Settings** ask for confirmation mid-game. In AI vs AI,
   **Pause/Resume** (Space) and **Step** (Enter) let you follow move by move. **How to play**
   (F1 or ?) opens the guide.
6. **End of match:** a result card shows the winner or draw, the final score, why it ended,
   words per player and the best word. Buttons: **Play again**, **Change settings**, **View board**.

The interface uses a soft, light warm-neutral theme (navy accent, dusty-blue vs terracotta
players, sage-green words). The palette lives in `wordgrid/ui/colors.py` and the fonts and
drawing helpers in `wordgrid/ui/theme.py`.

---

## Rules

| Rule | Implementation |
|------|----------------|
| Action | Place one letter in any empty cell. |
| Word detection | Only the horizontal and vertical letter runs through the new letter are examined. Every contiguous segment containing the new letter is checked, **in both reading directions** (left→right, right→left, top→bottom, bottom→top). Diagonals are never checked. |
| Eligible word | In the dictionary, at least the minimum length, and not already scored in this match by either player. |
| Selection | Only the **single longest** eligible word counts. Points = its length. No eligible word = 0 points. |
| Tie-break | Equal length: horizontal before vertical, forward reading before reversed, then top-most/left-most start. Deterministic and documented in `ScoringSystem.selection_key`. |
| Duplicates | A scored word is locked for the rest of the match, in any position or direction. If the longest word is locked, the next longest eligible word is chosen. |
| Example | With `PAN` on the board, adding `T` forms `PANT` and `ANT`. Only `PANT` counts: +4. |

### Termination (chosen before the match)

| Condition | Ends when | Winner |
|-----------|-----------|--------|
| Full board | No empty cells remain | Higher score, equal = draw |
| Target score | A player reaches the target | That player, immediately |
| Move limit | **Each** player has made the configured number of moves | Higher score, equal = draw |

In every mode, a full board ends the match early and the scores are compared.

### Ambiguities and the decisions made

1. **"Both reading directions":** a run such as `T A C` scores `CAT` read right-to-left. A word is
   identified by its spelling as read, so once `CAT` has scored it cannot score again in any
   position or direction.
2. **Several words at once:** only the longest word is selected *and locked*. Shorter words formed
   by the same move (e.g. `ANT` inside `PANT`) are not consumed and can still score later.
3. **Words already on the board:** only words that contain the newly placed letter are examined,
   so an existing word never scores twice by being "re-formed" elsewhere.
4. **Move limit** is per player (the spec's "each player gets 30 moves"). 10 moves each on a 5×5
   board means 20 moves in total.
5. **Target score:** only the mover gains points, so the first player to reach the target always
   leads. The match ends right after that move.
6. **Starting player:** Player 1, Player 2 or Random (seeded when a seed is given).
7. **Dictionary:** any `*.txt` word list in `data/` (one word per line) can be selected.
   `Standard English` is the preprocessed default list. Words shorter than the minimum length
   never score.

---

## Architecture

```
wordgrid/
├── config.py               GameConfig (+validation), heuristic weights, difficulty presets
├── settings.py             MatchSettings: pre-match settings, validation, agent construction
├── game/                   ── engine (no UI code) ──
│   ├── board.py            N×N grid
│   ├── state.py            GameState: board, scores, scored words, turn, counters, end reason
│   ├── rules.py            legal-action generation, state transitions, termination
│   ├── scoring.py          word detection (4 directions), longest-word selection, duplicates
│   └── engine.py           authoritative match coordinator, undo, word history & move log
├── dictionary/             Trie, WordValidator, loader, plural-filtering cleaner
├── ai/
│   ├── base_agent.py       common interface + bind_rules() (agents share the engine's rules)
│   ├── evaluation.py       heuristic evaluation (shared by Minimax variants)
│   ├── move_ordering.py    OpportunityScanner (fast trie analysis of each cell) + move ordering
│   ├── alphabeta_agent.py  Heuristic Minimax with configurable alpha-beta pruning
│   ├── minimax_agent.py    plain Minimax reference implementation
│   ├── mcts_agent.py       Monte Carlo Tree Search (UCT)
│   ├── random_agent.py     baseline
│   └── explain.py          human-readable explanation of a chosen move
├── ui/                     pygame screens: theme, controls, dialogs, settings, game, board, panels
└── experiments/            tournament runner, metrics, JSON/CSV export
```

* The engine never imports the UI. GUI, CLI, tournaments and every AI use the same
  `GameRules.apply_move` and `ScoringSystem` code.
* AI search runs in a background thread, so the window stays responsive. Results from a match
  that was restarted or left are discarded via a generation counter.
* The window can be resized. The layout scales from a 1100×760 logical canvas.

---

## AI algorithms

The two algorithms are separate. MCTS uses no minimax search and no heuristic evaluation
function. Both use the shared move generator and move ordering only to decide *which* moves to
consider first.

### Heuristic Minimax (with alpha-beta pruning)

* Depth-limited Minimax. Alpha-beta pruning can be switched off, and the root value is identical
  either way (tested).
* **Move ordering and breadth:** moves are ordered by immediate points, the value of occupying a
  contested cell (blocking), dictionary-prefix potential and adjacency. *Moves per node* (k)
  limits branching (0 = every legal move).
* **Evaluation** (root player's view, weights configurable):
  - `score_diff`: points already banked.
  - `own_future_potential`: the best immediate score available to us when we are to move.
  - `opponent_future_potential`: the opponent's best immediate reply, i.e. the concrete threat,
    such as finishing `PANT` after we wrote `PAN`.
  - `partial_sequence_bonus`: open letter runs that are prefixes of words in either direction.
  - `playable_space_factor`: a lead is worth more as the board fills or the move limit nears.
  - Termination awareness: large bonus/penalty when the side to move can reach the target score.
  - Terminal positions: ±10000 plus margin. The evaluation is also mapped to a win estimate for display.
* Because the evaluation is a score difference, the AI blocks only when blocking is worth more
  than scoring. It writes `PAN` if `PANT` is not a word, and blocks when `PAN` would hand over
  `PANT` (both covered by tests).

### Monte Carlo Tree Search

* **Selection:** UCT, `Q + C·sqrt(ln N / n)`. Rewards are stored from the root player's view, and
  at opponent nodes the child maximising `1 − Q` is chosen, so the tree assumes the opponent
  plays to win.
* **Expansion:** one child per iteration, most promising first, at most *children* per node.
* **Simulation:** semi-greedy rollouts (sample cells, take the best scoring letter 75% of the
  time) up to *rollout depth* plies.
* **Backpropagation:** reward in [0, 1] (win ≈ 0.8–1.0, loss ≈ 0–0.2, scaled by margin).
* The final move is the most-visited root child. The seed makes play reproducible. Each preset
  also has a 10 s safety time cap for very large boards.

### Difficulty presets (real search parameters)

| Difficulty | Minimax depth / moves per node | MCTS iterations / children / rollout |
|------------|-------------------------------|--------------------------------------|
| Easy       | 1 / 6                         | 80 / 8 / 4                           |
| Medium     | 2 / 10                        | 300 / 16 / 6                         |
| Hard       | 3 / 12                        | 900 / 24 / 8                         |
| Expert     | 4 / 10                        | 2000 / 28 / 8                        |
| Custom     | values from the Advanced AI column | values from the Advanced AI column |

Heuristic weights and the MCTS exploration constant always come from the Advanced AI column.

Typical think time on a 5×5 mid-game position: Minimax under 0.2 s at every level. MCTS takes
about 0.1 s (Easy), 0.5 s (Medium), 2 s (Hard) and 5–10 s (Expert). A sample run of 4 games per
pairing on 5×5: Minimax Expert beat Minimax Easy 4–0, MCTS Hard beat MCTS Easy 3–1, and
Minimax Easy beat Random 4–0.

### Performance notes

`OpportunityScanner` analyses an empty cell with a few trie walks and caches the result per
letter run. One cell's analysis yields the points every letter would earn there. This powers move
ordering, threat detection, MCTS rollouts and explanations without calling the full scorer 26
times per cell. A randomized test checks that it agrees exactly with the authoritative
`ScoringSystem`.

---

## Tests

`pytest -q` runs 89 tests, including:

* `test_spec_rules.py`: all four reading directions, no diagonals, invalid words, minimum length,
  the PAN→PANT example, longest-word selection across directions, tie-breaking, duplicates across
  players and directions, 0-point moves in the move log, legal actions, and every termination
  condition including a draw and player 2 starting. Also the scanner-vs-scorer consistency check.
* `test_ai_strategy.py`: blocking a threat, not sacrificing free points, taking the bigger score,
  pruning on/off giving the same value, weights changing the evaluation, agents honouring the
  minimum word length, MCTS opponent modelling and target-score wins, seeds, explanations,
  settings validation and difficulty presets.
* `test_ui_smoke.py`: renders every settings mode, advanced tab, dialog and a full two-player match headlessly.
* Earlier suites: board, dictionary, scoring, rules, Minimax/Alpha-Beta equivalence, MCTS,
  tournament export and word history.

## License

MIT.
