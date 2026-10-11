import time
import threading
import pygame
from typing import Optional, Dict, Any, Tuple, List
from wordgrid.game.engine import GameEngine
from wordgrid.game.rules import Move
from wordgrid.game.scoring import WordValidatorProtocol
from wordgrid.ai.base_agent import BaseAgent
from wordgrid.ui.board_renderer import BoardRenderer
from wordgrid.ui.statistics_panel import StatisticsPanel
from wordgrid.ui.controls import Button
from wordgrid.ui.colors import (
    COLOR_BG_DARK,
    COLOR_PANEL_BG,
    COLOR_PANEL_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_P1,
    COLOR_P2,
    COLOR_BTN_SUCCESS,
    COLOR_BTN_DANGER,
)


class GameScreen:
    """Manages active match gameplay, non-blocking AI threads, and user interaction."""

    def __init__(
        self,
        engine: GameEngine,
        validator: WordValidatorProtocol,
        p1_agent: Optional[BaseAgent],  # None means Human
        p2_agent: Optional[BaseAgent],  # None means Human
        p1_name: str,
        p2_name: str,
        title_font: pygame.font.Font,
        font: pygame.font.Font,
        small_font: pygame.font.Font,
        on_back_to_menu: Any,
    ):
        self.engine = engine
        self.validator = validator
        self.p1_agent = p1_agent
        self.p2_agent = p2_agent
        self.p1_name = p1_name
        self.p2_name = p2_name
        self.title_font = title_font
        self.font = font
        self.small_font = small_font
        self.on_back_to_menu = on_back_to_menu

        # Board & Panel layout
        self.board_renderer = BoardRenderer(
            board_rect=pygame.Rect(40, 40, 520, 520),
            font=font,
            small_font=small_font,
        )
        self.stats_panel = StatisticsPanel(
            rect=pygame.Rect(600, 40, 460, 520),
            title_font=title_font,
            font=font,
            small_font=small_font,
        )

        # AI vs AI controls
        self.is_ai_vs_ai = (p1_agent is not None and p2_agent is not None)
        self.auto_play = True
        self.ai_delay_seconds = 0.35
        self.last_move_time = time.time()

        # Threading for non-blocking search
        self.ai_thread: Optional[threading.Thread] = None
        self.pending_ai_move: Optional[Tuple[Move, Dict[str, Any]]] = None
        self.ai_searching = False
        self.last_ai_stats: Optional[Dict[str, Any]] = None

        # Bottom buttons
        btn_y = 620
        self.btn_back = Button(
            rect=pygame.Rect(40, btn_y, 140, 40),
            text="Menu",
            font=font,
            callback=self.on_back_to_menu,
        )
        self.btn_reset = Button(
            rect=pygame.Rect(200, btn_y, 140, 40),
            text="Reset Match",
            font=font,
            callback=self.reset_match,
        )
        self.btn_pause = Button(
            rect=pygame.Rect(360, btn_y, 140, 40),
            text="Pause" if self.auto_play else "Resume",
            font=font,
            callback=self.toggle_pause,
        )
        self.btn_step = Button(
            rect=pygame.Rect(520, btn_y, 140, 40),
            text="Step Move",
            font=font,
            callback=self.step_ai_move,
        )

        # Alphabet quick bar for Human clicks
        self.alpha_rects: List[Tuple[str, pygame.Rect]] = []
        self._init_alphabet_bar()

    def _init_alphabet_bar(self):
        start_x = 40
        start_y = 575
        w, h = 18, 26
        import string
        for idx, ch in enumerate(string.ascii_uppercase):
            r = pygame.Rect(start_x + idx * (w + 2), start_y, w, h)
            self.alpha_rects.append((ch, r))

    def reset_match(self):
        self.engine.reset()
        self.ai_thread = None
        self.pending_ai_move = None
        self.ai_searching = False
        self.last_ai_stats = None
        self.board_renderer.selected_cell = None

    def toggle_pause(self):
        self.auto_play = not self.auto_play
        self.btn_pause.text = "Pause" if self.auto_play else "Resume"

    def step_ai_move(self):
        if not self.engine.is_game_over and not self.ai_searching:
            self._trigger_ai_search()

    def current_agent_is_ai(self) -> bool:
        if self.engine.state.current_player == 1:
            return self.p1_agent is not None
        else:
            return self.p2_agent is not None

    def get_current_ai_agent(self) -> Optional[BaseAgent]:
        if self.engine.state.current_player == 1:
            return self.p1_agent
        else:
            return self.p2_agent

    def _trigger_ai_search(self):
        agent = self.get_current_ai_agent()
        if agent is None or self.ai_searching or self.engine.is_game_over:
            return

        self.ai_searching = True
        state_clone = self.engine.state.clone()

        def _worker():
            try:
                move = agent.select_move(state_clone, self.validator)
                stats = agent.get_last_stats()
                self.pending_ai_move = (move, stats)
            finally:
                self.ai_searching = False

        self.ai_thread = threading.Thread(target=_worker, daemon=True)
        self.ai_thread.start()

    def handle_event(self, event: pygame.event.Event):
        self.btn_back.handle_event(event)
        self.btn_reset.handle_event(event)
        if self.is_ai_vs_ai:
            self.btn_pause.handle_event(event)
            self.btn_step.handle_event(event)

        # Human turn interaction
        if not self.current_agent_is_ai() and not self.engine.is_game_over:
            # Mouse click on grid
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                cell = self.board_renderer.get_cell_at_pos(self.engine.state.board, event.pos)
                if cell and self.engine.state.board.is_empty(cell[0], cell[1]):
                    self.board_renderer.selected_cell = cell

                # Click on alphabet bar
                for ch, r in self.alpha_rects:
                    if r.collidepoint(event.pos) and self.board_renderer.selected_cell:
                        sr, sc = self.board_renderer.selected_cell
                        self._apply_human_move(sr, sc, ch)
                        break

            # Keyboard letter typing
            elif event.type == pygame.KEYDOWN and self.board_renderer.selected_cell:
                ch = event.unicode.upper()
                if ch.isalpha() and len(ch) == 1:
                    sr, sc = self.board_renderer.selected_cell
                    self._apply_human_move(sr, sc, ch)

    def _apply_human_move(self, r: int, c: int, letter: str):
        if self.engine.rules.is_legal_move(self.engine.state, (r, c, letter)):
            self.engine.make_move((r, c, letter))
            self.board_renderer.selected_cell = None
            self.last_move_time = time.time()

    def update(self):
        # Apply pending AI move when search thread finishes
        if self.pending_ai_move:
            move, stats = self.pending_ai_move
            self.pending_ai_move = None
            self.last_ai_stats = stats
            self.engine.make_move(move)
            self.last_move_time = time.time()

        # Handle automatic AI turn progression
        if (
            self.current_agent_is_ai()
            and not self.engine.is_game_over
            and not self.ai_searching
            and self.auto_play
        ):
            if time.time() - self.last_move_time >= self.ai_delay_seconds:
                self._trigger_ai_search()

    def render(self, surface: pygame.Surface):
        surface.fill(COLOR_BG_DARK)

        # Render Board
        self.board_renderer.render(
            surface=surface,
            board=self.engine.state.board,
            last_move=self.engine.state.last_move,
            highlight_occurrences=[
                (w, l, k) for w, l in self.engine.state.last_scored_words for k in [("", 0, 0, 0, 0)]
            ] if False else None,
        )

        # Render Alphabet Drawer if Human turn
        if not self.current_agent_is_ai() and not self.engine.is_game_over:
            mouse_pos = pygame.mouse.get_pos()
            for ch, r in self.alpha_rects:
                is_hover = r.collidepoint(mouse_pos)
                bg = pygame.Color(71, 85, 105) if is_hover else COLOR_PANEL_BG
                pygame.draw.rect(surface, bg, r, border_radius=3)
                pygame.draw.rect(surface, COLOR_PANEL_BORDER, r, width=1, border_radius=3)
                t = self.small_font.render(ch, True, COLOR_TEXT_PRIMARY)
                surface.blit(t, t.get_rect(center=r.center))

        # Render Statistics Panel
        self.stats_panel.render(
            surface=surface,
            state=self.engine.state,
            p1_name=self.p1_name,
            p2_name=self.p2_name,
            ai_stats=self.last_ai_stats,
        )

        # Render Buttons
        self.btn_back.render(surface)
        self.btn_reset.render(surface)
        if self.is_ai_vs_ai:
            self.btn_pause.render(surface)
            self.btn_step.render(surface)

        # Searching spinner / text indicator
        if self.ai_searching:
            search_txt = self.font.render("AI is calculating optimal move...", True, COLOR_P1)
            surface.blit(search_txt, (600, 580))
