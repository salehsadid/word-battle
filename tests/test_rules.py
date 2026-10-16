import pytest
from wordgrid.game.board import Board
from wordgrid.game.state import GameState
from wordgrid.game.rules import GameRules
from wordgrid.config import (
    MODE_UNTIL_BOARD_FULL,
    MODE_REACH_GOAL_SCORE,
    MODE_MOVE_LIMIT,
)


class MockValidator:
    def __init__(self, valid_words=None):
        self.words = set(valid_words or ["CAT", "DOG", "BAT"])

    def is_valid_word(self, word: str) -> bool:
        return word.upper() in self.words


def test_legal_moves_generation():
    rules = GameRules()
    state = GameState(board_size=3)
    moves = rules.get_legal_moves(state)
    # 9 empty cells * 26 letters = 234 moves
    assert len(moves) == 9 * 26

    # Occupy one cell
    state.board.set(0, 0, "A")
    moves2 = rules.get_legal_moves(state)
    assert len(moves2) == 8 * 26


def test_illegal_move_rejections():
    rules = GameRules()
    state = GameState(board_size=3)
    state.board.set(0, 0, "A")

    # Occupied cell
    assert not rules.is_legal_move(state, (0, 0, "B"))
    # Out of bounds
    assert not rules.is_legal_move(state, (-1, 0, "A"))
    assert not rules.is_legal_move(state, (0, 3, "A"))
    # Invalid letter
    assert not rules.is_legal_move(state, (0, 1, "1"))
    assert not rules.is_legal_move(state, (0, 1, "AB"))


def test_turn_alternation_and_immutability():
    validator = MockValidator()
    rules = GameRules()
    s0 = GameState(board_size=3, current_player=1)

    s1 = rules.apply_move(s0, (0, 0, "C"), validator)
    assert s0.board.is_empty(0, 0)
    assert s0.current_player == 1
    assert s1.board.get(0, 0) == "C"
    assert s1.current_player == 2
    assert s1.move_count == 1

    s2 = rules.apply_move(s1, (0, 1, "A"), validator)
    assert s2.current_player == 1
    assert s2.move_count == 2


def test_termination_board_full():
    validator = MockValidator()
    rules = GameRules()
    state = GameState(board_size=2, game_mode=MODE_UNTIL_BOARD_FULL)

    s = rules.apply_move(state, (0, 0, "A"), validator)
    s = rules.apply_move(s, (0, 1, "B"), validator)
    s = rules.apply_move(s, (1, 0, "C"), validator)
    assert not s.is_terminal

    s = rules.apply_move(s, (1, 1, "D"), validator)
    assert s.is_terminal
    assert len(rules.get_legal_moves(s)) == 0


def test_termination_reach_goal_score():
    validator = MockValidator(["CAT"])
    rules = GameRules()
    # Goal score 3
    state = GameState(board_size=3, game_mode=MODE_REACH_GOAL_SCORE, goal_score=3)

    s1 = rules.apply_move(state, (0, 0, "C"), validator)  # P1
    s2 = rules.apply_move(s1, (1, 0, "X"), validator)    # P2
    s3 = rules.apply_move(s2, (0, 1, "A"), validator)    # P1
    s4 = rules.apply_move(s3, (1, 1, "Y"), validator)    # P2
    s5 = rules.apply_move(s4, (0, 2, "T"), validator)    # P1 scores CAT (3 points)

    assert s5.scores[1] == 3
    assert s5.is_terminal
    assert s5.winner == 1


def test_termination_move_limit():
    validator = MockValidator()
    rules = GameRules()
    state = GameState(board_size=3, game_mode=MODE_MOVE_LIMIT, move_limit=2)

    s1 = rules.apply_move(state, (0, 0, "A"), validator)
    assert not s1.is_terminal
    s2 = rules.apply_move(s1, (0, 1, "B"), validator)
    assert s2.is_terminal


def test_apply_and_undo_inplace():
    validator = MockValidator(["CAT"])
    rules = GameRules()
    state = GameState(board_size=3, current_player=1)

    # Place C
    score1, words1, p1 = rules.apply_move_inplace(state, (0, 0, "C"), validator)
    assert state.board.get(0, 0) == "C"
    assert state.current_player == 2

    rules.undo_move_inplace(state, (0, 0, "C"), score1, words1, p1, None, [])
    assert state.board.is_empty(0, 0)
    assert state.current_player == 1
    assert state.move_count == 0


def test_rules_forbids_repeated_word_and_tracks_last_blocked_words():
    validator = MockValidator(["CAT"])
    rules = GameRules()
    s0 = GameState(board_size=5, current_player=1)

    # P1 forms CAT at row 0
    s1 = rules.apply_move(s0, (0, 0, "C"), validator)
    s2 = rules.apply_move(s1, (4, 4, "Z"), validator)  # P2 dummy
    s3 = rules.apply_move(s2, (0, 1, "A"), validator)
    s4 = rules.apply_move(s3, (4, 3, "Z"), validator)  # P2 dummy
    s5 = rules.apply_move(s4, (0, 2, "T"), validator)  # P1 completes CAT (+3)

    assert s5.scores[1] == 3
    assert "CAT" in s5.scored_words
    assert s5.last_scored_words == [("CAT", 3)]
    assert s5.last_blocked_words == []

    # Now P2 forms CAT at row 2
    s6 = rules.apply_move(s5, (2, 0, "C"), validator)
    s7 = rules.apply_move(s6, (4, 2, "Z"), validator)  # P1 dummy
    s8 = rules.apply_move(s7, (2, 1, "A"), validator)
    s9 = rules.apply_move(s8, (4, 1, "Z"), validator)  # P1 dummy
    s10 = rules.apply_move(s9, (2, 2, "T"), validator)  # P2 completes CAT again

    # P2 must NOT receive points because CAT has already been chosen in this match!
    assert s10.scores[2] == 0
    assert s10.last_scored_words == []
    assert "CAT" in s10.last_blocked_words

