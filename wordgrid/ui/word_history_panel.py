import time
import pygame
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from wordgrid.game.scoring import OccurrenceKey
from wordgrid.ui.colors import (
    COLOR_PANEL_BG,
    COLOR_PANEL_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_DIM,
    COLOR_P1,
    COLOR_P1_BG,
    COLOR_P2,
    COLOR_P2_BG,
    COLOR_HIGHLIGHT_WORD,
    COLOR_LAST_MOVE,
    COLOR_CARD_BG,
    COLOR_CARD_BORDER,
    COLOR_CARD_HOVER,
    COLOR_BADGE_BG,
)


@dataclass
class MatchedWordRecord:
    """Represents a successfully formed and scored word occurrence in match history."""
    word: str
    length: int
    player: int  # 1 or 2
    player_name: str
    move_number: int
    move: Tuple[int, int, str]  # (r, c, letter)
    occurrence_key: Optional[OccurrenceKey] = None
    timestamp: float = field(default_factory=time.time)


class WordHistoryPanel:
    """Displays an interactive, scrollable history of all matched words alongside the player who made each move."""

    def __init__(
        self,
        rect: pygame.Rect,
        title_font: pygame.font.Font,
        font: pygame.font.Font,
        small_font: pygame.font.Font,
    ):
        self.rect = rect
        self.title_font = title_font
        self.font = font
        self.small_font = small_font

        self.items: List[MatchedWordRecord] = []
        self.scroll_y: float = 0.0
        self.hovered_item: Optional[MatchedWordRecord] = None
        self.selected_item: Optional[MatchedWordRecord] = None

        self._visible_card_rects: List[Tuple[pygame.Rect, MatchedWordRecord]] = []

    def add_match(
        self,
        word: str,
        length: int,
        player: int,
        player_name: str,
        move_number: int,
        move: Tuple[int, int, str],
        occurrence_key: Optional[OccurrenceKey] = None,
    ) -> None:
        """Adds a newly matched word to the history.
        
        Newest words are kept at index 0 so the most recent move is always visible at the top.
        """
        record = MatchedWordRecord(
            word=word.upper(),
            length=length,
            player=player,
            player_name=player_name,
            move_number=move_number,
            move=move,
            occurrence_key=occurrence_key,
        )
        self.items.insert(0, record)
        self.scroll_y = 0.0  # Reset to top so the latest match is in view

    def clear(self) -> None:
        """Resets the matched word history."""
        self.items.clear()
        self.scroll_y = 0.0
        self.hovered_item = None
        self.selected_item = None
        self._visible_card_rects.clear()

    def handle_event(self, event: pygame.event.Event) -> None:
        """Handles scrolling and card selection events."""
        mouse_pos = pygame.mouse.get_pos()

        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(mouse_pos):
                self.scroll_y -= event.y * 36

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                # Mouse wheel buttons on older pygame versions
                if event.button == 4:
                    self.scroll_y -= 36
                elif event.button == 5:
                    self.scroll_y += 36
                elif event.button == 1:
                    # Check card click for board tile pinning
                    clicked_record = None
                    for card_r, record in self._visible_card_rects:
                        if card_r.collidepoint(event.pos):
                            clicked_record = record
                            break

                    if clicked_record:
                        if self.selected_item == clicked_record:
                            self.selected_item = None  # Toggle off
                        else:
                            self.selected_item = clicked_record
                    else:
                        # Clicked empty panel area
                        self.selected_item = None

    def update(self) -> None:
        """Updates hover states based on current mouse coordinates."""
        mouse_pos = pygame.mouse.get_pos()
        self.hovered_item = None
        if self.rect.collidepoint(mouse_pos):
            for card_r, record in self._visible_card_rects:
                if card_r.collidepoint(mouse_pos):
                    self.hovered_item = record
                    break

    def render(self, surface: pygame.Surface) -> None:
        """Renders the matched words history panel."""
        self.update()

        # 1. Outer Container
        pygame.draw.rect(surface, COLOR_PANEL_BG, self.rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, self.rect, width=1, border_radius=8)

        # 2. Header
        x = self.rect.x + 16
        y = self.rect.y + 12

        # Accent dot
        pygame.draw.circle(surface, COLOR_HIGHLIGHT_WORD, (x + 4, y + 10), 4)

        # Header Title
        title_surf = self.font.render("Chosen Words History", True, COLOR_TEXT_PRIMARY)
        surface.blit(title_surf, (x + 16, y))

        # Total summary badge on top-right
        count = len(self.items)
        total_pts = sum(item.length for item in self.items)
        if count > 0:
            badge_text = f"{count} Locked • {total_pts} pts"
            badge_color = COLOR_HIGHLIGHT_WORD
        else:
            badge_text = "0 Chosen"
            badge_color = COLOR_TEXT_MUTED

        badge_surf = self.small_font.render(badge_text, True, badge_color)
        badge_rect = pygame.Rect(
            self.rect.right - 16 - badge_surf.get_width() - 12,
            y - 1,
            badge_surf.get_width() + 12,
            24,
        )
        pygame.draw.rect(surface, COLOR_BADGE_BG, badge_rect, border_radius=12)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, badge_rect, width=1, border_radius=12)
        surface.blit(badge_surf, (badge_rect.x + 6, badge_rect.y + 3))

        y += 32
        pygame.draw.line(surface, COLOR_PANEL_BORDER, (x, y), (self.rect.right - 16, y))
        y += 8

        # 3. Content Area
        content_rect = pygame.Rect(
            self.rect.x + 12,
            y,
            self.rect.width - 24,
            self.rect.bottom - y - 12,
        )

        self._visible_card_rects.clear()

        # Empty State
        if not self.items:
            empty_box = pygame.Rect(content_rect.x + 10, content_rect.y + 20, content_rect.width - 20, 100)
            pygame.draw.rect(surface, COLOR_CARD_BG, empty_box, border_radius=6)
            pygame.draw.rect(surface, COLOR_CARD_BORDER, empty_box, width=1, border_radius=6)

            txt1 = self.font.render("No chosen words yet", True, COLOR_TEXT_MUTED)
            txt2 = self.small_font.render("Words can only be chosen once per match.", True, COLOR_TEXT_DIM)
            txt3 = self.small_font.render("Hover or click any word to inspect on the grid.", True, COLOR_TEXT_DIM)

            surface.blit(txt1, txt1.get_rect(center=(empty_box.centerx, empty_box.y + 24)))
            surface.blit(txt2, txt2.get_rect(center=(empty_box.centerx, empty_box.y + 52)))
            surface.blit(txt3, txt3.get_rect(center=(empty_box.centerx, empty_box.y + 74)))
            return

        # Scroll calculation
        card_h = 56
        gap = 6
        item_stride = card_h + gap
        total_height = len(self.items) * item_stride - gap
        max_scroll = max(0, total_height - content_rect.height)
        self.scroll_y = max(0.0, min(self.scroll_y, float(max_scroll)))

        has_scrollbar = total_height > content_rect.height
        card_w = content_rect.width - (14 if has_scrollbar else 0)

        # Set clipping region to prevent card overflow
        old_clip = surface.get_clip()
        surface.set_clip(content_rect)

        try:
            start_idx = max(0, int(self.scroll_y // item_stride))
            end_idx = min(len(self.items), int((self.scroll_y + content_rect.height) // item_stride) + 2)

            for idx in range(start_idx, end_idx):
                item = self.items[idx]
                item_y = content_rect.y + idx * item_stride - int(self.scroll_y)
                card_r = pygame.Rect(content_rect.x, item_y, card_w, card_h)

                if card_r.bottom < content_rect.top or card_r.top > content_rect.bottom:
                    continue

                self._visible_card_rects.append((card_r, item))

                # Determine card styling
                is_selected = (self.selected_item == item)
                is_hovered = (self.hovered_item == item)

                if is_selected:
                    card_bg = pygame.Color(16, 185, 129, 45)
                    card_border = COLOR_HIGHLIGHT_WORD
                    border_w = 2
                elif is_hovered:
                    card_bg = COLOR_CARD_HOVER
                    card_border = COLOR_HIGHLIGHT_WORD
                    border_w = 1
                else:
                    card_bg = COLOR_CARD_BG
                    card_border = COLOR_CARD_BORDER
                    border_w = 1

                pygame.draw.rect(surface, card_bg, card_r, border_radius=6)
                pygame.draw.rect(surface, card_border, card_r, width=border_w, border_radius=6)

                # --- Card Contents ---
                # A. Player Badge (Left)
                is_p1 = (item.player == 1)
                p_accent = COLOR_P1 if is_p1 else COLOR_P2
                p_bg = COLOR_P1_BG if is_p1 else COLOR_P2_BG

                badge_str = f"P{item.player}: {item.player_name}"
                if len(badge_str) > 15:
                    badge_str = badge_str[:13] + ".."
                p_surf = self.small_font.render(badge_str, True, p_accent)

                pill_r = pygame.Rect(card_r.x + 8, card_r.y + 6, p_surf.get_width() + 12, 20)
                pygame.draw.rect(surface, p_bg, pill_r, border_radius=10)
                pygame.draw.rect(surface, p_accent, pill_r, width=1, border_radius=10)
                surface.blit(p_surf, (pill_r.x + 6, pill_r.y + 2))

                # Move context below badge
                r_pos, c_pos, l_ch = item.move
                move_info = f"Move #{item.move_number} • ({r_pos}, {c_pos}) '{l_ch}'"
                move_surf = self.small_font.render(move_info, True, COLOR_TEXT_MUTED)
                surface.blit(move_surf, (card_r.x + 8, card_r.y + 32))

                # C. Points Pill & Direction Tag (Right - measured first to center word)
                score_str = f"+{item.length} pts"
                score_surf = self.font.render(score_str, True, COLOR_LAST_MOVE)
                score_x = card_r.right - 12 - score_surf.get_width()
                surface.blit(score_surf, (score_x, card_r.y + 7))

                orient_code = "Row (H)" if (not item.occurrence_key or item.occurrence_key[0] == "H") else "Col (V)"
                orient_surf = self.small_font.render(orient_code, True, COLOR_TEXT_MUTED)
                surface.blit(orient_surf, (card_r.right - 12 - orient_surf.get_width(), card_r.y + 32))

                # B. Matched Word & Locked Badge (Center)
                left_bound = pill_r.right + 10
                right_bound = min(score_x, card_r.right - 12 - orient_surf.get_width()) - 10
                center_x = (left_bound + right_bound) // 2

                # If word with spaces fits in available space, use spaced format; otherwise compact
                word_spaced = " ".join(item.word)
                word_surf = self.font.render(word_spaced, True, COLOR_HIGHLIGHT_WORD)
                if word_surf.get_width() > (right_bound - left_bound):
                    word_surf = self.font.render(item.word, True, COLOR_HIGHLIGHT_WORD)

                word_rect = word_surf.get_rect(center=(center_x, card_r.y + 17))
                surface.blit(word_surf, word_rect)

                lock_surf = self.small_font.render("[LOCKED]", True, COLOR_LAST_MOVE)
                lock_rect = lock_surf.get_rect(center=(center_x, card_r.y + 37))
                surface.blit(lock_surf, lock_rect)

        finally:
            surface.set_clip(old_clip)

        # 4. Scrollbar Track & Thumb
        if has_scrollbar:
            sb_x = content_rect.right - 8
            sb_y = content_rect.y
            sb_w = 5
            sb_h = content_rect.height

            # Track
            track_rect = pygame.Rect(sb_x, sb_y, sb_w, sb_h)
            pygame.draw.rect(surface, COLOR_CARD_BG, track_rect, border_radius=2)

            # Thumb
            thumb_h = max(24, int(sb_h * (sb_h / total_height)))
            thumb_y = sb_y + int((self.scroll_y / max_scroll) * (sb_h - thumb_h))
            thumb_rect = pygame.Rect(sb_x, thumb_y, sb_w, thumb_h)
            pygame.draw.rect(surface, COLOR_CARD_BORDER, thumb_rect, border_radius=2)
