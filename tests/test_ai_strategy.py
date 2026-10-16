"""AI correctness: threat handling, opponent modelling, configuration and explanations."""

import pytest

from wordgrid.game.state import GameState
from wordgrid.game.rules import GameRules
from wordgrid.game.scoring import ScoringSystem
from wordgrid.dictionary.trie import Trie
from wordgrid.dictionary.word_validator import WordValidator
from wordgrid.ai.alphabeta_agent import AlphaBetaAgent
from wordgrid.ai.minimax_agent import MinimaxAgent
from wordgrid.ai.mcts_agent import MCTSAgent, MCTSNode
from wordgrid.ai.evaluation import HeuristicEvaluator
from wordgrid.config import DIFFICULTIES, DIFFICULTY_PRESETS, MODE_REACH_GOAL_SCORE
from wordgrid.settings import (
    MatchSettings,
    PlayerSettings,
    CONTROLLER_HUMAN,
    CONTROLLER_MINIMAX,
    CONTROLLER_MCTS,
    MATCH_AI_VS_AI,
    MATCH_HUMAN_VS_AI,
    MATCH_HUMAN_VS_HUMAN,
    DIFFICULTY_CUSTOM,
)


def trie_validator(words):
    t = Trie()
    for w in words:
        t.insert(w)
    return WordValidator(t)


def pan_position():
    state = GameState(board_size=4, current_player=1)
    state.board.set(0, 0, "P")
    state.board.set(0, 1, "A")
    return state


def test_minimax_blocks_when_scoring_hands_opponent_a_longer_word():
    # Writing PAN (+3) lets the opponent answer PANT (+4). Occupying (0, 2) with a
    # harmless letter kills both words, which is worth more than the net -1.
    v = trie_validator(["PAN", "PANT"])
    agent = AlphaBetaAgent(depth=2, candidate_k=30)
    move = agent.select_move(pan_position(), v)
    assert move[:2] == (0, 2)
    assert move[2] != "N"


def test_minimax_does_not_sacrifice_free_points_to_block():
    # Without PANT in the dictionary there is no threat: just take PAN.
    v = trie_validator(["PAN"])
    agent = AlphaBetaAgent(depth=2, candidate_k=30)
    assert agent.select_move(pan_position(), v) == (0, 2, "N")


def test_minimax_takes_bigger_score_even_if_opponent_replies():
    # PANT is available now (+4); answering threats elsewhere is worth less.
    v = trie_validator(["PANT", "AT"])
    state = GameState(board_size=4)
    for c, ch in enumerate("PAN"):
        state.board.set(0, c, ch)
    state.board.set(2, 0, "A")
    agent = AlphaBetaAgent(depth=2, candidate_k=30)
    assert agent.select_move(state, v) == (0, 3, "T")


def test_pruning_toggle_preserves_minimax_value():
    v = trie_validator(["CAT", "CAR", "BAT", "BAR", "AT"])
    state = GameState(board_size=3)
    state.board.set(0, 0, "C")
    state.board.set(0, 1, "A")
    state.board.set(1, 0, "B")
    pruned = AlphaBetaAgent(depth=2, use_pruning=True, explain=False)
    plain = AlphaBetaAgent(depth=2, use_pruning=False, explain=False)
    reference = MinimaxAgent(depth=2)
    pruned.select_move(state, v)
    plain.select_move(state, v)
    reference.select_move(state, v)
    assert pruned.get_last_stats()["best_score"] == pytest.approx(plain.get_last_stats()["best_score"])
    assert plain.get_last_stats()["best_score"] == pytest.approx(reference.get_last_stats()["best_score"])
    assert pruned.get_last_stats()["nodes_visited"] < plain.get_last_stats()["nodes_visited"]
    assert plain.get_last_stats()["cutoffs"] == 0


def test_heuristic_weights_change_the_evaluation():
    v = trie_validator(["PAN", "PANT"])
    state = pan_position()
    nxt = GameRules().apply_move(state, (0, 2, "N"), v)  # opponent now threatens PANT
    cautious = HeuristicEvaluator()
    cautious.weights.opponent_future_potential = 2.0
    careless = HeuristicEvaluator()
    careless.weights.opponent_future_potential = 0.0
    assert cautious.evaluate_heuristic(nxt, 1, v) < careless.evaluate_heuristic(nxt, 1, v)


def test_agents_use_bound_minimum_word_length():
    v = trie_validator(["AT", "CAT"])
    state = GameState(board_size=3)
    state.board.set(0, 0, "A")
    rules3 = GameRules(ScoringSystem(min_word_length=3))
    agent = AlphaBetaAgent(depth=1, explain=False)
    agent.bind_rules(rules3)
    agent.select_move(state, v)
    # With min length 3 "AT" is worthless, so the agent cannot see any scoring move
    assert agent.get_last_stats()["best_score"] < 2


def test_mcts_selection_minimises_root_value_at_opponent_nodes():
    agent = MCTSAgent(simulations=1, c_param=0.0)
    root_state = GameState(board_size=3, current_player=1)
    opp_state = GameState(board_size=3, current_player=2)

    for state, expected in ((root_state, "good_for_root"), (opp_state, "bad_for_root")):
        parent = MCTSNode(state)
        parent.visits = 20
        good = MCTSNode(state, parent=parent, move=(0, 0, "A"))
        good.visits, good.total_reward = 10, 9.0   # Q = 0.9 for the root player
        bad = MCTSNode(state, parent=parent, move=(0, 1, "B"))
        bad.visits, bad.total_reward = 10, 1.0     # Q = 0.1 for the root player
        parent.children = {good.move: good, bad.move: bad}
        chosen = agent._select_best_uct_child(parent, root_player=1)
        assert chosen is (good if expected == "good_for_root" else bad)


def test_mcts_finds_immediate_target_score_win():
    v = trie_validator(["CAT"])
    state = GameState(board_size=3, game_mode=MODE_REACH_GOAL_SCORE, goal_score=3)
    state.board.set(0, 0, "C")
    state.board.set(0, 1, "A")
    agent = MCTSAgent(simulations=200, seed=5)
    assert agent.select_move(state, v) == (0, 2, "T")
    assert agent.get_last_stats()["win_probability"] > 0.8  # winning rewards lie in [0.8, 1.0]


def test_mcts_seed_reproducible_and_configurable():
    v = trie_validator(["CAT", "CAR", "BAT", "AT", "TA"])
    state = GameState(board_size=4)
    state.board.set(1, 1, "A")
    a = MCTSAgent(simulations=150, c_param=0.7, seed=11)
    b = MCTSAgent(simulations=150, c_param=0.7, seed=11)
    assert a.select_move(state, v) == b.select_move(state, v)
    assert a.get_last_stats()["simulations"] == 150
    assert a.get_last_stats()["c_param"] == 0.7


def test_ai_stats_include_explanation_and_immediate_score():
    v = trie_validator(["PAN", "PANT"])
    for agent in (AlphaBetaAgent(depth=2, candidate_k=20), MCTSAgent(simulations=60, seed=1)):
        agent.select_move(pan_position(), v)
        stats = agent.get_last_stats()
        assert "immediate_score" in stats
        assert isinstance(stats["explanation"], str) and stats["explanation"]


# --------------------------------------------------------------------------- settings

def _settings(**kw):
    s = MatchSettings(**kw)
    return s


def test_default_settings_are_valid():
    assert MatchSettings().validate() == []


@pytest.mark.parametrize(
    "changes, fragment",
    [
        ({"board_size": 2}, "Board size"),
        ({"board_size": 4, "min_word_length": 5}, "Minimum word length"),
        ({"game_mode": MODE_REACH_GOAL_SCORE, "goal_score": 0}, "Target score"),
        ({"minimax_depth": 9}, "Minimax depth"),
        ({"mcts_iterations": 1}, "MCTS iterations"),
        ({"mcts_c": -1.0}, "exploration"),
        ({"seed": -4}, "seed"),
        ({"starting_player": 3}, "Starting player"),
    ],
)
def test_invalid_settings_are_reported(changes, fragment):
    errors = MatchSettings(**changes).validate()
    assert any(fragment.lower() in e.lower() for e in errors), errors


def test_match_type_must_match_player_controllers():
    s = MatchSettings(match_type=MATCH_HUMAN_VS_HUMAN)  # p2 defaults to an AI
    assert any("Human vs Human" in e for e in s.validate())
    s = MatchSettings(match_type=MATCH_AI_VS_AI)  # p1 defaults to human
    assert any("AI vs AI" in e for e in s.validate())
    s = MatchSettings(
        match_type=MATCH_HUMAN_VS_AI,
        p1=PlayerSettings("A", CONTROLLER_HUMAN),
        p2=PlayerSettings("A", CONTROLLER_MCTS),
    )
    assert any("different names" in e for e in s.validate())


def test_difficulty_presets_scale_search_parameters():
    depths = [DIFFICULTY_PRESETS[d]["minimax"]["depth"] for d in DIFFICULTIES]
    iters = [DIFFICULTY_PRESETS[d]["mcts"]["iterations"] for d in DIFFICULTIES]
    assert depths == sorted(depths) and depths[0] < depths[-1]
    assert iters == sorted(iters) and iters[0] < iters[-1]

    rules = GameRules()
    easy = MatchSettings(match_type=MATCH_AI_VS_AI,
                         p1=PlayerSettings("E", CONTROLLER_MINIMAX, "Easy"),
                         p2=PlayerSettings("X", CONTROLLER_MCTS, "Expert"))
    a1, a2 = easy.create_agent(1, rules), easy.create_agent(2, rules)
    assert a1.depth == DIFFICULTY_PRESETS["Easy"]["minimax"]["depth"]
    assert a2.simulations == DIFFICULTY_PRESETS["Expert"]["mcts"]["iterations"]
    assert a1.rules is rules and a2.rules is rules


def test_custom_difficulty_uses_advanced_settings():
    s = MatchSettings(
        match_type=MATCH_AI_VS_AI,
        p1=PlayerSettings("A", CONTROLLER_MINIMAX, DIFFICULTY_CUSTOM),
        p2=PlayerSettings("B", CONTROLLER_MCTS, DIFFICULTY_CUSTOM),
        minimax_depth=3, use_pruning=False, candidate_k=7,
        mcts_iterations=123, mcts_c=0.5, seed=9,
    )
    s.weights.opponent_future_potential = 1.7
    rules = GameRules()
    mm, mc = s.create_agent(1, rules), s.create_agent(2, rules)
    assert (mm.depth, mm.use_pruning, mm.candidate_k) == (3, False, 7)
    assert mm.evaluator.weights.opponent_future_potential == 1.7
    assert (mc.simulations, mc.c_param, mc.seed) == (123, 0.5, 11)
    assert s.create_agent(1, rules) is not mm
    assert MatchSettings().create_agent(1, rules) is None  # human
