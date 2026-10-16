from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from wordgrid.game.state import GameState
from wordgrid.game.rules import GameRules, Move
from wordgrid.game.scoring import WordValidatorProtocol


class BaseAgent(ABC):
    """Abstract base class for all WordGrid AI agents.

    Every agent simulates the game with a GameRules instance. Call bind_rules() with the
    engine's rules so search uses the exact same scoring configuration as the real match.
    """

    def __init__(self, name: str, rules: Optional[GameRules] = None):
        self.name = name
        self.rules = rules or GameRules()
        self.last_stats: Dict[str, Any] = {}

    def bind_rules(self, rules: GameRules) -> None:
        """Shares the authoritative rules (and scoring settings) of the engine with this agent."""
        self.rules = rules

    @abstractmethod
    def select_move(self, state: GameState, validator: WordValidatorProtocol) -> Move:
        """Selects a legal move for the current game state without mutating it."""
        pass

    def get_last_stats(self) -> Dict[str, Any]:
        """Returns performance metrics from the most recent move search."""
        return self.last_stats.copy()

    def __str__(self) -> str:
        return self.name
