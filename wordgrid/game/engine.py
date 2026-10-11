from typing import Optional, List, Tuple
from wordgrid.game.state import GameState
from wordgrid.game.rules import GameRules, Move
from wordgrid.game.scoring import ScoringSystem, WordValidatorProtocol
from wordgrid.config import (
    GameConfig,
    MODE_UNTIL_BOARD_FULL,
)


class GameEngine:
    """Authoritative game coordinator for WordGrid.
    
    Serves as the single source of truth for match progress, move validation,
    scoring, and history tracking.
    """

    def __init__(
        self,
        validator: WordValidatorProtocol,
        config: Optional[GameConfig] = None,
        rules: Optional[GameRules] = None,
    ):
        self.validator = validator
        self.config = config or GameConfig()
        self.rules = rules or GameRules(scoring_system=ScoringSystem(self.config.min_word_length))
        self.history: List[GameState] = []
        self.state = self._create_initial_state()

    def _create_initial_state(self) -> GameState:
        return GameState(
            board_size=self.config.board_size,
            current_player=1,
            game_mode=self.config.game_mode,
            goal_score=self.config.goal_score,
            move_limit=self.config.move_limit,
        )

    def reset(self, config: Optional[GameConfig] = None) -> GameState:
        """Resets the engine to a new game with the given or current configuration."""
        if config is not None:
            self.config = config
            self.rules = GameRules(scoring_system=ScoringSystem(self.config.min_word_length))
        self.history.clear()
        self.state = self._create_initial_state()
        return self.state

    def make_move(self, move: Move) -> GameState:
        """Validates and applies a move to the current match state."""
        if self.state.is_terminal:
            raise RuntimeError("Cannot make move in a finished game.")

        # Save snapshot to history
        self.history.append(self.state.clone())

        # Apply move via rules
        self.state = self.rules.apply_move(self.state, move, self.validator)
        return self.state

    def undo_last_move(self) -> Optional[GameState]:
        """Rolls back the last move if available in history."""
        if not self.history:
            return None
        self.state = self.history.pop()
        return self.state

    def get_legal_moves(self) -> List[Move]:
        """Returns all legal moves for current state."""
        return self.rules.get_legal_moves(self.state)

    @property
    def is_game_over(self) -> bool:
        return self.state.is_terminal

    @property
    def winner(self) -> Optional[int]:
        return self.state.winner
