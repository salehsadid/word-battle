import argparse
from pathlib import Path
from wordgrid.config import (
    GameConfig,
    DATA_DIR,
    ALL_GAME_MODES,
    CLEANED_DICT_PATH,
)
from wordgrid.dictionary.loader import DictionaryLoader
from wordgrid.game.engine import GameEngine
from wordgrid.ai.random_agent import RandomAgent
from wordgrid.ai.minimax_agent import MinimaxAgent
from wordgrid.ai.alphabeta_agent import AlphaBetaAgent
from wordgrid.ai.mcts_agent import MCTSAgent
from wordgrid.experiments.tournament import TournamentRunner
from wordgrid.experiments.results_export import ResultsExporter
from wordgrid.settings import (
    MatchSettings,
    PlayerSettings,
    CONTROLLER_HUMAN,
    CONTROLLER_MINIMAX,
    CONTROLLER_MCTS,
    CONTROLLER_RANDOM,
    MATCH_HUMAN_VS_HUMAN,
    MATCH_HUMAN_VS_AI,
    MATCH_AI_VS_AI,
    DIFFICULTY_OPTIONS,
)


def _load_validator(args):
    path = Path(args.dict) if args.dict else CLEANED_DICT_PATH
    if path == CLEANED_DICT_PATH:
        validator, stats = DictionaryLoader.load_dictionary()
    else:
        validator, stats = DictionaryLoader.load_dictionary(dict_path=path)
    return validator, stats, path


def run_cli_tournament(args):
    print("=" * 60)
    print("WordBattle - Automated AI Tournament Benchmark")
    print("=" * 60)
    validator, stats, _ = _load_validator(args)
    print(f"Dictionary loaded: {stats.get('accepted_count', len(validator))} words accepted.")

    g_config = GameConfig(
        board_size=args.board_size,
        min_word_length=args.min_len,
        game_mode=args.game_mode,
        goal_score=args.goal_score,
        move_limit=args.move_limit,
    )
    errors = g_config.validate()
    if errors:
        raise SystemExit("Invalid settings:\n  " + "\n  ".join(errors))
    runner = TournamentRunner(validator=validator, config=g_config)

    agents = [
        RandomAgent("Random", seed=args.seed),
        MinimaxAgent("Minimax", depth=args.depth, candidate_k=args.k),
        AlphaBetaAgent("AlphaBeta", depth=args.depth, candidate_k=args.k, explain=False),
        MCTSAgent("MCTS", simulations=args.sims, c_param=args.c, seed=args.seed, explain=False),
    ]

    print(f"Starting tournament with {len(agents)} agents on {args.board_size}x{args.board_size} grid...")
    print(f"Games per pairing: {args.games} (alternating player starts)")

    matches, agent_stats = runner.run_tournament(agents, games_per_pairing=args.games)

    print("\nTournament Completed! Aggregated Results:")
    print("-" * 60)
    print(ResultsExporter.format_summary_table(agent_stats))
    print("-" * 60)

    out_dir = DATA_DIR / "tournament_results"
    json_path = out_dir / "results.json"
    csv_path = out_dir / "results.csv"
    ResultsExporter.export_to_json(matches, agent_stats, json_path)
    ResultsExporter.export_to_csv(agent_stats, csv_path)
    print(f"Exported metrics to:\n  {json_path}\n  {csv_path}")


def _controller(name: str) -> str:
    n = name.lower()
    if "mcts" in n:
        return CONTROLLER_MCTS
    if "mini" in n or "alpha" in n:
        return CONTROLLER_MINIMAX
    if "random" in n:
        return CONTROLLER_RANDOM
    return CONTROLLER_HUMAN


def run_cli_match(args):
    print("=" * 60)
    print("WordBattle - CLI Match Runner")
    print("=" * 60)
    validator, _, dict_path = _load_validator(args)

    p1 = PlayerSettings(args.p1, _controller(args.p1), args.difficulty)
    p2 = PlayerSettings(args.p2 if args.p2 != args.p1 else f"{args.p2} 2", _controller(args.p2), args.difficulty)
    humans = p1.is_human + p2.is_human
    match_type = {2: MATCH_HUMAN_VS_HUMAN, 1: MATCH_HUMAN_VS_AI, 0: MATCH_AI_VS_AI}[humans]
    settings = MatchSettings(
        match_type=match_type,
        board_size=args.board_size,
        starting_player=args.start,
        game_mode=args.game_mode,
        goal_score=args.goal_score,
        move_limit=args.move_limit,
        min_word_length=args.min_len,
        dictionary_path=dict_path,
        p1=p1,
        p2=p2,
        minimax_depth=args.depth,
        candidate_k=args.k,
        mcts_iterations=args.sims,
        mcts_c=args.c,
        seed=args.seed,
    )
    errors = settings.validate()
    if errors:
        raise SystemExit("Invalid settings:\n  " + "\n  ".join(errors))

    engine = GameEngine(validator=validator, config=settings.game_config(settings.resolve_starting_player()))
    agents = {pid: settings.create_agent(pid, engine.rules) for pid in (1, 2)}
    names = {1: p1.name, 2: p2.name}

    print(f"Match: {names[1]} vs {names[2]} on {args.board_size}x{args.board_size} grid "
          f"({args.game_mode}, {names[engine.state.current_player]} starts)")

    while not engine.is_game_over:
        curr_p = engine.state.current_player
        agent = agents[curr_p]
        print(f"\n--- Move {engine.state.move_count + 1}: {names[curr_p]} ---")
        print(f"Scores: {names[1]}={engine.state.scores[1]}, {names[2]}={engine.state.scores[2]} | "
              f"empty cells: {engine.state.empty_cell_count}")
        print(engine.state.board)

        if agent is None:
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
                    print("Illegal move! Cell must be empty and within board, letter A-Z.")
                except (ValueError, EOFError) as ex:
                    print(f"Input error: {ex}")
        else:
            move = agent.select_move(engine.state, validator)
            stats = agent.get_last_stats()
            print(f"AI chose: {move} (time: {stats.get('elapsed_time', 0.0):.3f}s)")
            if stats.get("explanation"):
                print(f"  Why: {stats['explanation']}")
            engine.make_move(move)

        entry = engine.move_log[-1]
        if entry["points"]:
            print(f"Scored {entry['word']} ({entry['direction']}) for +{entry['points']}")
        else:
            print("No new word (0 points).")

    print("\n" + "=" * 60)
    print(f"GAME OVER ({engine.state.end_reason})")
    print(f"Final Scores: {names[1]}={engine.state.scores[1]}, {names[2]}={engine.state.scores[2]}")
    if engine.state.winner in (1, 2):
        print(f"Winner: {names[engine.state.winner]}!")
    else:
        print("Result: Draw!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="WordBattle - Strategic Word Grid Game with AI")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode instead of Pygame GUI")
    parser.add_argument("--mode", choices=["play", "tournament"], default="tournament", help="CLI mode operation")
    parser.add_argument("--p1", default="Human", help="Player 1 (Human, Random, Minimax, MCTS)")
    parser.add_argument("--p2", default="Minimax", help="Player 2 (Human, Random, Minimax, MCTS)")
    parser.add_argument("--difficulty", choices=DIFFICULTY_OPTIONS, default="Medium",
                        help="AI difficulty preset (Custom uses --depth/--k/--sims/--c)")
    parser.add_argument("--start", type=int, choices=[0, 1, 2], default=1, help="Starting player (0 = random)")
    parser.add_argument("--board-size", type=int, default=5, help="Grid size N (3-8, default 5)")
    parser.add_argument("--min-len", type=int, default=2, help="Minimum word length (default 2)")
    parser.add_argument("--dict", default=None, help="Path to a word list (one word per line)")
    parser.add_argument("--game-mode", choices=ALL_GAME_MODES, default=ALL_GAME_MODES[0], help="Termination mode")
    parser.add_argument("--goal-score", type=int, default=30, help="Target score threshold")
    parser.add_argument("--move-limit", type=int, default=10, help="Moves per player in MOVE_LIMIT mode")
    parser.add_argument("--depth", type=int, default=2, help="Minimax search depth (Custom / tournament)")
    parser.add_argument("--k", type=int, default=12, help="Minimax moves per node, 0 = all (Custom / tournament)")
    parser.add_argument("--sims", type=int, default=300, help="MCTS iterations (Custom / tournament)")
    parser.add_argument("--c", type=float, default=1.414, help="MCTS exploration constant")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible AI play")
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
        try:
            from wordgrid.ui.runner import UIRunner
        except ImportError as e:
            print(f"Unable to import the Pygame GUI ({e}). Install pygame or use --cli.")
            return
        UIRunner().run()


if __name__ == "__main__":
    main()
