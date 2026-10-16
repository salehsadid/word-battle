"""Headless smoke test: every screen, dialog and state renders without errors."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from wordgrid.ui.runner import UIRunner
from wordgrid.ui.menu import MODE_VS_AI, MODE_TWO_PLAYERS, MODE_AI_VS_AI


@pytest.fixture(scope="module")
def ui():
    # pygame is left initialised: other tests reuse the cached theme fonts.
    return UIRunner()


def click(screen, pos):
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def test_settings_screen_modes_and_advanced_tabs(ui):
    menu = ui.menu_screen
    for mode in (MODE_VS_AI, MODE_TWO_PLAYERS, MODE_AI_VS_AI):
        menu._set_mode(mode)
        for option in ("Fill the board", "Reach a score", "Move limit"):
            menu.seg_length.set_value(option)
            menu.render(ui.screen)
            assert menu.errors == []
    menu.advanced_open = True
    for tab in range(4):
        menu.seg_adv_tab.index = tab
        menu.render(ui.screen)
    menu.advanced_open = False
    menu.help.open()
    menu.render(ui.screen)
    menu.help.close()


def test_invalid_name_blocks_start(ui):
    menu = ui.menu_screen
    menu._set_mode(MODE_TWO_PLAYERS)
    menu.inp_p2.text = ""
    menu._refresh()
    assert not menu.btn_start.enabled and menu.inp_p2.error
    menu.inp_p2.text = "Sam"
    menu._refresh()
    assert menu.btn_start.enabled


def test_two_player_match_with_picker_confirm_and_result(ui):
    menu = ui.menu_screen
    menu._set_mode(MODE_TWO_PLAYERS)
    menu.seg_board.set_value("3×3")
    menu._refresh()
    menu._handle_start_click()
    game = ui.game_screen
    assert game is not None

    # Select a square, then pick a letter from the pop-up picker
    cell = game.board_renderer.cell_rect(game.engine.state.board, 1, 1)
    click(game, cell.center)
    assert game.picker.visible
    click(game, dict(game.picker.keys)["A"].center)
    assert game.engine.state.board.grid[1][1] == "A"
    game.render(ui.screen)

    # Restart mid-game asks for confirmation first
    game._ask_restart()
    assert game.confirm.visible
    game.render(ui.screen)
    game.confirm.close()

    # Fill the board by keyboard and reach the result card
    for r in range(3):
        for c in range(3):
            if game.engine.state.board.grid[r][c] is None:
                game._select_cell((r, c))
                game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_x, unicode="x", mod=0))
    assert game.engine.is_game_over
    game.render(ui.screen)
    game.word_history_panel.active_tab = "log"
    game._dismiss_overlay()
    game.render(ui.screen)
    ui.return_to_menu()
