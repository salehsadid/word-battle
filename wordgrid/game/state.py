from typing import Dict, Set, Optional, List, Tuple
from wordgrid.game.board import Board
from wordgrid.game.scoring import OccurrenceKey
from wordgrid.config import (
    MODE_UNTIL_BOARD_FULL,
    MODE_REACH_GOAL_SCORE,
    MODE_MOVE_LIMIT,
)


class GameState:
    """Represents the complete game state for WordGrid.
    
    Contains all state necessary for authoritative game progression,
    undo/redo, and search simulation.
    """

    def __init__(
        self,
        board: Optional[Board] = None,
        board_size: int = 5,
        current_player: int = 1,
        scores: Optional[Dict[int, int]] = None,
        scored_occurrences: Optional[Set[OccurrenceKey]] = None,
        scored_words: Optional[Set[str]] = None,
        move_count: int = 0,
        game_mode: str = MODE_UNTIL_BOARD_FULL,
        goal_score: int = 30,
        move_limit: int = 20,
        is_terminal: bool = False,
        winner: Optional[int] = None,
        last_move: Optional[Tuple[int, int, str]] = None,
        last_scored_words: Optional[List[Tuple[str, int]]] = None,
        last_scored_occurrences: Optional[List[Tuple[str, int, OccurrenceKey]]] = None,
        last_blocked_words: Optional[List[str]] = None,
        starting_player: Optional[int] = None,
        end_reason: Optional[str] = None,
    ):
        self.board = board if board is not None else Board(size=board_size)
        self.current_player = current_player
        self.scores: Dict[int, int] = scores.copy() if scores is not None else {1: 0, 2: 0}
        self.scored_occurrences: Set[OccurrenceKey] = (
            scored_occurrences.copy() if scored_occurrences is not None else set()
        )
        self.scored_words: Set[str] = (
            scored_words.copy() if scored_words is not None else set()
        )
        self.move_count = move_count
        self.game_mode = game_mode
        self.goal_score = goal_score
        self.move_limit = move_limit
        self.is_terminal = is_terminal
        self.winner = winner  # 1, 2, 0 (draw), or None if game in progress
        self.last_move = last_move
        self.last_scored_words = last_scored_words[:] if last_scored_words is not None else []
        self.last_scored_occurrences = (
            last_scored_occurrences[:] if last_scored_occurrences is not None else []
        )
        self.last_blocked_words = last_blocked_words[:] if last_blocked_words is not None else []
        self.starting_player = starting_player if starting_player is not None else current_player
        self.end_reason = end_reason  # Why the match ended (see rules.END_* constants)

    @property
    def opponent_player(self) -> int:
        return 2 if self.current_player == 1 else 1

    def clone(self) -> "GameState":
        """Returns a fast, completely independent copy of the state."""
        return GameState(
            board=self.board.copy(),
            board_size=self.board.size,
            current_player=self.current_player,
            scores=self.scores,
            scored_occurrences=self.scored_occurrences,
            scored_words=self.scored_words,
            move_count=self.move_count,
            game_mode=self.game_mode,
            goal_score=self.goal_score,
            move_limit=self.move_limit,
            is_terminal=self.is_terminal,
            winner=self.winner,
            last_move=self.last_move,
            last_scored_words=self.last_scored_words,
            last_scored_occurrences=self.last_scored_occurrences,
            last_blocked_words=self.last_blocked_words,
            starting_player=self.starting_player,
            end_reason=self.end_reason,
        )

    def moves_made_by(self, player: int) -> int:
        """Number of moves the given player has made so far (players strictly alternate)."""
        first = (self.move_count + 1) // 2
        return first if player == self.starting_player else self.move_count - first

    @property
    def empty_cell_count(self) -> int:
        return sum(1 for row in self.board.grid for v in row if v is None)

    def get_score_difference(self, player: int) -> int:
        """Returns score difference from perspective of specified player."""
        opp = 2 if player == 1 else 1
        return self.scores.get(player, 0) - self.scores.get(opp, 0)

    def __repr__(self) -> str:
        status = f"Terminal (Winner: {self.winner})" if self.is_terminal else f"Turn: Player {self.current_player}"
        return (
            f"GameState(P1={self.scores.get(1, 0)}, P2={self.scores.get(2, 0)}, "
            f"Moves={self.move_count}, Mode={self.game_mode}, {status})\n"
            f"{self.board}"
        )
