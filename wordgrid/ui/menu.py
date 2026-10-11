import pygame
from typing import Callable, Any
from wordgrid.ui.controls import Button, OptionSelector
from wordgrid.ui.colors import (
    COLOR_BG_DARK,
    COLOR_PANEL_BG,
    COLOR_PANEL_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_P1,
    COLOR_P2,
    COLOR_HIGHLIGHT_WORD,
    COLOR_BTN_PRIMARY,
)
from wordgrid.config import (
    MODE_UNTIL_BOARD_FULL,
    MODE_REACH_GOAL_SCORE,
    MODE_MOVE_LIMIT,
)


class MenuScreen:
    """Configures game settings, algorithm selection, and tournament execution."""

    def __init__(
        self,
        on_start_match: Callable[[dict], None],
        on_start_tournament: Callable[[dict], None],
        title_font: pygame.font.Font,
        font: pygame.font.Font,
        small_font: pygame.font.Font,
    ):
        self.on_start_match = on_start_match
        self.on_start_tournament = on_start_tournament
        self.title_font = title_font
        self.font = font
        self.small_font = small_font

        # Option Selectors
        self.sel_match_type = OptionSelector(
            rect=pygame.Rect(320, 150, 460, 48),
            label="Game Type",
            options=["Human vs AI", "AI vs AI", "Human vs Human"],
            initial_index=0,
            font=font,
            small_font=small_font,
        )

        self.sel_board_size = OptionSelector(
            rect=pygame.Rect(320, 210, 460, 48),
            label="Board Dimensions",
            options=["3 x 3 (Fast)", "4 x 4 (Standard)", "5 x 5 (Full)"],
            initial_index=2,
            font=font,
            small_font=small_font,
        )

        self.sel_game_mode = OptionSelector(
            rect=pygame.Rect(320, 270, 460, 48),
            label="Termination Condition",
            options=[
                MODE_UNTIL_BOARD_FULL,
                f"{MODE_REACH_GOAL_SCORE} (30 pts)",
                f"{MODE_MOVE_LIMIT} (20 moves)",
            ],
            initial_index=0,
            font=font,
            small_font=small_font,
        )

        self.sel_p1 = OptionSelector(
            rect=pygame.Rect(320, 330, 460, 48),
            label="Player 1 Agent",
            options=["Human", "Alpha-Beta", "Minimax", "MCTS", "Random"],
            initial_index=0,
            font=font,
            small_font=small_font,
        )

        self.sel_p2 = OptionSelector(
            rect=pygame.Rect(320, 390, 460, 48),
            label="Player 2 Agent",
            options=["Alpha-Beta", "Minimax", "MCTS", "Random", "Human"],
            initial_index=0,
            font=font,
            small_font=small_font,
        )

        self.sel_depth = OptionSelector(
            rect=pygame.Rect(320, 450, 220, 48),
            label="Search Depth",
            options=["Depth 1", "Depth 2", "Depth 3"],
            initial_index=1,
            font=font,
            small_font=small_font,
        )

        self.sel_mcts_sims = OptionSelector(
            rect=pygame.Rect(560, 450, 220, 48),
            label="MCTS Budget",
            options=["50 Sims", "100 Sims", "200 Sims"],
            initial_index=1,
            font=font,
            small_font=small_font,
        )

        # Action Buttons
        self.btn_start = Button(
            rect=pygame.Rect(320, 520, 460, 50),
            text="Start Match",
            font=title_font,
            is_primary=True,
            callback=self._handle_start_click,
        )

        self.btn_tournament = Button(
            rect=pygame.Rect(320, 580, 460, 42),
            text="Run AI Tournament Benchmark",
            font=font,
            callback=self._handle_tournament_click,
        )

    def _handle_start_click(self):
        settings = self.get_current_settings()
        self.on_start_match(settings)

    def _handle_tournament_click(self):
        settings = self.get_current_settings()
        self.on_start_tournament(settings)

    def get_current_settings(self) -> dict:
        # Parse board size
        size_str = self.sel_board_size.selected_value
        if "3" in size_str:
            b_size = 3
        elif "4" in size_str:
            b_size = 4
        else:
            b_size = 5

        # Parse termination mode
        mode_str = self.sel_game_mode.selected_value
        if MODE_REACH_GOAL_SCORE in mode_str:
            mode = MODE_REACH_GOAL_SCORE
        elif MODE_MOVE_LIMIT in mode_str:
            mode = MODE_MOVE_LIMIT
        else:
            mode = MODE_UNTIL_BOARD_FULL

        # Parse search depth & MCTS sims
        d_val = int(self.sel_depth.selected_value.split()[1])
        s_val = int(self.sel_mcts_sims.selected_value.split()[0])

        return {
            "match_type": self.sel_match_type.selected_value,
            "board_size": b_size,
            "game_mode": mode,
            "goal_score": 30,
            "move_limit": 20,
            "p1_agent": self.sel_p1.selected_value,
            "p2_agent": self.sel_p2.selected_value,
            "search_depth": d_val,
            "mcts_sims": s_val,
        }

    def handle_event(self, event: pygame.event.Event):
        self.sel_match_type.handle_event(event)
        self.sel_board_size.handle_event(event)
        self.sel_game_mode.handle_event(event)
        self.sel_p1.handle_event(event)
        self.sel_p2.handle_event(event)
        self.sel_depth.handle_event(event)
        self.sel_mcts_sims.handle_event(event)
        self.btn_start.handle_event(event)
        self.btn_tournament.handle_event(event)

    def update(self):
        pass

    def render(self, surface: pygame.Surface):
        surface.fill(COLOR_BG_DARK)

        # Header Title
        title_surf = self.title_font.render("WordBattle — Adversarial Word Construction", True, COLOR_P1)
        surface.blit(title_surf, title_surf.get_rect(center=(surface.get_width() // 2, 70)))

        sub_surf = self.small_font.render(
            "Adversarial Search Lab: Minimax, Alpha-Beta Pruning & Monte Carlo Tree Search",
            True,
            COLOR_TEXT_MUTED,
        )
        surface.blit(sub_surf, sub_surf.get_rect(center=(surface.get_width() // 2, 105)))

        # Render Selectors
        self.sel_match_type.render(surface)
        self.sel_board_size.render(surface)
        self.sel_game_mode.render(surface)
        self.sel_p1.render(surface)
        self.sel_p2.render(surface)
        self.sel_depth.render(surface)
        self.sel_mcts_sims.render(surface)

        # Render Buttons
        self.btn_start.render(surface)
        self.btn_tournament.render(surface)
