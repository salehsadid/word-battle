import csv
import json
from pathlib import Path
from typing import List, Dict
from wordgrid.experiments.metrics import MatchResult, AgentTournamentStats


class ResultsExporter:
    """Exports tournament outcomes to CSV and JSON formats and renders ASCII tables."""

    @staticmethod
    def export_to_json(
        matches: List[MatchResult],
        agent_stats: Dict[str, AgentTournamentStats],
        filepath: Path,
    ) -> None:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "summary": {name: stats.to_dict() for name, stats in agent_stats.items()},
            "matches": [
                {
                    "p1": m.p1_name,
                    "p2": m.p2_name,
                    "p1_score": m.p1_score,
                    "p2_score": m.p2_score,
                    "winner": m.winner,
                    "moves": m.total_moves,
                    "duration_sec": round(m.duration_seconds, 3),
                    "p1_avg_move_time": round(m.p1_avg_time_per_move, 4),
                    "p2_avg_move_time": round(m.p2_avg_time_per_move, 4),
                    "p1_nodes": m.p1_nodes_visited,
                    "p2_nodes": m.p2_nodes_visited,
                    "p1_cutoffs": m.p1_cutoffs,
                    "p2_cutoffs": m.p2_cutoffs,
                    "p1_mcts_sims": m.p1_mcts_sims,
                    "p2_mcts_sims": m.p2_mcts_sims,
                }
                for m in matches
            ],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def export_to_csv(
        agent_stats: Dict[str, AgentTournamentStats],
        filepath: Path,
    ) -> None:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "name",
            "matches_played",
            "wins",
            "losses",
            "draws",
            "win_rate",
            "avg_score",
            "avg_score_diff",
            "avg_move_time_seconds",
            "total_nodes_visited",
            "total_cutoffs",
            "total_mcts_simulations",
        ]
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for stats in agent_stats.values():
                writer.writerow(stats.to_dict())

    @staticmethod
    def format_summary_table(agent_stats: Dict[str, AgentTournamentStats]) -> str:
        headers = [
            "Agent",
            "Matches",
            "W-L-D",
            "Win Rate",
            "Avg Score",
            "Avg Diff",
            "Avg Time(s)",
            "Nodes/Sims",
        ]
        rows = []
        for name, s in sorted(agent_stats.items(), key=lambda x: x[1].win_rate, reverse=True):
            wld = f"{s.wins}-{s.losses}-{s.draws}"
            nodes_sims = s.total_nodes_visited + s.total_mcts_sims
            rows.append([
                name,
                str(s.matches_played),
                wld,
                f"{s.win_rate * 100:.1f}%",
                f"{s.avg_score:.1f}",
                f"{s.avg_score_diff:+.1f}",
                f"{s.avg_move_time:.4f}",
                str(nodes_sims),
            ])

        col_widths = [max(len(h), max((len(r[i]) for r in rows), default=0)) for i, h in enumerate(headers)]

        def fmt_row(row_items):
            return " | ".join(item.ljust(col_widths[i]) for i, item in enumerate(row_items))

        sep_line = "-+-".join("-" * w for w in col_widths)

        lines = [
            fmt_row(headers),
            sep_line,
        ]
        for r in rows:
            lines.append(fmt_row(r))

        return "\n".join(lines)
