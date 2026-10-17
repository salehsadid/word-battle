import random
import string
import time
import threading
import pygame
from typing import Optional, Dict, Any, Tuple, List, Callable
from wordgrid.game.engine import GameEngine
from wordgrid.game.rules import Move
from wordgrid.game.scoring import WordValidatorProtocol
from wordgrid.ai.base_agent import BaseAgent
from wordgrid.settings import (
    MatchSettings,
    CONTROLLER_HUMAN,
    CONTROLLER_RANDOM,
    DIFFICULTY_CUSTOM,
    MATCH_HUMAN_VS_AI,
    MATCH_AI_VS_AI,
)
from wordgrid.ui import colors as col
from wordgrid.ui import theme
from wordgrid.ui.board_renderer import BoardRenderer
from wordgrid.ui.statistics_panel import (
    StatisticsPanel,
    InsightPanel,
    render_info_strip,
    friendly_ai_text,
    ai_details_text,
    cell_label,
)
from wordgrid.ui.word_history_panel import WordHistoryPanel
from wordgrid.ui.controls import Button, wrap_text
from wordgrid.ui.dialogs import ConfirmDialog, HelpOverlay

EngineFactory = Callable[[MatchSettings, WordValidatorProtocol, random.Random],
                         Tuple[GameEngine, Dict[int, Optional[BaseAgent]]]]

TOAST_SECONDS = 1.8
TOOLTIP_DELAY = 0.6
MATCH_TITLES = {MATCH_HUMAN_VS_AI: "Play vs Computer", MATCH_AI_VS_AI: "AI vs AI"}


class LetterPicker:
    """Small A-Z panel that pops up next to the selected square."""

    COLS, KEY, GAP, PAD, HEADER = 7, 36, 5, 12, 26

    def __init__(self):
        self.visible = False
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.keys: List[Tuple[str, pygame.Rect]] = []

    def open(self, anchor: pygame.Rect, bounds: pygame.Rect) -> None:
        rows = (26 + self.COLS - 1) // self.COLS
        w = 2 * self.PAD + self.COLS * self.KEY + (self.COLS - 1) * self.GAP
        h = 2 * self.PAD + self.HEADER + rows * self.KEY + (rows - 1) * self.GAP
        rect = pygame.Rect(anchor.right + 10, anchor.centery - h // 2, w, h)
        if rect.right > bounds.right:
            rect.right = anchor.x - 10
        rect.clamp_ip(bounds)
        self.rect = rect
        self.keys = []
        for i, ch in enumerate(string.ascii_uppercase):
            r, c = divmod(i, self.COLS)
            key = pygame.Rect(rect.x + self.PAD + c * (self.KEY + self.GAP),
                              rect.y + self.PAD + self.HEADER + r * (self.KEY + self.GAP), self.KEY, self.KEY)
            self.keys.append((ch, key))
        self.visible = True

    def close(self) -> None:
        self.visible = False

    def letter_at(self, pos) -> Optional[str]:
        if not self.visible:
            return None
        return next((ch for ch, r in self.keys if r.collidepoint(pos)), None)

    def render(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        theme.draw_card(surface, self.rect, radius=14)
        theme.draw_text(surface, "Pick a letter  (or just type it)", theme.font(theme.SIZE_CAPTION, bold=True),
                        col.TEXT_MUTED, (self.rect.x + self.PAD, self.rect.y + self.PAD - 2))
        mouse = pygame.mouse.get_pos()
        fnt = theme.font(theme.SIZE_HEADING, bold=True)
        for ch, r in self.keys:
            hover = r.collidepoint(mouse)
            theme.aa_rect(surface, col.PRIMARY if hover else col.SURFACE_ALT, r, border_radius=8)
            theme.draw_text(surface, ch, fnt, col.TEXT_ON_ACCENT if hover else col.TEXT, r.center, "center")


class GameScreen:
    """Runs a match: human input, non-blocking AI turns, history, and the result screen."""

    def __init__(
        self,
        settings: MatchSettings,
        validator: WordValidatorProtocol,
        build_engine: EngineFactory,
        title_font=None,
        font=None,
        small_font=None,
        on_back_to_menu: Callable[[], None] = lambda: None,
    ):
        self.settings = settings
        self.validator = validator
        self.build_engine = build_engine
        self.on_back_to_menu = on_back_to_menu
        self.rng = random.Random(settings.seed)

        self.names = {1: settings.p1.name, 2: settings.p2.name}
        self.p1_name, self.p2_name = self.names[1], self.names[2]
        self.roles = {pid: self._role_label(pid) for pid in (1, 2)}

        # Layout
        self.banner_rect = pygame.Rect(40, 82, 520, 46)
        self.board_renderer = BoardRenderer(pygame.Rect(62, 158, 478, 478))
        self.stats_panel = StatisticsPanel(pygame.Rect(590, 82, 470, 150))
        self.info_rect = pygame.Rect(590, 244, 470, 28)
        self.insight = InsightPanel(pygame.Rect(590, 284, 470, 118))
        self.word_history_panel = WordHistoryPanel(pygame.Rect(590, 414, 470, 306))

        self.picker = LetterPicker()
        self.confirm = ConfirmDialog()
        self.help = HelpOverlay()
        self.show_details = settings.show_ai_details
        self.auto_play = True
        self.overlay_dismissed = False
        self.message: Optional[Tuple[str, float]] = None
        self.toast: Optional[Dict[str, Any]] = None
        self.flash: Optional[Tuple[Any, float]] = None
        self._hover: Tuple[Optional[Tuple[int, int]], float] = (None, 0.0)

        # Threading for non-blocking search; generation guards against stale results
        self._generation = 0
        self._lock = threading.Lock()
        self.pending_ai_move: Optional[Tuple[int, Move, Dict[str, Any]]] = None
        self.ai_searching = False
        self.ai_error: Optional[str] = None
        self.last_ai_stats: Optional[Dict[str, Any]] = None

        # Top bar
        self.btn_help = Button(pygame.Rect(800, 26, 130, 40), "How to play", variant="ghost",
                               callback=self.help.open)
        self.btn_back = Button(pygame.Rect(940, 26, 120, 40), "Settings", callback=self._ask_leave)
        # Controls under the board
        self.btn_reset = Button(pygame.Rect(40, 656, 140, 44), "Restart", callback=self._ask_restart)
        self.btn_pause = Button(pygame.Rect(190, 656, 120, 44), "Pause", callback=self.toggle_pause)
        self.btn_step = Button(pygame.Rect(320, 656, 120, 44), "Step", callback=self.step_ai_move)
        self.btn_details = Button(pygame.Rect(0, 0, 112, 30), "Details", variant="ghost",
                                  font=theme.font(theme.SIZE_CAPTION, bold=True), callback=self._toggle_details)
        # Result card
        self.result_card = pygame.Rect(0, 0, 480, 330)
        self.btn_rematch = Button(pygame.Rect(0, 0, 140, 46), "Play again", variant="primary",
                                  callback=self.reset_match)
        self.btn_new = Button(pygame.Rect(0, 0, 160, 46), "Change settings", callback=self.on_back_to_menu)
        self.btn_view = Button(pygame.Rect(0, 0, 120, 46), "View board", variant="ghost",
                               callback=self._dismiss_overlay)

        self.engine: GameEngine
        self.agents: Dict[int, Optional[BaseAgent]] = {}
        self._new_match()

    # ------------------------------------------------------------------ setup
    def _role_label(self, pid: int) -> str:
        p = self.settings.player(pid)
        if p.controller == CONTROLLER_HUMAN:
            return "Human player"
        if p.controller == CONTROLLER_RANDOM:
            return "Computer · random moves"
        level = "custom settings" if p.difficulty == DIFFICULTY_CUSTOM else p.difficulty
        return f"Computer · {level}"

    def _new_match(self) -> None:
        with self._lock:
            self._generation += 1
            self.pending_ai_move = None
        self.engine, self.agents = self.build_engine(self.settings, self.validator, self.rng)
        self.p1_agent = self.agents.get(1)
        self.p2_agent = self.agents.get(2)
        self.has_any_ai = self.p1_agent is not None or self.p2_agent is not None
        self.is_ai_vs_ai = self.p1_agent is not None and self.p2_agent is not None
        self.btn_pause.visible = self.btn_step.visible = self.is_ai_vs_ai
        self.word_history_panel.clear()
        self.stats_panel.clear()
        self.ai_searching = False
        self.ai_error = None
        self.last_ai_stats = None
        self.overlay_dismissed = False
        self.toast = None
        self.flash = None
        self.board_renderer.selected_cell = None
        self.picker.close()
        self.last_move_time = time.time()
        self.auto_play = True
        self.btn_pause.text = "Pause"

    def reset_match(self) -> None:
        """Restarts with the same settings."""
        self._new_match()

    def shutdown(self) -> None:
        """Invalidates any running AI search (its result will be ignored)."""
        with self._lock:
            self._generation += 1
            self.pending_ai_move = None

    # ------------------------------------------------------------------ helpers
    def _in_progress(self) -> bool:
        return self.engine.state.move_count > 0 and not self.engine.is_game_over

    def _ask_leave(self) -> None:
        if self._in_progress():
            self.confirm.open("Leave this match?", "The current game will be lost. Your settings are kept.",
                              "Leave", self.on_back_to_menu)
        else:
            self.on_back_to_menu()

    def _ask_restart(self) -> None:
        if self._in_progress():
            self.confirm.open("Restart the match?", "The board will be cleared and both scores reset to 0.",
                              "Restart", self.reset_match)
        else:
            self.reset_match()

    def _flash_message(self, text: str, seconds: float = 3.0) -> None:
        self.message = (text, time.time() + seconds)

    def _dismiss_overlay(self) -> None:
        self.overlay_dismissed = True

    def _toggle_details(self) -> None:
        self.show_details = not self.show_details

    def toggle_pause(self) -> None:
        self.auto_play = not self.auto_play
        self.btn_pause.text = "Pause" if self.auto_play else "Resume"

    def step_ai_move(self) -> None:
        """Plays exactly one AI move (useful while paused)."""
        if self.engine.is_game_over or self.ai_searching or not self.current_agent_is_ai():
            return
        self._trigger_ai_search()

    def current_agent_is_ai(self) -> bool:
        return self.get_current_ai_agent() is not None

    def get_current_ai_agent(self) -> Optional[BaseAgent]:
        return self.agents.get(self.engine.state.current_player)

    def _human_turn(self) -> bool:
        return not self.current_agent_is_ai() and not self.engine.is_game_over

    def _turn_owner(self, pid: int) -> str:
        if self.settings.match_type == MATCH_HUMAN_VS_AI and self.settings.player(pid).is_human:
            return "Your"
        return f"{self.names[pid]}'s"

    # ------------------------------------------------------------------ AI
    def _trigger_ai_search(self) -> None:
        agent = self.get_current_ai_agent()
        if agent is None or self.ai_searching or self.engine.is_game_over:
            return
        self.ai_searching = True
        state_clone = self.engine.state.clone()
        generation = self._generation

        def _worker():
            try:
                move = agent.select_move(state_clone, self.validator)
                stats = agent.get_last_stats()
                with self._lock:
                    if generation == self._generation:
                        self.pending_ai_move = (generation, move, stats)
            except Exception as ex:  # surface errors instead of silently stalling
                with self._lock:
                    if generation == self._generation:
                        self.ai_error = f"The AI ran into a problem: {ex}"
            finally:
                if generation == self._generation:
                    self.ai_searching = False

        threading.Thread(target=_worker, daemon=True).start()

    # ------------------------------------------------------------------ moves
    def _after_move(self, player: int) -> None:
        entry = self.engine.move_log[-1]
        name = self.names[player]
        self.word_history_panel.add_move(
            move_number=entry["move_count"], player=player, player_name=name, move=entry["move"],
            points=entry["points"], word=entry["word"], occurrence_key=entry["occurrence"],
            blocked_words=entry["blocked_words"],
        )
        now = time.time()
        if entry["points"] > 0:
            self.word_history_panel.add_match(
                word=entry["word"], length=entry["points"], player=player, player_name=name,
                move_number=entry["move_count"], move=entry["move"], occurrence_key=entry["occurrence"],
            )
            self.stats_panel.add_score_popup(player, entry["points"])
            self.toast = {"text": f"{entry['word']}  +{entry['points']}", "kind": "score", "player": player, "t0": now}
            self.flash = (entry["occurrence"], now)
        elif entry["blocked_words"]:
            self.toast = {"text": f"{entry['blocked_words'][0]} was already used - no points", "kind": "info",
                          "player": player, "t0": now}
        else:
            self.toast = {"text": "No word formed", "kind": "info", "player": player, "t0": now}
        self.board_renderer.selected_cell = None
        self.picker.close()
        self.last_move_time = now

    def _apply_human_move(self, r: int, c: int, letter: str) -> None:
        move = (r, c, letter.upper())
        if not self.engine.rules.is_legal_move(self.engine.state, move):
            self._flash_message("That square is already taken.")
            return
        player = self.engine.state.current_player
        self.engine.make_move(move)
        self._after_move(player)

    def _select_cell(self, cell: Optional[Tuple[int, int]]) -> None:
        self.board_renderer.selected_cell = cell
        if cell is None:
            self.picker.close()
        else:
            anchor = self.board_renderer.cell_rect(self.engine.state.board, *cell)
            self.picker.open(anchor, pygame.Rect(8, 8, 1084, 744))

    # ------------------------------------------------------------------ events
    def _overlay_visible(self) -> bool:
        return self.engine.is_game_over and not self.overlay_dismissed

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.help.handle_event(event) or self.confirm.handle_event(event):
            return
        if event.type == pygame.KEYDOWN and (event.key == pygame.K_F1 or event.unicode == "?"):
            self.help.open()
            return

        if self._overlay_visible():
            for btn in (self.btn_rematch, self.btn_new, self.btn_view):
                if btn.handle_event(event):
                    return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._dismiss_overlay()
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                return

        for btn in (self.btn_help, self.btn_back, self.btn_reset, self.btn_pause, self.btn_step):
            if btn.handle_event(event):
                return
        if self.last_ai_stats and self.btn_details.handle_event(event):
            return
        self.word_history_panel.handle_event(event)

        human_turn = self._human_turn()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._select_cell(None)
                return
            if self.is_ai_vs_ai and event.key == pygame.K_SPACE:
                self.toggle_pause()
                return
            if self.is_ai_vs_ai and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.step_ai_move()
                return
            if human_turn and event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                self._move_selection(event.key)
                return
            if human_turn and self.board_renderer.selected_cell:
                ch = event.unicode.upper()
                if len(ch) == 1 and ch in string.ascii_uppercase:
                    self._apply_human_move(*self.board_renderer.selected_cell, ch)
            return

        if not human_turn or event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        letter = self.picker.letter_at(event.pos)
        if letter and self.board_renderer.selected_cell:
            self._apply_human_move(*self.board_renderer.selected_cell, letter)
            return
        if self.picker.visible and self.picker.rect.collidepoint(event.pos):
            return
        cell = self.board_renderer.get_cell_at_pos(self.engine.state.board, event.pos)
        if cell is None:
            self._select_cell(None)
        elif self.engine.state.board.is_empty(*cell):
            self._select_cell(None if cell == self.board_renderer.selected_cell else cell)
        else:
            self._select_cell(None)
            self._flash_message("That square is already taken - pick an empty one.")

    def _move_selection(self, key: int) -> None:
        size = self.engine.state.board.size
        current = self.board_renderer.selected_cell
        if current is None:
            r, c = size // 2, size // 2
        else:
            dr, dc = {pygame.K_UP: (-1, 0), pygame.K_DOWN: (1, 0), pygame.K_LEFT: (0, -1), pygame.K_RIGHT: (0, 1)}[key]
            r, c = (current[0] + dr) % size, (current[1] + dc) % size
        self._select_cell((r, c))

    # ------------------------------------------------------------------ update
    def update(self) -> None:
        with self._lock:
            pending = self.pending_ai_move
            self.pending_ai_move = None
        if pending and pending[0] == self._generation and not self.engine.is_game_over:
            _, move, stats = pending
            player = self.engine.state.current_player
            self.last_ai_stats = stats
            self.engine.make_move(move)
            self._after_move(player)

        if (
            self.current_agent_is_ai()
            and not self.engine.is_game_over
            and not self.ai_searching
            and self.auto_play
            and self.ai_error is None
            and not self.confirm.visible
            and time.time() - self.last_move_time >= self.settings.ai_move_delay
        ):
            self._trigger_ai_search()

    # ------------------------------------------------------------------ text
    def _banner(self) -> Tuple[str, pygame.Color, pygame.Color]:
        state = self.engine.state
        if state.is_terminal:
            if state.winner in (1, 2):
                winner = "You win" if self._turn_owner(state.winner) == "Your" else f"{self.names[state.winner]} wins"
                return f"Match over - {winner}!", col.player_color(state.winner), col.player_soft(state.winner)
            return "Match over - it's a draw!", col.SUCCESS, col.SUCCESS_SOFT
        pid = state.current_player
        accent, soft = col.player_color(pid), col.player_soft(pid)
        if self.current_agent_is_ai():
            if self.is_ai_vs_ai and not self.auto_play:
                return f"Paused - press Step to see {self.names[pid]}'s next move", accent, soft
            dots = "." * (int(time.time() * 3) % 4)
            return f"{self.names[pid]} is thinking{dots}", accent, soft
        owner = self._turn_owner(pid)
        if self.board_renderer.selected_cell:
            r, c = self.board_renderer.selected_cell
            return f"{owner} turn - now choose a letter for {cell_label(r, c)}", accent, soft
        return f"{owner} turn - click an empty square", accent, soft

    def _insight_content(self) -> Tuple[str, str, Optional[str], pygame.Color, bool]:
        state = self.engine.state
        if self.ai_error:
            return "Something went wrong", self.ai_error, None, col.DANGER, False
        if self.ai_searching:
            pid = state.current_player
            return f"{self.names[pid]} is thinking", "Looking for the best move", None, col.player_color(pid), True
        if not self.engine.move_log:
            starter = self.names[state.current_player]
            return ("Ready to play", f"{starter} goes first. Build words across rows or columns; "
                    "only the longest new word scores.", None, col.PRIMARY, False)
        entry = self.engine.move_log[-1]
        pid = entry["player"]
        name = self.names[pid]
        r, c, ch = entry["move"]
        stats = self.last_ai_stats
        if self.agents.get(pid) and stats and tuple(stats.get("selected_move", ())) == tuple(entry["move"]):
            if self.settings.show_ai_explanations:
                text = friendly_ai_text(stats, name, self.names[3 - pid])
            else:
                text = f"{name} placed {ch} at {cell_label(r, c)}."
            details = ai_details_text(stats) if self.show_details else None
            return f"{name}'s move", text, details, col.player_color(pid), False
        if entry["points"]:
            text = f"{name} placed {ch} at {cell_label(r, c)}, making {entry['word']} for +{entry['points']}."
        elif entry["blocked_words"]:
            text = f"{name} placed {ch} at {cell_label(r, c)}. {entry['blocked_words'][0]} was already used, so no points."
        else:
            text = f"{name} placed {ch} at {cell_label(r, c)}. No new word this time."
        return "Last move", text, None, col.player_color(pid), False

    # ------------------------------------------------------------------ render
    def _render_top_bar(self, surface) -> None:
        theme.draw_logo(surface, (40, 20), tile=26, gap=3)
        s = self.settings
        title = MATCH_TITLES.get(s.match_type, "Two Players")
        board = self.engine.state.board.size
        theme.draw_text(surface, f"{title}  ·  {board}×{board} board  ·  "
                                 f"{self.names[1]} vs {self.names[2]}",
                        theme.font(theme.SIZE_CAPTION), col.TEXT_MUTED, (40, 58))
        self.btn_help.render(surface)
        self.btn_back.render(surface)

    def _render_banner(self, surface) -> None:
        text, accent, soft = self._banner()
        rect = self.banner_rect
        theme.aa_rect(surface, soft, rect, border_radius=12)
        theme.aa_rect(surface, accent, (rect.x, rect.y, 6, rect.height), border_top_left_radius=12,
                         border_bottom_left_radius=12)
        theme.draw_text(surface, text, theme.font(theme.SIZE_HEADING, bold=True), col.TEXT,
                        (rect.x + 22, rect.centery), "midleft", max_width=rect.width - 40)

    def _render_toast(self, surface) -> None:
        if not self.toast:
            return
        age = time.time() - self.toast["t0"]
        if age > TOAST_SECONDS:
            self.toast = None
            return
        score = self.toast["kind"] == "score"
        fnt = theme.font(theme.SIZE_HEADING if score else theme.SIZE_BODY, bold=True)
        surf = fnt.render(self.toast["text"], True, col.TEXT_ON_ACCENT if score else col.TEXT_MUTED)
        rect = pygame.Rect(0, 0, surf.get_width() + 32, surf.get_height() + 14)
        rect.midtop = (self.board_renderer.board_rect.centerx, self.board_renderer.board_rect.y + 14 - int(age * 6))
        alpha = 255 if age < TOAST_SECONDS - 0.4 else int(255 * (TOAST_SECONDS - age) / 0.4)
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        fill = col.SUCCESS if score else col.SURFACE
        theme.aa_rect(layer, (*fill[:3], alpha), layer.get_rect(), border_radius=rect.height // 2)
        if not score:
            theme.aa_rect(layer, (*col.BORDER[:3], alpha), layer.get_rect(), width=1, border_radius=rect.height // 2)
        surf.set_alpha(alpha)
        layer.blit(surf, (16, 7))
        surface.blit(layer, rect)

    def _render_tooltip(self, surface) -> None:
        board = self.engine.state.board
        mouse = pygame.mouse.get_pos()
        cell = self.board_renderer.get_cell_at_pos(board, mouse)
        if self.picker.visible and self.picker.rect.collidepoint(mouse):
            cell = None
        if cell != self._hover[0]:
            self._hover = (cell, time.time())
            return
        if cell is None or time.time() - self._hover[1] < TOOLTIP_DELAY:
            return
        r, c = cell
        letter = board.grid[r][c]
        text = f"Row {r + 1}, column {c + 1}" + (f"  ·  {letter}" if letter else "")
        theme.draw_tooltip(surface, text, mouse)

    def _render_controls(self, surface) -> None:
        self.btn_reset.text = "Play again" if self.engine.is_game_over else "Restart"
        self.btn_pause.enabled = self.btn_step.enabled = not self.engine.is_game_over
        self.btn_step.enabled = self.btn_step.enabled and not self.ai_searching
        for btn in (self.btn_reset, self.btn_pause, self.btn_step):
            btn.render(surface)
        if self.message and time.time() < self.message[1]:
            text, color = self.message[0], col.DANGER
        elif self.is_ai_vs_ai:
            text, color = "Space pauses, Enter steps one move. F1 opens the guide.", col.TEXT_SUBTLE
        else:
            text, color = "Tip: arrow keys move the selection and typing places a letter.", col.TEXT_SUBTLE
        theme.draw_text(surface, text, theme.font(theme.SIZE_CAPTION), color, (40, 714), max_width=520)

    def _render_result(self, surface) -> None:
        state = self.engine.state
        theme.draw_overlay(surface)
        card = self.result_card
        card.center = surface.get_rect().center
        theme.draw_card(surface, card, radius=18)
        if state.winner in (1, 2):
            accent = col.player_color(state.winner)
            you = self._turn_owner(state.winner) == "Your"
            headline = "You win!" if you else f"{self.names[state.winner]} wins!"
        else:
            accent, headline = col.SUCCESS, "It's a draw!"
        theme.aa_rect(surface, accent, (card.x, card.y, card.width, 8), border_top_left_radius=18,
                         border_top_right_radius=18)
        theme.draw_text(surface, "FINAL RESULT", theme.font(13, bold=True), col.TEXT_SUBTLE,
                        (card.centerx, card.y + 46), "center")
        theme.draw_text(surface, headline, theme.serif(34), col.TEXT, (card.centerx, card.y + 92),
                        "center", max_width=card.width - 40)

        s1, s2 = state.scores.get(1, 0), state.scores.get(2, 0)
        score_font = theme.font(theme.SIZE_TITLE, bold=True)
        theme.draw_text(surface, f"{s1}", score_font, col.P1, (card.centerx - 30, card.y + 150), "midright")
        theme.draw_text(surface, "-", score_font, col.TEXT_SUBTLE, (card.centerx, card.y + 150), "center")
        theme.draw_text(surface, f"{s2}", score_font, col.P2, (card.centerx + 30, card.y + 150), "midleft")
        cap = theme.font(theme.SIZE_CAPTION)
        theme.draw_text(surface, self.names[1], cap, col.TEXT_MUTED, (card.centerx - 30, card.y + 172), "topright",
                        max_width=180)
        theme.draw_text(surface, self.names[2], cap, col.TEXT_MUTED, (card.centerx + 30, card.y + 172), "topleft",
                        max_width=180)

        words = self.engine.matched_words
        counts = {pid: sum(1 for m in words if m["player"] == pid) for pid in (1, 2)}
        lines = [f"Ended because: {state.end_reason or 'rules'}  ·  {state.move_count} moves  ·  "
                 f"words {counts[1]} - {counts[2]}"]
        if words:
            best = max(words, key=lambda m: m["length"])
            lines.append(f"Best word: {best['word']} (+{best['length']}) by {self.names[best['player']]}")
        y = card.y + 204
        for line in lines:
            theme.draw_text(surface, line, cap, col.TEXT_MUTED, (card.centerx, y), "center", max_width=card.width - 40)
            y += 20

        self.btn_view.rect.bottomleft = (card.x + 20, card.bottom - 22)
        self.btn_rematch.rect.bottomright = (card.right - 20, card.bottom - 22)
        self.btn_new.rect.bottomright = (self.btn_rematch.rect.x - 10, card.bottom - 22)
        for btn in (self.btn_view, self.btn_new, self.btn_rematch):
            btn.render(surface)

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(col.BG)
        state = self.engine.state
        self._render_top_bar(surface)
        self._render_banner(surface)

        highlight = self.word_history_panel.highlight_key
        highlight_occ = [highlight] if highlight else (state.last_scored_occurrences or None)
        flash = (self.flash[0], time.time() - self.flash[1]) if self.flash else None
        self.board_renderer.render(surface, state.board, last_move=state.last_move,
                                   highlight_occurrences=highlight_occ, interactive=self._human_turn(), flash=flash)
        self._render_toast(surface)
        self._render_controls(surface)

        self.stats_panel.render(surface, state, self.names, self.roles)
        render_info_strip(surface, self.info_rect, state)
        title, text, details, accent, thinking = self._insight_content()
        self.insight.render(surface, title, text, details, accent, thinking)
        if self.last_ai_stats and not self.ai_searching and title.endswith("'s move"):
            self.btn_details.text = "Hide details" if self.show_details else "Show details"
            self.btn_details.rect.topright = (self.insight.rect.right - 12, self.insight.rect.y + 10)
            self.btn_details.render(surface)
        else:
            self.btn_details.rect.topleft = (-500, -500)
        self.word_history_panel.render(surface)

        self.picker.render(surface)
        if not self.picker.visible and not self.confirm.visible and not self._overlay_visible():
            self._render_tooltip(surface)
        if self._overlay_visible():
            self._render_result(surface)
        self.confirm.render(surface)
        self.help.render(surface)
