from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any

# Root directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DICT_PATH = DATA_DIR / "raw_words.txt"
CLEANED_DICT_PATH = DATA_DIR / "cleaned_words.txt"
TEST_DICT_PATH = DATA_DIR / "test_words.txt"

# Game Modes
MODE_UNTIL_BOARD_FULL = "UNTIL_BOARD_FULL"
MODE_REACH_GOAL_SCORE = "REACH_GOAL_SCORE"
MODE_MOVE_LIMIT = "MOVE_LIMIT"

ALL_GAME_MODES = [
    MODE_UNTIL_BOARD_FULL,
    MODE_REACH_GOAL_SCORE,
    MODE_MOVE_LIMIT,
]

@dataclass
class GameConfig:
    board_size: int = 5
    min_word_length: int = 2
    game_mode: str = MODE_UNTIL_BOARD_FULL
    goal_score: int = 30
    move_limit: int = 20
    dictionary_path: Path = CLEANED_DICT_PATH

@dataclass
class HeuristicWeights:
    score_diff: float = 1.0
    own_future_potential: float = 0.5
    opponent_future_potential: float = 0.5
    partial_sequence_bonus: float = 0.2
    playable_space_factor: float = 0.1

@dataclass
class AIConfig:
    minimax_depth: int = 2
    alphabeta_depth: int = 2
    mcts_simulations: int = 100
    mcts_c_param: float = 1.414
    heuristic_weights: HeuristicWeights = field(default_factory=HeuristicWeights)
    candidate_filtering_k: int = 0  # 0 means exhaustive (no filtering)

@dataclass
class UIConfig:
    window_width: int = 1100
    window_height: int = 760
    fps: int = 60
    ai_delay_ms: int = 400
