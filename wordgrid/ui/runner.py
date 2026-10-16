import random
import threading
import pygame
from pathlib import Path
from typing import Optional, Dict
from wordgrid.config import UIConfig, DATA_DIR, CLEANED_DICT_PATH
from wordgrid.game.engine import GameEngine
from wordgrid.dictionary.loader import DictionaryLoader
from wordgrid.dictionary.word_validator import WordValidator
from wordgrid.ai.random_agent import RandomAgent
from wordgrid.ai.alphabeta_agent import AlphaBetaAgent
from wordgrid.ai.mcts_agent import MCTSAgent
from wordgrid.ai.evaluation import HeuristicEvaluator
from wordgrid.config import DIFFICULTY_PRESETS, HeuristicWeights
from wordgrid.experiments.tournament import TournamentRunner
from wordgrid.experiments.results_export import ResultsExporter
from wordgrid.settings import MatchSettings
from wordgrid.ui.menu import MenuScreen
from wordgrid.ui.game_screen import GameScreen
from wordgrid.ui.controls import Button
from wordgrid.ui import colors as col
from wordgrid.ui import theme


class UIRunner:
    """Coordinates Pygame window lifecycle, screen transitions, and tournament threads."""

    def __init__(self, config: Optional[UIConfig] = None):
        self.config = config or UIConfig()
        pygame.init()
        pygame.display.set_caption("WordBattle - Strategic Word Grid")

        size = (self.config.window_width, self.config.window_height)
        try:
            # SCALED keeps the logical 1100x760 layout and maps mouse input when resized.
            self.screen = pygame.display.set_mode(size, pygame.SCALED | pygame.RESIZABLE)
        except pygame.error:
            self.screen = pygame.display.set_mode(size)
        self.clock = pygame.time.Clock()

        # Fonts (screens mostly use theme.font directly)
        self.title_font = theme.font(theme.SIZE_TITLE, bold=True)
        self.font = theme.font(theme.SIZE_BODY, bold=True)
        self.small_font = theme.font(theme.SIZE_CAPTION)
        try:
            self.mono_font = pygame.font.SysFont("Consolas", 15)
        except Exception:
            self.mono_font = pygame.font.Font(None, 20)

        # Dictionaries are loaded lazily and cached by path
        self._validators: Dict[Path, WordValidator] = {}
        self.validator = self._get_validator(CLEANED_DICT_PATH)
        self.status_message: Optional[str] = None

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
        self.last_settings: Optional[MatchSettings] = None

        # Tournament state
        self.tournament_running = False
        self.tournament_progress = ""
        self.tournament_summary_text: Optional[str] = None
        self.tournament_error: Optional[str] = None
        self.btn_tourney_back = Button(
            rect=pygame.Rect(60, 680, 200, 46),
            text="Back to settings",
            icon="back",
            callback=self.return_to_menu,
        )

    def _get_validator(self, path: Path) -> WordValidator:
        path = Path(path)
        if path not in self._validators:
            if path == CLEANED_DICT_PATH:
                validator, _ = DictionaryLoader.load_dictionary()
            else:
                validator, _ = DictionaryLoader.load_dictionary(dict_path=path)
            self._validators[path] = validator
        return self._validators[path]

    # ------------------------------------------------------------------ matches
    def start_match(self, settings: MatchSettings):
        try:
            validator = self._get_validator(settings.dictionary_path)
        except Exception as ex:  # unreadable dictionary
            self.menu_screen.errors = [f"Could not load dictionary: {ex}"]
            return
        if len(validator) == 0:
            self.menu_screen.errors = ["The selected dictionary contains no words."]
            return

        self.last_settings = settings
        self.game_screen = GameScreen(
            settings=settings,
            validator=validator,
            build_engine=self._build_engine,
            title_font=self.title_font,
            font=self.font,
            small_font=self.small_font,
            on_back_to_menu=self.return_to_menu,
        )
        self.current_screen_name = "GAME"

    def _build_engine(self, settings: MatchSettings, validator: WordValidator, rng: random.Random):
        """Creates a fresh engine and agents for a (re)started match."""
        start = settings.resolve_starting_player(rng)
        engine = GameEngine(validator=validator, config=settings.game_config(start))
        agents = {pid: settings.create_agent(pid, engine.rules) for pid in (1, 2)}
        return engine, agents

    # ------------------------------------------------------------------ tournament
    def start_tournament(self, settings: MatchSettings):
        self.current_screen_name = "TOURNAMENT"
        self.tournament_running = True
        self.tournament_summary_text = None
        self.tournament_error = None
        self.tournament_progress = "Preparing agents..."

        validator = self._get_validator(settings.dictionary_path)
        g_config = settings.game_config(1)
        seed = settings.seed if settings.seed is not None else 42
        difficulty = "Medium"

        def _worker():
            try:
                runner = TournamentRunner(validator=validator, config=g_config)
                mm = DIFFICULTY_PRESETS[difficulty]["minimax"]
                mc = DIFFICULTY_PRESETS[difficulty]["mcts"]
                agents = [
                    RandomAgent("Random", seed=seed),
                    AlphaBetaAgent(
                        "Minimax",
                        depth=mm["depth"],
                        candidate_k=mm["candidate_k"],
                        evaluator=HeuristicEvaluator(HeuristicWeights(**vars(settings.weights))),
                        explain=False,
                    ),
                    MCTSAgent(
                        "MCTS",
                        simulations=mc["iterations"],
                        c_param=settings.mcts_c,
                        max_children=mc["max_children"],
                        max_rollout_depth=mc["rollout_depth"],
                        seed=seed,
                        explain=False,
                    ),
                ]
                self.tournament_progress = (
                    f"Round robin on {g_config.board_size}x{g_config.board_size}, "
                    f"{difficulty} presets, 2 games per pairing..."
                )
                matches, stats = runner.run_tournament(agents, games_per_pairing=2)

                out_dir = DATA_DIR / "tournament_results"
                ResultsExporter.export_to_json(matches, stats, out_dir / "results.json")
                ResultsExporter.export_to_csv(stats, out_dir / "results.csv")
                self.tournament_summary_text = ResultsExporter.format_summary_table(stats)
            except Exception as ex:
                self.tournament_error = f"Tournament failed: {ex}"
            finally:
                self.tournament_running = False

        threading.Thread(target=_worker, daemon=True).start()

    def return_to_menu(self):
        if self.game_screen is not None:
            self.game_screen.shutdown()
        self.current_screen_name = "MENU"
        self.game_screen = None
        self.menu_screen._refresh()

    # ------------------------------------------------------------------ loop
    def run(self):
        running = True
        while running:
            self.clock.tick(self.config.fps)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif self.current_screen_name == "MENU":
                    self.menu_screen.handle_event(event)
                elif self.current_screen_name == "GAME" and self.game_screen:
                    self.game_screen.handle_event(event)
                elif self.current_screen_name == "TOURNAMENT":
                    self.btn_tourney_back.handle_event(event)

            if self.current_screen_name == "MENU":
                self.menu_screen.update()
                self.menu_screen.render(self.screen)
            elif self.current_screen_name == "GAME" and self.game_screen:
                self.game_screen.update()
                self.game_screen.render(self.screen)
            elif self.current_screen_name == "TOURNAMENT":
                self._render_tournament_screen()

            pygame.display.flip()

        if self.game_screen is not None:
            self.game_screen.shutdown()
        pygame.quit()

    def _render_tournament_screen(self):
        self.screen.fill(col.BG)
        theme.draw_text(self.screen, "AI benchmark", theme.font(theme.SIZE_DISPLAY, bold=True), col.TEXT, (60, 40))
        theme.draw_text(self.screen, "Random, Strategist (Minimax) and Explorer (MCTS) play each other twice, "
                                     "alternating who starts.", theme.font(theme.SIZE_BODY), col.TEXT_MUTED, (60, 88))
        card = pygame.Rect(60, 130, 980, 520)
        theme.draw_card(self.screen, card, radius=16)

        if self.tournament_running:
            dots = "." * (pygame.time.get_ticks() // 400 % 4)
            theme.draw_text(self.screen, f"Playing matches{dots}", theme.font(theme.SIZE_TITLE, bold=True),
                            col.TEXT, (card.x + 32, card.y + 32))
            theme.draw_text(self.screen, self.tournament_progress, theme.font(theme.SIZE_BODY), col.TEXT_MUTED,
                            (card.x + 32, card.y + 70))
            bar = pygame.Rect(card.x + 32, card.y + 110, card.width - 64, 8)
            pygame.draw.rect(self.screen, col.SURFACE_SUNK, bar, border_radius=4)
            span = bar.width // 4
            off = (pygame.time.get_ticks() // 4) % (bar.width + span) - span
            seg = pygame.Rect(bar.x + max(0, off), bar.y, min(span, bar.right - bar.x - max(0, off)), bar.height)
            if seg.width > 0:
                pygame.draw.rect(self.screen, col.PRIMARY, seg, border_radius=4)
        elif self.tournament_error:
            theme.draw_text(self.screen, self.tournament_error, theme.font(theme.SIZE_BODY, bold=True), col.DANGER,
                            (card.x + 32, card.y + 32))
        elif self.tournament_summary_text:
            theme.draw_text(self.screen, "Results", theme.font(theme.SIZE_TITLE, bold=True), col.TEXT,
                            (card.x + 32, card.y + 28))
            y = card.y + 72
            for line in self.tournament_summary_text.splitlines():
                self.screen.blit(self.mono_font.render(line, True, col.TEXT), (card.x + 32, y))
                y += 26
            theme.draw_text(self.screen, "Saved to data/tournament_results/ (results.json, results.csv)",
                            theme.font(theme.SIZE_CAPTION), col.SUCCESS, (card.x + 32, y + 16))

        self.btn_tourney_back.render(self.screen)
