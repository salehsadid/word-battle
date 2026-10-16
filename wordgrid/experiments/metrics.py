from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class MatchResult:
    """Detailed record of a single game between two agents."""
    p1_name: str
    p2_name: str
    p1_score: int
    p2_score: int
    winner: Optional[int]  # 1, 2, or 0 (draw)
    total_moves: int
    duration_seconds: float
    p1_avg_time_per_move: float
    p2_avg_time_per_move: float
    p1_nodes_visited: int = 0
    p2_nodes_visited: int = 0
    p1_cutoffs: int = 0
    p2_cutoffs: int = 0
    p1_mcts_sims: int = 0
    p2_mcts_sims: int = 0
    p1_moves: int = 0
    p2_moves: int = 0


@dataclass
class AgentTournamentStats:
    """Aggregated tournament statistics for a single agent."""
    name: str
    matches_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    total_score: int = 0
    total_score_diff: int = 0
    total_time_seconds: float = 0.0
    total_moves: int = 0
    total_nodes_visited: int = 0
    total_cutoffs: int = 0
    total_mcts_sims: int = 0

    @property
    def win_rate(self) -> float:
        return (self.wins / self.matches_played) if self.matches_played > 0 else 0.0

    @property
    def avg_score(self) -> float:
        return (self.total_score / self.matches_played) if self.matches_played > 0 else 0.0

    @property
    def avg_score_diff(self) -> float:
        return (self.total_score_diff / self.matches_played) if self.matches_played > 0 else 0.0

    @property
    def avg_move_time(self) -> float:
        return (self.total_time_seconds / self.total_moves) if self.total_moves > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "matches_played": self.matches_played,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "win_rate": round(self.win_rate, 4),
            "avg_score": round(self.avg_score, 2),
            "avg_score_diff": round(self.avg_score_diff, 2),
            "avg_move_time_seconds": round(self.avg_move_time, 4),
            "total_nodes_visited": self.total_nodes_visited,
            "total_cutoffs": self.total_cutoffs,
            "total_mcts_simulations": self.total_mcts_sims,
        }
