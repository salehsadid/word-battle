from typing import Optional, List, Tuple
from wordgrid.game.state import GameState
from wordgrid.game.rules import GameRules, Move
from wordgrid.game.scoring import ScoringSystem, WordValidatorProtocol, direction_label
from wordgrid.config import GameConfig


class GameEngine:
    """Authoritative game coordinator for WordGrid.

    Serves as the single source of truth for match progress, move validation,
    scoring, and history tracking. Contains no UI code.
    """

    def __init__(
        self,
        validator: WordValidatorProtocol,
        config: Optional[GameConfig] = None,
        rules: Optional[GameRules] = None,
    ):
        self.validator = validator
        self.config = config or GameConfig()
        self.rules = rules or GameRules(scoring_system=ScoringSystem(self.config.min_word_length))
        self.history: List[GameState] = []
        self.matched_words: List[dict] = []  # Scored words only
        self.move_log: List[dict] = []       # Every move, including zero-point moves
        self.state = self._create_initial_state()

    def _create_initial_state(self) -> GameState:
        return GameState(
            board_size=self.config.board_size,
            current_player=self.config.starting_player,
            starting_player=self.config.starting_player,
            game_mode=self.config.game_mode,
            goal_score=self.config.goal_score,
            move_limit=self.config.move_limit,
        )

    def reset(self, config: Optional[GameConfig] = None) -> GameState:
        """Resets the engine to a new game with the given or current configuration."""
        if config is not None:
            self.config = config
            self.rules = GameRules(scoring_system=ScoringSystem(self.config.min_word_length))
        self.history.clear()
        self.matched_words.clear()
        self.move_log.clear()
        self.state = self._create_initial_state()
        return self.state

    def make_move(self, move: Move) -> GameState:
        """Validates and applies a move to the current match state."""
        if self.state.is_terminal:
            raise RuntimeError("Cannot make move in a finished game.")

        # Save snapshot to history
        self.history.append(self.state.clone())
        prev_player = self.state.current_player
        prev_score = self.state.scores.get(prev_player, 0)

        # Apply move via rules
        self.state = self.rules.apply_move(self.state, move, self.validator)
        r, c, ch = self.state.last_move
        points = self.state.scores.get(prev_player, 0) - prev_score

        # Record matched words
        scored = list(self.state.last_scored_occurrences)
        for word, length, occ in scored:
            self.matched_words.append({
                "word": word,
                "length": length,
                "player": prev_player,
                "move_count": self.state.move_count,
                "move": (r, c, ch),
                "occurrence": occ,
                "direction": direction_label(occ),
            })

        word, _, occ = scored[0] if scored else (None, 0, None)
        self.move_log.append({
            "move_count": self.state.move_count,
            "player": prev_player,
            "move": (r, c, ch),
            "points": points,
            "word": word,
            "occurrence": occ,
            "direction": direction_label(occ) if occ else None,
            "blocked_words": list(self.state.last_blocked_words),
            "score_after": dict(self.state.scores),
        })

        return self.state

    def undo_last_move(self) -> Optional[GameState]:
        """Rolls back the last move if available in history."""
        if not self.history:
            return None
        self.state = self.history.pop()
        self.matched_words = [
            m for m in self.matched_words if m["move_count"] <= self.state.move_count
        ]
        self.move_log = [m for m in self.move_log if m["move_count"] <= self.state.move_count]
        return self.state

    def get_legal_moves(self) -> List[Move]:
        """Returns all legal moves for current state."""
        return self.rules.get_legal_moves(self.state)

    @property
    def is_game_over(self) -> bool:
        return self.state.is_terminal

    @property
    def winner(self) -> Optional[int]:
        return self.state.winner
