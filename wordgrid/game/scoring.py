from typing import List, Tuple, Set, Optional, Protocol
from wordgrid.game.board import Board

# Occurrence identity: (orientation: 'H'|'V', start_row, start_col, end_row, end_col)
OccurrenceKey = Tuple[str, int, int, int, int]


class WordValidatorProtocol(Protocol):
    """Protocol for checking word validity."""
    def is_valid_word(self, word: str) -> bool:
        ...


class ScoringSystem:
    """Authoritative scoring engine for WordGrid.
    
    Evaluates newly completed words formed by placing a letter at (row, col).
    Ensures:
      - Only contiguous horizontal (L-R) and vertical (T-B) words passing through (row, col) are checked.
      - Words must meet the minimum word length and exist in the accepted dictionary.
      - Each word occurrence scores at most once in its lifetime.
      - When multiple eligible words form on a single move, the score awarded is max(lengths).
      - All newly completed eligible word occurrences are recorded to prevent duplicate scoring.
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
        size = board.size

        # 1. Horizontal sequence (same row)
        left_col = col
        while left_col - 1 >= 0 and board.get(row, left_col - 1) is not None:
            left_col -= 1

        right_col = col
        while right_col + 1 < size and board.get(row, right_col + 1) is not None:
            right_col += 1

        h_letters = [board.get(row, c) for c in range(left_col, right_col + 1)]
        h_word = "".join(h_letters)
        h_key: OccurrenceKey = ("H", row, left_col, row, right_col)

        # 2. Vertical sequence (same col)
        top_row = row
        while top_row - 1 >= 0 and board.get(top_row - 1, col) is not None:
            top_row -= 1

        bottom_row = row
        while bottom_row + 1 < size and board.get(bottom_row + 1, col) is not None:
            bottom_row += 1

        v_letters = [board.get(r, col) for r in range(top_row, bottom_row + 1)]
        v_word = "".join(v_letters)
        v_key: OccurrenceKey = ("V", top_row, col, bottom_row, col)

        return (h_word, h_key), (v_word, v_key)

    def evaluate_move(
        self,
        board: Board,
        row: int,
        col: int,
        validator: WordValidatorProtocol,
        scored_occurrences: Set[OccurrenceKey],
        scored_words: Optional[Set[str]] = None,
        blocked_collector: Optional[List[str]] = None,
    ) -> Tuple[int, List[Tuple[str, int, OccurrenceKey]]]:
        """Evaluates scoring for a move placed at (row, col).
        
        Checks in all 4 directions (Left, Right, Up, Down, and across) for valid words
        passing through (row, col).
        Rules:
          - If a word was already chosen/scored previously in this match (in scored_words),
            it cannot be chosen a second time and awards no points.
          - In each direction (horizontal and vertical), the highest matched valid word is selected.
          - Move score awards the maximum length among the highest matched eligible words.
        
        Returns:
            move_score: int, maximum length of eligible newly formed words (or 0).
            newly_scored: list of (word, length, occurrence_key) for the scored words.
        """
        if scored_words is None:
            scored_words = set()

        size = board.size

        # 1. Horizontal letter boundaries on row
        left_col = col
        while left_col - 1 >= 0 and board.get(row, left_col - 1) is not None:
            left_col -= 1
        right_col = col
        while right_col + 1 < size and board.get(row, right_col + 1) is not None:
            right_col += 1

        # Check all contiguous horizontal subsegments passing through (row, col)
        # Covers words formed:
        #   - Left of (row, col): c_start < col, c_end == col
        #   - Right of (row, col): c_start == col, c_end > col
        #   - Across (row, col): c_start < col < c_end
        eligible_h_words: List[Tuple[str, int, OccurrenceKey]] = []
        for c_start in range(left_col, col + 1):
            for c_end in range(col, right_col + 1):
                length = c_end - c_start + 1
                if length < self.min_word_length:
                    continue
                w_letters = [board.get(row, c) for c in range(c_start, c_end + 1)]
                word = "".join(w_letters)
                key: OccurrenceKey = ("H", row, c_start, row, c_end)

                if word in scored_words:
                    if blocked_collector is not None and word not in blocked_collector:
                        blocked_collector.append(word)
                    continue
                if key in scored_occurrences:
                    continue
                if validator.is_valid_word(word):
                    eligible_h_words.append((word, length, key))

        # Best horizontal word: highest matched word length
        best_h: Optional[Tuple[str, int, OccurrenceKey]] = None
        if eligible_h_words:
            eligible_h_words.sort(key=lambda x: (x[1], x[2][4] - x[2][2]), reverse=True)
            best_h = eligible_h_words[0]

        # 2. Vertical letter boundaries on col
        top_row = row
        while top_row - 1 >= 0 and board.get(top_row - 1, col) is not None:
            top_row -= 1
        bottom_row = row
        while bottom_row + 1 < size and board.get(bottom_row + 1, col) is not None:
            bottom_row += 1

        # Check all contiguous vertical subsegments passing through (row, col)
        # Covers words formed:
        #   - Up (above) (row, col): r_start < row, r_end == row
        #   - Down (below) (row, col): r_start == row, r_end > row
        #   - Across (row, col): r_start < row < r_end
        eligible_v_words: List[Tuple[str, int, OccurrenceKey]] = []
        for r_start in range(top_row, row + 1):
            for r_end in range(row, bottom_row + 1):
                length = r_end - r_start + 1
                if length < self.min_word_length:
                    continue
                w_letters = [board.get(r, col) for r in range(r_start, r_end + 1)]
                word = "".join(w_letters)
                key: OccurrenceKey = ("V", r_start, col, r_end, col)

                if word in scored_words:
                    if blocked_collector is not None and word not in blocked_collector:
                        blocked_collector.append(word)
                    continue
                if key in scored_occurrences:
                    continue
                if validator.is_valid_word(word):
                    eligible_v_words.append((word, length, key))

        # Best vertical word: highest matched word length
        best_v: Optional[Tuple[str, int, OccurrenceKey]] = None
        if eligible_v_words:
            eligible_v_words.sort(key=lambda x: (x[1], x[2][3] - x[2][1]), reverse=True)
            best_v = eligible_v_words[0]

        # 3. Combine results
        eligible_new_words: List[Tuple[str, int, OccurrenceKey]] = []
        if best_h:
            eligible_new_words.append(best_h)
        if best_v and (not best_h or best_v[0] != best_h[0]):
            eligible_new_words.append(best_v)

        if not eligible_new_words:
            return 0, []

        move_score = max(length for _, length, _ in eligible_new_words)
        return move_score, eligible_new_words
