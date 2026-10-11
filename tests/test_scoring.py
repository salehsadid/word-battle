import pytest
from wordgrid.game.board import Board
from wordgrid.game.scoring import ScoringSystem
from wordgrid.dictionary.trie import Trie
from wordgrid.dictionary.word_validator import WordValidator


class SimpleValidator:
    def __init__(self, words):
        self.words = {w.upper() for w in words}

    def is_valid_word(self, word: str) -> bool:
        return word.upper() in self.words


def test_cat_scores_only_once_as_occurrence():
    validator = SimpleValidator(["CAT"])
    scoring = ScoringSystem(min_word_length=2)
    board = Board(size=5)
    scored_occurrences = set()

    # Place C at (0, 0)
    board.set(0, 0, "C")
    score, words = scoring.evaluate_move(board, 0, 0, validator, scored_occurrences)
    assert score == 0
    assert len(words) == 0

    # Place A at (0, 1)
    board.set(0, 1, "A")
    score, words = scoring.evaluate_move(board, 0, 1, validator, scored_occurrences)
    assert score == 0

    # Place T at (0, 2) -> completes CAT
    board.set(0, 2, "T")
    score, words = scoring.evaluate_move(board, 0, 2, validator, scored_occurrences)
    assert score == 3
    assert len(words) == 1
    w_text, length, key = words[0]
    assert w_text == "CAT"
    assert length == 3
    assert key == ("H", 0, 0, 0, 2)

    # Record occurrence as scored
    scored_occurrences.add(key)

    # Place a letter somewhere else on the board (e.g. (3, 3))
    board.set(3, 3, "Z")
    score_elsewhere, words_elsewhere = scoring.evaluate_move(board, 3, 3, validator, scored_occurrences)
    assert score_elsewhere == 0

    # If somehow the same cell is re-evaluated, CAT must not score again
    score_repeat, words_repeat = scoring.evaluate_move(board, 0, 2, validator, scored_occurrences)
    assert score_repeat == 0
    assert len(words_repeat) == 0


def test_extending_cat_into_cats_scores_cats_without_rescoring_cat():
    validator = SimpleValidator(["CAT", "CATS"])
    scoring = ScoringSystem(min_word_length=2)
    board = Board(size=5)
    scored_occurrences = set()

    # Build CAT horizontally at row 1: cols 0, 1, 2
    board.set(1, 0, "C")
    board.set(1, 1, "A")
    board.set(1, 2, "T")
    score_cat, words_cat = scoring.evaluate_move(board, 1, 2, validator, scored_occurrences)
    assert score_cat == 3
    for _, _, k in words_cat:
        scored_occurrences.add(k)
    assert ("H", 1, 0, 1, 2) in scored_occurrences

    # Now extend CAT by placing S at (1, 3) -> CATS
    board.set(1, 3, "S")
    score_cats, words_cats = scoring.evaluate_move(board, 1, 3, validator, scored_occurrences)
    # The new move awards 4 points, not 3 + 4
    assert score_cats == 4
    assert len(words_cats) == 1
    w_text, length, key = words_cats[0]
    assert w_text == "CATS"
    assert length == 4
    assert key == ("H", 1, 0, 1, 3)

    for _, _, k in words_cats:
        scored_occurrences.add(k)

    # Both occurrences are now in scored_occurrences
    assert ("H", 1, 0, 1, 2) in scored_occurrences
    assert ("H", 1, 0, 1, 3) in scored_occurrences


def test_two_identical_words_in_different_locations_score_separately():
    validator = SimpleValidator(["CAT"])
    scoring = ScoringSystem(min_word_length=2)
    board = Board(size=5)
    scored_occurrences = set()

    # CAT at row 0, cols 0..2
    board.set(0, 0, "C")
    board.set(0, 1, "A")
    board.set(0, 2, "T")
    score1, words1 = scoring.evaluate_move(board, 0, 2, validator, scored_occurrences)
    assert score1 == 3
    for _, _, k in words1:
        scored_occurrences.add(k)

    # Second CAT at row 2, cols 1..3
    board.set(2, 1, "C")
    board.set(2, 2, "A")
    board.set(2, 3, "T")
    score2, words2 = scoring.evaluate_move(board, 2, 3, validator, scored_occurrences)
    assert score2 == 3
    assert len(words2) == 1
    assert words2[0][2] == ("H", 2, 1, 2, 3)
    assert ("H", 0, 0, 0, 2) != ("H", 2, 1, 2, 3)


def test_simultaneous_horizontal_and_vertical_words_score_max_length():
    # Example C: Horizontal HOUSE (5) and Vertical TREE (4) intersecting at 'E'
    # Suppose HOUSE is at row 2, cols 0..4: H O U S E
    # TREE is at rows 0..3, col 4: T R E E -> intersects at row 2, col 4 (letter 'E' of TREE)
    # Wait, TREE letters: row 0: T, row 1: R, row 2: E, row 3: E
    validator = SimpleValidator(["HOUSE", "TREE"])
    scoring = ScoringSystem(min_word_length=2)
    board = Board(size=5)
    scored_occurrences = set()

    # Setup board without completing the intersection
    board.set(2, 0, "H")
    board.set(2, 1, "O")
    board.set(2, 2, "U")
    board.set(2, 3, "S")

    board.set(0, 4, "T")
    board.set(1, 4, "R")
    board.set(3, 4, "E")

    # Now place 'E' at intersection (2, 4)
    board.set(2, 4, "E")
    score, words = scoring.evaluate_move(board, 2, 4, validator, scored_occurrences)

    # Score awarded must be max(5, 4) = 5, not 5 + 4 = 9!
    assert score == 5
    assert len(words) == 2
    word_texts = {w[0] for w in words}
    assert word_texts == {"HOUSE", "TREE"}

    # Both occurrences must be marked
    for _, _, k in words:
        scored_occurrences.add(k)
    assert ("H", 2, 0, 2, 4) in scored_occurrences
    assert ("V", 0, 4, 3, 4) in scored_occurrences


def test_extending_valid_word_into_invalid_sequence_scores_zero():
    validator = SimpleValidator(["CAT"])  # CATA is NOT valid
    scoring = ScoringSystem(min_word_length=2)
    board = Board(size=5)
    scored_occurrences = set()

    board.set(0, 0, "C")
    board.set(0, 1, "A")
    board.set(0, 2, "T")
    score_cat, words_cat = scoring.evaluate_move(board, 0, 2, validator, scored_occurrences)
    assert score_cat == 3
    for _, _, k in words_cat:
        scored_occurrences.add(k)

    # Place 'A' at (0, 3) -> row sequence is "CATA"
    board.set(0, 3, "A")
    score_cata, words_cata = scoring.evaluate_move(board, 0, 3, validator, scored_occurrences)
    # CATA is invalid, so score is 0, CAT is not rescored!
    assert score_cata == 0
    assert len(words_cata) == 0
