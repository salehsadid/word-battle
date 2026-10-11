import os
import sys
import threading
import pygame
from typing import Optional, Dict, Any, List
from wordgrid.config import UIConfig, GameConfig, DATA_DIR
from wordgrid.game.engine import GameEngine
from wordgrid.dictionary.loader import DictionaryLoader
from wordgrid.dictionary.word_validator import WordValidator
from wordgrid.ai.base_agent import BaseAgent
from wordgrid.ai.random_agent import RandomAgent
from wordgrid.ai.minimax_agent import MinimaxAgent
from wordgrid.ai.alphabeta_agent import AlphaBetaAgent
from wordgrid.ai.mcts_agent import MCTSAgent
from wordgrid.experiments.tournament import TournamentRunner
from wordgrid.experiments.results_export import ResultsExporter
from wordgrid.ui.menu import MenuScreen
from wordgrid.ui.game_screen import GameScreen
from wordgrid.ui.controls import Button
from wordgrid.ui.colors import (
    COLOR_BG_DARK,
    COLOR_PANEL_BG,
    COLOR_PANEL_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_P1,
    COLOR_HIGHLIGHT_WORD,
)


class UIRunner:
    """Coordinates Pygame window lifecycle, screen transitions, and tournament threads."""

    def __init__(self, config: Optional[UIConfig] = None):
        self.config = config or UIConfig()
        pygame.init()
        pygame.display.set_caption("WordBattle — Adversarial Word Construction")

        self.screen = pygame.display.set_mode((self.config.window_width, self.config.window_height))
        self.clock = pygame.time.Clock()

        # Initialize fonts
        try:
            self.title_font = pygame.font.SysFont("Segoe UI", 26, bold=True)
            self.font = pygame.font.SysFont("Segoe UI", 18, bold=True)
            self.small_font = pygame.font.SysFont("Segoe UI", 14)
            self.mono_font = pygame.font.SysFont("Consolas", 14)
        except Exception:
            self.title_font = pygame.font.Font(None, 32)
            self.font = pygame.font.Font(None, 24)
            self.small_font = pygame.font.Font(None, 18)
            self.mono_font = pygame.font.Font(None, 18)

        # Load dictionary
        self.validator, self.dict_stats = DictionaryLoader.load_dictionary()

        # Navigation State
        self.current_screen_name = "MENU"
        self.menu_screen = MenuScreen(
            on_start_match=self.start_match,
            on_start_tournament=self.start_tournament,
            title_font=self.title_font,
            font=self.font,
            small_font=self.small_font,
        )
        self.game_screen: Optional[GameScreen] = None

        # Tournament state
        self.tournament_running = False
        self.tournament_summary_text: Optional[str] = None
        self.btn_tourney_back = Button(
            rect=pygame.Rect(50, 680, 160, 40),
            text="Back to Menu",
            font=self.font,
            callback=self.return_to_menu,
        )

    def _create_agent(self, agent_name: str, depth: int, mcts_sims: int) -> Optional[BaseAgent]:
        name_lower = agent_name.lower()
        if "alpha" in name_lower:
            return AlphaBetaAgent(depth=depth)
        elif "mini" in name_lower:
            return MinimaxAgent(depth=depth)
        elif "mcts" in name_lower:
            return MCTSAgent(simulations=mcts_sims)
        elif "random" in name_lower:
            return RandomAgent()
        return None  # Human

    def start_match(self, settings: dict):
        g_config = GameConfig(
            board_size=settings["board_size"],
            game_mode=settings["game_mode"],
            goal_score=settings["goal_score"],
            move_limit=settings["move_limit"],
        )
        engine = GameEngine(validator=self.validator, config=g_config)

        p1_agent = self._create_agent(settings["p1_agent"], settings["search_depth"], settings["mcts_sims"])
        p2_agent = self._create_agent(settings["p2_agent"], settings["search_depth"], settings["mcts_sims"])

        self.game_screen = GameScreen(
            engine=engine,
            validator=self.validator,
            p1_agent=p1_agent,
            p2_agent=p2_agent,
            p1_name=settings["p1_agent"],
            p2_name=settings["p2_agent"],
            title_font=self.title_font,
            font=self.font,
            small_font=self.small_font,
            on_back_to_menu=self.return_to_menu,
        )
        self.current_screen_name = "GAME"

    def start_tournament(self, settings: dict):
        self.current_screen_name = "TOURNAMENT"
        self.tournament_running = True
        self.tournament_summary_text = None

        d_val = settings["search_depth"]
        s_val = settings["mcts_sims"]
        b_size = settings["board_size"]
        mode = settings["game_mode"]

        def _worker():
            try:
                g_config = GameConfig(board_size=b_size, game_mode=mode)
                runner = TournamentRunner(validator=self.validator, config=g_config)
                agents = [
                    RandomAgent("Random", seed=42),
                    MinimaxAgent("Minimax", depth=d_val),
                    AlphaBetaAgent("AlphaBeta", depth=d_val),
                    MCTSAgent("MCTS", simulations=s_val, seed=42),
                ]
                matches, stats = runner.run_tournament(agents, games_per_pairing=2)

                # Export
                out_dir = DATA_DIR / "tournament_results"
                ResultsExporter.export_to_json(matches, stats, out_dir / "results.json")
                ResultsExporter.export_to_csv(stats, out_dir / "results.csv")
                self.tournament_summary_text = ResultsExporter.format_summary_table(stats)
            finally:
                self.tournament_running = False

        threading.Thread(target=_worker, daemon=True).start()

    def return_to_menu(self):
        self.current_screen_name = "MENU"
        self.game_screen = None

    def run(self):
        running = True
        while running:
            self.clock.tick(self.config.fps)

            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif self.current_screen_name == "MENU":
                    self.menu_screen.handle_event(event)
                elif self.current_screen_name == "GAME" and self.game_screen:
                    self.game_screen.handle_event(event)
                elif self.current_screen_name == "TOURNAMENT":
                    self.btn_tourney_back.handle_event(event)

            # Update logic
            if self.current_screen_name == "MENU":
                self.menu_screen.update()
            elif self.current_screen_name == "GAME" and self.game_screen:
                self.game_screen.update()

            # Render logic
            if self.current_screen_name == "MENU":
                self.menu_screen.render(self.screen)
            elif self.current_screen_name == "GAME" and self.game_screen:
                self.game_screen.render(self.screen)
            elif self.current_screen_name == "TOURNAMENT":
                self._render_tournament_screen()

            pygame.display.flip()

        pygame.quit()

    def _render_tournament_screen(self):
        self.screen.fill(COLOR_BG_DARK)
        title = self.title_font.render("AI Tournament & Benchmark Results", True, COLOR_P1)
        self.screen.blit(title, (50, 40))

        if self.tournament_running:
            prog_txt = self.font.render("Running tournament matches in background... Please wait.", True, COLOR_TEXT_PRIMARY)
            self.screen.blit(prog_txt, (50, 100))
        elif self.tournament_summary_text:
            y = 90
            lines = self.tournament_summary_text.splitlines()
            for line in lines:
                l_surf = self.mono_font.render(line, True, COLOR_TEXT_PRIMARY)
                self.screen.blit(l_surf, (50, y))
                y += 24

            msg = self.small_font.render(
                "Results exported successfully to data/tournament_results/ (results.json, results.csv)",
                True,
                COLOR_HIGHLIGHT_WORD,
            )
            self.screen.blit(msg, (50, y + 20))

        self.btn_tourney_back.render(self.screen)
