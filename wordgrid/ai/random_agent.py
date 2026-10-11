import random
import time
from typing import Optional
from wordgrid.game.state import GameState
from wordgrid.game.rules import GameRules, Move
from wordgrid.game.scoring import WordValidatorProtocol
from wordgrid.ai.base_agent import BaseAgent


class RandomAgent(BaseAgent):
    """Baseline agent that chooses uniformly at random among all legal moves."""

    def __init__(self, name: str = "Random", seed: Optional[int] = None):
        super().__init__(name)
        self.rng = random.Random(seed)
        self.rules = GameRules()

    def set_seed(self, seed: Optional[int]) -> None:
        self.rng = random.Random(seed)

    def select_move(self, state: GameState, validator: WordValidatorProtocol) -> Move:
        start_time = time.perf_counter()
        legal_moves = self.rules.get_legal_moves(state)
        if not legal_moves:
            raise RuntimeError("No legal moves available for RandomAgent.")

        chosen_move = self.rng.choice(legal_moves)
        elapsed_time = time.perf_counter() - start_time

        self.last_stats = {
            "agent": self.name,
            "legal_moves_count": len(legal_moves),
            "elapsed_time": elapsed_time,
            "selected_move": chosen_move,
        }
        return chosen_move
