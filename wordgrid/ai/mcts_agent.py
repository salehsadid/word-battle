import math
import random
import time
from typing import Optional, Dict, List, Tuple, Any
from wordgrid.game.state import GameState
from wordgrid.game.rules import GameRules, Move
from wordgrid.game.scoring import WordValidatorProtocol, ScoringSystem
from wordgrid.ai.base_agent import BaseAgent


class MCTSNode:
    """A node in the Monte Carlo Tree Search tree."""

    __slots__ = (
        "state",
        "parent",
        "move",
        "children",
        "untried_moves",
        "visits",
        "total_reward",
    )

    def __init__(
        self,
        state: GameState,
        parent: Optional["MCTSNode"] = None,
        move: Optional[Move] = None,
        untried_moves: Optional[List[Move]] = None,
    ):
        self.state = state
        self.parent = parent
        self.move = move
        self.children: Dict[Move, "MCTSNode"] = {}
        self.untried_moves = untried_moves if untried_moves is not None else []
        self.visits: int = 0
        self.total_reward: float = 0.0

    @property
    def q_value(self) -> float:
        """Returns average reward from root player's perspective."""
        return self.total_reward / self.visits if self.visits > 0 else 0.0

    def uct_value(self, c_param: float = 1.414) -> float:
        """Computes Upper Confidence Bound for Trees (UCT)."""
        if self.visits == 0:
            return float("inf")
        parent_visits = self.parent.visits if self.parent else self.visits
        exploitation = self.q_value
        exploration = c_param * math.sqrt(math.log(parent_visits) / self.visits)
        return exploitation + exploration

    def is_fully_expanded(self) -> bool:
        return len(self.untried_moves) == 0

    def is_terminal(self) -> bool:
        return self.state.is_terminal


class MCTSAgent(BaseAgent):
    """Monte Carlo Tree Search Agent using UCT selection, expansion, simulation, and backpropagation."""

    def __init__(
        self,
        name: str = "MCTS",
        simulations: int = 100,
        c_param: float = 1.414,
        max_rollout_depth: int = 8,
        seed: Optional[int] = None,
    ):
        super().__init__(name)
        self.simulations = simulations
        self.c_param = c_param
        self.max_rollout_depth = max_rollout_depth
        self.rng = random.Random(seed)
        self.rules = GameRules(ScoringSystem())

    def set_seed(self, seed: Optional[int]) -> None:
        self.rng = random.Random(seed)

    def select_move(self, state: GameState, validator: WordValidatorProtocol) -> Move:
        start_time = time.perf_counter()
        legal_moves = self.rules.get_legal_moves(state)
        if not legal_moves:
            raise RuntimeError("No legal moves available for MCTS.")

        if len(legal_moves) == 1:
            return legal_moves[0]

        root_player = state.current_player
        self.rng.shuffle(legal_moves)
        root = MCTSNode(state=state, untried_moves=legal_moves)

        # Run MCTS iterations
        for _ in range(self.simulations):
            # 1. Selection
            node = root
            while not node.is_terminal() and node.is_fully_expanded() and node.children:
                node = self._select_best_uct_child(node)

            # 2. Expansion
            if not node.is_terminal() and not node.is_fully_expanded():
                node = self._expand(node, validator)

            # 3. Simulation / Rollout
            reward = self._simulate(node.state, root_player, validator)

            # 4. Backpropagation
            self._backpropagate(node, reward)

        elapsed_time = time.perf_counter() - start_time

        # Best move: child with most visits (most robust)
        if not root.children:
            best_move = self.rng.choice(legal_moves)
            best_visits = 0
            best_q = 0.0
        else:
            best_child = max(root.children.values(), key=lambda c: c.visits)
            best_move = best_child.move
            best_visits = best_child.visits
            best_q = best_child.q_value

        self.last_stats = {
            "agent": self.name,
            "simulations": self.simulations,
            "root_visits": root.visits,
            "selected_move_visits": best_visits,
            "selected_move_q": best_q,
            "elapsed_time": elapsed_time,
            "selected_move": best_move,
        }
        return best_move

    def _select_best_uct_child(self, node: MCTSNode) -> MCTSNode:
        return max(node.children.values(), key=lambda c: c.uct_value(self.c_param))

    def _expand(self, node: MCTSNode, validator: WordValidatorProtocol) -> MCTSNode:
        move = node.untried_moves.pop()
        next_state = self.rules.apply_move(node.state, move, validator)
        legal_next = self.rules.get_legal_moves(next_state)
        self.rng.shuffle(legal_next)
        child = MCTSNode(
            state=next_state,
            parent=node,
            move=move,
            untried_moves=legal_next,
        )
        node.children[move] = child
        return child

    def _simulate(
        self,
        sim_state: GameState,
        root_player: int,
        validator: WordValidatorProtocol,
    ) -> float:
        """Rollout policy that balances random exploration with biased move selection."""
        curr = sim_state.clone()
        depth = 0

        while not curr.is_terminal and depth < self.max_rollout_depth:
            legal = self.rules.get_legal_moves(curr)
            if not legal:
                break

            # Semi-biased rollout: sample candidate moves and favor immediate scoring
            chosen = self._rollout_policy_choice(curr, legal, validator)
            curr = self.rules.apply_move(curr, chosen, validator)
            depth += 1

        # Calculate reward from root_player's perspective in [0.0, 1.0]
        return self._compute_reward(curr, root_player)

    def _rollout_policy_choice(
        self,
        state: GameState,
        legal_moves: List[Move],
        validator: WordValidatorProtocol,
    ) -> Move:
        """Selects move for rollout: prefers immediate scoring with high probability, else random."""
        # Check a random sample of moves to keep rollout fast
        sample_size = min(len(legal_moves), 6)
        sample = self.rng.sample(legal_moves, sample_size)

        scoring_moves = []
        for m in sample:
            r, c, ch = m
            state.board.set(r, c, ch)
            try:
                score, _ = self.rules.scoring.evaluate_move(
                    state.board, r, c, validator, state.scored_occurrences
                )
                if score > 0:
                    scoring_moves.append((score, m))
            finally:
                state.board.clear_cell(r, c)

        # 75% chance to pick scoring move if available
        if scoring_moves and self.rng.random() < 0.75:
            scoring_moves.sort(key=lambda item: item[0], reverse=True)
            return scoring_moves[0][1]

        return self.rng.choice(sample)

    def _compute_reward(self, final_state: GameState, root_player: int) -> float:
        """Computes reward scaled between 0.0 and 1.0 from root_player's perspective.
        
        Rewards:
          - Win: [0.7, 1.0] depending on score margin
          - Loss: [0.0, 0.3] depending on score margin
          - Draw: ~0.5
        """
        score_diff = final_state.get_score_difference(root_player)
        opponent = 2 if root_player == 1 else 1

        # Logistic-like margin bonus in [-0.2, 0.2]
        margin_bonus = math.tanh(score_diff / 8.0) * 0.2

        if final_state.winner == root_player:
            base = 0.8
        elif final_state.winner == opponent:
            base = 0.2
        else:
            base = 0.5

        reward = max(0.0, min(1.0, base + margin_bonus))
        return reward

    def _backpropagate(self, node: MCTSNode, reward: float) -> None:
        curr: Optional[MCTSNode] = node
        while curr is not None:
            curr.visits += 1
            curr.total_reward += reward
            curr = curr.parent
