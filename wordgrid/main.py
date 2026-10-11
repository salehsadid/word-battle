import argparse
import sys
from pathlib import Path
from wordgrid.config import GameConfig, DATA_DIR
from wordgrid.dictionary.loader import DictionaryLoader
from wordgrid.game.engine import GameEngine
from wordgrid.ai.random_agent import RandomAgent
from wordgrid.ai.minimax_agent import MinimaxAgent
from wordgrid.ai.alphabeta_agent import AlphaBetaAgent
from wordgrid.ai.mcts_agent import MCTSAgent
from wordgrid.experiments.tournament import TournamentRunner
from wordgrid.experiments.results_export import ResultsExporter


def run_cli_tournament(args):
    print("=" * 60)
    print("WordBattle — Automated AI Tournament Benchmark")
    print("=" * 60)
    validator, stats = DictionaryLoader.load_dictionary()
    print(f"Dictionary loaded: {stats.get('accepted_count', len(validator))} words accepted.")

    g_config = GameConfig(
        board_size=args.board_size,
        game_mode=args.game_mode,
        goal_score=args.goal_score,
        move_limit=args.move_limit,
    )
    runner = TournamentRunner(validator=validator, config=g_config)

    agents = [
        RandomAgent("Random", seed=42),
        MinimaxAgent("Minimax", depth=args.depth),
        AlphaBetaAgent("AlphaBeta", depth=args.depth),
        MCTSAgent("MCTS", simulations=args.sims, seed=42),
    ]

    print(f"Starting tournament with {len(agents)} agents on {args.board_size}x{args.board_size} grid...")
    print(f"Games per pairing: {args.games} (alternating player starts)")

    matches, agent_stats = runner.run_tournament(agents, games_per_pairing=args.games)

    print("\nTournament Completed! Aggregated Results:")
    print("-" * 60)
    table = ResultsExporter.format_summary_table(agent_stats)
    print(table)
    print("-" * 60)

    out_dir = DATA_DIR / "tournament_results"
    json_path = out_dir / "results.json"
    csv_path = out_dir / "results.csv"
    ResultsExporter.export_to_json(matches, agent_stats, json_path)
    ResultsExporter.export_to_csv(agent_stats, csv_path)
    print(f"Exported metrics to:\n  {json_path}\n  {csv_path}")


def run_cli_match(args):
    print("=" * 60)
    print("WordBattle — CLI Match Runner")
    print("=" * 60)
    validator, _ = DictionaryLoader.load_dictionary()
    g_config = GameConfig(
        board_size=args.board_size,
        game_mode=args.game_mode,
        goal_score=args.goal_score,
        move_limit=args.move_limit,
    )
    engine = GameEngine(validator=validator, config=g_config)

    def create_agent(name):
        n = name.lower()
        if "alpha" in n:
            return AlphaBetaAgent("AlphaBeta", depth=args.depth)
        elif "mini" in n:
            return MinimaxAgent("Minimax", depth=args.depth)
        elif "mcts" in n:
            return MCTSAgent("MCTS", simulations=args.sims)
        elif "random" in n:
            return RandomAgent("Random")
        return None

    a1 = create_agent(args.p1)
    a2 = create_agent(args.p2)

    print(f"Match: {args.p1} vs {args.p2} on {args.board_size}x{args.board_size} grid")

    while not engine.is_game_over:
        curr_p = engine.state.current_player
        agent = a1 if curr_p == 1 else a2
        print(f"\n--- Turn: Player {curr_p} ({args.p1 if curr_p == 1 else args.p2}) ---")
        print(f"Scores: P1={engine.state.scores[1]}, P2={engine.state.scores[2]}")
        print(engine.state.board)

        if agent is None:
            # Human CLI input
            while True:
                try:
                    inp = input("Enter move as 'row col letter' (e.g. 0 2 T): ").strip().split()
                    if len(inp) != 3:
                        print("Invalid format. Example: 0 2 T")
                        continue
                    r, c, ch = int(inp[0]), int(inp[1]), inp[2].upper()
                    if engine.rules.is_legal_move(engine.state, (r, c, ch)):
                        engine.make_move((r, c, ch))
                        break
                    else:
                        print("Illegal move! Cell must be empty and within board.")
                except Exception as ex:
                    print(f"Input error: {ex}")
        else:
            move = agent.select_move(engine.state, validator)
            stats = agent.get_last_stats()
            print(f"AI chose: {move} (time: {stats.get('elapsed_time', 0.0):.3f}s)")
            engine.make_move(move)

        if engine.state.last_scored_words:
            print(f"Scored word(s): {engine.state.last_scored_words}")

    print("\n" + "=" * 60)
    print("GAME OVER!")
    print(f"Final Scores: P1={engine.state.scores[1]}, P2={engine.state.scores[2]}")
    if engine.state.winner == 1:
        print(f"Winner: Player 1 ({args.p1})!")
    elif engine.state.winner == 2:
        print(f"Winner: Player 2 ({args.p2})!")
    else:
        print("Result: Draw!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="WordBattle — Adversarial Word Construction Game")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode instead of Pygame GUI")
    parser.add_argument("--mode", choices=["play", "tournament"], default="tournament", help="CLI mode operation")
    parser.add_argument("--p1", default="Human", help="Player 1 agent (Human, Random, Minimax, AlphaBeta, MCTS)")
    parser.add_argument("--p2", default="AlphaBeta", help="Player 2 agent")
    parser.add_argument("--board-size", type=int, default=5, help="Grid size N (default 5)")
    parser.add_argument("--game-mode", default="UNTIL_BOARD_FULL", help="Termination mode")
    parser.add_argument("--goal-score", type=int, default=30, help="Goal score threshold")
    parser.add_argument("--move-limit", type=int, default=20, help="Move limit threshold")
    parser.add_argument("--depth", type=int, default=2, help="Minimax / AlphaBeta search depth")
    parser.add_argument("--sims", type=int, default=100, help="MCTS simulation budget")
    parser.add_argument("--games", type=int, default=2, help="Tournament games per pairing")
    parser.add_argument("--clean-dict", action="store_true", help="Force reclean raw dictionary")

    args = parser.parse_args()

    if args.clean_dict:
        print("Recleaning offline dictionary...")
        DictionaryLoader.load_dictionary(force_clean=True)
        print("Dictionary cleaned successfully.")
        return

    if args.cli:
        if args.mode == "tournament":
            run_cli_tournament(args)
        else:
            run_cli_match(args)
    else:
        # GUI Mode via Pygame
        try:
            from wordgrid.ui.runner import UIRunner
            runner = UIRunner()
            runner.run()
        except Exception as e:
            print(f"Unable to launch Pygame GUI ({e}). Falling back to CLI mode...")
            run_cli_tournament(args)


if __name__ == "__main__":
    main()
