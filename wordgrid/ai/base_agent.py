from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from wordgrid.game.state import GameState
from wordgrid.game.rules import GameRules, Move
from wordgrid.game.scoring import WordValidatorProtocol


# Abstract base class for all WordGrid AI agents.
#
# Every agent simulates the game with a GameRules instance. Call bind_rules() with the engine's rules so search uses
# the exact same scoring configuration as the real match.
class BaseAgent(ABC):

    # Store the agent's name and rules, and start with empty stats.
    def __init__(self, name: str, rules: Optional[GameRules] = None):
        self.name = name
        self.rules = rules or GameRules()
        self.last_stats: Dict[str, Any] = {}

    # Shares the authoritative rules (and scoring settings) of the engine with this agent.
    def bind_rules(self, rules: GameRules) -> None:
        self.rules = rules

    # Selects a legal move for the current game state without mutating it.
    @abstractmethod
    def select_move(self, state: GameState, validator: WordValidatorProtocol) -> Move:
        pass

    # Returns performance metrics from the most recent move search.
    def get_last_stats(self) -> Dict[str, Any]:
        return self.last_stats.copy()

    # Show the agent by its name.
    def __str__(self) -> str:
        return self.name
