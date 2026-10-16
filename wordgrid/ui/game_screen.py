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
from wordgrid.ui.word_history_panel import WordHistoryPanel
from wordgrid.ui.controls import Button
from wordgrid.ui.colors import (
    COLOR_BG_DARK,
    COLOR_PANEL_BG,
    COLOR_PANEL_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_DIM,
    COLOR_P1,
    COLOR_P2,
    COLOR_HIGHLIGHT_WORD,
    COLOR_CARD_BG,
    COLOR_CARD_BORDER,
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
            rect=pygame.Rect(590, 40, 470, 260),
            title_font=title_font,
            font=font,
            small_font=small_font,
        )
        self.word_history_panel = WordHistoryPanel(
            rect=pygame.Rect(590, 315, 470, 355),
            title_font=title_font,
            font=font,
            small_font=small_font,
        )

        # AI vs AI controls
        self.is_ai_vs_ai = (p1_agent is not None and p2_agent is not None)
        self.has_any_ai = (p1_agent is not None or p2_agent is not None)
        self.auto_play = True
        self.ai_delay_seconds = 0.35
        self.last_move_time = time.time()

        # Threading for non-blocking search
        self.ai_thread: Optional[threading.Thread] = None
        self.pending_ai_move: Optional[Tuple[Move, Dict[str, Any]]] = None
        self.ai_searching = False
        self.last_ai_stats: Optional[Dict[str, Any]] = None

        # Bottom buttons evenly distributed across the 520px board width
        btn_y = 625
        btn_h = 42
        btn_w = 121
        self.btn_back = Button(
            rect=pygame.Rect(40, btn_y, btn_w, btn_h),
            text="Menu",
            font=font,
            callback=self.on_back_to_menu,
        )
        self.btn_reset = Button(
            rect=pygame.Rect(173, btn_y, btn_w, btn_h),
            text="Reset",
            font=font,
            callback=self.reset_match,
        )
        self.btn_pause = Button(
            rect=pygame.Rect(306, btn_y, btn_w, btn_h),
            text="Pause" if self.auto_play else "Resume",
            font=font,
            callback=self.toggle_pause,
        )
        self.btn_step = Button(
            rect=pygame.Rect(439, btn_y, btn_w, btn_h),
            text="Step Move",
            font=font,
            callback=self.step_ai_move,
        )
        if not self.has_any_ai:
            self.btn_pause.enabled = False
            self.btn_step.enabled = False

        # Alphabet quick bar for Human clicks
        self.alpha_rects: List[Tuple[str, pygame.Rect]] = []
        self._init_alphabet_bar()

    def _init_alphabet_bar(self):
        start_x = 40
        start_y = 574
        w, h = 18, 32
        import string
        for idx, ch in enumerate(string.ascii_uppercase):
            r = pygame.Rect(start_x + idx * (w + 2), start_y, w, h)
            self.alpha_rects.append((ch, r))

    def reset_match(self):
        self.engine.reset()
        self.word_history_panel.clear()
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

    def _record_matched_words(self, player_id: int, player_name: str, move: Move):
        occurrences = getattr(self.engine.state, "last_scored_occurrences", None)
        if occurrences:
            for word, length, occ_key in occurrences:
                self.word_history_panel.add_match(
                    word=word,
                    length=length,
                    player=player_id,
                    player_name=player_name,
                    move_number=self.engine.state.move_count,
                    move=move,
                    occurrence_key=occ_key,
                )
        elif self.engine.state.last_scored_words:
            for word, length in self.engine.state.last_scored_words:
                self.word_history_panel.add_match(
                    word=word,
                    length=length,
                    player=player_id,
                    player_name=player_name,
                    move_number=self.engine.state.move_count,
                    move=move,
                    occurrence_key=None,
                )

    def handle_event(self, event: pygame.event.Event):
        self.btn_back.handle_event(event)
        self.btn_reset.handle_event(event)
        if self.has_any_ai:
            self.btn_pause.handle_event(event)
            self.btn_step.handle_event(event)

        # Matched words panel scrolling and selection
        self.word_history_panel.handle_event(event)

        # Deselect cell on Escape
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.board_renderer.selected_cell = None

        # Human turn interaction
        if not self.current_agent_is_ai() and not self.engine.is_game_over:
            # Mouse click on grid
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                cell = self.board_renderer.get_cell_at_pos(self.engine.state.board, event.pos)
                if cell:
                    if self.engine.state.board.is_empty(cell[0], cell[1]):
                        self.board_renderer.selected_cell = cell
                    else:
                        self.board_renderer.selected_cell = None

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
        move = (r, c, letter)
        if self.engine.rules.is_legal_move(self.engine.state, move):
            p_id = self.engine.state.current_player
            p_name = self.p1_name if p_id == 1 else self.p2_name
            self.engine.make_move(move)
            self._record_matched_words(p_id, p_name, move)
            self.board_renderer.selected_cell = None
            self.last_move_time = time.time()

    def update(self):
        # Apply pending AI move when search thread finishes
        if self.pending_ai_move:
            move, stats = self.pending_ai_move
            self.pending_ai_move = None
            self.last_ai_stats = stats
            p_id = self.engine.state.current_player
            p_name = self.p1_name if p_id == 1 else self.p2_name
            self.engine.make_move(move)
            self._record_matched_words(p_id, p_name, move)
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

        # Highlight on board: hovered history word > selected history word > latest scored word
        highlight_occ = None
        hovered = self.word_history_panel.hovered_item
        selected = self.word_history_panel.selected_item

        if hovered and hovered.occurrence_key:
            highlight_occ = [(hovered.word, hovered.length, hovered.occurrence_key)]
        elif selected and selected.occurrence_key:
            highlight_occ = [(selected.word, selected.length, selected.occurrence_key)]
        elif getattr(self.engine.state, "last_scored_occurrences", None):
            highlight_occ = self.engine.state.last_scored_occurrences

        # Render Board
        self.board_renderer.render(
            surface=surface,
            board=self.engine.state.board,
            last_move=self.engine.state.last_move,
            highlight_occurrences=highlight_occ,
        )

        # Render Alphabet Bar (stable presence without layout shift)
        is_human_turn = not self.current_agent_is_ai() and not self.engine.is_game_over
        has_sel = self.board_renderer.selected_cell is not None
        mouse_pos = pygame.mouse.get_pos()

        for ch, r in self.alpha_rects:
            if is_human_turn:
                is_hover = r.collidepoint(mouse_pos)
                if is_hover and has_sel:
                    bg = pygame.Color(14, 116, 144)
                    border_col = COLOR_P1
                elif is_hover:
                    bg = pygame.Color(51, 65, 85)
                    border_col = COLOR_TEXT_MUTED
                else:
                    bg = COLOR_PANEL_BG
                    border_col = COLOR_PANEL_BORDER
                txt_col = COLOR_TEXT_PRIMARY
            else:
                bg = COLOR_CARD_BG
                border_col = COLOR_CARD_BORDER
                txt_col = COLOR_TEXT_DIM

            pygame.draw.rect(surface, bg, r, border_radius=4)
            pygame.draw.rect(surface, border_col, r, width=1, border_radius=4)
            t = self.small_font.render(ch, True, txt_col)
            surface.blit(t, t.get_rect(center=r.center))

        # Render Statistics Panel
        self.stats_panel.render(
            surface=surface,
            state=self.engine.state,
            p1_name=self.p1_name,
            p2_name=self.p2_name,
            ai_stats=self.last_ai_stats,
            ai_searching=self.ai_searching,
        )

        # Render Word History Panel beside the board
        self.word_history_panel.render(surface=surface)

        # Render Buttons
        self.btn_back.render(surface)
        self.btn_reset.render(surface)
        self.btn_pause.render(surface)
        self.btn_step.render(surface)
