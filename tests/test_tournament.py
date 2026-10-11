import pytest
from pathlib import Path
from wordgrid.game.scoring import WordValidatorProtocol
from wordgrid.config import GameConfig, MODE_MOVE_LIMIT
from wordgrid.ai.random_agent import RandomAgent
from wordgrid.ai.alphabeta_agent import AlphaBetaAgent
from wordgrid.ai.mcts_agent import MCTSAgent
from wordgrid.experiments.tournament import TournamentRunner
from wordgrid.experiments.results_export import ResultsExporter


class MockValidator:
    def __init__(self):
        self.words = {"CAT", "CAR", "BAT", "BAR", "RAT", "MAT", "AT", "TO", "IN", "ON"}

    def is_valid_word(self, word: str) -> bool:
        return word.upper() in self.words

    def is_valid_prefix(self, prefix: str) -> bool:
        p = prefix.upper()
        return any(w.startswith(p) for w in self.words)


def test_tournament_runner_and_export(tmp_path: Path):
    validator = MockValidator()
    # Fast config: 3x3 board, move limit 4
    config = GameConfig(board_size=3, game_mode=MODE_MOVE_LIMIT, move_limit=4)
    runner = TournamentRunner(validator=validator, config=config)

    agents = [
        RandomAgent(name="Random", seed=1),
        AlphaBetaAgent(name="AlphaBeta", depth=1),
        MCTSAgent(name="MCTS", simulations=5, seed=2),
    ]

    matches, stats = runner.run_tournament(agents, games_per_pairing=2)

    # 3 pairs * 2 games = 6 matches
    assert len(matches) == 6
    for a in agents:
        assert stats[a.name].matches_played == 4

    # Test export
    json_path = tmp_path / "results.json"
    csv_path = tmp_path / "results.csv"

    ResultsExporter.export_to_json(matches, stats, json_path)
    ResultsExporter.export_to_csv(stats, csv_path)

    assert json_path.exists()
    assert csv_path.exists()

    table = ResultsExporter.format_summary_table(stats)
    assert "Random" in table
    assert "AlphaBeta" in table
    assert "MCTS" in table
