"""Pre-match settings: a simple main screen plus an optional Advanced options sheet."""

import pygame
from typing import Callable, List, Optional, Tuple
from wordgrid.ui import colors as col
from wordgrid.ui import theme
from wordgrid.ui.controls import (
    Button,
    ChoiceCard,
    OptionSelector,
    SegmentedControl,
    Slider,
    Stepper,
    TextInput,
    Toggle,
    UnderlineTabs,
    wrap_text,
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

MODE_VS_AI = "vs_ai"
MODE_TWO_PLAYERS = "two_players"
MODE_AI_VS_AI = "ai_vs_ai"

ALGO_NAMES = ["Strategist", "Explorer"]
ALGO_CONTROLLERS = [CONTROLLER_MINIMAX, CONTROLLER_MCTS]
ALGO_HINTS = [
    "Minimax search: plans ahead and weighs your threats.",
    "Monte Carlo search: simulates many possible futures.",
]
BOARD_OPTIONS = [f"{n}×{n}" for n in range(MIN_BOARD_SIZE, MAX_BOARD_SIZE + 1)]
LENGTH_OPTIONS = ["Fill the board", "Reach a score", "Move limit"]
LENGTH_MODES = [MODE_UNTIL_BOARD_FULL, MODE_REACH_GOAL_SCORE, MODE_MOVE_LIMIT]
LENGTH_HINTS = [
    "Play until every square is used.",
    "The first player to reach the target wins.",
    "Each player gets the same number of moves.",
]

CONTENT_X = (110, 570)
CONTENT_W = 420
ROW_Y = (250, 342, 434, 526)
CONTROL_H = 42


class _Field:
    """A captioned control on the settings grid."""

    def __init__(self, caption: str, widget, col_idx: int, row: int, hint: Callable[[], str] = lambda: "",
                 width: int = CONTENT_W):
        self.caption = caption
        self.widget = widget
        self.hint = hint
        x = CONTENT_X[col_idx]
        y = ROW_Y[row]
        self.caption_pos = (x, y)
        widget.rect = pygame.Rect(x, y + 22, width, CONTROL_H)
        self.hint_pos = (x, y + 22 + CONTROL_H + 5)


class MenuScreen:
    """Friendly settings screen: choose how to play, then press Start."""

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
        self.mode = MODE_VS_AI

        self._build_main()
        self._build_advanced(MatchSettings())
        self._layout()
        self._refresh()

    # ================================================================== main screen
    def _build_main(self) -> None:
        r = pygame.Rect(0, 0, 10, 10)
        refresh = lambda *a: self._refresh()

        card_w, gap = 280, 20
        specs = [
            (MODE_VS_AI, "Play vs Computer", "Challenge an AI opponent at the level you choose.", ["person", "computer"]),
            (MODE_TWO_PLAYERS, "Two Players", "Take turns with a friend on the same screen.", ["person", "person"]),
            (MODE_AI_VS_AI, "Watch AI vs AI", "See the Strategist and the Explorer battle it out.", ["computer", "computer"]),
        ]
        self.mode_cards: List[Tuple[str, ChoiceCard]] = []
        for i, (mode, title, desc, icons) in enumerate(specs):
            rect = pygame.Rect(CONTENT_X[0] + i * (card_w + gap), 120, card_w, 104)
            card = ChoiceCard(rect, title, desc, icons, callback=lambda m=mode: self._set_mode(m))
            self.mode_cards.append((mode, card))

        # Play vs Computer
        self.inp_you = TextInput(r, text="You", placeholder="Your name", on_change=lambda t: self._refresh())
        self.seg_opp = SegmentedControl(r, ALGO_NAMES, 0, on_change=refresh)
        self.seg_diff = SegmentedControl(r, DIFFICULTIES, 1, on_change=refresh)
        self.seg_first_vs = SegmentedControl(r, ["You", "Computer", "Random"], 0, on_change=refresh)
        # Two players
        self.inp_p1 = TextInput(r, text="Player 1", placeholder="Player 1 name", on_change=lambda t: self._refresh())
        self.inp_p2 = TextInput(r, text="Player 2", placeholder="Player 2 name", on_change=lambda t: self._refresh())
        self.seg_first_2p = SegmentedControl(r, ["Player 1", "Player 2", "Random"], 0, on_change=refresh)
        # AI vs AI
        self.seg_ai1 = SegmentedControl(r, ALGO_NAMES, 0, on_change=refresh)
        self.seg_ai2 = SegmentedControl(r, ALGO_NAMES, 1, on_change=refresh)
        self.seg_ai1_diff = SegmentedControl(r, DIFFICULTIES, 1, on_change=refresh)
        self.seg_ai2_diff = SegmentedControl(r, DIFFICULTIES, 1, on_change=refresh)
        self.seg_first_ai = SegmentedControl(r, ["Blue", "Orange", "Random"], 0, on_change=refresh)
        # Shared
        self.seg_board = SegmentedControl(r, BOARD_OPTIONS, 2, on_change=refresh)
        self.seg_length = SegmentedControl(r, LENGTH_OPTIONS, 0, on_change=lambda *a: self._layout_and_refresh())
        self.step_goal = Stepper(r, 30, 5, 300, 5, on_change=refresh, fmt=lambda v: f"{v:g} points")
        self.step_limit = Stepper(r, 10, 1, 40, 1, on_change=refresh, fmt=lambda v: f"{v:g} moves each")

        self.btn_help = Button(pygame.Rect(860, 34, 130, 40), "How to play", variant="ghost",
                               callback=self.help.open)
        self.btn_advanced = Button(pygame.Rect(CONTENT_X[0], 664, 210, 46), "Advanced options",
                                   variant="secondary", callback=self._open_advanced)
        self.btn_bench = Button(pygame.Rect(CONTENT_X[0] + 222, 664, 180, 46), "AI benchmark", variant="ghost",
                                callback=self._handle_tournament_click,
                                tooltip="Round-robin of all AIs on this board; results saved to data/")
        self.btn_start = Button(pygame.Rect(770, 660, 220, 52), "Start game", variant="primary",
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

    def _layout(self) -> None:
        board_hint = lambda: ""
        length_hint = lambda: LENGTH_HINTS[self.seg_length.index]
        fields: List[_Field] = []
        if self.mode == MODE_VS_AI:
            fields += [
                _Field("Your name", self.inp_you, 0, 0),
                _Field("Opponent", self.seg_opp, 1, 0, lambda: ALGO_HINTS[self.seg_opp.index]),
                _Field("Difficulty", self.seg_diff, 0, 1,
                       lambda: self._difficulty_hint(self.seg_opp.index, self.seg_diff.value)),
                _Field("Who goes first", self.seg_first_vs, 1, 1),
            ]
        elif self.mode == MODE_TWO_PLAYERS:
            fields += [
                _Field("Player 1 (blue)", self.inp_p1, 0, 0),
                _Field("Player 2 (orange)", self.inp_p2, 1, 0),
                _Field("Who goes first", self.seg_first_2p, 0, 1),
            ]
        else:
            fields += [
                _Field("Blue player", self.seg_ai1, 0, 0, lambda: ALGO_HINTS[self.seg_ai1.index]),
                _Field("Orange player", self.seg_ai2, 1, 0, lambda: ALGO_HINTS[self.seg_ai2.index]),
                _Field("Blue difficulty", self.seg_ai1_diff, 0, 1,
                       lambda: self._difficulty_hint(self.seg_ai1.index, self.seg_ai1_diff.value)),
                _Field("Orange difficulty", self.seg_ai2_diff, 1, 1,
                       lambda: self._difficulty_hint(self.seg_ai2.index, self.seg_ai2_diff.value)),
                _Field("Who goes first", self.seg_first_ai, 0, 3),
            ]
        fields += [
            _Field("Board size", self.seg_board, 0, 2, board_hint),
            _Field("How the match ends", self.seg_length, 1, 2, length_hint),
        ]
        mode = LENGTH_MODES[self.seg_length.index]
        if mode == MODE_REACH_GOAL_SCORE:
            fields.append(_Field("Target score", self.step_goal, 1, 3, width=220))
        elif mode == MODE_MOVE_LIMIT:
            fields.append(_Field("Moves per player", self.step_limit, 1, 3, width=220))
        self.fields = fields

    def _layout_and_refresh(self) -> None:
        self._layout()
        self._refresh()

    def _set_mode(self, mode: str) -> None:
        self.mode = mode
        for inp in (self.inp_you, self.inp_p1, self.inp_p2):
            inp.focused = False
        self._layout_and_refresh()

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
            return f"{n1} Blue", f"{n2} Orange"
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

        if self.mode == MODE_VS_AI:
            i = self.seg_opp.index
            p1 = PlayerSettings(self.inp_you.text.strip(), CONTROLLER_HUMAN)
            p2 = PlayerSettings(ALGO_NAMES[i], ALGO_CONTROLLERS[i], self._difficulty(i, self.seg_diff.value))
            start = [1, 2, 0][self.seg_first_vs.index]
            match_type = MATCH_HUMAN_VS_AI
        elif self.mode == MODE_TWO_PLAYERS:
            p1 = PlayerSettings(self.inp_p1.text.strip(), CONTROLLER_HUMAN)
            p2 = PlayerSettings(self.inp_p2.text.strip(), CONTROLLER_HUMAN)
            start = [1, 2, 0][self.seg_first_2p.index]
            match_type = MATCH_HUMAN_VS_HUMAN
        else:
            i1, i2 = self.seg_ai1.index, self.seg_ai2.index
            n1, n2 = self._names(i1, i2)
            p1 = PlayerSettings(n1, ALGO_CONTROLLERS[i1], self._difficulty(i1, self.seg_ai1_diff.value))
            p2 = PlayerSettings(n2, ALGO_CONTROLLERS[i2], self._difficulty(i2, self.seg_ai2_diff.value))
            start = [1, 2, 0][self.seg_first_ai.index]
            match_type = MATCH_AI_VS_AI

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
        for card_mode, card in self.mode_cards:
            card.selected = card_mode == self.mode
        self.seg_diff.enabled = not self.override[ALGO_CONTROLLERS[self.seg_opp.index]]
        self.seg_ai1_diff.enabled = not self.override[ALGO_CONTROLLERS[self.seg_ai1.index]]
        self.seg_ai2_diff.enabled = not self.override[ALGO_CONTROLLERS[self.seg_ai2.index]]
        _, self.errors = self.build_settings()
        same_names = any("different names" in e for e in self.errors)
        visible = self._visible_inputs() if not self.advanced_open else []
        for inp in (self.inp_you, self.inp_p1, self.inp_p2):
            inp.error = not inp.text.strip() or len(inp.text) > 16 or (same_names and inp in visible)
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
        return [card for _, card in self.mode_cards] + [f.widget for f in self.fields] + [
            self.btn_help, self.btn_advanced, self.btn_bench, self.btn_start]

    def _visible_inputs(self) -> List[TextInput]:
        if self.advanced_open:
            return [self.inp_seed] if self.seg_adv_tab.index == 0 else []
        return [f.widget for f in self.fields if isinstance(f.widget, TextInput)]

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
        surface.fill(col.BG)

        theme.draw_logo(surface, (CONTENT_X[0], 30), tile=38)
        theme.draw_text(surface, "Build words on the grid and outscore your opponent.",
                        theme.font(theme.SIZE_BODY), col.TEXT_MUTED, (CONTENT_X[0], 82))
        self.btn_help.render(surface)

        for _, card in self.mode_cards:
            card.render(surface)

        caption_font = theme.font(theme.SIZE_CAPTION, bold=True)
        hint_font = theme.font(theme.SIZE_CAPTION)
        for f in self.fields:
            theme.draw_text(surface, f.caption, caption_font, col.TEXT_MUTED, f.caption_pos)
            f.widget.render(surface)
            hint = f.hint()
            if hint:
                theme.draw_text(surface, hint, hint_font, col.TEXT_SUBTLE, f.hint_pos, max_width=CONTENT_W)

        pygame.draw.line(surface, col.BORDER, (CONTENT_X[0], 640), (CONTENT_X[1] + CONTENT_W, 640))
        self.btn_advanced.render(surface)
        self.btn_bench.render(surface)
        self.btn_start.render(surface)

        status_font = theme.font(theme.SIZE_CAPTION)
        if self.errors:
            theme.draw_text(surface, self.errors[0], status_font, col.DANGER, (self.btn_start.rect.right, 724),
                            "topright", max_width=560)
        else:
            customised = [n for c, n in zip(ALGO_CONTROLLERS, ALGO_NAMES) if self.override[c]]
            note = "Ready when you are. Press Enter to start."
            if customised:
                note = f"Custom {' and '.join(customised)} settings active. Press Enter to start."
            theme.draw_text(surface, note, status_font, col.TEXT_SUBTLE, (self.btn_start.rect.right, 724), "topright")

        if self.btn_bench.is_hovered and self.btn_bench.tooltip:
            theme.draw_tooltip(surface, self.btn_bench.tooltip, self.btn_bench.rect.midtop)

        if self.advanced_open:
            self._render_advanced(surface)
        self.help.render(surface)

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
