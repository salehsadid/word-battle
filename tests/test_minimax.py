import pytest
from wordgrid.game.state import GameState
from wordgrid.game.board import Board
from wordgrid.dictionary.loader import DictionaryLoader
from wordgrid.ai.minimax_agent import MinimaxAgent
from wordgrid.ai.evaluation import HeuristicEvaluator
from wordgrid.config import MODE_UNTIL_BOARD_FULL, MODE_MOVE_LIMIT


class SimpleValidator:
    def __init__(self, words):
        self.words = {w.upper() for w in words}

    def is_valid_word(self, word: str) -> bool:
        return word.upper() in self.words

    def is_valid_prefix(self, prefix: str) -> bool:
        p = prefix.upper()
        return any(w.startswith(p) for w in self.words)


def test_minimax_selects_legal_move():
    validator = SimpleValidator(["CAT", "DOG", "BAT"])
    agent = MinimaxAgent(depth=1)
    state = GameState(board_size=3)

    move = agent.select_move(state, validator)
    r, c, ch = move
    assert state.board.is_valid_coord(r, c)
    assert state.board.is_empty(r, c)
    assert ch.isalpha()


def test_minimax_finds_immediate_winning_move():
    # Setup board where P1 can complete "CAT" in row 0
    validator = SimpleValidator(["CAT"])
    agent = MinimaxAgent(depth=1)
    state = GameState(board_size=3, current_player=1)
    state.board.set(0, 0, "C")
    state.board.set(0, 1, "A")

    move = agent.select_move(state, validator)
    assert move == (0, 2, "T")
    stats = agent.get_last_stats()
    assert stats["nodes_visited"] > 0
    assert stats["best_score"] > 0


def test_minimax_does_not_mutate_state():
    validator = SimpleValidator(["CAT", "CAR"])
    agent = MinimaxAgent(depth=2)
    state = GameState(board_size=3, current_player=1)
    state.board.set(0, 0, "C")

    # Snapshot before search
    board_tuple_before = state.board.to_tuple()
    scores_before = state.scores.copy()
    player_before = state.current_player
    occurrences_before = state.scored_occurrences.copy()

    move = agent.select_move(state, validator)

    # Verify state was untouched
    assert state.board.to_tuple() == board_tuple_before
    assert state.scores == scores_before
    assert state.current_player == player_before
    assert state.scored_occurrences == occurrences_before
