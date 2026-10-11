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
            (h_word, h_key), (v_word, v_key) = self.scoring.inspect_sequences(board, r, c)
            move_score = 0
            if len(h_word) >= self.scoring.min_word_length and h_key not in state.scored_occurrences:
                if validator.is_valid_word(h_word):
                    move_score = max(move_score, len(h_word))

            if len(v_word) >= self.scoring.min_word_length and v_key not in state.scored_occurrences:
                if validator.is_valid_word(v_word):
                    move_score = max(move_score, len(v_word))

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
