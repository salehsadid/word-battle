# Pre-match settings: a two-column player setup, shared match settings and an Advanced options sheet.

import pygame
from typing import Callable, List, Optional, Tuple
from wordgrid.ui import colors as col
from wordgrid.ui import theme
from wordgrid.ui.backdrop import draw_backdrop
from wordgrid.ui.controls import (
    Button,
    SegmentedControl,
    Slider,
    Stepper,
    TextInput,
    Toggle,
    UnderlineTabs,
)
from wordgrid.ui.dialogs import HelpOverlay
from wordgrid.config import (
    DIFFICULTIES,
    HeuristicWeights,
    MODE_UNTIL_BOARD_FULL,
    MODE_REACH_GOAL_SCORE,
    MODE_MOVE_LIMIT,
    MIN_BOARD_SIZE,
    MAX_BOARD_SIZE,
    DEFAULT_BOARD_SIZE,
    DIFFICULTY_PRESETS,
)
from wordgrid.settings import (
    MatchSettings,
    PlayerSettings,
    MATCH_HUMAN_VS_AI,
    MATCH_AI_VS_AI,
    MATCH_HUMAN_VS_HUMAN,
    CONTROLLER_HUMAN,
    CONTROLLER_MINIMAX,
    CONTROLLER_MCTS,
    DIFFICULTY_CUSTOM,
)

# Presets used by tests and shortcuts: (player 1 human?, player 2 human?)
MODE_VS_AI = "vs_ai"
MODE_TWO_PLAYERS = "two_players"
MODE_AI_VS_AI = "ai_vs_ai"
MODE_HUMANS = {MODE_VS_AI: (True, False), MODE_TWO_PLAYERS: (True, True), MODE_AI_VS_AI: (False, False)}

ALGO_NAMES = ["Minimax", "MCTS"]
ALGO_CONTROLLERS = [CONTROLLER_MINIMAX, CONTROLLER_MCTS]
CONTROLLER_OPTIONS = ["Human", "Computer"]
BOARD_OPTIONS = [f"{n}×{n}" for n in range(MIN_BOARD_SIZE, MAX_BOARD_SIZE + 1)]
LENGTH_OPTIONS = ["Fill the board", "Reach a score", "Move limit"]
LENGTH_MODES = [MODE_UNTIL_BOARD_FULL, MODE_REACH_GOAL_SCORE, MODE_MOVE_LIMIT]

CONTROL_H = 40
# One white sheet on the paper background: players on top, match rules below
SHEET = pygame.Rect(60, 108, 980, 566)
COL_X = (92, 590)          # left edge of the Player 1 / Player 2 columns
COL_W = 418
PANEL_Y = 158
PANEL_H = 240
SEG_Y, ROW1_Y, ROW2_Y = 40, 120, 198   # control offsets inside a player column (captions sit 22 px above)
RULE_Y = 432
FORM_LABEL_X = 92
FORM_X, FORM_W = 300, 440
FORM_ROWS_Y = (478, 532, 586)          # board size / game ends / first move


# One side of the match: whether a person or the computer plays it, and how.
class _PlayerPanel:

    # Build the controls for one player: Human/Computer, name, algorithm and level.
    def __init__(self, pid: int, name: str, human: bool, algo_idx: int, on_change: Callable[..., None]):
        self.pid = pid
        self.accent = col.player_color(pid)
        self.rect = pygame.Rect(COL_X[pid - 1], PANEL_Y, COL_W, PANEL_H)
        x, w = self.rect.x, COL_W
        row = lambda off: pygame.Rect(x, self.rect.y + off, w, CONTROL_H)
        self.seg_ctrl = SegmentedControl(row(SEG_Y), CONTROLLER_OPTIONS, 0 if human else 1, on_change=on_change)
        self.inp_name = TextInput(row(ROW1_Y), text=name, placeholder=f"Player {pid} name",
                                  on_change=lambda t: on_change())
        self.seg_algo = SegmentedControl(row(ROW1_Y), ALGO_NAMES, algo_idx, on_change=on_change)
        self.seg_diff = SegmentedControl(row(ROW2_Y), DIFFICULTIES, 1, on_change=on_change)

    # True if this player is set to Human.
    @property
    def is_human(self) -> bool:
        return self.seg_ctrl.index == 0

    # Selected algorithm (Minimax or MCTS).
    @property
    def controller(self) -> str:
        return ALGO_CONTROLLERS[self.seg_algo.index]

    # Controls shown for this player right now.
    def widgets(self) -> list:
        if self.is_human:
            return [self.seg_ctrl, self.inp_name]
        return [self.seg_ctrl, self.seg_algo, self.seg_diff]


# Friendly settings screen: set up each player, pick the shared rules, then press Start.
class MenuScreen:

    # Build the setup screen and load the saved settings.
    def __init__(
        self,
        on_start_match: Callable[[MatchSettings], None],
        on_start_tournament: Callable[[MatchSettings], None],
        title_font: Optional[pygame.font.Font] = None,
        font: Optional[pygame.font.Font] = None,
        small_font: Optional[pygame.font.Font] = None,
    ):
        self.on_start_match = on_start_match
        self.on_start_tournament = on_start_tournament
        self.help = HelpOverlay()
        self.advanced_open = False
        self.errors: List[str] = []

        self._build_main()
        self._build_advanced(MatchSettings())
        self._refresh()

    # ================================================================== main screen
    def _build_main(self) -> None:
        refresh = lambda *a: self._refresh()

        self.panels = [
            _PlayerPanel(1, "You", True, 0, refresh),
            _PlayerPanel(2, "Player 2", False, 0, refresh),
        ]
        self.inp_p1, self.inp_p2 = (p.inp_name for p in self.panels)

        form = lambda i: pygame.Rect(FORM_X, FORM_ROWS_Y[i], FORM_W, CONTROL_H)
        self.seg_board = SegmentedControl(form(0), BOARD_OPTIONS, DEFAULT_BOARD_SIZE - MIN_BOARD_SIZE,
                                          on_change=refresh)
        self.seg_length = SegmentedControl(form(1), LENGTH_OPTIONS, 0, on_change=refresh)
        self.seg_first = SegmentedControl(form(2), ["Player 1", "Player 2", "Random"], 0, on_change=refresh)
        step_rect = pygame.Rect(FORM_X + FORM_W + 20, FORM_ROWS_Y[1], 200, CONTROL_H)
        self.step_goal = Stepper(step_rect, 30, 5, 300, 5, on_change=refresh, fmt=lambda v: f"{v:g} points")
        self.step_limit = Stepper(step_rect.copy(), 10, 1, 40, 1, on_change=refresh,
                                  fmt=lambda v: f"{v:g} moves each")

        self.btn_help = Button(pygame.Rect(920, 36, 120, 38), "How to play", variant="secondary",
                               callback=self.help.open)
        self.btn_advanced = Button(pygame.Rect(60, 692, 180, 44), "Advanced options", variant="secondary",
                                   callback=self._open_advanced)
        self.btn_bench = Button(pygame.Rect(252, 692, 150, 44), "AI benchmark", variant="secondary",
                                callback=self._handle_tournament_click,
                                tooltip="Minimax vs MCTS, 4 games on this board; results are saved")
        self.btn_start = Button(pygame.Rect(860, 690, 180, 48), "Start game", variant="primary",
                                font=theme.font(theme.SIZE_HEADING, bold=True), callback=self._handle_start_click)

    # Stepper for the target score or move limit, if the end rule needs one.
    def _goal_stepper(self) -> Optional[Stepper]:
        mode = LENGTH_MODES[self.seg_length.index]
        if mode == MODE_REACH_GOAL_SCORE:
            return self.step_goal
        if mode == MODE_MOVE_LIMIT:
            return self.step_limit
        return None

    # Apply a preset (who is human on each side).
    def _set_mode(self, mode: str) -> None:
        for panel, human in zip(self.panels, MODE_HUMANS[mode]):
            panel.seg_ctrl.index = 0 if human else 1
            panel.inp_name.focused = False
        self._refresh()

    # ================================================================== advanced sheet
    def _build_advanced(self, d: MatchSettings) -> None:
        r = pygame.Rect(0, 0, 10, 10)
        refresh = lambda *a: self._refresh()
        self.override = {CONTROLLER_MINIMAX: False, CONTROLLER_MCTS: False}
        self.adv_card = pygame.Rect(150, 60, 800, 640)
        self.seg_adv_tab = UnderlineTabs(r, ["General", "Minimax", "MCTS"], 0)

        # Make a callback that turns custom search settings on or off.
        def set_override(ctrl):
            # Store the switch value and refresh the screen.
            def _f(value):
                self.override[ctrl] = value
                self._refresh()
            return _f

        self.step_minlen = Stepper(r, d.min_word_length, 2, 5, 1, on_change=refresh,
                                   fmt=lambda v: f"{v:g} letters")

        self.tog_mm_custom = Toggle(r, False, on_change=set_override(CONTROLLER_MINIMAX))
        self.step_depth = Stepper(r, d.minimax_depth, 1, 5, 1, on_change=refresh,
                                  fmt=lambda v: "1 move" if v == 1 else f"{v:g} moves")
        self.step_k = Stepper(r, d.candidate_k, 0, 60, 2, on_change=refresh,
                              fmt=lambda v: "All" if v == 0 else f"{v:g}")
        self.tog_pruning = Toggle(r, d.use_pruning, on_change=refresh)
        w = d.weights
        self.sl_w_score = Slider(r, w.score_diff, 0, 3, 0.1, on_change=refresh)
        self.sl_w_own = Slider(r, w.own_future_potential, 0, 3, 0.1, on_change=refresh)
        self.sl_w_opp = Slider(r, w.opponent_future_potential, 0, 3, 0.1, on_change=refresh)
        self.sl_w_space = Slider(r, w.playable_space_factor, 0, 3, 0.1, on_change=refresh)

        self.tog_mc_custom = Toggle(r, False, on_change=set_override(CONTROLLER_MCTS))
        self.step_iter = Stepper(r, d.mcts_iterations, 100, 20000, 100, on_change=refresh,
                                 fmt=lambda v: f"{v:,.0f}")
        self.step_rollout = Stepper(r, d.mcts_rollout_depth, 1, 30, 1, on_change=refresh)
        self.step_children = Stepper(r, d.mcts_max_children, 0, 100, 4, on_change=refresh,
                                     fmt=lambda v: "All" if v == 0 else f"{v:g}")
        self.sl_c = Slider(r, d.mcts_c, 0, 3, 0.05, on_change=refresh, fmt=lambda v: f"{v:.2f}")

        self.tog_explain = Toggle(r, d.show_ai_explanations, on_change=refresh)
        self.tog_details = Toggle(r, d.show_ai_details, on_change=refresh)
        self.step_delay = Stepper(r, d.ai_move_delay, 0.0, 3.0, 0.25, on_change=refresh,
                                  fmt=lambda v: f"{v:.2f} s")

        self.btn_adv_close = Button(r, "", variant="ghost", icon="close", callback=self._close_advanced)
        self.btn_adv_reset = Button(r, "Reset to recommended", variant="ghost",
                                    callback=self._reset_advanced)
        self.btn_adv_done = Button(r, "Done", variant="primary", callback=self._close_advanced)

    # (label, hint, widget) rows for the active tab; widget None = section header.
    def _advanced_rows(self):
        tab = self.seg_adv_tab.index
        if tab == 0:
            return [
                ("Minimum word length", "Shorter words never score. Limited by the board size.", self.step_minlen),
                ("Display", "", None),
                ("Explain AI moves", "A short sentence after every AI move.", self.tog_explain),
                ("Show technical details", "Search time, positions examined, win estimate.", self.tog_details),
                ("Pause between AI moves", "Gives you time to follow the game.", self.step_delay),
            ]
        if tab == 1:
            custom = self.override[CONTROLLER_MINIMAX]
            for wdg in (self.step_depth, self.step_k, self.tog_pruning):
                wdg.enabled = custom
            return [
                ("Use custom search settings", "Off = follow the difficulty chosen on the main screen.",
                 self.tog_mm_custom),
                ("Look-ahead", "How many moves ahead it plans.", self.step_depth),
                ("Options compared per move", "Its best candidate moves. 'All' is very slow.", self.step_k),
                ("Alpha-beta pruning", "Skips hopeless lines: same answer, much faster.", self.tog_pruning),
                ("Playing style (applies to every difficulty)", "", None),
                ("Value of its current lead", "", self.sl_w_score),
                ("Eagerness to score next turn", "", self.sl_w_own),
                ("Caution about your threats", "", self.sl_w_opp),
                ("Endgame urgency", "", self.sl_w_space),
            ]
        custom = self.override[CONTROLLER_MCTS]
        for wdg in (self.step_iter, self.step_rollout, self.step_children):
            wdg.enabled = custom
        return [
            ("Use custom search settings", "Off = follow the difficulty chosen on the main screen.",
             self.tog_mc_custom),
            ("Simulated games per move", "More is stronger but slower.", self.step_iter),
            ("Playout length", "Moves played in each simulated game.", self.step_rollout),
            ("Moves explored per position", "'All' spreads the search thin.", self.step_children),
            ("Playing style (applies to every difficulty)", "", None),
            ("Curiosity (exploration constant)", "Higher tries more unusual moves.", self.sl_c),
        ]

    # Place the tabs and buttons of the Advanced options sheet.
    def _layout_advanced(self):
        card = self.adv_card
        self.seg_adv_tab.rect = pygame.Rect(card.x + 28, card.y + 72, card.width - 56, 42)
        self.btn_adv_close.rect = pygame.Rect(card.right - 56, card.y + 20, 36, 36)
        self.btn_adv_reset.rect = pygame.Rect(card.x + 20, card.bottom - 66, 230, 46)
        self.btn_adv_done.rect = pygame.Rect(card.right - 168, card.bottom - 66, 140, 46)
        rows = []
        y = card.y + 134
        ctrl_x = card.x + 450
        ctrl_w = card.width - 450 - 28
        for label, hint, widget in self._advanced_rows():
            if widget is None:
                rows.append((label, hint, None, y))
                y += 30
                continue
            h = 48 if hint else 36
            if isinstance(widget, Toggle):
                widget.rect = pygame.Rect(ctrl_x + ctrl_w - 50, y + 6, 50, 28)
            elif isinstance(widget, Slider):
                widget.rect = pygame.Rect(ctrl_x, y + 2, ctrl_w, 34)
            else:
                widget.rect = pygame.Rect(ctrl_x, y, ctrl_w, 40)
            rows.append((label, hint, widget, y))
            y += h
        return rows

    # Show the Advanced options sheet.
    def _open_advanced(self) -> None:
        self.advanced_open = True

    # Hide the Advanced options sheet and refresh the screen.
    def _close_advanced(self) -> None:
        self.advanced_open = False
        self._refresh()

    # Put the advanced settings back to the recommended values.
    def _reset_advanced(self) -> None:
        tab = self.seg_adv_tab.index
        self._build_advanced(MatchSettings())
        self.seg_adv_tab.index = tab
        self._refresh()

    # ================================================================== settings model
    def _names(self, i1: int, i2: int) -> Tuple[str, str]:
        n1, n2 = ALGO_NAMES[i1], ALGO_NAMES[i2]
        if n1 == n2:
            return f"{n1} 1", f"{n2} 2"
        return n1, n2

    # Level name to save: 'Custom' when custom search settings are on.
    def _difficulty(self, algo_idx: int, difficulty: str) -> str:
        return DIFFICULTY_CUSTOM if self.override[ALGO_CONTROLLERS[algo_idx]] else difficulty

    # Settings described by the screen, plus every problem found.
    def build_settings(self) -> Tuple[MatchSettings, List[str]]:
        problems: List[str] = []

        sides = []
        for panel in self.panels:
            if panel.is_human:
                sides.append(PlayerSettings(panel.inp_name.text.strip(), CONTROLLER_HUMAN))
            else:
                i = panel.seg_algo.index
                sides.append(PlayerSettings(ALGO_NAMES[i], panel.controller, self._difficulty(i, panel.seg_diff.value)))
        p1, p2 = sides
        if not p1.is_human and not p2.is_human:
            p1.name, p2.name = self._names(self.panels[0].seg_algo.index, self.panels[1].seg_algo.index)
        humans = p1.is_human + p2.is_human
        match_type = {2: MATCH_HUMAN_VS_HUMAN, 1: MATCH_HUMAN_VS_AI, 0: MATCH_AI_VS_AI}[humans]
        start = [1, 2, 0][self.seg_first.index]

        settings = MatchSettings(
            match_type=match_type,
            board_size=MIN_BOARD_SIZE + self.seg_board.index,
            starting_player=start,
            game_mode=LENGTH_MODES[self.seg_length.index],
            goal_score=int(self.step_goal.value),
            move_limit=int(self.step_limit.value),
            min_word_length=int(self.step_minlen.value),
            p1=p1,
            p2=p2,
            minimax_depth=int(self.step_depth.value),
            use_pruning=self.tog_pruning.value,
            candidate_k=int(self.step_k.value),
            weights=HeuristicWeights(
                score_diff=self.sl_w_score.value,
                own_future_potential=self.sl_w_own.value,
                opponent_future_potential=self.sl_w_opp.value,
                playable_space_factor=self.sl_w_space.value,
            ),
            mcts_iterations=int(self.step_iter.value),
            mcts_c=self.sl_c.value,
            mcts_rollout_depth=int(self.step_rollout.value),
            mcts_max_children=int(self.step_children.value),
            show_ai_explanations=self.tog_explain.value,
            show_ai_details=self.tog_details.value,
            ai_move_delay=self.step_delay.value,
        )
        problems += self._friendly(settings.validate())
        return settings, problems

    # Turn validation errors into short messages for the user.
    @staticmethod
    def _friendly(errors: List[str]) -> List[str]:
        out = []
        for e in errors:
            if "needs a name" in e:
                out.append("Please enter a name for every player.")
            elif "different names" in e:
                out.append("The two players need different names.")
            elif "at most 16" in e:
                out.append("Names can be at most 16 characters long.")
            else:
                out.append(e)
        return list(dict.fromkeys(out))

    # Update limits, hints and visible controls after any change.
    def _refresh(self) -> None:
        board = MIN_BOARD_SIZE + self.seg_board.index
        self.step_minlen.set_range(2, max(2, min(board, 8)))
        for panel in self.panels:
            panel.seg_diff.enabled = not self.override[panel.controller]
            if not panel.is_human:
                panel.inp_name.focused = False
        settings, self.errors = self.build_settings()
        same_names = any("different names" in e for e in self.errors)
        for panel in self.panels:
            inp = panel.inp_name
            inp.error = panel.is_human and (not inp.text.strip() or len(inp.text) > 16 or same_names)
        self.btn_start.enabled = not self.errors

    # Settings from the form, or None if something is invalid.
    def get_current_settings(self) -> Optional[MatchSettings]:
        settings, self.errors = self.build_settings()
        return None if self.errors else settings

    # Start the match if the settings are valid.
    def _handle_start_click(self) -> None:
        settings = self.get_current_settings()
        if settings is not None:
            self.on_start_match(settings)

    # Start the AI benchmark with the current settings.
    def _handle_tournament_click(self) -> None:
        settings, _ = self.build_settings()
        self.on_start_tournament(settings)

    # ================================================================== events
    def _main_widgets(self):
        widgets = [w for panel in self.panels for w in panel.widgets()]
        widgets += [self.seg_board, self.seg_length, self.seg_first]
        stepper = self._goal_stepper()
        if stepper:
            widgets.append(stepper)
        return widgets + [self.btn_help, self.btn_advanced, self.btn_bench, self.btn_start]

    # Name boxes that are visible now (none while the sheet is open).
    def _visible_inputs(self) -> List[TextInput]:
        if self.advanced_open:
            return []
        return [p.inp_name for p in self.panels if p.is_human]

    # Pass input to the help card, the advanced sheet or the form.
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.help.handle_event(event):
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            self.help.open()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            inputs = self._visible_inputs()
            if inputs:
                current = next((i for i, c in enumerate(inputs) if c.focused), -1)
                for c in inputs:
                    c.focused = False
                inputs[(current + 1) % len(inputs)].focused = True
            return

        if self.advanced_open:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._close_advanced()
                return
            if event.type == pygame.MOUSEBUTTONDOWN and not self.adv_card.collidepoint(event.pos):
                self._close_advanced()
                return
            self._layout_advanced()
            if self.seg_adv_tab.handle_event(event):
                return
            for btn in (self.btn_adv_close, self.btn_adv_reset, self.btn_adv_done):
                if btn.handle_event(event):
                    return
            for _, _, widget, _ in self._layout_advanced():
                if widget is not None:
                    widget.handle_event(event)
            return

        typing = any(i.focused for i in self._visible_inputs())
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and not typing:
            if self.btn_start.enabled:
                self._handle_start_click()
            return
        for widget in self._main_widgets():
            widget.handle_event(event)

    # Nothing to update each frame.
    def update(self) -> None:
        pass

    # ================================================================== render
    def render(self, surface: pygame.Surface) -> None:
        draw_backdrop(surface)

        theme.draw_logo(surface, (SHEET.x, 36), tile=36)
        self.btn_help.render(surface)
        theme.rule(surface, SHEET.x, SHEET.right, 90, width=2, color=col.TEXT)

        theme.draw_card(surface, SHEET, border=col.BORDER_STRONG)
        theme.draw_label(surface, "Players", (FORM_LABEL_X, SHEET.y + 22))
        for panel in self.panels:
            self._render_panel(surface, panel)
        divider_x = (COL_X[0] + COL_W + COL_X[1]) // 2
        pygame.draw.line(surface, col.BORDER, (divider_x, PANEL_Y), (divider_x, PANEL_Y + PANEL_H - 2))
        theme.rule(surface, FORM_LABEL_X, SHEET.right - 32, RULE_Y)
        self._render_match_form(surface)

        self.btn_advanced.render(surface)
        self.btn_bench.render(surface)
        self.btn_start.render(surface)
        if self.errors:
            theme.draw_text(surface, self.errors[0], theme.font(theme.SIZE_CAPTION, bold=True), col.DANGER,
                            (self.btn_start.rect.x - 16, self.btn_start.rect.centery), "midright", max_width=420)

        if self.btn_bench.is_hovered and self.btn_bench.tooltip:
            theme.draw_tooltip(surface, self.btn_bench.tooltip, self.btn_bench.rect.midtop)

        if self.advanced_open:
            self._render_advanced(surface)
        self.help.render(surface)

    # Draw one player's panel.
    def _render_panel(self, surface: pygame.Surface, panel: _PlayerPanel) -> None:
        rect = panel.rect
        title = theme.draw_text(surface, f"Player {panel.pid}", theme.serif(22), col.TEXT, (rect.x + 20, rect.y - 4))
        theme.draw_swatch(surface, panel.accent, (rect.x + 6, title.centery + 1), 12)
        panel.seg_ctrl.render(surface)
        if panel.is_human:
            self._render_field(surface, "Name", panel.inp_name)
        else:
            self._render_field(surface, "Algorithm", panel.seg_algo)
            self._render_field(surface, "Level", panel.seg_diff)
            theme.draw_text(surface, self._level_summary(panel), theme.font(13), col.TEXT_SUBTLE,
                            (panel.seg_diff.rect.x, panel.seg_diff.rect.bottom + 6), max_width=COL_W)

    # What the chosen level means for this algorithm (custom values when Advanced options override it).
    def _level_summary(self, panel: _PlayerPanel) -> str:
        custom = self.override[panel.controller]
        if panel.controller == CONTROLLER_MINIMAX:
            if custom:
                depth, k = int(self.step_depth.value), int(self.step_k.value)
            else:
                p = DIFFICULTY_PRESETS[panel.seg_diff.value]["minimax"]
                depth, k = p["depth"], p["candidate_k"]
            text = (f"Look-ahead: {depth} {'move' if depth == 1 else 'moves'}  ·  "
                    f"Options compared: {'all' if k == 0 else k}")
        else:
            if custom:
                sims, playout, explored = (int(self.step_iter.value), int(self.step_rollout.value),
                                           int(self.step_children.value))
            else:
                p = DIFFICULTY_PRESETS[panel.seg_diff.value]["mcts"]
                sims, playout, explored = p["iterations"], p["rollout_depth"], p["max_children"]
            text = (f"Simulations: {sims:,}  ·  Playout length: {playout}  ·  "
                    f"Moves explored: {'all' if explored == 0 else explored}")
        return ("Custom  ·  " + text) if custom else text

    # Draw a caption above a control, then the control.
    @staticmethod
    def _render_field(surface: pygame.Surface, caption: str, widget) -> None:
        theme.draw_label(surface, caption, (widget.rect.x, widget.rect.y - 22))
        widget.render(surface)

    # Draw the board size, end rule and first-player rows.
    def _render_match_form(self, surface: pygame.Surface) -> None:
        theme.draw_label(surface, "Match", (FORM_LABEL_X, RULE_Y + 16))
        rows = (("Board size", self.seg_board), ("Game ends", self.seg_length), ("First move", self.seg_first))
        for label, widget in rows:
            theme.draw_text(surface, label, theme.font(theme.SIZE_BODY, bold=True), col.TEXT,
                            (FORM_LABEL_X, widget.rect.centery), "midleft")
            widget.render(surface)
        stepper = self._goal_stepper()
        if stepper:
            stepper.render(surface)

    # Draw the Advanced options sheet over a dimmed screen.
    def _render_advanced(self, surface: pygame.Surface) -> None:
        theme.draw_overlay(surface)
        card = self.adv_card
        theme.draw_card(surface, card, border=col.TEXT)
        rows = self._layout_advanced()
        theme.draw_text(surface, "Advanced options", theme.serif(theme.SIZE_TITLE), col.TEXT,
                        (card.x + 28, card.y + 26))
        self.btn_adv_close.render(surface)
        self.seg_adv_tab.render(surface)

        label_font = theme.font(theme.SIZE_BODY, bold=True)
        hint_font = theme.font(theme.SIZE_CAPTION)
        for label, hint, widget, y in rows:
            if widget is None:
                pygame.draw.line(surface, col.BORDER, (card.x + 28, y + 6), (card.right - 28, y + 6))
                theme.draw_label(surface, label, (card.x + 28, y + 12))
                continue
            enabled = getattr(widget, "enabled", True)
            theme.draw_text(surface, label, label_font, col.TEXT if enabled else col.TEXT_SUBTLE,
                            (card.x + 28, y + (2 if hint else 10)))
            if hint:
                theme.draw_text(surface, hint, hint_font, col.TEXT_SUBTLE, (card.x + 28, y + 25), max_width=410)
            widget.render(surface)

        pygame.draw.line(surface, col.BORDER, (card.x, card.bottom - 86), (card.right, card.bottom - 86))
        self.btn_adv_reset.render(surface)
        self.btn_adv_done.render(surface)
