"""Rule coverage for the project specification: directions, longest-word selection,
duplicates, zero-point moves, legal actions and every termination condition."""

import random
import pytest

from wordgrid.game.board import Board
from wordgrid.game.state import GameState
from wordgrid.game.rules import GameRules, END_TARGET_SCORE, END_BOARD_FULL, END_MOVE_LIMIT
from wordgrid.game.scoring import ScoringSystem
from wordgrid.game.engine import GameEngine
from wordgrid.config import GameConfig, MODE_REACH_GOAL_SCORE, MODE_MOVE_LIMIT, MODE_UNTIL_BOARD_FULL
from wordgrid.dictionary.trie import Trie
from wordgrid.dictionary.word_validator import WordValidator
from wordgrid.ai.move_ordering import OpportunityScanner


class SetValidator:
    """Validator without a trie (exercises the generic code paths)."""

    def __init__(self, words):
        self.words = {w.upper() for w in words}

    def is_valid_word(self, word):
        return word.upper() in self.words


def trie_validator(words):
    t = Trie()
    for w in words:
        t.insert(w)
    return WordValidator(t)


def place(board, cells):
    for (r, c), ch in cells.items():
        board.set(r, c, ch)


# --------------------------------------------------------------------------- directions

@pytest.mark.parametrize("make_validator", [SetValidator, trie_validator])
def test_word_read_right_to_left_scores(make_validator):
    v = make_validator(["CAT"])
    scoring = ScoringSystem()
    board = Board(5)
    place(board, {(0, 0): "T", (0, 1): "A"})
    board.set(0, 2, "C")  # row reads T A C -> CAT right-to-left
    score, words = scoring.evaluate_move(board, 0, 2, v, set(), set())
    assert score == 3
    assert words == [("CAT", 3, ("HR", 0, 0, 0, 2))]


@pytest.mark.parametrize("make_validator", [SetValidator, trie_validator])
def test_word_read_bottom_to_top_scores(make_validator):
    v = make_validator(["DOG"])
    scoring = ScoringSystem()
    board = Board(5)
    place(board, {(4, 3): "D", (3, 3): "O"})
    board.set(2, 3, "G")  # column reads G O D top-down -> DOG bottom-to-top
    score, words = scoring.evaluate_move(board, 2, 3, v, set(), set())
    assert score == 3
    assert words == [("DOG", 3, ("VR", 2, 3, 4, 3))]


def test_diagonals_are_not_detected():
    v = SetValidator(["CAT"])
    board = Board(4)
    place(board, {(0, 0): "C", (1, 1): "A"})
    board.set(2, 2, "T")
    score, words = ScoringSystem().evaluate_move(board, 2, 2, v, set(), set())
    assert score == 0 and words == []


def test_invalid_sequence_scores_zero():
    v = SetValidator(["CAT"])
    board = Board(4)
    place(board, {(0, 0): "C", (0, 1): "X"})
    board.set(0, 2, "T")
    assert ScoringSystem().evaluate_move(board, 0, 2, v, set(), set()) == (0, [])


def test_minimum_word_length_is_respected():
    v = SetValidator(["AT", "CAT"])
    board = Board(4)
    board.set(0, 0, "A")
    board.set(0, 1, "T")
    assert ScoringSystem(min_word_length=3).evaluate_move(board, 0, 1, v, set(), set())[0] == 0
    assert ScoringSystem(min_word_length=2).evaluate_move(board, 0, 1, v, set(), set())[0] == 2


# --------------------------------------------------------------------------- selection

def test_spec_example_pan_to_pant_counts_only_pant():
    v = SetValidator(["PAN", "PANT", "ANT"])
    board = Board(5)
    place(board, {(0, 0): "P", (0, 1): "A", (0, 2): "N"})
    board.set(0, 3, "T")
    score, words = ScoringSystem().evaluate_move(board, 0, 3, v, set(), {"PAN"})
    assert score == 4
    assert words == [("PANT", 4, ("H", 0, 0, 0, 3))]


def test_longest_word_wins_across_directions_and_shorter_is_not_consumed():
    v = SetValidator(["TO", "STOP"])
    rules = GameRules()
    s = GameState(board_size=4)
    s.board.set(0, 1, "S")
    s.board.set(2, 1, "O")
    s.board.set(3, 1, "P")
    s.board.set(1, 2, "O")
    s = rules.apply_move(s, (1, 1, "T"), v)  # vertical STOP (4), horizontal TO (2)
    assert s.scores[1] == 4
    assert s.last_scored_words == [("STOP", 4)]
    assert "TO" not in s.scored_words


def test_tie_break_prefers_horizontal_then_forward_reading():
    v = SetValidator(["CAT", "TAC", "BAT"])
    board = Board(5)
    place(board, {(2, 1): "C", (2, 3): "T", (1, 2): "B", (3, 2): "T"})
    board.set(2, 2, "A")
    # Candidates of length 3: CAT (H), TAC (HR), BAT (V), TAB? (not a word)
    score, words = ScoringSystem().evaluate_move(board, 2, 2, v, set(), set())
    assert words == [("CAT", 3, ("H", 2, 1, 2, 3))]
    # If CAT is used up, the right-to-left reading of the same row is next
    score, words = ScoringSystem().evaluate_move(board, 2, 2, v, set(), {"CAT"})
    assert words == [("TAC", 3, ("HR", 2, 1, 2, 3))]


def test_word_scores_once_per_match_even_when_read_in_other_direction():
    v = SetValidator(["CAT"])
    rules = GameRules()
    s = GameState(board_size=5)
    for move in [(0, 0, "C"), (4, 4, "X"), (0, 1, "A"), (4, 3, "X"), (0, 2, "T")]:
        s = rules.apply_move(s, move, v)
    assert s.scores[1] == 3
    # Player 2 forms CAT again, this time right-to-left in row 2
    for move in [(2, 2, "C"), (4, 1, "X"), (2, 1, "A"), (4, 0, "X"), (2, 0, "T")]:
        s = rules.apply_move(s, move, v)
    assert s.scores[2] == 0
    assert s.last_blocked_words == ["CAT"]


# --------------------------------------------------------------------------- engine log

def test_engine_move_log_records_zero_point_moves():
    engine = GameEngine(SetValidator(["AT"]), GameConfig(board_size=3))
    engine.make_move((0, 0, "Q"))
    engine.make_move((1, 1, "A"))
    engine.make_move((1, 2, "T"))
    assert [m["points"] for m in engine.move_log] == [0, 0, 2]
    assert engine.move_log[0]["word"] is None
    assert engine.move_log[2]["word"] == "AT"
    assert engine.move_log[2]["direction"] == "left-to-right"
    assert engine.move_log[2]["player"] == 1
    engine.undo_last_move()
    assert len(engine.move_log) == 2


def test_legal_actions_cover_every_empty_cell_and_letter():
    rules = GameRules()
    s = GameState(board_size=4)
    s.board.set(1, 1, "A")
    moves = rules.get_legal_moves(s)
    assert len(moves) == 15 * 26
    assert (1, 1, "B") not in moves
    assert all(s.board.is_empty(r, c) for r, c, _ in moves)
    s.is_terminal = True
    assert rules.get_legal_moves(s) == []


# --------------------------------------------------------------------------- termination

def test_target_score_wins_immediately_for_the_player_who_reaches_it():
    v = SetValidator(["AT", "CAT"])
    rules = GameRules()
    s = GameState(board_size=4, game_mode=MODE_REACH_GOAL_SCORE, goal_score=3, current_player=2, starting_player=2)
    s.scores = {1: 2, 2: 0}
    s.board.set(0, 0, "C")
    s.board.set(0, 1, "A")
    s = rules.apply_move(s, (0, 2, "T"), v)  # player 2 scores CAT = 3
    assert s.is_terminal
    assert s.winner == 2
    assert s.end_reason == END_TARGET_SCORE


def test_board_full_ends_target_mode_with_score_comparison():
    v = SetValidator(["AT"])
    rules = GameRules()
    s = GameState(board_size=2, game_mode=MODE_REACH_GOAL_SCORE, goal_score=50)
    for move in [(0, 0, "A"), (1, 1, "X"), (0, 1, "T"), (1, 0, "X")]:
        s = rules.apply_move(s, move, v)
    assert s.is_terminal
    assert s.end_reason == END_BOARD_FULL
    assert s.winner == 1


def test_full_board_draw():
    rules = GameRules()
    s = GameState(board_size=2, game_mode=MODE_UNTIL_BOARD_FULL)
    for move in [(0, 0, "X"), (0, 1, "X"), (1, 0, "X"), (1, 1, "X")]:
        s = rules.apply_move(s, move, SetValidator([]))
    assert s.is_terminal and s.winner == 0 and s.end_reason == END_BOARD_FULL


def test_move_limit_with_second_player_starting():
    engine = GameEngine(
        SetValidator(["AT"]),
        GameConfig(board_size=4, game_mode=MODE_MOVE_LIMIT, move_limit=2, starting_player=2),
    )
    assert engine.state.current_player == 2
    for move in [(0, 0, "A"), (0, 1, "T"), (3, 3, "X")]:
        engine.make_move(move)
        assert not engine.is_game_over
    assert engine.move_log[0]["player"] == 2
    assert engine.state.moves_made_by(2) == 2 and engine.state.moves_made_by(1) == 1
    engine.make_move((3, 2, "X"))
    assert engine.is_game_over
    assert engine.state.end_reason == END_MOVE_LIMIT
    assert engine.winner == 1  # player 1 scored AT


# --------------------------------------------------------------------------- scanner

def test_opportunity_scanner_matches_authoritative_scoring():
    """The fast trie scanner must agree with ScoringSystem on random positions."""
    words = ["AT", "TO", "CAT", "ACT", "TAN", "ANT", "NOT", "TON", "CANTO", "OCTAN", "PANT", "TAP",
             "PAT", "APT", "COT", "CON", "NAP", "PAN", "OAT", "TACO"]
    trie_v = trie_validator(words)
    set_v = SetValidator(words)
    rng = random.Random(7)
    for min_len in (2, 3):
        scoring = ScoringSystem(min_len)
        for _ in range(40):
            s = GameState(board_size=5)
            for r in range(5):
                for c in range(5):
                    if rng.random() < 0.45:
                        s.board.set(r, c, rng.choice("ACNOPTX"))
            s.scored_words = set(rng.sample(words, 4))
            for v in (trie_v, set_v):
                scanner = OpportunityScanner(scoring)
                for r, c in s.board.get_empty_cells():
                    opts = scanner.letter_options(s, r, c, v)
                    for ch in "ACNOPTXZ":
                        s.board.grid[r][c] = ch
                        expected, _ = scoring.evaluate_move(s.board, r, c, v, s.scored_occurrences, s.scored_words)
                        s.board.grid[r][c] = None
                        assert opts.get(ch, (0, 0))[0] == expected, (r, c, ch, s.board)
                    assert scanner.cell_best(s, r, c, v) == max((p for p, _ in opts.values()), default=0)
