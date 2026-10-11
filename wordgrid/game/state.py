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
        move_count: int = 0,
        game_mode: str = MODE_UNTIL_BOARD_FULL,
        goal_score: int = 30,
        move_limit: int = 20,
        is_terminal: bool = False,
        winner: Optional[int] = None,
        last_move: Optional[Tuple[int, int, str]] = None,
        last_scored_words: Optional[List[Tuple[str, int]]] = None,
    ):
        self.board = board if board is not None else Board(size=board_size)
        self.current_player = current_player
        self.scores: Dict[int, int] = scores.copy() if scores is not None else {1: 0, 2: 0}
        self.scored_occurrences: Set[OccurrenceKey] = (
            scored_occurrences.copy() if scored_occurrences is not None else set()
        )
        self.move_count = move_count
        self.game_mode = game_mode
        self.goal_score = goal_score
        self.move_limit = move_limit
        self.is_terminal = is_terminal
        self.winner = winner  # 1, 2, 0 (draw), or None if game in progress
        self.last_move = last_move
        self.last_scored_words = last_scored_words[:] if last_scored_words is not None else []

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
            move_count=self.move_count,
            game_mode=self.game_mode,
            goal_score=self.goal_score,
            move_limit=self.move_limit,
            is_terminal=self.is_terminal,
            winner=self.winner,
            last_move=self.last_move,
            last_scored_words=self.last_scored_words,
        )

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
