import pytest
from wordgrid.game.state import GameState
from wordgrid.ai.mcts_agent import MCTSAgent


class ControlledValidator:
    def __init__(self, words):
        self.words = {w.upper() for w in words}

    def is_valid_word(self, word: str) -> bool:
        return word.upper() in self.words

    def is_valid_prefix(self, prefix: str) -> bool:
        p = prefix.upper()
        return any(w.startswith(p) for w in self.words)


def test_mcts_selects_legal_move_with_small_budget():
    validator = ControlledValidator(["CAT", "DOG", "BAT"])
    state = GameState(board_size=3)

    # Test tiny budget: 1 simulation
    agent_1 = MCTSAgent(simulations=1, seed=42)
    move_1 = agent_1.select_move(state, validator)
    r, c, ch = move_1
    assert state.board.is_valid_coord(r, c)
    assert state.board.is_empty(r, c)
    assert ch.isalpha()

    stats_1 = agent_1.get_last_stats()
    assert stats_1["simulations"] == 1
    assert stats_1["elapsed_time"] >= 0

    # Test small budget: 10 simulations
    agent_10 = MCTSAgent(simulations=10, seed=42)
    move_10 = agent_10.select_move(state, validator)
    assert state.board.is_empty(move_10[0], move_10[1])


def test_mcts_preserves_word_occurrence_history_and_no_duplicate_points():
    validator = ControlledValidator(["CAT", "CATS"])
    state = GameState(board_size=3, current_player=1)
    state.board.set(0, 0, "C")
    state.board.set(0, 1, "A")
    state.board.set(0, 2, "T")
    # Mark CAT as already scored
    state.scored_occurrences.add(("H", 0, 0, 0, 2))
    state.scores[1] = 3

    agent = MCTSAgent(simulations=20, seed=123)
    move = agent.select_move(state, validator)

    # Verify search did not duplicate or corrupt occurrences
    assert ("H", 0, 0, 0, 2) in state.scored_occurrences
    assert state.scores[1] == 3


def test_mcts_does_not_mutate_state():
    validator = ControlledValidator(["CAT", "DOG", "FOX"])
    state = GameState(board_size=3, current_player=1)
    state.board.set(1, 1, "O")

    board_before = state.board.to_tuple()
    scores_before = state.scores.copy()
    player_before = state.current_player
    occ_before = state.scored_occurrences.copy()

    agent = MCTSAgent(simulations=25, seed=999)
    move = agent.select_move(state, validator)

    assert state.board.to_tuple() == board_before
    assert state.scores == scores_before
    assert state.current_player == player_before
    assert state.scored_occurrences == occ_before


def test_mcts_reproducibility_with_seed():
    validator = ControlledValidator(["CAT", "DOG", "BAT", "CAR"])
    state = GameState(board_size=3, current_player=1)
    state.board.set(0, 0, "C")

    agent1 = MCTSAgent(simulations=30, seed=777)
    move1 = agent1.select_move(state, validator)

    agent2 = MCTSAgent(simulations=30, seed=777)
    move2 = agent2.select_move(state, validator)

    assert move1 == move2
