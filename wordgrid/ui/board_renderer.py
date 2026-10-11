import pygame
from typing import Optional, Tuple, List
from wordgrid.game.board import Board
from wordgrid.ui.colors import (
    COLOR_GRID_BG,
    COLOR_CELL_EMPTY,
    COLOR_CELL_HOVER,
    COLOR_CELL_SELECTED,
    COLOR_CELL_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_LAST_MOVE,
    COLOR_HIGHLIGHT_WORD,
    COLOR_P1,
    COLOR_P2,
    COLOR_PANEL_BORDER,
)


class BoardRenderer:
    """Renders the game board with smooth highlights, cell selection, and letter tiles."""

    def __init__(
        self,
        board_rect: pygame.Rect,
        font: pygame.font.Font,
        small_font: pygame.font.Font,
    ):
        self.board_rect = board_rect
        self.font = font
        self.small_font = small_font
        self.selected_cell: Optional[Tuple[int, int]] = None
        self.highlighted_cells: List[Tuple[int, int]] = []

    def get_cell_at_pos(self, board: Board, pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Maps screen coordinate pos to (row, col) or None."""
        if not self.board_rect.collidepoint(pos):
            return None

        size = board.size
        cell_size = self.board_rect.width / size
        c = int((pos[0] - self.board_rect.x) // cell_size)
        r = int((pos[1] - self.board_rect.y) // cell_size)

        if 0 <= r < size and 0 <= c < size:
            return (r, c)
        return None

    def render(
        self,
        surface: pygame.Surface,
        board: Board,
        last_move: Optional[Tuple[int, int, str]] = None,
        highlight_occurrences: Optional[List[Tuple[str, int, Tuple[str, int, int, int, int]]]] = None,
    ) -> None:
        size = board.size
        cell_size = self.board_rect.width / size
        mouse_pos = pygame.mouse.get_pos()
        hovered_cell = self.get_cell_at_pos(board, mouse_pos)

        # Draw grid backdrop
        pygame.draw.rect(surface, COLOR_GRID_BG, self.board_rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, self.board_rect, width=2, border_radius=8)

        # Gather highlight cells from last scored words
        highlight_set = set()
        if highlight_occurrences:
            for _, _, key in highlight_occurrences:
                orient, r1, c1, r2, c2 = key
                if orient == "H":
                    for c in range(c1, c2 + 1):
                        highlight_set.add((r1, c))
                else:
                    for r in range(r1, r2 + 1):
                        highlight_set.add((r, c1))

        # Render each cell
        for r in range(size):
            for c in range(size):
                cell_rect = pygame.Rect(
                    self.board_rect.x + c * cell_size + 3,
                    self.board_rect.y + r * cell_size + 3,
                    cell_size - 6,
                    cell_size - 6,
                )

                val = board.get(r, c)
                is_hover = (r, c) == hovered_cell and val is None
                is_selected = (r, c) == self.selected_cell and val is None
                is_last = last_move is not None and (r, c) == (last_move[0], last_move[1])
                is_word_cell = (r, c) in highlight_set

                # Determine cell background
                if is_word_cell:
                    bg = pygame.Color(16, 185, 129, 40)
                    border_color = COLOR_HIGHLIGHT_WORD
                    border_w = 3
                elif is_selected:
                    bg = COLOR_CELL_SELECTED
                    border_color = COLOR_P1
                    border_w = 2
                elif is_last:
                    bg = pygame.Color(234, 179, 8, 30)
                    border_color = COLOR_LAST_MOVE
                    border_w = 2
                elif is_hover:
                    bg = COLOR_CELL_HOVER
                    border_color = COLOR_CELL_BORDER
                    border_w = 1
                else:
                    bg = COLOR_CELL_EMPTY
                    border_color = COLOR_CELL_BORDER
                    border_w = 1

                pygame.draw.rect(surface, bg, cell_rect, border_radius=6)
                pygame.draw.rect(surface, border_color, cell_rect, width=border_w, border_radius=6)

                # Render letter if present
                if val is not None:
                    txt_surf = self.font.render(val, True, COLOR_TEXT_PRIMARY)
                    txt_rect = txt_surf.get_rect(center=cell_rect.center)
                    surface.blit(txt_surf, txt_rect)
                elif is_selected:
                    # Pulsing prompt or underscore
                    prompt_surf = self.small_font.render("type A-Z", True, COLOR_P1)
                    surface.blit(prompt_surf, prompt_surf.get_rect(center=cell_rect.center))
