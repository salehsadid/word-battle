import string
from typing import List, Tuple, Optional, Set
from wordgrid.game.state import GameState
from wordgrid.game.scoring import ScoringSystem, WordValidatorProtocol, OccurrenceKey
from wordgrid.config import (
    MODE_UNTIL_BOARD_FULL,
    MODE_REACH_GOAL_SCORE,
    MODE_MOVE_LIMIT,
)

Move = Tuple[int, int, str]  # (row, col, letter)
ALPHABET = list(string.ascii_uppercase)


class GameRules:
    """Implements authoritative rules, legal moves, state transitions, and termination checks."""

    def __init__(self, scoring_system: Optional[ScoringSystem] = None):
        self.scoring = scoring_system or ScoringSystem()

    def get_legal_moves(self, state: GameState) -> List[Move]:
        """Generates all legal moves for the current state.
        
        If the game is over, returns an empty list.
        Otherwise returns every (row, col, letter) where (row, col) is empty and letter in A-Z.
        """
        if state.is_terminal:
            return []

        empty_cells = state.board.get_empty_cells()
        moves = []
        for r, c in empty_cells:
            for ch in ALPHABET:
                moves.append((r, c, ch))
        return moves

    def is_legal_move(self, state: GameState, move: Move) -> bool:
        """Validates if a move is legal in the current state."""
        if state.is_terminal:
            return False
        r, c, ch = move
        if not state.board.is_valid_coord(r, c):
            return False
        if not state.board.is_empty(r, c):
            return False
        if not (isinstance(ch, str) and len(ch) == 1 and ch.upper() in string.ascii_uppercase):
            return False
        return True

    def check_termination(self, state: GameState) -> Tuple[bool, Optional[int]]:
        """Checks if state has reached a terminal condition based on game_mode.
        
        Returns:
            (is_terminal: bool, winner: Optional[int])
            Winner is 1, 2, 0 (draw), or None if game is not terminal.
        """
        is_terminal = False

        if state.board.is_full():
            is_terminal = True
        elif state.game_mode == MODE_REACH_GOAL_SCORE:
            if state.scores[1] >= state.goal_score or state.scores[2] >= state.goal_score:
                is_terminal = True
        elif state.game_mode == MODE_MOVE_LIMIT:
            if state.move_count >= state.move_limit:
                is_terminal = True

        if not is_terminal:
            return False, None

        # Determine winner
        p1_score = state.scores.get(1, 0)
        p2_score = state.scores.get(2, 0)
        if p1_score > p2_score:
            winner = 1
        elif p2_score > p1_score:
            winner = 2
        else:
            winner = 0  # Draw

        return True, winner

    def apply_move(
        self,
        state: GameState,
        move: Move,
        validator: WordValidatorProtocol,
    ) -> GameState:
        """Applies a legal move to a state and returns a new simulated/transitioned GameState.
        
        Leaves the input state unmodified.
        """
        r, c, ch = move
        ch = ch.upper()
        if not self.is_legal_move(state, (r, c, ch)):
            raise ValueError(f"Illegal move {move} for state.")

        next_state = state.clone()
        next_state.board.set(r, c, ch)

        # Evaluate scoring
        move_score, new_words = self.scoring.evaluate_move(
            next_state.board,
            r,
            c,
            validator,
            next_state.scored_occurrences,
        )

        # Update scored occurrences
        for _, _, occ_key in new_words:
            next_state.scored_occurrences.add(occ_key)

        # Award points to current player
        current_p = next_state.current_player
        next_state.scores[current_p] = next_state.scores.get(current_p, 0) + move_score

        # Update metadata
        next_state.move_count += 1
        next_state.last_move = (r, c, ch)
        next_state.last_scored_words = [(word, length) for word, length, _ in new_words]

        # Check termination
        term, winner = self.check_termination(next_state)
        next_state.is_terminal = term
        next_state.winner = winner

        if not term:
            next_state.current_player = next_state.opponent_player

        return next_state

    def apply_move_inplace(
        self,
        state: GameState,
        move: Move,
        validator: WordValidatorProtocol,
    ) -> Tuple[int, List[Tuple[str, int, OccurrenceKey]], int]:
        """Applies move in place to state for performance-critical search when undo is needed.
        
        Returns:
            (move_score, new_words, previous_player)
        """
        r, c, ch = move
        ch = ch.upper()
        state.board.set(r, c, ch)

        move_score, new_words = self.scoring.evaluate_move(
            state.board,
            r,
            c,
            validator,
            state.scored_occurrences,
        )

        for _, _, occ_key in new_words:
            state.scored_occurrences.add(occ_key)

        prev_player = state.current_player
        state.scores[prev_player] += move_score
        state.move_count += 1
        state.last_move = (r, c, ch)
        state.last_scored_words = [(w, l) for w, l, _ in new_words]

        term, winner = self.check_termination(state)
        state.is_terminal = term
        state.winner = winner

        if not term:
            state.current_player = 2 if prev_player == 1 else 1

        return move_score, new_words, prev_player

    def undo_move_inplace(
        self,
        state: GameState,
        move: Move,
        move_score: int,
        new_words: List[Tuple[str, int, OccurrenceKey]],
        prev_player: int,
        prev_last_move: Optional[Move],
        prev_last_scored: List[Tuple[str, int]],
    ) -> None:
        """Reverts in-place move application."""
        r, c, _ = move
        state.board.clear_cell(r, c)

        for _, _, occ_key in new_words:
            state.scored_occurrences.discard(occ_key)

        state.scores[prev_player] -= move_score
        state.move_count -= 1
        state.current_player = prev_player
        state.is_terminal = False
        state.winner = None
        state.last_move = prev_last_move
        state.last_scored_words = prev_last_scored
