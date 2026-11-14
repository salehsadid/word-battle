import pygame
from typing import Optional, Tuple, List, Set
from wordgrid.game.board import Board
from wordgrid.game.scoring import occurrence_cells, OccurrenceKey
from wordgrid.ui import colors as col
from wordgrid.ui import theme

FLASH_SECONDS = 1.4


class BoardRenderer:
    """Draws the grid as flat puzzle squares: yellow = newest letter, green = scored word."""

    def __init__(self, board_rect: pygame.Rect, font=None, small_font=None):
        self.board_rect = board_rect
        self.selected_cell: Optional[Tuple[int, int]] = None

    def cell_rect(self, board: Board, r: int, c: int) -> pygame.Rect:
        size = board.size
        pad = 10
        inner = self.board_rect.inflate(-2 * pad, -2 * pad)
        cell = inner.width / size
        gap = max(4, int(cell * 0.07))
        return pygame.Rect(
            round(inner.x + c * cell + gap / 2),
            round(inner.y + r * cell + gap / 2),
            round(cell - gap),
            round(cell - gap),
        )

    def get_cell_at_pos(self, board: Board, pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Maps a screen position to (row, col), or None."""
        if not self.board_rect.collidepoint(pos):
            return None
        for r in range(board.size):
            for c in range(board.size):
                if self.cell_rect(board, r, c).inflate(4, 4).collidepoint(pos):
                    return (r, c)
        return None

    def render(
        self,
        surface: pygame.Surface,
        board: Board,
        last_move: Optional[Tuple[int, int, str]] = None,
        highlight_occurrences: Optional[List[Tuple[str, int, OccurrenceKey]]] = None,
        interactive: bool = True,
        flash: Optional[Tuple[OccurrenceKey, float]] = None,
    ) -> None:
        size = board.size
        mouse = pygame.mouse.get_pos()
        hovered = self.get_cell_at_pos(board, mouse) if interactive else None

        # Coordinate labels (1-based, matching the rest of the UI)
        cap = theme.label(13)
        for i in range(size):
            top = self.cell_rect(board, 0, i)
            left = self.cell_rect(board, i, 0)
            theme.draw_text(surface, str(i + 1), cap, col.TEXT_SUBTLE, (top.centerx, self.board_rect.y - 11), "center")
            theme.draw_text(surface, str(i + 1), cap, col.TEXT_SUBTLE, (self.board_rect.x - 13, left.centery), "center")

        highlight: Set[Tuple[int, int]] = set()
        for _, _, key in highlight_occurrences or []:
            highlight.update(occurrence_cells(key))
        flash_cells: Set[Tuple[int, int]] = set()
        flash_strength = 0.0
        if flash:
            key, age = flash
            if age < FLASH_SECONDS:
                flash_cells = set(occurrence_cells(key))
                flash_strength = 1.0 - age / FLASH_SECONDS

        tile_font = theme.label(max(18, int(self.cell_rect(board, 0, 0).height * 0.56)))
        for r in range(size):
            for c in range(size):
                rect = self.cell_rect(board, r, c)
                letter = board.grid[r][c]
                is_last = last_move is not None and (r, c) == (last_move[0], last_move[1])

                if letter is None:
                    selected = (r, c) == self.selected_cell
                    pygame.draw.rect(surface, col.CELL_EMPTY, rect)
                    if selected:
                        pygame.draw.rect(surface, col.TEXT, rect, 3)
                    else:
                        border = col.BORDER_STRONG if (r, c) == hovered else col.BORDER
                        pygame.draw.rect(surface, border, rect, 2)
                    continue

                in_word = (r, c) in highlight
                if (r, c) in flash_cells:
                    rect = rect.inflate(round(6 * flash_strength), round(6 * flash_strength))  # brief "pop"
                if in_word:
                    face, edge, ink = col.SUCCESS, col.SUCCESS, col.TEXT_ON_ACCENT
                elif is_last:
                    face, edge, ink = col.AMBER, col.AMBER, col.TEXT
                else:
                    face, edge, ink = col.TILE_FACE, col.TILE_EDGE, col.TILE_TEXT
                pygame.draw.rect(surface, face, rect)
                pygame.draw.rect(surface, edge, rect, 2)
                if is_last and in_word:
                    pygame.draw.rect(surface, col.AMBER, rect, 4)
                theme.draw_text(surface, letter, tile_font, ink, (rect.centerx, rect.centery + 1), "center")
