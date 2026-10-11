import time
from typing import Optional, Tuple, Dict, Any, List
from wordgrid.game.state import GameState
from wordgrid.game.rules import GameRules, Move
from wordgrid.game.scoring import WordValidatorProtocol, ScoringSystem
from wordgrid.ai.base_agent import BaseAgent
from wordgrid.ai.evaluation import HeuristicEvaluator
from wordgrid.ai.move_ordering import MoveOrdering


class AlphaBetaAgent(BaseAgent):
    """Depth-limited Minimax Agent with Alpha-Beta Pruning and Move Ordering."""

    def __init__(
        self,
        name: str = "AlphaBeta",
        depth: int = 2,
        evaluator: Optional[HeuristicEvaluator] = None,
        candidate_k: int = 0,
        use_move_ordering: bool = True,
    ):
        super().__init__(name)
        self.depth = depth
        self.evaluator = evaluator or HeuristicEvaluator()
        self.rules = GameRules(ScoringSystem())
        self.move_orderer = MoveOrdering(self.rules.scoring)
        self.candidate_k = candidate_k
        self.use_move_ordering = use_move_ordering
        self.nodes_visited = 0
        self.cutoffs = 0

    def select_move(self, state: GameState, validator: WordValidatorProtocol) -> Move:
        start_time = time.perf_counter()
        self.nodes_visited = 0
        self.cutoffs = 0
        root_player = state.current_player

        best_score, best_move = self._alphabeta(
            state=state,
            depth=self.depth,
            alpha=float("-inf"),
            beta=float("inf"),
            is_maximizing=True,
            root_player=root_player,
            validator=validator,
        )

        elapsed_time = time.perf_counter() - start_time

        if best_move is None:
            legal = self.rules.get_legal_moves(state)
            if legal:
                best_move = legal[0]
            else:
                raise RuntimeError("No legal moves available for AlphaBeta.")

        self.last_stats = {
            "agent": self.name,
            "depth": self.depth,
            "nodes_visited": self.nodes_visited,
            "cutoffs": self.cutoffs,
            "elapsed_time": elapsed_time,
            "best_score": best_score,
            "selected_move": best_move,
        }
        return best_move

    def _alphabeta(
        self,
        state: GameState,
        depth: int,
        alpha: float,
        beta: float,
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

        # Order moves if enabled
        if self.use_move_ordering:
            ordered_moves = self.move_orderer.order_moves(
                state, legal_moves, validator, top_k=self.candidate_k
            )
        else:
            ordered_moves = legal_moves

        best_move: Optional[Move] = None

        if is_maximizing:
            max_eval = float("-inf")
            for move in ordered_moves:
                next_state = self.rules.apply_move(state, move, validator)
                eval_score, _ = self._alphabeta(
                    state=next_state,
                    depth=depth - 1,
                    alpha=alpha,
                    beta=beta,
                    is_maximizing=False,
                    root_player=root_player,
                    validator=validator,
                )
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    self.cutoffs += 1
                    break
            return max_eval, best_move
        else:
            min_eval = float("inf")
            for move in ordered_moves:
                next_state = self.rules.apply_move(state, move, validator)
                eval_score, _ = self._alphabeta(
                    state=next_state,
                    depth=depth - 1,
                    alpha=alpha,
                    beta=beta,
                    is_maximizing=True,
                    root_player=root_player,
                    validator=validator,
                )
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                beta = min(beta, eval_score)
                if beta <= alpha:
                    self.cutoffs += 1
                    break
            return min_eval, best_move
