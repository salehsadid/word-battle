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
    ) -> Tuple[int, List[Tuple[str, int, OccurrenceKey]]]:
        """Evaluates scoring for a move just placed at (row, col).
        
        Returns:
            move_score: int, the maximum length of eligible newly completed words (or 0).
            newly_scored: list of (word, length, occurrence_key) for all newly completed valid occurrences.
        """
        (h_word, h_key), (v_word, v_key) = self.inspect_sequences(board, row, col)

        eligible_new_words: List[Tuple[str, int, OccurrenceKey]] = []

        # Check Horizontal
        if len(h_word) >= self.min_word_length:
            if h_key not in scored_occurrences:
                if validator.is_valid_word(h_word):
                    eligible_new_words.append((h_word, len(h_word), h_key))

        # Check Vertical
        if len(v_word) >= self.min_word_length:
            if v_key not in scored_occurrences:
                if validator.is_valid_word(v_word):
                    eligible_new_words.append((v_word, len(v_word), v_key))

        if not eligible_new_words:
            return 0, []

        move_score = max(length for _, length, _ in eligible_new_words)
        return move_score, eligible_new_words
