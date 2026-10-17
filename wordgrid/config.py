from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List

# Root directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DICT_PATH = DATA_DIR / "raw_words.txt"
CLEANED_DICT_PATH = DATA_DIR / "cleaned_words.txt"
TEST_DICT_PATH = DATA_DIR / "test_words.txt"
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
MENU_BACKGROUND_PATH = ASSETS_DIR / "images" / "menu_background.png"

# Game Modes (termination conditions)
MODE_UNTIL_BOARD_FULL = "UNTIL_BOARD_FULL"
MODE_REACH_GOAL_SCORE = "REACH_GOAL_SCORE"
MODE_MOVE_LIMIT = "MOVE_LIMIT"

ALL_GAME_MODES = [
    MODE_UNTIL_BOARD_FULL,
    MODE_REACH_GOAL_SCORE,
    MODE_MOVE_LIMIT,
]

MODE_LABELS = {
    MODE_UNTIL_BOARD_FULL: "Full board",
    MODE_REACH_GOAL_SCORE: "Target score",
    MODE_MOVE_LIMIT: "Move limit",
}

# Board limits
MIN_BOARD_SIZE = 3
MAX_BOARD_SIZE = 8
DEFAULT_BOARD_SIZE = 8


@dataclass
class GameConfig:
    board_size: int = DEFAULT_BOARD_SIZE
    min_word_length: int = 2
    game_mode: str = MODE_UNTIL_BOARD_FULL
    goal_score: int = 30
    move_limit: int = 10  # Moves *per player* in MODE_MOVE_LIMIT
    starting_player: int = 1
    dictionary_path: Path = CLEANED_DICT_PATH

    def validate(self) -> List[str]:
        """Returns a list of human readable problems (empty when valid)."""
        errors: List[str] = []
        if not (MIN_BOARD_SIZE <= self.board_size <= MAX_BOARD_SIZE):
            errors.append(f"Board size must be between {MIN_BOARD_SIZE} and {MAX_BOARD_SIZE}.")
        if not (2 <= self.min_word_length <= max(2, self.board_size)):
            errors.append(f"Minimum word length must be between 2 and the board size ({self.board_size}).")
        if self.game_mode not in ALL_GAME_MODES:
            errors.append(f"Unknown termination condition '{self.game_mode}'.")
        if self.game_mode == MODE_REACH_GOAL_SCORE and not (1 <= self.goal_score <= 999):
            errors.append("Target score must be between 1 and 999.")
        if self.game_mode == MODE_MOVE_LIMIT and not (1 <= self.move_limit <= 999):
            errors.append("Move limit must be between 1 and 999 moves per player.")
        if self.starting_player not in (1, 2):
            errors.append("Starting player must be 1 or 2.")
        return errors


@dataclass
class HeuristicWeights:
    score_diff: float = 1.0                 # Points already banked (own - opponent)
    own_future_potential: float = 0.6       # Best immediate score available to root player next turn
    opponent_future_potential: float = 0.8  # Best immediate score the opponent could take (threat)
    partial_sequence_bonus: float = 0.2     # Promising open letter sequences (dictionary prefixes)
    playable_space_factor: float = 0.1      # Lead matters more as empty cells run out


@dataclass
class AIConfig:
    minimax_depth: int = 2
    alphabeta_depth: int = 2
    mcts_simulations: int = 100
    mcts_c_param: float = 1.414
    heuristic_weights: HeuristicWeights = field(default_factory=HeuristicWeights)
    candidate_filtering_k: int = 0  # 0 means exhaustive (no filtering)


DIFFICULTIES = ["Easy", "Medium", "Hard", "Expert"]

# Difficulty presets change real search parameters.
#   depth / candidate_k : Minimax search horizon and branching (0 = every legal move)
#   iterations / max_children / rollout_depth : MCTS budget and breadth
#   time_limit : MCTS safety cap in seconds (search stops early on very large boards)
DIFFICULTY_PRESETS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "Easy": {
        "minimax": {"depth": 1, "candidate_k": 6, "use_pruning": True},
        "mcts": {"iterations": 80, "max_children": 8, "rollout_depth": 4, "time_limit": 10.0},
    },
    "Medium": {
        "minimax": {"depth": 2, "candidate_k": 10, "use_pruning": True},
        "mcts": {"iterations": 300, "max_children": 16, "rollout_depth": 6, "time_limit": 10.0},
    },
    "Hard": {
        "minimax": {"depth": 3, "candidate_k": 12, "use_pruning": True},
        "mcts": {"iterations": 900, "max_children": 24, "rollout_depth": 8, "time_limit": 10.0},
    },
    "Expert": {
        "minimax": {"depth": 4, "candidate_k": 10, "use_pruning": True},
        "mcts": {"iterations": 2000, "max_children": 28, "rollout_depth": 8, "time_limit": 10.0},
    },
}


@dataclass
class UIConfig:
    window_width: int = 1100
    window_height: int = 760
    fps: int = 60
    ai_delay_ms: int = 400
