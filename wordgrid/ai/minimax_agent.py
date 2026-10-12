import time
from typing import Optional, Tuple, Dict, Any, List
from wordgrid.game.state import GameState
from wordgrid.game.rules import GameRules, Move
from wordgrid.game.scoring import WordValidatorProtocol, ScoringSystem
from wordgrid.ai.base_agent import BaseAgent
from wordgrid.ai.evaluation import HeuristicEvaluator


class MinimaxAgent(BaseAgent):
    """Depth-limited Minimax Agent with heuristic evaluation."""

    def __init__(
        self,
        name: str = "Minimax",
        depth: int = 2,
        evaluator: Optional[HeuristicEvaluator] = None,
        candidate_k: int = 0,
    ):
        super().__init__(name)
        self.depth = depth
        self.evaluator = evaluator or HeuristicEvaluator()
        self.rules = GameRules(ScoringSystem())
        self.candidate_k = candidate_k
        self.nodes_visited = 0

    def select_move(self, state: GameState, validator: WordValidatorProtocol) -> Move:
        start_time = time.perf_counter()
        self.nodes_visited = 0
        root_player = state.current_player

        best_score, best_move = self._minimax(
            state=state,
            depth=self.depth,
            is_maximizing=True,
            root_player=root_player,
            validator=validator,
        )

        elapsed_time = time.perf_counter() - start_time

        if best_move is None:
            # Fallback to any legal move if available
            legal = self.rules.get_legal_moves(state)
            if legal:
                best_move = legal[0]
            else:
                raise RuntimeError("No legal moves available for Minimax.")

        self.last_stats = {
            "agent": self.name,
            "depth": self.depth,
            "nodes_visited": self.nodes_visited,
            "elapsed_time": elapsed_time,
            "best_score": best_score,
            "selected_move": best_move,
        }
        return best_move

    def _minimax(
        self,
        state: GameState,
        depth: int,
        is_maximizing: bool,
        root_player: int,
        validator: WordValidatorProtocol,
    ) -> Tuple[float, Optional[Move]]:
        self.nodes_visited += 1

        if depth == 0 or state.is_terminal:
            return self.evaluator.evaluate_heuristic(state, root_player, validator), None

        legal_moves = self.rules.get_legal_moves(state)
        if not legal_moves:
            return self.evaluator.evaluate_heuristic(state, root_player, validator), None

        best_move: Optional[Move] = None

        if is_maximizing:
            max_eval = float("-inf")
            for move in legal_moves:
                next_state = self.rules.apply_move(state, move, validator)
                eval_score, _ = self._minimax(
                    state=next_state,
                    depth=depth - 1,
                    is_maximizing=False,
                    root_player=root_player,
                    validator=validator,
                )
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
            return max_eval, best_move
        else:
            min_eval = float("inf")
            for move in legal_moves:
                next_state = self.rules.apply_move(state, move, validator)
                eval_score, _ = self._minimax(
                    state=next_state,
                    depth=depth - 1,
                    is_maximizing=True,
                    root_player=root_player,
                    validator=validator,
                )
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
            return min_eval, best_move
