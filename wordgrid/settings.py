"""Pre-match settings: data model, validation and agent construction (UI independent)."""

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from wordgrid.config import (
    GameConfig,
    HeuristicWeights,
    DIFFICULTIES,
    DIFFICULTY_PRESETS,
    ALL_GAME_MODES,
    MODE_REACH_GOAL_SCORE,
    MODE_MOVE_LIMIT,
    MIN_BOARD_SIZE,
    MAX_BOARD_SIZE,
    CLEANED_DICT_PATH,
    DATA_DIR,
)
from wordgrid.game.rules import GameRules
from wordgrid.ai.base_agent import BaseAgent
from wordgrid.ai.random_agent import RandomAgent
from wordgrid.ai.alphabeta_agent import AlphaBetaAgent
from wordgrid.ai.mcts_agent import MCTSAgent
from wordgrid.ai.evaluation import HeuristicEvaluator

MATCH_HUMAN_VS_HUMAN = "Human vs Human"
MATCH_HUMAN_VS_AI = "Human vs AI"
MATCH_AI_VS_AI = "AI vs AI"
MATCH_TYPES = [MATCH_HUMAN_VS_AI, MATCH_AI_VS_AI, MATCH_HUMAN_VS_HUMAN]

CONTROLLER_HUMAN = "Human"
CONTROLLER_MINIMAX = "Heuristic Minimax"
CONTROLLER_MCTS = "MCTS"
CONTROLLER_RANDOM = "Random"
AI_CONTROLLERS = [CONTROLLER_MINIMAX, CONTROLLER_MCTS, CONTROLLER_RANDOM]

DIFFICULTY_CUSTOM = "Custom"
DIFFICULTY_OPTIONS = DIFFICULTIES + [DIFFICULTY_CUSTOM]


def available_dictionaries() -> List[Tuple[str, Path]]:
    """Word lists that can be selected: every *.txt in data/ (default dictionary first)."""
    found: List[Tuple[str, Path]] = []
    if CLEANED_DICT_PATH.exists():
        found.append(("Standard English", CLEANED_DICT_PATH))
    if DATA_DIR.exists():
        for p in sorted(DATA_DIR.glob("*.txt")):
            if p.resolve() == CLEANED_DICT_PATH.resolve():
                continue
            label = p.stem.replace("_", " ").title()
            found.append((label, p))
    return found


@dataclass
class PlayerSettings:
    name: str = "Player"
    controller: str = CONTROLLER_HUMAN
    difficulty: str = "Medium"

    @property
    def is_human(self) -> bool:
        return self.controller == CONTROLLER_HUMAN


@dataclass
class MatchSettings:
    match_type: str = MATCH_HUMAN_VS_AI
    board_size: int = 5
    starting_player: int = 1
    game_mode: str = ALL_GAME_MODES[0]
    goal_score: int = 30
    move_limit: int = 10
    min_word_length: int = 2
    dictionary_path: Path = CLEANED_DICT_PATH

    p1: PlayerSettings = field(default_factory=lambda: PlayerSettings("Player 1", CONTROLLER_HUMAN))
    p2: PlayerSettings = field(default_factory=lambda: PlayerSettings("Player 2", CONTROLLER_MINIMAX))

    # Custom / advanced AI parameters
    minimax_depth: int = 2
    use_pruning: bool = True
    candidate_k: int = 12
    weights: HeuristicWeights = field(default_factory=HeuristicWeights)
    mcts_iterations: int = 400
    mcts_c: float = 1.414
    mcts_rollout_depth: int = 8
    mcts_max_children: int = 24
    seed: Optional[int] = None

    show_ai_explanations: bool = True
    show_ai_details: bool = False   # search statistics in the AI panel
    ai_move_delay: float = 0.5      # seconds between AI moves (lets people follow along)

    # ------------------------------------------------------------------ helpers
    def player(self, pid: int) -> PlayerSettings:
        return self.p1 if pid == 1 else self.p2

    def game_config(self, starting_player: Optional[int] = None) -> GameConfig:
        """Engine configuration. starting_player overrides a 'random' (0) start choice."""
        start = starting_player or (self.starting_player if self.starting_player in (1, 2) else 1)
        return GameConfig(
            board_size=self.board_size,
            min_word_length=self.min_word_length,
            game_mode=self.game_mode,
            goal_score=self.goal_score,
            move_limit=self.move_limit,
            starting_player=start,
            dictionary_path=self.dictionary_path,
        )

    def validate(self) -> List[str]:
        """Returns every problem with the settings (empty list when the match can start)."""
        errors = self.game_config().validate()
        if self.starting_player not in (0, 1, 2):
            errors.append("Starting player must be Player 1, Player 2 or Random.")
        if self.match_type not in MATCH_TYPES:
            errors.append(f"Unknown game mode '{self.match_type}'.")
        humans = [p.is_human for p in (self.p1, self.p2)]
        if self.match_type == MATCH_HUMAN_VS_HUMAN and not all(humans):
            errors.append("Human vs Human requires both players to be human.")
        if self.match_type == MATCH_HUMAN_VS_AI and sum(humans) != 1:
            errors.append("Human vs AI requires exactly one human and one AI player.")
        if self.match_type == MATCH_AI_VS_AI and any(humans):
            errors.append("AI vs AI requires both players to be AI.")
        for pid in (1, 2):
            p = self.player(pid)
            if not p.name.strip():
                errors.append(f"Player {pid} needs a name.")
            elif len(p.name) > 16:
                errors.append(f"Player {pid} name must be at most 16 characters.")
            if not p.is_human:
                if p.controller not in AI_CONTROLLERS:
                    errors.append(f"Player {pid}: unknown AI algorithm '{p.controller}'.")
                if p.difficulty not in DIFFICULTY_OPTIONS:
                    errors.append(f"Player {pid}: unknown difficulty '{p.difficulty}'.")
        if self.p1.name.strip() and self.p1.name.strip() == self.p2.name.strip():
            errors.append("Players must have different names.")
        if not Path(self.dictionary_path).exists():
            errors.append(f"Dictionary file not found: {self.dictionary_path}")

        if not (1 <= self.minimax_depth <= 5):
            errors.append("Minimax depth must be between 1 and 5.")
        if not (0 <= self.candidate_k <= 200):
            errors.append("Candidate breadth must be between 0 (all moves) and 200.")
        for wname in ("score_diff", "own_future_potential", "opponent_future_potential",
                      "partial_sequence_bonus", "playable_space_factor"):
            val = getattr(self.weights, wname)
            if not (0.0 <= val <= 10.0):
                errors.append(f"Heuristic weight '{wname}' must be between 0 and 10.")
        if not (10 <= self.mcts_iterations <= 50000):
            errors.append("MCTS iterations must be between 10 and 50000.")
        if not (0.0 <= self.mcts_c <= 10.0):
            errors.append("MCTS exploration constant must be between 0 and 10.")
        if not (1 <= self.mcts_rollout_depth <= 64):
            errors.append("MCTS rollout depth must be between 1 and 64.")
        if self.seed is not None and not (0 <= self.seed <= 2**31 - 1):
            errors.append("Random seed must be a non-negative integer (or blank).")
        return errors

    # ------------------------------------------------------------------ agents
    def create_agent(self, pid: int, rules: GameRules) -> Optional[BaseAgent]:
        """Builds the agent for player pid (None for a human). Agents share the engine rules."""
        p = self.player(pid)
        if p.is_human:
            return None
        # Distinct but reproducible seeds per player when a seed is given
        seed = None if self.seed is None else self.seed + pid
        custom = p.difficulty == DIFFICULTY_CUSTOM
        label = p.difficulty

        if p.controller == CONTROLLER_RANDOM:
            agent: BaseAgent = RandomAgent(name=p.name, seed=seed, rules=rules)
        elif p.controller == CONTROLLER_MCTS:
            preset = DIFFICULTY_PRESETS.get(p.difficulty, {}).get("mcts", {})
            agent = MCTSAgent(
                name=p.name,
                simulations=self.mcts_iterations if custom else preset["iterations"],
                c_param=self.mcts_c,
                max_rollout_depth=self.mcts_rollout_depth if custom else preset["rollout_depth"],
                max_children=self.mcts_max_children if custom else preset["max_children"],
                time_limit=0.0 if custom else preset.get("time_limit", 0.0),
                seed=seed,
                rules=rules,
            )
        else:
            preset = DIFFICULTY_PRESETS.get(p.difficulty, {}).get("minimax", {})
            weights = HeuristicWeights(**vars(self.weights))
            agent = AlphaBetaAgent(
                name=p.name,
                depth=self.minimax_depth if custom else preset["depth"],
                candidate_k=self.candidate_k if custom else preset["candidate_k"],
                use_pruning=self.use_pruning if custom else preset["use_pruning"],
                evaluator=HeuristicEvaluator(weights=weights, scoring=rules.scoring),
                rules=rules,
            )
        agent.difficulty = label  # type: ignore[attr-defined]
        return agent

    def resolve_starting_player(self, rng: Optional[random.Random] = None) -> int:
        """1 or 2; a 'random' start (0) is drawn from rng (or the seed)."""
        if self.starting_player in (1, 2):
            return self.starting_player
        return (rng or random.Random(self.seed)).choice([1, 2])
