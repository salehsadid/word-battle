import math
import random
import time
from typing import Optional, Dict, List, Tuple, Any
from wordgrid.game.state import GameState
from wordgrid.game.rules import GameRules, Move, ALPHABET
from wordgrid.game.scoring import WordValidatorProtocol
from wordgrid.ai.base_agent import BaseAgent
from wordgrid.ai.move_ordering import MoveOrdering
from wordgrid.ai.explain import describe_move


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
    """Monte Carlo Tree Search Agent using UCT selection, expansion, simulation, and backpropagation.

    Rewards are stored from the root player's perspective in [0, 1]. During selection, a node
    whose player to move is the opponent picks the child maximising (1 - Q), so the tree models
    an opponent who plays to win rather than one who cooperates.

    Configuration:
      simulations       - number of MCTS iterations per move.
      c_param           - UCT exploration constant.
      max_rollout_depth - plies simulated before the position is scored.
      max_children      - expand at most this many children per node, chosen by the shared
                          move ordering (0 = every legal move).
      time_limit        - optional cap in seconds (0 = none); stops iterating early.
      seed              - random seed for reproducible play (None = random).
    """

    def __init__(
        self,
        name: str = "MCTS",
        simulations: int = 100,
        c_param: float = 1.414,
        max_rollout_depth: int = 8,
        seed: Optional[int] = None,
        max_children: int = 24,
        time_limit: float = 0.0,
        explain: bool = True,
        rules: Optional[GameRules] = None,
    ):
        super().__init__(name, rules)
        self.simulations = max(1, simulations)
        self.c_param = c_param
        self.max_rollout_depth = max_rollout_depth
        self.max_children = max_children
        self.time_limit = time_limit
        self.explain = explain
        self.seed = seed
        self.rng = random.Random(seed)
        self.move_orderer = MoveOrdering(self.rules.scoring)

    def bind_rules(self, rules: GameRules) -> None:
        super().bind_rules(rules)
        self.move_orderer.set_scoring(rules.scoring)

    def set_seed(self, seed: Optional[int]) -> None:
        self.seed = seed
        self.rng = random.Random(seed)

    def _expansion_order(self, state: GameState, validator: WordValidatorProtocol) -> List[Move]:
        """Candidate moves for a node, most promising LAST (they are popped from the end)."""
        legal = self.rules.get_legal_moves(state)
        if not legal:
            return []
        if self.max_children > 0 and len(legal) > self.max_children:
            ordered = self.move_orderer.order_moves(state, legal, validator, top_k=self.max_children)
        else:
            self.rng.shuffle(legal)
            ordered = self.move_orderer.order_moves(state, legal, validator)
        ordered.reverse()
        return ordered

    def select_move(self, state: GameState, validator: WordValidatorProtocol) -> Move:
        start_time = time.perf_counter()
        legal_moves = self.rules.get_legal_moves(state)
        if not legal_moves:
            raise RuntimeError("No legal moves available for MCTS.")

        if len(legal_moves) == 1:
            return legal_moves[0]

        root_player = state.current_player
        root = MCTSNode(state=state, untried_moves=self._expansion_order(state, validator))

        # Run MCTS iterations
        iterations_done = 0
        for _ in range(self.simulations):
            if self.time_limit > 0 and iterations_done and time.perf_counter() - start_time > self.time_limit:
                break
            iterations_done += 1
            # 1. Selection
            node = root
            while not node.is_terminal() and node.is_fully_expanded() and node.children:
                node = self._select_best_uct_child(node, root_player)

            # 2. Expansion
            if not node.is_terminal() and not node.is_fully_expanded():
                node = self._expand(node, validator)

            # 3. Simulation / Rollout
            reward = self._simulate(node.state, root_player, validator)

            # 4. Backpropagation
            self._backpropagate(node, reward)

        elapsed_time = time.perf_counter() - start_time

        # Best move: child with most visits (most robust), ties broken by value
        if not root.children:
            best_move = self.rng.choice(legal_moves)
            best_visits = 0
            best_q = 0.0
        else:
            best_child = max(root.children.values(), key=lambda c: (c.visits, c.q_value))
            best_move = best_child.move
            best_visits = best_child.visits
            best_q = best_child.q_value

        self.last_stats = {
            "agent": self.name,
            "algorithm": "MCTS (UCT)",
            "simulations": iterations_done,
            "simulation_budget": self.simulations,
            "c_param": self.c_param,
            "root_children": len(root.children),
            "root_visits": root.visits,
            "selected_move_visits": best_visits,
            "selected_move_q": best_q,
            "win_probability": best_q,
            "elapsed_time": elapsed_time,
            "selected_move": best_move,
        }
        if self.explain:
            facts = describe_move(self.rules, state, best_move, validator)
            facts["summary"] += (
                f" Most visited of {len(root.children)} explored moves "
                f"({best_visits}/{root.visits} visits, est. win {best_q:.0%})."
            )
            self.last_stats.update(facts)
            self.last_stats["explanation"] = facts["summary"]
        return best_move

    def _select_best_uct_child(self, node: MCTSNode, root_player: int) -> MCTSNode:
        mover = node.state.current_player  # player choosing among these children
        log_n = math.log(node.visits) if node.visits > 0 else 0.0

        def score(child: MCTSNode) -> float:
            if child.visits == 0:
                return float("inf")
            q = child.q_value if mover == root_player else 1.0 - child.q_value
            return q + self.c_param * math.sqrt(log_n / child.visits)

        return max(node.children.values(), key=score)

    def _expand(self, node: MCTSNode, validator: WordValidatorProtocol) -> MCTSNode:
        move = node.untried_moves.pop()
        next_state = self.rules.apply_move(node.state, move, validator)
        child = MCTSNode(
            state=next_state,
            parent=node,
            move=move,
            untried_moves=self._expansion_order(next_state, validator),
        )
        node.children[move] = child
        return child

    def _simulate(
        self,
        sim_state: GameState,
        root_player: int,
        validator: WordValidatorProtocol,
    ) -> float:
        """Rollout with a light, randomised greedy policy on a private copy of the state."""
        curr = sim_state.clone()
        depth = 0

        while not curr.is_terminal and depth < self.max_rollout_depth:
            chosen = self._rollout_policy_choice(curr, validator)
            if chosen is None:
                break
            # The copy is private to this rollout, so the cheaper in-place transition is safe.
            self.rules.apply_move_inplace(curr, chosen, validator)
            depth += 1

        # Calculate reward from root_player's perspective in [0.0, 1.0]
        return self._compute_reward(curr, root_player)

    def _rollout_policy_choice(
        self,
        state: GameState,
        validator: WordValidatorProtocol,
    ) -> Optional[Move]:
        """Samples a few empty cells; plays the best scoring letter there with probability 0.75,
        otherwise a random move."""
        board = state.board
        empty = [
            (r, c)
            for r in range(board.size)
            for c in range(board.size)
            if board.grid[r][c] is None
        ]
        if not empty:
            return None

        scanner = self.move_orderer.scanner
        sample = self.rng.sample(empty, min(len(empty), 4))
        best_move: Optional[Move] = None
        best_pts = 0
        for r, c in sample:
            if not scanner.has_neighbor(board, r, c):
                continue
            opts = scanner.letter_options(state, r, c, validator)
            for ch, (pts, _) in opts.items():
                if pts > best_pts:
                    best_pts = pts
                    best_move = (r, c, ch)

        # 75% chance to pick scoring move if available
        if best_move is not None and self.rng.random() < 0.75:
            return best_move

        r, c = self.rng.choice(sample)
        return (r, c, self.rng.choice(ALPHABET))

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
