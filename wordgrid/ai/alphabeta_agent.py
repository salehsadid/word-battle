import time
from typing import Optional, Tuple, List
from wordgrid.game.state import GameState
from wordgrid.game.rules import GameRules, Move
from wordgrid.game.scoring import WordValidatorProtocol
from wordgrid.ai.base_agent import BaseAgent
from wordgrid.ai.evaluation import HeuristicEvaluator
from wordgrid.ai.move_ordering import MoveOrdering
from wordgrid.ai.explain import describe_move


class AlphaBetaAgent(BaseAgent):
    """Heuristic Minimax with optional Alpha-Beta pruning and move ordering.

    Configuration:
      depth            - search horizon in plies.
      use_pruning      - Alpha-Beta pruning on/off (off = plain Minimax over the same tree).
      candidate_k      - consider only the k most promising moves per node (0 = all legal moves).
      evaluator        - HeuristicEvaluator carrying the heuristic weights.
    """

    def __init__(
        self,
        name: str = "AlphaBeta",
        depth: int = 2,
        evaluator: Optional[HeuristicEvaluator] = None,
        candidate_k: int = 0,
        use_move_ordering: bool = True,
        use_pruning: bool = True,
        explain: bool = True,
        rules: Optional[GameRules] = None,
    ):
        super().__init__(name, rules)
        self.depth = max(1, depth)
        self.evaluator = evaluator or HeuristicEvaluator()
        self.move_orderer = MoveOrdering(self.rules.scoring)
        self.evaluator.set_scoring(self.rules.scoring)
        self.candidate_k = candidate_k
        self.use_move_ordering = use_move_ordering
        self.use_pruning = use_pruning
        self.explain = explain
        self.nodes_visited = 0
        self.cutoffs = 0

    def bind_rules(self, rules: GameRules) -> None:
        super().bind_rules(rules)
        self.move_orderer.set_scoring(rules.scoring)
        self.evaluator.set_scoring(rules.scoring)

    def _candidates(self, state: GameState, validator: WordValidatorProtocol) -> List[Move]:
        legal_moves = self.rules.get_legal_moves(state)
        if self.use_move_ordering or self.candidate_k > 0:
            return self.move_orderer.order_moves(state, legal_moves, validator, top_k=self.candidate_k)
        return legal_moves

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

        if best_move is None:
            legal = self.rules.get_legal_moves(state)
            if legal:
                best_move = legal[0]
            else:
                raise RuntimeError("No legal moves available for AlphaBeta.")

        elapsed_time = time.perf_counter() - start_time

        self.last_stats = {
            "agent": self.name,
            "algorithm": "Minimax + Alpha-Beta" if self.use_pruning else "Minimax",
            "depth": self.depth,
            "candidate_k": self.candidate_k,
            "nodes_visited": self.nodes_visited,
            "cutoffs": self.cutoffs,
            "elapsed_time": elapsed_time,
            "best_score": best_score,
            "win_probability": HeuristicEvaluator.win_probability(best_score),
            "selected_move": best_move,
        }
        if self.explain:
            facts = describe_move(self.rules, state, best_move, validator)
            breadth = f"top {self.candidate_k}" if self.candidate_k > 0 else "all"
            if best_score >= HeuristicEvaluator.TERMINAL_WIN / 2:
                verdict = "forced win found"
            elif best_score <= HeuristicEvaluator.TERMINAL_LOSS / 2:
                verdict = "every line loses; best resistance"
            else:
                verdict = f"eval {best_score:+.1f}"
            facts["summary"] += (
                f" Chosen by {self.depth}-ply search over {breadth} moves per node ({verdict})."
            )
            self.last_stats.update(facts)
            self.last_stats["explanation"] = facts["summary"]
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

        ordered_moves = self._candidates(state, validator)
        if not ordered_moves:
            return self.evaluator.evaluate_heuristic(state, root_player, validator), None

        best_move: Optional[Move] = None

        if is_maximizing:
            max_eval = float("-inf")
            for move in ordered_moves:
                next_state = self.rules.apply_move(state, move, validator)
                eval_score, _ = self._alphabeta(
                    next_state, depth - 1, alpha, beta, False, root_player, validator
                )
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                if self.use_pruning:
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
                    next_state, depth - 1, alpha, beta, True, root_player, validator
                )
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                if self.use_pruning:
                    beta = min(beta, eval_score)
                    if beta <= alpha:
                        self.cutoffs += 1
                        break
            return min_eval, best_move
