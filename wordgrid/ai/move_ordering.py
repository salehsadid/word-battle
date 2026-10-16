from typing import List, Tuple
from wordgrid.game.state import GameState
from wordgrid.game.rules import Move
from wordgrid.game.scoring import WordValidatorProtocol, ScoringSystem


class MoveOrdering:
    """Prioritizes moves based on immediate scoring potential and prefix likelihood.
    
    Used to accelerate Alpha-Beta pruning cutoffs and guide MCTS rollouts.
    """

    def __init__(self, scoring_system: ScoringSystem):
        self.scoring = scoring_system

    def score_candidate_move(
        self,
        state: GameState,
        move: Move,
        validator: WordValidatorProtocol,
    ) -> float:
        """Estimates the immediate promise of placing letter at (r, c)."""
        r, c, ch = move
        board = state.board

        # Check adjacency to existing letters
        has_neighbor = False
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if board.is_valid_coord(nr, nc) and not board.is_empty(nr, nc):
                has_neighbor = True
                break

        # Simulate placement temporarily to check newly completed words and prefixes
        board.set(r, c, ch)
        try:
            move_score, _ = self.scoring.evaluate_move(
                board,
                r,
                c,
                validator,
                state.scored_occurrences,
                state.scored_words,
            )
            (h_word, _), (v_word, _) = self.scoring.inspect_sequences(board, r, c)

            prefix_bonus = 0.0
            if validator.is_valid_prefix(h_word):
                prefix_bonus += 0.25 * len(h_word)
            if validator.is_valid_prefix(v_word):
                prefix_bonus += 0.25 * len(v_word)

            priority = (move_score * 10.0) + prefix_bonus + (1.0 if has_neighbor else 0.0)
            return priority
        finally:
            board.clear_cell(r, c)

    def order_moves(
        self,
        state: GameState,
        moves: List[Move],
        validator: WordValidatorProtocol,
        top_k: int = 0,
    ) -> List[Move]:
        """Orders moves in descending order of promise.
        
        If top_k > 0, returns at most top_k moves. If top_k <= 0, returns all sorted moves.
        """
        if not moves:
            return []

        scored_moves: List[Tuple[float, Move]] = []
        for m in moves:
            p = self.score_candidate_move(state, m, validator)
            scored_moves.append((p, m))

        # Sort descending by estimated priority
        scored_moves.sort(key=lambda item: item[0], reverse=True)

        if top_k > 0:
            return [m for _, m in scored_moves[:top_k]]
        return [m for _, m in scored_moves]
