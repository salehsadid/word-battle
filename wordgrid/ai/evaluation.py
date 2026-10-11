from typing import Optional, Tuple
from wordgrid.game.state import GameState
from wordgrid.game.scoring import WordValidatorProtocol
from wordgrid.config import HeuristicWeights


class HeuristicEvaluator:
    """Configurable heuristic evaluation function for Minimax and Alpha-Beta.
    
    Considers:
      - Current score difference from the root player's perspective.
      - Potential future scoring opportunities for the root player.
      - Potential future scoring opportunities for the opponent.
      - Promising incomplete letter sequences (valid prefixes).
      - Remaining playable space and game horizon.
    """

    TERMINAL_WIN: float = 10000.0
    TERMINAL_LOSS: float = -10000.0
    TERMINAL_DRAW: float = 0.0

    def __init__(self, weights: Optional[HeuristicWeights] = None):
        self.weights = weights or HeuristicWeights()

    def evaluate_terminal(self, state: GameState, root_player: int) -> float:
        """Returns authoritative evaluation for terminal state."""
        score_diff = float(state.get_score_difference(root_player))
        if state.winner == root_player:
            return self.TERMINAL_WIN + score_diff
        elif state.winner == (2 if root_player == 1 else 1):
            return self.TERMINAL_LOSS + score_diff
        else:
            # Draw
            return self.TERMINAL_DRAW + score_diff

    def estimate_line_potentials(
        self,
        line: list,
        validator: WordValidatorProtocol,
    ) -> Tuple[float, float]:
        """Estimates incomplete sequence potential along a 1D line of board cells.
        
        Returns:
            (promising_prefix_potential, partial_sequence_count)
        """
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

                # Check if this contiguous sequence is a valid prefix
                if validator.is_valid_prefix(seq):
                    empty_adj = 0
                    if start > 0 and line[start - 1] is None:
                        empty_adj += 1
                    if end < n and line[end] is None:
                        empty_adj += 1

                    if empty_adj > 0:
                        # Future scoring estimate: length bonus discounted by probability
                        est_gain = (k + min(empty_adj, 2)) * 0.25
                        potential += est_gain
                        partial_count += 1.0
            else:
                i += 1

        return potential, partial_count

    def evaluate_heuristic(
        self,
        state: GameState,
        root_player: int,
        validator: WordValidatorProtocol,
    ) -> float:
        """Calculates depth-limited heuristic score from root_player's perspective."""
        if state.is_terminal:
            return self.evaluate_terminal(state, root_player)

        score_diff = float(state.get_score_difference(root_player))

        # Inspect horizontal and vertical lines for promising partial sequences
        board = state.board
        total_potential = 0.0
        total_partials = 0.0

        for r in range(board.size):
            h_line = [board.get(r, c) for c in range(board.size)]
            p, count = self.estimate_line_potentials(h_line, validator)
            total_potential += p
            total_partials += count

        for c in range(board.size):
            v_line = [board.get(r, c) for r in range(board.size)]
            p, count = self.estimate_line_potentials(v_line, validator)
            total_potential += p
            total_partials += count

        # Turn advantage: the player whose turn it is next has initiative to complete sequences
        if state.current_player == root_player:
            own_future = total_potential * 0.65
            opp_future = total_potential * 0.35
        else:
            own_future = total_potential * 0.35
            opp_future = total_potential * 0.65

        # Playable space / game horizon:
        total_cells = board.size * board.size
        empty_cells = len(board.get_empty_cells())
        horizon_ratio = empty_cells / total_cells

        # Weighted combination
        eval_score = (
            self.weights.score_diff * score_diff
            + self.weights.own_future_potential * own_future
            - self.weights.opponent_future_potential * opp_future
            + self.weights.partial_sequence_bonus * total_partials
            + self.weights.playable_space_factor * (score_diff * (1.0 - horizon_ratio))
        )

        return eval_score
