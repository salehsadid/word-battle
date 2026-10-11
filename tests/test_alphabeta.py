import pytest
from wordgrid.game.state import GameState
from wordgrid.dictionary.loader import DictionaryLoader
from wordgrid.ai.minimax_agent import MinimaxAgent
from wordgrid.ai.alphabeta_agent import AlphaBetaAgent
from wordgrid.ai.evaluation import HeuristicEvaluator


class ControlledValidator:
    def __init__(self, words):
        self.words = {w.upper() for w in words}

    def is_valid_word(self, word: str) -> bool:
        return word.upper() in self.words

    def is_valid_prefix(self, prefix: str) -> bool:
        p = prefix.upper()
        return any(w.startswith(p) for w in self.words)


def test_alphabeta_and_minimax_agree_on_optimal_evaluation():
    validator = ControlledValidator(["CAT", "CAR", "BAT", "BAR"])
    evaluator = HeuristicEvaluator()

    # Small test position with 2 empty cells left
    state = GameState(board_size=2, current_player=1)
    state.board.set(0, 0, "C")
    state.board.set(0, 1, "A")
    # 2 empty cells remain: (1, 0) and (1, 1)

    minimax = MinimaxAgent(depth=2, evaluator=evaluator)
    alphabeta = AlphaBetaAgent(depth=2, evaluator=evaluator, use_move_ordering=True)

    m_move = minimax.select_move(state, validator)
    ab_move = alphabeta.select_move(state, validator)

    m_stats = minimax.get_last_stats()
    ab_stats = alphabeta.get_last_stats()

    # Optimal evaluations MUST be identical
    assert pytest.approx(m_stats["best_score"], abs=1e-5) == ab_stats["best_score"]

    # Alpha-Beta should visit fewer or equal nodes
    assert ab_stats["nodes_visited"] <= m_stats["nodes_visited"]


def test_alphabeta_records_cutoffs():
    validator = ControlledValidator(["CAT", "CAR", "BAT", "BAR", "RAT", "MAT"])
    evaluator = HeuristicEvaluator()

    state = GameState(board_size=3, current_player=1)
    state.board.set(0, 0, "C")
    state.board.set(0, 1, "A")
    state.board.set(1, 0, "B")

    alphabeta = AlphaBetaAgent(depth=2, evaluator=evaluator, use_move_ordering=True)
    move = alphabeta.select_move(state, validator)
    stats = alphabeta.get_last_stats()

    assert stats["nodes_visited"] > 0
    assert stats["cutoffs"] > 0
    assert "elapsed_time" in stats


def test_alphabeta_does_not_mutate_state():
    validator = ControlledValidator(["CAT", "CAR"])
    alphabeta = AlphaBetaAgent(depth=2)
    state = GameState(board_size=3, current_player=1)
    state.board.set(0, 0, "C")

    board_before = state.board.to_tuple()
    scores_before = state.scores.copy()
    player_before = state.current_player
    occ_before = state.scored_occurrences.copy()

    move = alphabeta.select_move(state, validator)

    assert state.board.to_tuple() == board_before
    assert state.scores == scores_before
    assert state.current_player == player_before
    assert state.scored_occurrences == occ_before
