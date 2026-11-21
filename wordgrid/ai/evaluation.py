import math
from typing import Optional, Tuple, Dict
from wordgrid.game.state import GameState
from wordgrid.game.scoring import WordValidatorProtocol, ScoringSystem
from wordgrid.config import HeuristicWeights, MODE_REACH_GOAL_SCORE, MODE_MOVE_LIMIT
from wordgrid.ai.move_ordering import OpportunityScanner


# Configurable heuristic evaluation function for Minimax and Alpha-Beta.
#
# Features (all from the root player's perspective):
#   - score_diff: points already banked.
#   - own_future_potential: best points the root player can take on its next move
#     (only when the root player is the one to move).
#   - opponent_future_potential: best points the opponent can take on its next move
#     (the concrete *threat*, e.g. finishing PANT after we wrote PAN).
#   - playable_space_factor: the lead weighs more as the board fills up.
# Terminal states return a large win/loss value plus the final margin.
class HeuristicEvaluator:

    TERMINAL_WIN: float = 10000.0
    TERMINAL_LOSS: float = -10000.0
    TERMINAL_DRAW: float = 0.0

    # Set the feature weights and the scanner that finds next-move scores.
    def __init__(self, weights: Optional[HeuristicWeights] = None, scoring: Optional[ScoringSystem] = None):
        self.weights = weights or HeuristicWeights()
        self.scanner = OpportunityScanner(scoring or ScoringSystem())

    # Use a new scoring system (for example a different minimum word length).
    def set_scoring(self, scoring: ScoringSystem) -> None:
        self.scanner = OpportunityScanner(scoring)

    # Returns authoritative evaluation for terminal state.
    def evaluate_terminal(self, state: GameState, root_player: int) -> float:
        score_diff = float(state.get_score_difference(root_player))
        if state.winner == root_player:
            return self.TERMINAL_WIN + score_diff
        elif state.winner == (2 if root_player == 1 else 1):
            return self.TERMINAL_LOSS + score_diff
        else:
            return self.TERMINAL_DRAW + score_diff

    # Raw (unweighted) feature values, exposed for explanations and tests.
    def features(
        self,
        state: GameState,
        root_player: int,
        validator: WordValidatorProtocol,
    ) -> Dict[str, float]:
        board = state.board
        threat = float(self.scanner.best_immediate_score(state, validator))
        to_move_is_root = state.current_player == root_player

        total_cells = board.size * board.size
        horizon_ratio = state.empty_cell_count / total_cells

        return {
            "score_diff": float(state.get_score_difference(root_player)),
            "own_next": threat if to_move_is_root else 0.0,
            "opp_next": 0.0 if to_move_is_root else threat,
            "filled_ratio": 1.0 - horizon_ratio,
        }

    # Calculates depth-limited heuristic score from root_player's perspective.
    def evaluate_heuristic(
        self,
        state: GameState,
        root_player: int,
        validator: WordValidatorProtocol,
    ) -> float:
        if state.is_terminal:
            return self.evaluate_terminal(state, root_player)

        f = self.features(state, root_player, validator)
        w = self.weights
        score_diff = f["score_diff"]

        eval_score = (
            w.score_diff * score_diff
            + w.own_future_potential * f["own_next"]
            - w.opponent_future_potential * f["opp_next"]
            + w.playable_space_factor * score_diff * f["filled_ratio"]
        )

        # Termination-aware urgency: being one move from the target is close to a win.
        if state.game_mode == MODE_REACH_GOAL_SCORE and state.goal_score > 0:
            opp = 2 if root_player == 1 else 1
            mine = state.scores.get(root_player, 0)
            theirs = state.scores.get(opp, 0)
            eval_score += 2.0 * (mine - theirs) / state.goal_score * max(mine, theirs) / state.goal_score
            if not (state.current_player == root_player) and theirs + f["opp_next"] >= state.goal_score:
                eval_score -= 50.0
            if state.current_player == root_player and mine + f["own_next"] >= state.goal_score:
                eval_score += 50.0
        elif state.game_mode == MODE_MOVE_LIMIT:
            remaining = max(0, 2 * state.move_limit - state.move_count)
            eval_score += w.playable_space_factor * score_diff * (1.0 / (1 + remaining))

        return eval_score

    # Maps an evaluation to an approximate win probability for display.
    @staticmethod
    def win_probability(eval_score: float) -> float:
        if eval_score >= HeuristicEvaluator.TERMINAL_WIN / 2:
            return 1.0
        if eval_score <= HeuristicEvaluator.TERMINAL_LOSS / 2:
            return 0.0
        return 1.0 / (1.0 + math.exp(-eval_score / 4.0))
