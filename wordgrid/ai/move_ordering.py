import string
from typing import Dict, List, Tuple
from wordgrid.game.board import Board
from wordgrid.game.state import GameState
from wordgrid.game.rules import Move
from wordgrid.game.scoring import WordValidatorProtocol, ScoringSystem

ALPHABET = string.ascii_uppercase

# Rough English letter frequencies, used only to break ties between otherwise equal moves.
LETTER_FREQUENCY = {
    "E": 12.7, "T": 9.1, "A": 8.2, "O": 7.5, "I": 7.0, "N": 6.7, "S": 6.3, "H": 6.1,
    "R": 6.0, "D": 4.3, "L": 4.0, "C": 2.8, "U": 2.8, "M": 2.4, "W": 2.4, "F": 2.2,
    "G": 2.0, "Y": 2.0, "P": 1.9, "B": 1.5, "V": 1.0, "K": 0.8, "J": 0.15, "X": 0.15,
    "Q": 0.1, "Z": 0.07,
}

FREQUENT_LETTERS = sorted(ALPHABET, key=lambda ch: -LETTER_FREQUENCY[ch])
FILLER_LETTERS = 3

# letter -> (immediate points if placed now, longest dictionary-prefix run through the cell)
# Sparse: letters with (0, 0) are omitted.
LetterOptions = Dict[str, Tuple[int, int]]


class OpportunityScanner:
    """Computes, for an empty cell, what every letter would score there.

    Uses the dictionary trie directly when available (WordValidator), so a whole cell is analysed
    with a handful of trie walks instead of 26 full move evaluations. Falls back to the
    authoritative ScoringSystem for validators without a trie (e.g. small test validators).
    Both paths implement exactly the rules of ScoringSystem.evaluate_move.
    """

    def __init__(self, scoring: ScoringSystem):
        self.scoring = scoring
        self._validator = None
        self._root = None
        self._cache: Dict[tuple, tuple] = {}       # directional scan cache
        self._cell_cache: Dict[tuple, tuple] = {}  # merged per-cell cache

    # ------------------------------------------------------------------ cells
    @staticmethod
    def _runs(board: Board, r: int, c: int) -> Tuple[List[str], List[str], List[str], List[str]]:
        grid, n = board.grid, board.size
        left: List[str] = []
        cc = c - 1
        while cc >= 0 and grid[r][cc] is not None:
            left.append(grid[r][cc])
            cc -= 1
        left.reverse()
        right: List[str] = []
        cc = c + 1
        while cc < n and grid[r][cc] is not None:
            right.append(grid[r][cc])
            cc += 1
        up: List[str] = []
        rr = r - 1
        while rr >= 0 and grid[rr][c] is not None:
            up.append(grid[rr][c])
            rr -= 1
        up.reverse()
        down: List[str] = []
        rr = r + 1
        while rr < n and grid[rr][c] is not None:
            down.append(grid[rr][c])
            rr += 1
        return left, right, up, down

    @staticmethod
    def has_neighbor(board: Board, r: int, c: int) -> bool:
        grid, n = board.grid, board.size
        return (
            (r > 0 and grid[r - 1][c] is not None)
            or (r + 1 < n and grid[r + 1][c] is not None)
            or (c > 0 and grid[r][c - 1] is not None)
            or (c + 1 < n and grid[r][c + 1] is not None)
        )

    def _directional(
        self,
        before: Tuple[str, ...],
        after: Tuple[str, ...],
        validator: WordValidatorProtocol,
    ):
        """All words before[i:] + X + after[:j] (read forward) for every letter X.

        Returns (words, alive, best, word_set): words is a list of (X, word, length) meeting the
        minimum length, alive maps X to the longest dictionary-prefix run through the cell, best
        maps X to its longest word and word_set holds every word. Results ignore match history
        so they can be cached; callers filter out already scored words.
        """
        key = (before, after)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        words: List[Tuple[str, str, int]] = []
        alive: Dict[str, int] = {}
        nb = len(before)
        root = self._root

        if root is not None:
            for i in range(nb + 1):
                node = root
                for ch in before[i:]:
                    node = node.children.get(ch)
                    if node is None:
                        break
                if node is None:
                    continue
                head = "".join(before[i:])
                for x, child in node.children.items():
                    length = nb - i + 1
                    word = head + x
                    if child.is_terminal:
                        words.append((x, word, length))
                    n2 = child
                    for ch in after:
                        n2 = n2.children.get(ch)
                        if n2 is None:
                            break
                        length += 1
                        word += ch
                        if n2.is_terminal:
                            words.append((x, word, length))
                    if length > alive.get(x, 0):
                        alive[x] = length
        else:
            has_prefix = hasattr(validator, "is_valid_prefix")
            for x in ALPHABET:
                for i in range(nb + 1):
                    word = "".join(before[i:]) + x
                    if has_prefix and not validator.is_valid_prefix(word):
                        continue
                    length = len(word)
                    if validator.is_valid_word(word):
                        words.append((x, word, length))
                    for ch in after:
                        nxt = word + ch
                        if has_prefix and not validator.is_valid_prefix(nxt):
                            break
                        word = nxt
                        length += 1
                        if validator.is_valid_word(word):
                            words.append((x, word, length))
                    if has_prefix and length > alive.get(x, 0):
                        alive[x] = length

        min_len = self.scoring.min_word_length
        words = [w for w in words if w[2] >= min_len]
        best: Dict[str, int] = {}
        for x, _, length in words:
            if length > best.get(x, 0):
                best[x] = length
        if len(self._cache) > 200000:
            self._cache.clear()
        result = (words, alive, best, frozenset(w for _, w, _ in words))
        self._cache[key] = result
        return result

    def _bind_validator(self, validator: WordValidatorProtocol) -> None:
        if validator is not self._validator:
            self._validator = validator
            self._root = getattr(getattr(validator, "trie", None), "root", None)
            self._cache = {}
            self._cell_cache = {}

    def _cell_scans(self, board: Board, r: int, c: int, validator: WordValidatorProtocol):
        """Directional scans for a cell plus the merged, history-free letter options."""
        self._bind_validator(validator)
        left, right, up, down = self._runs(board, r, c)
        key = (tuple(left), tuple(right), tuple(up), tuple(down))
        cached = self._cell_cache.get(key)
        if cached is not None:
            return cached

        scans = []
        if left or right:
            scans.append(self._directional(key[0], key[1], validator))
            scans.append(self._directional(tuple(right[::-1]), tuple(left[::-1]), validator))
        if up or down:
            scans.append(self._directional(key[2], key[3], validator))
            scans.append(self._directional(tuple(down[::-1]), tuple(up[::-1]), validator))

        best: Dict[str, int] = {}
        alive: Dict[str, int] = {}
        word_set = frozenset().union(*(scan[3] for scan in scans)) if scans else frozenset()
        for _, reach, scan_best, _ in scans:
            for x, n in scan_best.items():
                if n > best.get(x, 0):
                    best[x] = n
            for x, n in reach.items():
                if n > alive.get(x, 0):
                    alive[x] = n
        merged = {ch: (best.get(ch, 0), alive.get(ch, 0)) for ch in (best.keys() | alive.keys())}
        top = max(best.values(), default=0)

        if len(self._cell_cache) > 200000:
            self._cell_cache.clear()
        result = (scans, merged, word_set, top)
        self._cell_cache[key] = result
        return result

    def letter_options(
        self,
        state: GameState,
        r: int,
        c: int,
        validator: WordValidatorProtocol,
    ) -> LetterOptions:
        """Returns {letter: (points, prefix_reach)} for placing letters at empty cell (r, c).

        Sparse: letters that neither score nor extend a dictionary prefix are omitted, so look
        them up with opts.get(letter, (0, 0)). The returned dict may be shared: do not mutate it.
        """
        scans, merged, word_set, _ = self._cell_scans(state.board, r, c, validator)
        scored_words = state.scored_words
        if scored_words.isdisjoint(word_set):
            return merged

        best: Dict[str, int] = {}
        for words, _, _, _ in scans:
            for x, word, length in words:
                if length > best.get(x, 0) and word not in scored_words:
                    best[x] = length
        return {ch: (best.get(ch, 0), reach) for ch, (_, reach) in merged.items()}

    def cell_best(self, state: GameState, r: int, c: int, validator: WordValidatorProtocol) -> int:
        """Best points any letter could earn at empty cell (r, c)."""
        scans, _, word_set, top = self._cell_scans(state.board, r, c, validator)
        scored_words = state.scored_words
        if scored_words.isdisjoint(word_set):
            return top
        best = 0
        for words, _, _, _ in scans:
            for _, word, length in words:
                if length > best and word not in scored_words:
                    best = length
        return best

    # ------------------------------------------------------------------ board
    def best_immediate_score(self, state: GameState, validator: WordValidatorProtocol) -> int:
        """Highest number of points the player to move could earn with a single move."""
        board = state.board
        best = 0
        for r in range(board.size):
            for c in range(board.size):
                if board.grid[r][c] is None and self.has_neighbor(board, r, c):
                    cell_best = self.cell_best(state, r, c, validator)
                    if cell_best > best:
                        best = cell_best
        return best

    def threat_map(self, state: GameState, validator: WordValidatorProtocol) -> Dict[Tuple[int, int], int]:
        """{cell: best points available there} for every empty cell next to a letter."""
        board = state.board
        out: Dict[Tuple[int, int], int] = {}
        for r in range(board.size):
            for c in range(board.size):
                if board.grid[r][c] is None and self.has_neighbor(board, r, c):
                    out[(r, c)] = self.cell_best(state, r, c, validator)
        return out


class MoveOrdering:
    """Prioritizes moves based on immediate scoring, blocking value and prefix potential.

    Used to accelerate Alpha-Beta pruning cutoffs, to limit branching (top_k) and to choose
    which children MCTS expands first.
    """

    def __init__(self, scoring_system: ScoringSystem):
        self.scoring = scoring_system
        self.scanner = OpportunityScanner(scoring_system)

    def set_scoring(self, scoring_system: ScoringSystem) -> None:
        self.scoring = scoring_system
        self.scanner = OpportunityScanner(scoring_system)

    def score_candidate_move(
        self,
        state: GameState,
        move: Move,
        validator: WordValidatorProtocol,
    ) -> float:
        """Estimates the immediate promise of a single move (without diversity adjustments)."""
        r, c, ch = move
        opts = self.scanner.letter_options(state, r, c, validator)
        return self._cell_base(state, r, c, opts) + self._letter_priority(ch, opts)

    def _cell_base(self, state: GameState, r: int, c: int, opts: LetterOptions) -> float:
        """Part of the priority shared by every letter placed at (r, c)."""
        board = state.board
        cell_best = max((p for p, _ in opts.values()), default=0)
        center = (board.size - 1) / 2.0
        centrality = 1.0 - (abs(r - center) + abs(c - center)) / max(1.0, 2 * center)
        base = 0.1 * centrality
        if cell_best > 0:
            # Occupying a cell where *someone* can score denies it to the opponent.
            base += 0.5 * cell_best
        if self.scanner.has_neighbor(board, r, c):
            base += 1.0
        return base

    @staticmethod
    def _letter_priority(ch: str, opts: LetterOptions) -> float:
        pts, reach = opts.get(ch, (0, 0))
        return pts * 10.0 + 0.25 * reach + 0.02 * LETTER_FREQUENCY.get(ch, 0.0)

    def order_moves(
        self,
        state: GameState,
        moves: List[Move],
        validator: WordValidatorProtocol,
        top_k: int = 0,
    ) -> List[Move]:
        """Orders moves in descending order of promise.

        Letters competing for the same cell are slightly penalised by rank so that a truncated
        list (top_k > 0) covers several cells instead of 26 letters on one cell.
        If top_k <= 0, returns all moves sorted.
        """
        if not moves:
            return []

        by_cell: Dict[Tuple[int, int], List[str]] = {}
        for r, c, ch in moves:
            by_cell.setdefault((r, c), []).append(ch)

        scored_moves: List[Tuple[float, Move]] = []
        for (r, c), letters in by_cell.items():
            opts = self.scanner.letter_options(state, r, c, validator)
            base = self._cell_base(state, r, c, opts)
            if top_k > 0:
                # Letters with no effect at this cell differ only by frequency and rank penalty,
                # so a handful of the most common ones is enough to compete for the top k.
                legal = set(letters)
                pool = [ch for ch in opts if ch in legal]
                pool += [ch for ch in FREQUENT_LETTERS if ch in legal and ch not in opts][:FILLER_LETTERS]
            else:
                pool = letters
            local = sorted(((self._letter_priority(ch, opts), ch) for ch in pool), reverse=True)
            for rank, (p, ch) in enumerate(local):
                penalty = 0.0 if opts.get(ch, (0, 0))[0] > 0 else 0.75 * rank
                scored_moves.append((base + p - penalty, (r, c, ch)))

        # Sort descending by estimated priority; ties broken by move for determinism
        scored_moves.sort(key=lambda item: (-item[0], item[1]))

        if top_k > 0:
            return [m for _, m in scored_moves[:top_k]]
        return [m for _, m in scored_moves]
