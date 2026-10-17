import time
import pygame
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Union
from wordgrid.game.scoring import OccurrenceKey, direction_label
from wordgrid.ui import colors as col
from wordgrid.ui import theme
from wordgrid.ui.controls import UnderlineTabs


@dataclass
class MatchedWordRecord:
    """A scored word in the match history."""
    word: str
    length: int
    player: int  # 1 or 2
    player_name: str
    move_number: int
    move: Tuple[int, int, str]  # (r, c, letter)
    occurrence_key: Optional[OccurrenceKey] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class MoveLogRecord:
    """One entry of the full move log (zero-point moves included)."""
    move_number: int
    player: int
    player_name: str
    move: Tuple[int, int, str]
    points: int
    word: Optional[str] = None
    occurrence_key: Optional[OccurrenceKey] = None
    blocked_words: List[str] = field(default_factory=list)


TAB_WORDS = "words"
TAB_LOG = "log"

Record = Union[MatchedWordRecord, MoveLogRecord]


class WordHistoryPanel:
    """Scrollable match history with two tabs: scored words, and every move.

    Hovering or clicking an entry highlights its word on the board.
    """

    WORD_ROW_H = 50
    LOG_ROW_H = 32

    def __init__(self, rect: pygame.Rect, title_font=None, font=None, small_font=None):
        # Fonts are accepted for backwards compatibility; the theme provides typography.
        self.rect = rect
        self.items: List[MatchedWordRecord] = []
        self.log_items: List[MoveLogRecord] = []
        self.scroll_y: float = 0.0
        self.hovered_item: Optional[Record] = None
        self.selected_item: Optional[Record] = None
        self._visible_rows: List[Tuple[pygame.Rect, Record]] = []
        self.tabs = UnderlineTabs(pygame.Rect(rect.x + 12, rect.y + 50, rect.width - 24, 38),
                                     ["Words", "All moves"], 0, on_change=self._on_tab)

    @property
    def active_tab(self) -> str:
        return TAB_WORDS if self.tabs.index == 0 else TAB_LOG

    @active_tab.setter
    def active_tab(self, tab: str) -> None:
        self.tabs.index = 0 if tab == TAB_WORDS else 1
        self._on_tab()

    def _on_tab(self, *args) -> None:
        self.scroll_y = 0.0
        self.selected_item = None

    # ------------------------------------------------------------------ data
    def add_match(self, word: str, length: int, player: int, player_name: str, move_number: int,
                  move: Tuple[int, int, str], occurrence_key: Optional[OccurrenceKey] = None) -> None:
        """Adds a scored word (newest first)."""
        self.items.insert(0, MatchedWordRecord(word.upper(), length, player, player_name, move_number, move,
                                               occurrence_key))
        if self.active_tab == TAB_WORDS:
            self.scroll_y = 0.0

    def add_move(self, move_number: int, player: int, player_name: str, move: Tuple[int, int, str], points: int,
                 word: Optional[str] = None, occurrence_key: Optional[OccurrenceKey] = None,
                 blocked_words: Optional[List[str]] = None) -> None:
        """Adds a move to the move log (newest first)."""
        self.log_items.insert(0, MoveLogRecord(move_number, player, player_name, move, points, word,
                                               occurrence_key, list(blocked_words or [])))
        if self.active_tab == TAB_LOG:
            self.scroll_y = 0.0

    def clear(self) -> None:
        self.items.clear()
        self.log_items.clear()
        self.scroll_y = 0.0
        self.hovered_item = None
        self.selected_item = None
        self._visible_rows.clear()

    @property
    def highlight_key(self) -> Optional[Tuple[str, int, OccurrenceKey]]:
        """Occurrence to highlight on the board (hovered entry first, then selected)."""
        for item in (self.hovered_item, self.selected_item):
            if item is not None and item.occurrence_key:
                word = item.word or ""
                return (word, len(word), item.occurrence_key)
        return None

    # ------------------------------------------------------------------ events
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.tabs.handle_event(event):
            return
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            self.scroll_y -= event.y * 40
        elif event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            if event.button == 1:
                clicked = next((rec for r, rec in self._visible_rows if r.collidepoint(event.pos)), None)
                self.selected_item = None if (clicked is None or clicked is self.selected_item) else clicked
            elif event.button == 4:
                self.scroll_y -= 40
            elif event.button == 5:
                self.scroll_y += 40

    def update(self) -> None:
        mouse = pygame.mouse.get_pos()
        self.hovered_item = None
        if self.rect.collidepoint(mouse):
            self.hovered_item = next((rec for r, rec in self._visible_rows if r.collidepoint(mouse)), None)

    # ------------------------------------------------------------------ render
    def _row_background(self, surface, rect: pygame.Rect, item: Record) -> None:
        if item is self.selected_item:
            theme.aa_rect(surface, col.SUCCESS_SOFT, rect, border_radius=8)
            theme.aa_rect(surface, col.SUCCESS, rect, width=1, border_radius=8)
        elif item is self.hovered_item:
            theme.aa_rect(surface, col.SURFACE_ALT, rect, border_radius=8)

    def _render_word(self, surface, rect: pygame.Rect, item: MatchedWordRecord) -> None:
        self._row_background(surface, rect, item)
        theme.aa_circle(surface, col.player_color(item.player), (rect.x + 14, rect.y + 17), 5)
        theme.draw_text(surface, item.word, theme.font(theme.SIZE_HEADING, bold=True), col.TEXT,
                        (rect.x + 28, rect.y + 6))
        r, c, ch = item.move
        sub = f"Move {item.move_number}  ·  {item.player_name}  ·  {ch} at row {r + 1}, col {c + 1}  ·  " \
              f"{direction_label(item.occurrence_key)}"
        theme.draw_text(surface, sub, theme.font(12), col.TEXT_MUTED, (rect.x + 28, rect.y + 29),
                        max_width=rect.width - 100)
        pill = pygame.Rect(0, 0, 50, 26)
        pill.midright = (rect.right - 8, rect.centery)
        theme.aa_rect(surface, col.SUCCESS_SOFT, pill, border_radius=13)
        theme.draw_text(surface, f"+{item.length}", theme.font(theme.SIZE_BODY, bold=True), col.SUCCESS,
                        pill.center, "center")

    def _render_log(self, surface, rect: pygame.Rect, item: MoveLogRecord) -> None:
        self._row_background(surface, rect, item)
        cy = rect.centery
        theme.draw_text(surface, str(item.move_number), theme.font(theme.SIZE_CAPTION), col.TEXT_SUBTLE,
                        (rect.x + 22, cy), "center")
        theme.aa_circle(surface, col.player_color(item.player), (rect.x + 44, cy), 4)
        theme.draw_text(surface, item.player_name, theme.font(theme.SIZE_CAPTION, bold=True), col.TEXT,
                        (rect.x + 54, cy), "midleft", max_width=110)
        r, c, ch = item.move
        theme.draw_text(surface, f"{ch} at row {r + 1}, col {c + 1}", theme.font(theme.SIZE_CAPTION), col.TEXT_MUTED,
                        (rect.x + 172, cy), "midleft")
        if item.points > 0 and item.word:
            result, color = f"{item.word}  +{item.points}", col.SUCCESS
        elif item.blocked_words:
            result, color = f"{item.blocked_words[0]} already used", col.TEXT_SUBTLE
        else:
            result, color = "no word", col.TEXT_SUBTLE
        theme.draw_text(surface, result, theme.font(theme.SIZE_CAPTION, bold=item.points > 0), color,
                        (rect.right - 10, cy), "midright", max_width=150)

    def render(self, surface: pygame.Surface) -> None:
        self.update()
        theme.draw_card(surface, self.rect)
        x = self.rect.x + 18
        theme.draw_text(surface, "Match history", theme.serif(20), col.TEXT, (x, self.rect.y + 14))
        total = sum(i.length for i in self.items)
        theme.draw_text(surface, f"{len(self.items)} words  ·  {total} points", theme.font(theme.SIZE_CAPTION),
                        col.TEXT_MUTED, (self.rect.right - 18, self.rect.y + 20), "topright")
        self.tabs.options = [f"Words ({len(self.items)})", f"All moves ({len(self.log_items)})"]
        self.tabs.render(surface)

        content = pygame.Rect(self.rect.x + 10, self.rect.y + 98, self.rect.width - 20, self.rect.height - 108)
        self._visible_rows.clear()
        words_tab = self.active_tab == TAB_WORDS
        records: List[Record] = list(self.items) if words_tab else list(self.log_items)
        row_h = self.WORD_ROW_H if words_tab else self.LOG_ROW_H

        if not records:
            msg = "Words you score will appear here." if words_tab else "Every move, including 0-point moves."
            theme.draw_text(surface, "Nothing yet", theme.font(theme.SIZE_BODY, bold=True), col.TEXT_MUTED,
                            (content.centerx, content.y + 40), "center")
            theme.draw_text(surface, msg, theme.font(theme.SIZE_CAPTION), col.TEXT_SUBTLE,
                            (content.centerx, content.y + 64), "center")
            return

        total_h = len(records) * row_h
        max_scroll = max(0, total_h - content.height)
        self.scroll_y = max(0.0, min(self.scroll_y, float(max_scroll)))
        has_bar = max_scroll > 0
        row_w = content.width - (10 if has_bar else 0)

        old_clip = surface.get_clip()
        surface.set_clip(content)
        try:
            first = int(self.scroll_y // row_h)
            last = min(len(records), int((self.scroll_y + content.height) // row_h) + 2)
            for idx in range(first, last):
                rect = pygame.Rect(content.x, content.y + idx * row_h - int(self.scroll_y), row_w, row_h - 4)
                item = records[idx]
                self._visible_rows.append((rect, item))
                if words_tab:
                    self._render_word(surface, rect, item)
                else:
                    self._render_log(surface, rect, item)
                if idx < len(records) - 1:
                    pygame.draw.line(surface, col.SURFACE_ALT, (rect.x + 10, rect.bottom + 1),
                                     (rect.right - 10, rect.bottom + 1))
        finally:
            surface.set_clip(old_clip)

        if has_bar:
            track = pygame.Rect(content.right - 5, content.y, 4, content.height)
            thumb_h = max(30, int(track.height * content.height / total_h))
            thumb_y = track.y + int((self.scroll_y / max_scroll) * (track.height - thumb_h))
            theme.aa_rect(surface, col.BORDER_STRONG, (track.x, thumb_y, track.width, thumb_h), border_radius=2)
