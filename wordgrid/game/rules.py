import string
from typing import List, Tuple, Optional
from wordgrid.game.state import GameState
from wordgrid.game.scoring import ScoringSystem, WordValidatorProtocol, OccurrenceKey
from wordgrid.config import MODE_REACH_GOAL_SCORE, MODE_MOVE_LIMIT

Move = Tuple[int, int, str]  # (row, col, letter)
ALPHABET = list(string.ascii_uppercase)

END_TARGET_SCORE = "target score reached"
END_MOVE_LIMIT = "move limit reached"
END_BOARD_FULL = "board full"


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

        - Target score: the first player to reach goal_score wins immediately.
        - Move limit: ends once *each* player has made move_limit moves; highest score wins.
        - Full board (any mode): ends when no empty cells remain; highest score wins.
        Equal scores at the end are a draw.

        Returns:
            (is_terminal, winner) where winner is 1, 2, 0 (draw), or None if not terminal.
            The reason is stored on state.end_reason by the transition functions.
        """
        terminal, winner, _ = self._termination_details(state)
        return terminal, winner

    def _termination_details(self, state: GameState) -> Tuple[bool, Optional[int], Optional[str]]:
        if state.game_mode == MODE_REACH_GOAL_SCORE:
            reached = [p for p in (1, 2) if state.scores.get(p, 0) >= state.goal_score]
            if reached:
                # Only the mover gains points, so the mover is the first to reach the target.
                winner = state.current_player if state.current_player in reached else reached[0]
                return True, winner, END_TARGET_SCORE

        if state.game_mode == MODE_MOVE_LIMIT and state.move_count >= 2 * state.move_limit:
            return True, self._winner_by_score(state), END_MOVE_LIMIT

        if state.board.is_full():
            return True, self._winner_by_score(state), END_BOARD_FULL

        return False, None, None

    @staticmethod
    def _winner_by_score(state: GameState) -> int:
        p1_score = state.scores.get(1, 0)
        p2_score = state.scores.get(2, 0)
        if p1_score > p2_score:
            return 1
        if p2_score > p1_score:
            return 2
        return 0  # Draw

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
        blocked_words: List[str] = []
        move_score, new_words = self.scoring.evaluate_move(
            next_state.board,
            r,
            c,
            validator,
            next_state.scored_occurrences,
            next_state.scored_words,
            blocked_collector=blocked_words,
        )

        # Update scored occurrences and chosen words
        for word, _, occ_key in new_words:
            next_state.scored_occurrences.add(occ_key)
            next_state.scored_words.add(word)

        # Award points to current player
        current_p = next_state.current_player
        next_state.scores[current_p] = next_state.scores.get(current_p, 0) + move_score

        # Update metadata
        next_state.move_count += 1
        next_state.last_move = (r, c, ch)
        next_state.last_scored_words = [(word, length) for word, length, _ in new_words]
        next_state.last_scored_occurrences = new_words[:]
        next_state.last_blocked_words = blocked_words if not new_words else []

        # Check termination
        term, winner, reason = self._termination_details(next_state)
        next_state.is_terminal = term
        next_state.winner = winner
        next_state.end_reason = reason

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

        blocked_words: List[str] = []
        move_score, new_words = self.scoring.evaluate_move(
            state.board,
            r,
            c,
            validator,
            state.scored_occurrences,
            state.scored_words,
            blocked_collector=blocked_words,
        )

        for word, _, occ_key in new_words:
            state.scored_occurrences.add(occ_key)
            state.scored_words.add(word)

        prev_player = state.current_player
        state.scores[prev_player] += move_score
        state.move_count += 1
        state.last_move = (r, c, ch)
        state.last_scored_words = [(w, l) for w, l, _ in new_words]
        state.last_scored_occurrences = new_words[:]
        state.last_blocked_words = blocked_words if not new_words else []

        term, winner, reason = self._termination_details(state)
        state.is_terminal = term
        state.winner = winner
        state.end_reason = reason

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

        for word, _, occ_key in new_words:
            state.scored_occurrences.discard(occ_key)
            state.scored_words.discard(word)

        state.scores[prev_player] -= move_score
        state.move_count -= 1
        state.current_player = prev_player
        state.is_terminal = False
        state.winner = None
        state.end_reason = None
        state.last_move = prev_last_move
        state.last_scored_words = prev_last_scored
        state.last_scored_occurrences = []
        state.last_blocked_words = []
