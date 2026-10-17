"""Pre-match settings: a two-column player setup, shared match settings and an Advanced options sheet."""

import pygame
from typing import Callable, List, Optional, Tuple
from wordgrid.ui import colors as col
from wordgrid.ui import theme
from wordgrid.ui.backdrop import draw_backdrop, draw_glass_card
from wordgrid.ui.controls import (
    Button,
    OptionSelector,
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
    DIFFICULTY_PRESETS,
    HeuristicWeights,
    MODE_UNTIL_BOARD_FULL,
    MODE_REACH_GOAL_SCORE,
    MODE_MOVE_LIMIT,
    MIN_BOARD_SIZE,
    MAX_BOARD_SIZE,
    DEFAULT_BOARD_SIZE,
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
    available_dictionaries,
)

# Presets used by tests and shortcuts: (player 1 human?, player 2 human?)
MODE_VS_AI = "vs_ai"
MODE_TWO_PLAYERS = "two_players"
MODE_AI_VS_AI = "ai_vs_ai"
MODE_HUMANS = {MODE_VS_AI: (True, False), MODE_TWO_PLAYERS: (True, True), MODE_AI_VS_AI: (False, False)}

ALGO_NAMES = ["Strategist", "Explorer"]
ALGO_CONTROLLERS = [CONTROLLER_MINIMAX, CONTROLLER_MCTS]
ALGO_HINTS = [
    "Minimax search: plans ahead and weighs your threats.",
    "Monte Carlo search: simulates many possible futures.",
]
CONTROLLER_OPTIONS = ["Human", "AI"]
BOARD_OPTIONS = [f"{n}×{n}" for n in range(MIN_BOARD_SIZE, MAX_BOARD_SIZE + 1)]
LENGTH_OPTIONS = ["Fill the board", "Reach a score", "Move limit"]
LENGTH_MODES = [MODE_UNTIL_BOARD_FULL, MODE_REACH_GOAL_SCORE, MODE_MOVE_LIMIT]
LENGTH_HINTS = [
    "Play until every square is used.",
    "The first player to reach the target wins.",
    "Each player gets the same number of moves.",
]

CONTROL_H = 42
# Player panels: two columns with a "VS" badge between them
PANEL_X = (40, 570)
PANEL_Y = 104
PANEL_W = 490
PANEL_H = 326
PANEL_PAD = 24
ROW1_Y = 142   # caption offsets inside a panel
ROW2_Y = 234
# Shared match settings: one full-width card under both players
MATCH_RECT = pygame.Rect(40, 446, 1020, 208)
MATCH_COLS = ((64, 300), (388, 360), (772, 264))  # (x, width) of board / ending / first move
MATCH_ROW_Y = 60
HEADER_RECT = pygame.Rect(40, 18, 1020, 70)
FOOTER_RECT = pygame.Rect(40, 666, 1020, 86)


class _PlayerPanel:
    """One side of the match: whether a person or an AI plays it, and how."""

    def __init__(self, pid: int, name: str, human: bool, algo_idx: int, on_change: Callable[..., None]):
        self.pid = pid
        self.accent = col.player_color(pid)
        self.rect = pygame.Rect(PANEL_X[pid - 1], PANEL_Y, PANEL_W, PANEL_H)
        x, w = self.rect.x + PANEL_PAD, PANEL_W - 2 * PANEL_PAD
        row = lambda off: pygame.Rect(x, self.rect.y + off + 22, w, CONTROL_H)
        self.seg_ctrl = SegmentedControl(pygame.Rect(x, self.rect.y + 84, w, CONTROL_H), CONTROLLER_OPTIONS,
                                         0 if human else 1, on_change=on_change, accent=self.accent)
        self.inp_name = TextInput(row(ROW1_Y), text=name, placeholder=f"Player {pid} name",
                                  on_change=lambda t: on_change())
        self.seg_algo = SegmentedControl(row(ROW1_Y), ALGO_NAMES, algo_idx, on_change=on_change, accent=self.accent)
        self.seg_diff = SegmentedControl(row(ROW2_Y), DIFFICULTIES, 1, on_change=on_change, accent=self.accent)

    @property
    def is_human(self) -> bool:
        return self.seg_ctrl.index == 0

    @property
    def controller(self) -> str:
        return ALGO_CONTROLLERS[self.seg_algo.index]

    def widgets(self) -> list:
        if self.is_human:
            return [self.seg_ctrl, self.inp_name]
        return [self.seg_ctrl, self.seg_algo, self.seg_diff]


class MenuScreen:
    """Friendly settings screen: set up each player, pick the shared rules, then press Start."""

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
        self.dictionaries = available_dictionaries()
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

        top = MATCH_RECT.y + MATCH_ROW_Y + 22
        (bx, bw), (lx, lw), (fx, fw) = MATCH_COLS
        self.seg_board = SegmentedControl(pygame.Rect(bx, top, bw, CONTROL_H), BOARD_OPTIONS,
                                          DEFAULT_BOARD_SIZE - MIN_BOARD_SIZE, on_change=refresh)
        self.seg_length = SegmentedControl(pygame.Rect(lx, top, lw, CONTROL_H), LENGTH_OPTIONS, 0, on_change=refresh)
        self.seg_first = SegmentedControl(pygame.Rect(fx, top, fw, CONTROL_H), ["Player 1", "Player 2", "Random"], 0,
                                          on_change=refresh)
        step_rect = pygame.Rect(lx, top + CONTROL_H + 28, 200, 38)
        self.step_goal = Stepper(step_rect, 30, 5, 300, 5, on_change=refresh, fmt=lambda v: f"{v:g} points")
        self.step_limit = Stepper(step_rect.copy(), 10, 1, 40, 1, on_change=refresh,
                                  fmt=lambda v: f"{v:g} moves each")

        self.btn_help = Button(pygame.Rect(898, 32, 144, 42), "How to play", variant="secondary", icon="help",
                               callback=self.help.open)
        self.btn_advanced = Button(pygame.Rect(62, 686, 210, 46), "Advanced options", variant="secondary",
                                   icon="gear", callback=self._open_advanced)
        self.btn_bench = Button(pygame.Rect(284, 686, 180, 46), "AI benchmark", variant="secondary", icon="trophy",
                                callback=self._handle_tournament_click,
                                tooltip="Round-robin of all AIs on this board; results saved to data/")
        self.btn_start = Button(pygame.Rect(818, 676, 220, 48), "Start game", variant="primary", icon="play",
                                font=theme.font(theme.SIZE_HEADING, bold=True), callback=self._handle_start_click)

    def _difficulty_hint(self, algo_idx: int, difficulty: str) -> str:
        ctrl = ALGO_CONTROLLERS[algo_idx]
        if self.override[ctrl]:
            return "Using your custom settings from Advanced options."
        if ctrl == CONTROLLER_MINIMAX:
            p = DIFFICULTY_PRESETS[difficulty]["minimax"]
            ahead = "1 move" if p["depth"] == 1 else f"{p['depth']} moves"
            return f"Plans {ahead} ahead, comparing its best {p['candidate_k']} options."
        p = DIFFICULTY_PRESETS[difficulty]["mcts"]
        return f"Simulates {p['iterations']:,} games before every move."

    def _goal_stepper(self) -> Optional[Stepper]:
        mode = LENGTH_MODES[self.seg_length.index]
        if mode == MODE_REACH_GOAL_SCORE:
            return self.step_goal
        if mode == MODE_MOVE_LIMIT:
            return self.step_limit
        return None

    def _set_mode(self, mode: str) -> None:
        """Apply a preset (who is human on each side)."""
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
        self.seg_adv_tab = UnderlineTabs(r, ["Rules", "Strategist AI", "Explorer AI", "Display"], 0)

        def set_override(ctrl):
            def _f(value):
                self.override[ctrl] = value
                self._refresh()
            return _f

        self.step_minlen = Stepper(r, d.min_word_length, 2, 5, 1, on_change=refresh,
                                   fmt=lambda v: f"{v:g} letters")
        labels = [label for label, _ in self.dictionaries] or ["Standard English"]
        self.sel_dict = OptionSelector(r, "", labels, 0, on_change=refresh)
        self.inp_seed = TextInput(r, text="", kind="int", max_chars=10, placeholder="Empty = different every game",
                                  on_change=lambda t: self._refresh())

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
        self.sl_w_prefix = Slider(r, w.partial_sequence_bonus, 0, 3, 0.1, on_change=refresh)
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

    def _advanced_rows(self):
        """(label, hint, widget) rows for the active tab; widget None = section header."""
        tab = self.seg_adv_tab.index
        if tab == 0:
            return [
                ("Minimum word length", "Shorter words never score. Limited by the board size.", self.step_minlen),
                ("Dictionary", "Word lists found in the data folder.", self.sel_dict),
                ("Random seed", "Same number = the AIs repeat the same choices.", self.inp_seed),
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
                ("Interest in open letter runs", "", self.sl_w_prefix),
                ("Endgame urgency", "", self.sl_w_space),
            ]
        if tab == 2:
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
        return [
            ("Explain AI moves", "A short sentence after every AI move.", self.tog_explain),
            ("Show technical details", "Search time, positions examined, win estimate.", self.tog_details),
            ("Pause between AI moves", "Gives you time to follow the game.", self.step_delay),
        ]

    def _layout_advanced(self):
        card = self.adv_card
        self.seg_adv_tab.rect = pygame.Rect(card.x + 28, card.y + 84, card.width - 56, 42)
        self.btn_adv_close.rect = pygame.Rect(card.right - 56, card.y + 20, 36, 36)
        self.btn_adv_reset.rect = pygame.Rect(card.x + 20, card.bottom - 66, 230, 46)
        self.btn_adv_done.rect = pygame.Rect(card.right - 168, card.bottom - 66, 140, 46)
        rows = []
        y = card.y + 142
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

    def _open_advanced(self) -> None:
        self.advanced_open = True

    def _close_advanced(self) -> None:
        self.advanced_open = False
        self.inp_seed.focused = False
        self._refresh()

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

    def _difficulty(self, algo_idx: int, difficulty: str) -> str:
        return DIFFICULTY_CUSTOM if self.override[ALGO_CONTROLLERS[algo_idx]] else difficulty

    def build_settings(self) -> Tuple[MatchSettings, List[str]]:
        """Settings described by the screen, plus every problem found."""
        problems: List[str] = []
        seed_text = self.inp_seed.text.strip()
        seed = None
        self.inp_seed.error = False
        if seed_text:
            try:
                seed = int(seed_text)
            except ValueError:
                self.inp_seed.error = True
                problems.append("The random seed must be a whole number (or left empty).")

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

        defaults = MatchSettings()
        dict_path = self.dictionaries[self.sel_dict.index][1] if self.dictionaries else defaults.dictionary_path
        settings = MatchSettings(
            match_type=match_type,
            board_size=MIN_BOARD_SIZE + self.seg_board.index,
            starting_player=start,
            game_mode=LENGTH_MODES[self.seg_length.index],
            goal_score=int(self.step_goal.value),
            move_limit=int(self.step_limit.value),
            min_word_length=int(self.step_minlen.value),
            dictionary_path=dict_path,
            p1=p1,
            p2=p2,
            minimax_depth=int(self.step_depth.value),
            use_pruning=self.tog_pruning.value,
            candidate_k=int(self.step_k.value),
            weights=HeuristicWeights(
                score_diff=self.sl_w_score.value,
                own_future_potential=self.sl_w_own.value,
                opponent_future_potential=self.sl_w_opp.value,
                partial_sequence_bonus=self.sl_w_prefix.value,
                playable_space_factor=self.sl_w_space.value,
            ),
            mcts_iterations=int(self.step_iter.value),
            mcts_c=self.sl_c.value,
            mcts_rollout_depth=int(self.step_rollout.value),
            mcts_max_children=int(self.step_children.value),
            seed=seed,
            show_ai_explanations=self.tog_explain.value,
            show_ai_details=self.tog_details.value,
            ai_move_delay=self.step_delay.value,
        )
        problems += self._friendly(settings.validate())
        return settings, problems

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

    def _refresh(self) -> None:
        board = MIN_BOARD_SIZE + self.seg_board.index
        self.step_minlen.set_range(2, max(2, min(board, 8)))
        for panel in self.panels:
            panel.seg_diff.enabled = not self.override[panel.controller]
            if not panel.is_human:
                panel.inp_name.focused = False
        settings, self.errors = self.build_settings()
        self.first_hint = ("Decided by a coin toss." if self.seg_first.index == 2
                           else f"First move: {settings.player(self.seg_first.index + 1).name or 'Player'}")
        same_names = any("different names" in e for e in self.errors)
        for panel in self.panels:
            inp = panel.inp_name
            inp.error = panel.is_human and (not inp.text.strip() or len(inp.text) > 16 or same_names)
        self.btn_start.enabled = not self.errors

    def get_current_settings(self) -> Optional[MatchSettings]:
        settings, self.errors = self.build_settings()
        return None if self.errors else settings

    def _handle_start_click(self) -> None:
        settings = self.get_current_settings()
        if settings is not None:
            self.on_start_match(settings)

    def _handle_tournament_click(self) -> None:
        settings, problems = self.build_settings()
        if not any("seed" in p for p in problems):
            self.on_start_tournament(settings)

    # ================================================================== events
    def _main_widgets(self):
        widgets = [w for panel in self.panels for w in panel.widgets()]
        widgets += [self.seg_board, self.seg_length, self.seg_first]
        stepper = self._goal_stepper()
        if stepper:
            widgets.append(stepper)
        return widgets + [self.btn_help, self.btn_advanced, self.btn_bench, self.btn_start]

    def _visible_inputs(self) -> List[TextInput]:
        if self.advanced_open:
            return [self.inp_seed] if self.seg_adv_tab.index == 0 else []
        return [p.inp_name for p in self.panels if p.is_human]

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
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and not self.inp_seed.focused:
                self._close_advanced()
                return
            if event.type == pygame.MOUSEBUTTONDOWN and not self.adv_card.collidepoint(event.pos):
                self._close_advanced()
                return
            self._layout_advanced()
            if self.seg_adv_tab.handle_event(event):
                self.inp_seed.focused = False
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

    def update(self) -> None:
        pass

    # ================================================================== render
    def render(self, surface: pygame.Surface) -> None:
        draw_backdrop(surface)

        draw_glass_card(surface, HEADER_RECT)
        logo = theme.draw_logo(surface, (HEADER_RECT.x + 22, HEADER_RECT.y + 14), tile=38)
        theme.draw_text(surface, "Build words. Outsmart your opponent.", theme.font(theme.SIZE_BODY),
                        col.TEXT_MUTED, (logo.right + 24, logo.centery), "midleft")
        self.btn_help.render(surface)

        for panel in self.panels:
            self._render_panel(surface, panel)
        self._render_vs_badge(surface)
        self._render_match_card(surface)
        draw_glass_card(surface, FOOTER_RECT)

        self.btn_advanced.render(surface)
        self.btn_bench.render(surface)
        self.btn_start.render(surface)

        status_font = theme.font(theme.SIZE_CAPTION)
        status_pos = (self.btn_start.rect.right, self.btn_start.rect.bottom + 5)
        if self.errors:
            theme.draw_text(surface, self.errors[0], status_font, col.DANGER, status_pos, "topright", max_width=560)
        else:
            customised = [n for c, n in zip(ALGO_CONTROLLERS, ALGO_NAMES) if self.override[c]]
            note = "Ready when you are. Press Enter to start."
            if customised:
                note = f"Custom {' and '.join(customised)} settings active. Press Enter to start."
            theme.draw_text(surface, note, status_font, col.TEXT_SUBTLE, status_pos, "topright")

        if self.btn_bench.is_hovered and self.btn_bench.tooltip:
            theme.draw_tooltip(surface, self.btn_bench.tooltip, self.btn_bench.rect.midtop)

        if self.advanced_open:
            self._render_advanced(surface)
        self.help.render(surface)

    def _render_panel(self, surface: pygame.Surface, panel: _PlayerPanel) -> None:
        rect, accent = panel.rect, panel.accent
        draw_glass_card(surface, rect)
        theme.aa_rect(surface, accent, (rect.x + 14, rect.y, rect.width - 28, 4),
                         border_bottom_left_radius=3, border_bottom_right_radius=3)

        icon_center = (rect.x + PANEL_PAD + 24, rect.y + 44)
        theme.aa_circle(surface, col.player_soft(panel.pid), icon_center, 24)
        theme.draw_icon(surface, "person" if panel.is_human else "computer", icon_center, 26, accent)
        tx = rect.x + PANEL_PAD + 62
        theme.draw_text(surface, f"Player {panel.pid}", theme.serif(theme.SIZE_TITLE), col.TEXT, (tx, rect.y + 20))
        theme.draw_text(surface, "Choose who controls this side.", theme.font(theme.SIZE_CAPTION),
                        col.TEXT_SUBTLE, (tx, rect.y + 52))
        tag = "Blue tiles" if panel.pid == 1 else "Orange tiles"
        theme.draw_text(surface, tag, theme.font(theme.SIZE_CAPTION, bold=True), accent,
                        (rect.right - PANEL_PAD, rect.y + 26), "topright")
        panel.seg_ctrl.render(surface)

        x, w = rect.x + PANEL_PAD, rect.width - 2 * PANEL_PAD
        if panel.is_human:
            self._render_field(surface, "Name", panel.inp_name, "", (x, rect.y + ROW1_Y), w)
            note = pygame.Rect(x, rect.y + ROW2_Y + 8, w, 64)
            theme.aa_rect(surface, col.SURFACE_ALT, note, border_radius=10)
            hint_font = theme.font(theme.SIZE_CAPTION)
            theme.draw_text(surface, "Plays on this computer: click a square, then type a letter.",
                            hint_font, col.TEXT_MUTED, (note.x + 16, note.y + 14), max_width=w - 32)
            theme.draw_text(surface, "Switch to AI to let the computer play this side.",
                            hint_font, col.TEXT_SUBTLE, (note.x + 16, note.y + 34), max_width=w - 32)
        else:
            idx = panel.seg_algo.index
            self._render_field(surface, "Algorithm", panel.seg_algo, ALGO_HINTS[idx], (x, rect.y + ROW1_Y), w)
            self._render_field(surface, "Difficulty", panel.seg_diff,
                               self._difficulty_hint(idx, panel.seg_diff.value), (x, rect.y + ROW2_Y), w)

    @staticmethod
    def _render_field(surface: pygame.Surface, caption: str, widget, hint: str, pos: Tuple[int, int],
                      width: int) -> None:
        theme.draw_text(surface, caption, theme.font(theme.SIZE_CAPTION, bold=True), col.TEXT_MUTED, pos)
        widget.render(surface)
        if hint:
            theme.draw_text(surface, hint, theme.font(theme.SIZE_CAPTION), col.TEXT_SUBTLE,
                            (pos[0], widget.rect.bottom + 5), max_width=width)

    def _render_vs_badge(self, surface: pygame.Surface) -> None:
        center = ((PANEL_X[0] + PANEL_W + PANEL_X[1]) // 2, PANEL_Y + PANEL_H // 2)
        theme.aa_circle(surface, col.SHADOW, (center[0], center[1] + 2), 27)
        theme.aa_circle(surface, col.SURFACE, center, 27)
        theme.aa_circle(surface, col.BORDER, center, 27, 1)
        theme.draw_text(surface, "VS", theme.serif(theme.SIZE_HEADING), col.TEXT_MUTED, center, "center")

    def _render_match_card(self, surface: pygame.Surface) -> None:
        card = MATCH_RECT
        draw_glass_card(surface, card)
        title = theme.draw_text(surface, "Match settings", theme.serif(20), col.TEXT, (card.x + PANEL_PAD, card.y + 18))
        theme.draw_text(surface, "Shared by both players.", theme.font(theme.SIZE_CAPTION), col.TEXT_SUBTLE,
                        (title.right + 14, title.centery), "midleft")

        board = MIN_BOARD_SIZE + self.seg_board.index
        (bx, bw), (lx, lw), (fx, fw) = MATCH_COLS
        y = card.y + MATCH_ROW_Y
        self._render_field(surface, "Board size", self.seg_board, f"{board * board} squares to fill.", (bx, y), bw)
        self._render_field(surface, "How the match ends", self.seg_length, LENGTH_HINTS[self.seg_length.index],
                           (lx, y), lw)
        self._render_field(surface, "Who goes first", self.seg_first, self.first_hint, (fx, y), fw)
        stepper = self._goal_stepper()
        if stepper:
            stepper.render(surface)
            label = "Target score" if stepper is self.step_goal else "Moves per player"
            theme.draw_text(surface, label, theme.font(theme.SIZE_CAPTION, bold=True), col.TEXT_MUTED,
                            (stepper.rect.right + 14, stepper.rect.centery), "midleft")

    def _render_advanced(self, surface: pygame.Surface) -> None:
        theme.draw_overlay(surface)
        card = self.adv_card
        theme.draw_card(surface, card, radius=16)
        rows = self._layout_advanced()
        theme.draw_text(surface, "Advanced options", theme.serif(theme.SIZE_TITLE), col.TEXT,
                        (card.x + 28, card.y + 22))
        theme.draw_text(surface, "Optional. The recommended values work well for most games.",
                        theme.font(theme.SIZE_CAPTION), col.TEXT_MUTED, (card.x + 28, card.y + 56))
        self.btn_adv_close.render(surface)
        self.seg_adv_tab.render(surface)

        label_font = theme.font(theme.SIZE_BODY, bold=True)
        hint_font = theme.font(theme.SIZE_CAPTION)
        for label, hint, widget, y in rows:
            if widget is None:
                pygame.draw.line(surface, col.BORDER, (card.x + 28, y + 6), (card.right - 28, y + 6))
                theme.draw_text(surface, label.upper(), theme.font(13, bold=True), col.TEXT_SUBTLE,
                                (card.x + 28, y + 12))
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
