import math
from typing import Optional, Tuple, Dict
from wordgrid.game.state import GameState
from wordgrid.game.scoring import WordValidatorProtocol, ScoringSystem
from wordgrid.config import HeuristicWeights, MODE_REACH_GOAL_SCORE, MODE_MOVE_LIMIT
from wordgrid.ai.move_ordering import OpportunityScanner


class HeuristicEvaluator:
    """Configurable heuristic evaluation function for Minimax and Alpha-Beta.

    Features (all from the root player's perspective):
      - score_diff: points already banked.
      - own_future_potential: best points the root player can take on its next move
        (only when the root player is the one to move).
      - opponent_future_potential: best points the opponent can take on its next move
        (the concrete *threat*, e.g. finishing PANT after we wrote PAN).
      - partial_sequence_bonus: open letter runs that are dictionary prefixes (longer-term potential).
      - playable_space_factor: the lead weighs more as the board fills up.
    Terminal states return a large win/loss value plus the final margin.
    """

    TERMINAL_WIN: float = 10000.0
    TERMINAL_LOSS: float = -10000.0
    TERMINAL_DRAW: float = 0.0

    def __init__(self, weights: Optional[HeuristicWeights] = None, scoring: Optional[ScoringSystem] = None):
        self.weights = weights or HeuristicWeights()
        self.scanner = OpportunityScanner(scoring or ScoringSystem())

    def set_scoring(self, scoring: ScoringSystem) -> None:
        self.scanner = OpportunityScanner(scoring)

    def evaluate_terminal(self, state: GameState, root_player: int) -> float:
        """Returns authoritative evaluation for terminal state."""
        score_diff = float(state.get_score_difference(root_player))
        if state.winner == root_player:
            return self.TERMINAL_WIN + score_diff
        elif state.winner == (2 if root_player == 1 else 1):
            return self.TERMINAL_LOSS + score_diff
        else:
            return self.TERMINAL_DRAW + score_diff

    def estimate_line_potentials(
        self,
        line: list,
        validator: WordValidatorProtocol,
    ) -> Tuple[float, float]:
        """Estimates incomplete sequence potential along a 1D line of board cells.

        A run counts when it can still grow (an adjacent empty cell) and it is a dictionary
        prefix in either reading direction.

        Returns:
            (promising_prefix_potential, partial_sequence_count)
        """
        has_prefix = hasattr(validator, "is_valid_prefix")
        if not has_prefix:
            return 0.0, 0.0
        n = len(line)
        potential = 0.0
        partial_count = 0.0

        i = 0
        while i < n:
            if line[i] is not None:
                start = i
                while i < n and line[i] is not None:
                    i += 1
                end = i
                seq = "".join(line[start:end])
                k = len(seq)
                open_after = end < n and line[end] is None
                open_before = start > 0 and line[start - 1] is None
                fwd = open_after and validator.is_valid_prefix(seq)
                rev = open_before and validator.is_valid_prefix(seq[::-1])
                if fwd or rev:
                    potential += (k + (1 if fwd else 0) + (1 if rev else 0)) * 0.25
                    partial_count += 1.0
            else:
                i += 1

        return potential, partial_count

    def features(
        self,
        state: GameState,
        root_player: int,
        validator: WordValidatorProtocol,
    ) -> Dict[str, float]:
        """Raw (unweighted) feature values, exposed for explanations and tests."""
        board = state.board
        total_potential = 0.0
        total_partials = 0.0
        for r in range(board.size):
            p, count = self.estimate_line_potentials(board.grid[r], validator)
            total_potential += p
            total_partials += count
        for c in range(board.size):
            p, count = self.estimate_line_potentials([board.grid[r][c] for r in range(board.size)], validator)
            total_potential += p
            total_partials += count

        threat = float(self.scanner.best_immediate_score(state, validator))
        to_move_is_root = state.current_player == root_player

        total_cells = board.size * board.size
        horizon_ratio = state.empty_cell_count / total_cells

        return {
            "score_diff": float(state.get_score_difference(root_player)),
            "own_next": threat if to_move_is_root else 0.0,
            "opp_next": 0.0 if to_move_is_root else threat,
            "prefix_potential": total_potential if to_move_is_root else -total_potential,
            "partials": total_partials,
            "filled_ratio": 1.0 - horizon_ratio,
        }

    def evaluate_heuristic(
        self,
        state: GameState,
        root_player: int,
        validator: WordValidatorProtocol,
    ) -> float:
        """Calculates depth-limited heuristic score from root_player's perspective."""
        if state.is_terminal:
            return self.evaluate_terminal(state, root_player)

        f = self.features(state, root_player, validator)
        w = self.weights
        score_diff = f["score_diff"]

        eval_score = (
            w.score_diff * score_diff
            + w.own_future_potential * f["own_next"]
            - w.opponent_future_potential * f["opp_next"]
            + w.partial_sequence_bonus * 0.5 * f["prefix_potential"]
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

    @staticmethod
    def win_probability(eval_score: float) -> float:
        """Maps an evaluation to an approximate win probability for display."""
        if eval_score >= HeuristicEvaluator.TERMINAL_WIN / 2:
            return 1.0
        if eval_score <= HeuristicEvaluator.TERMINAL_LOSS / 2:
            return 0.0
        return 1.0 / (1.0 + math.exp(-eval_score / 4.0))
