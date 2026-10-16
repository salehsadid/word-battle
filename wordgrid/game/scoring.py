from typing import List, Tuple, Set, Optional, Protocol
from wordgrid.game.board import Board

# Occurrence identity: (direction, start_row, start_col, end_row, end_col)
# Direction is one of:
#   "H"  - horizontal, read left-to-right   "HR" - horizontal, read right-to-left
#   "V"  - vertical,   read top-to-bottom   "VR" - vertical,   read bottom-to-top
# Coordinates are always stored top-left -> bottom-right regardless of reading direction.
OccurrenceKey = Tuple[str, int, int, int, int]

# Tie-break order among equally long words (lower index wins).
DIRECTION_PRIORITY = {"H": 0, "HR": 1, "V": 2, "VR": 3}

DIRECTION_LABELS = {
    "H": "left-to-right",
    "HR": "right-to-left",
    "V": "top-to-bottom",
    "VR": "bottom-to-top",
}

ScoredWord = Tuple[str, int, OccurrenceKey]


def direction_label(key: Optional[OccurrenceKey]) -> str:
    """Human readable reading direction for an occurrence key."""
    if not key:
        return "-"
    return DIRECTION_LABELS.get(key[0], key[0])


def occurrence_cells(key: OccurrenceKey) -> List[Tuple[int, int]]:
    """Returns the board cells covered by an occurrence key."""
    orient, r1, c1, r2, c2 = key
    if orient.startswith("H"):
        return [(r1, c) for c in range(c1, c2 + 1)]
    return [(r, c1) for r in range(r1, r2 + 1)]


class WordValidatorProtocol(Protocol):
    """Protocol for checking word validity."""
    def is_valid_word(self, word: str) -> bool:
        ...


class ScoringSystem:
    """Authoritative scoring engine for WordGrid.

    Rules implemented:
      - Only contiguous horizontal and vertical letter runs through the placed cell are examined.
        Diagonals are never examined.
      - Every contiguous sub-segment containing the placed cell is a candidate, read in both
        directions (left-to-right, right-to-left, top-to-bottom, bottom-to-top).
      - A candidate is eligible when it meets the minimum length, is in the dictionary and has
        not already been scored earlier in the match (by either player).
      - Only the single longest eligible word is selected and scored; shorter words formed by the
        same move stay available for later moves.
      - Ties between equally long words are broken deterministically by direction
        (H, HR, V, VR), then by top-most / left-most start cell.
      - The move earns points equal to the selected word's length, or 0 if nothing is eligible.
    """

    def __init__(self, min_word_length: int = 2):
        self.min_word_length = min_word_length

    def inspect_sequences(
        self, board: Board, row: int, col: int
    ) -> Tuple[Tuple[str, OccurrenceKey], Tuple[str, OccurrenceKey]]:
        """Finds the maximal contiguous horizontal and vertical letter sequences passing through (row, col).

        Returns:
            ((h_word, h_occurrence_key), (v_word, v_occurrence_key))
        """
        left_col, right_col = self._horizontal_bounds(board, row, col)
        h_word = "".join(board.grid[row][c] for c in range(left_col, right_col + 1))
        h_key: OccurrenceKey = ("H", row, left_col, row, right_col)

        top_row, bottom_row = self._vertical_bounds(board, row, col)
        v_word = "".join(board.grid[r][col] for r in range(top_row, bottom_row + 1))
        v_key: OccurrenceKey = ("V", top_row, col, bottom_row, col)

        return (h_word, h_key), (v_word, v_key)

    @staticmethod
    def _horizontal_bounds(board: Board, row: int, col: int) -> Tuple[int, int]:
        grid = board.grid
        left_col = col
        while left_col - 1 >= 0 and grid[row][left_col - 1] is not None:
            left_col -= 1
        right_col = col
        while right_col + 1 < board.size and grid[row][right_col + 1] is not None:
            right_col += 1
        return left_col, right_col

    @staticmethod
    def _vertical_bounds(board: Board, row: int, col: int) -> Tuple[int, int]:
        grid = board.grid
        top_row = row
        while top_row - 1 >= 0 and grid[top_row - 1][col] is not None:
            top_row -= 1
        bottom_row = row
        while bottom_row + 1 < board.size and grid[bottom_row + 1][col] is not None:
            bottom_row += 1
        return top_row, bottom_row

    def _scan_run(
        self,
        run: List[str],
        pos: int,
        validator: WordValidatorProtocol,
    ) -> List[Tuple[str, int, int, bool]]:
        """Finds dictionary words in `run` that contain index `pos`, in both reading directions.

        Returns a list of (word, start_idx, end_idx, reversed) with indices into `run`.
        """
        n = len(run)
        found: List[Tuple[str, int, int, bool]] = []
        if n < self.min_word_length:
            return found
        has_prefix = hasattr(validator, "is_valid_prefix")

        for is_reversed in (False, True):
            seq = run[::-1] if is_reversed else run
            p = (n - 1 - pos) if is_reversed else pos
            for i in range(p + 1):
                word = "".join(seq[i:p])
                for j in range(p, n):
                    word += seq[j]
                    if has_prefix and not validator.is_valid_prefix(word):
                        break
                    if len(word) >= self.min_word_length and validator.is_valid_word(word):
                        if is_reversed:
                            found.append((word, n - 1 - j, n - 1 - i, True))
                        else:
                            found.append((word, i, j, False))
        return found

    def find_candidates(
        self,
        board: Board,
        row: int,
        col: int,
        validator: WordValidatorProtocol,
    ) -> List[ScoredWord]:
        """Every dictionary word (any direction) containing (row, col), ignoring match history."""
        candidates: List[ScoredWord] = []

        left_col, right_col = self._horizontal_bounds(board, row, col)
        h_run = [board.grid[row][c] for c in range(left_col, right_col + 1)]
        for word, s, e, rev in self._scan_run(h_run, col - left_col, validator):
            key: OccurrenceKey = ("HR" if rev else "H", row, left_col + s, row, left_col + e)
            candidates.append((word, len(word), key))

        top_row, bottom_row = self._vertical_bounds(board, row, col)
        v_run = [board.grid[r][col] for r in range(top_row, bottom_row + 1)]
        for word, s, e, rev in self._scan_run(v_run, row - top_row, validator):
            key = ("VR" if rev else "V", top_row + s, col, top_row + e, col)
            candidates.append((word, len(word), key))

        return candidates

    @staticmethod
    def selection_key(item: ScoredWord) -> Tuple[int, int, int, int]:
        """Sort key implementing the documented tie-breaking rule (smaller sorts first)."""
        word, length, key = item
        return (-length, DIRECTION_PRIORITY.get(key[0], 9), key[1], key[2])

    def evaluate_move(
        self,
        board: Board,
        row: int,
        col: int,
        validator: WordValidatorProtocol,
        scored_occurrences: Set[OccurrenceKey],
        scored_words: Optional[Set[str]] = None,
        blocked_collector: Optional[List[str]] = None,
    ) -> Tuple[int, List[ScoredWord]]:
        """Evaluates scoring for a letter already placed at (row, col).

        Returns:
            move_score: length of the selected word (or 0).
            newly_scored: [] or a single-element list [(word, length, occurrence_key)].
        """
        if scored_words is None:
            scored_words = set()

        eligible: List[ScoredWord] = []
        for item in self.find_candidates(board, row, col, validator):
            word, _, key = item
            if word in scored_words:
                if blocked_collector is not None and word not in blocked_collector:
                    blocked_collector.append(word)
                continue
            if key in scored_occurrences:
                continue
            eligible.append(item)

        if not eligible:
            return 0, []

        best = min(eligible, key=self.selection_key)
        return best[1], [best]
