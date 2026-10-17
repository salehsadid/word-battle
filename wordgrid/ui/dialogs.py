"""Modal dialogs: confirmation prompt and the How-to-play guide."""

import pygame
from typing import Callable, Optional
from wordgrid.ui import colors as col
from wordgrid.ui import theme
from wordgrid.ui.controls import Button, wrap_text


class ConfirmDialog:
    """Small modal asking the user to confirm a destructive action."""

    def __init__(self):
        self.visible = False
        self.title = ""
        self.message = ""
        self._on_confirm: Optional[Callable[[], None]] = None
        self.card = pygame.Rect(0, 0, 420, 190)
        self.btn_cancel = Button(pygame.Rect(0, 0, 130, 42), "Keep playing", callback=self.close)
        self.btn_confirm = Button(pygame.Rect(0, 0, 130, 42), "Leave", variant="danger", callback=self._confirm)

    def open(self, title: str, message: str, confirm_text: str, on_confirm: Callable[[], None]) -> None:
        self.title, self.message = title, message
        self.btn_confirm.text = confirm_text
        self._on_confirm = on_confirm
        self.visible = True

    def close(self) -> None:
        self.visible = False

    def _confirm(self) -> None:
        self.visible = False
        if self._on_confirm:
            self._on_confirm()

    def _layout(self, surface: pygame.Surface) -> None:
        self.card.center = surface.get_rect().center
        self.btn_confirm.rect.bottomright = (self.card.right - 20, self.card.bottom - 20)
        self.btn_cancel.rect.bottomright = (self.btn_confirm.rect.x - 10, self.card.bottom - 20)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Returns True when the dialog consumed the event (always, while visible)."""
        if not self.visible:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
        elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._confirm()
        else:
            self.btn_cancel.handle_event(event) or self.btn_confirm.handle_event(event)
        return True

    def render(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        self._layout(surface)
        theme.draw_overlay(surface)
        theme.draw_card(surface, self.card, radius=16)
        theme.draw_text(surface, self.title, theme.serif(theme.SIZE_TITLE), col.TEXT,
                        (self.card.x + 24, self.card.y + 20))
        fnt = theme.font(theme.SIZE_BODY)
        y = self.card.y + 62
        for line in wrap_text(fnt, self.message, self.card.width - 48, max_lines=3):
            theme.draw_text(surface, line, fnt, col.TEXT_MUTED, (self.card.x + 24, y))
            y += 21
        self.btn_cancel.render(surface)
        self.btn_confirm.render(surface)


HELP_SECTIONS = [
    ("Goal", [
        "Score more points than your opponent by building English words on the grid.",
    ]),
    ("Your turn", [
        "Click any empty square, then type a letter or pick one from the letter panel.",
        "Arrow keys move the selection; Esc cancels it.",
    ]),
    ("Scoring", [
        "Words count along rows and columns, read in either direction. Diagonals never count.",
        "Only the longest new word that uses your letter scores. Points = number of letters.",
        "Each word can score only once per match, no matter who makes it.",
    ]),
    ("Strategy", [
        "Watch out: a short word can set up a longer one for your opponent (PAN -> PANT).",
        "Sometimes blocking a square is worth more than a small score.",
    ]),
    ("Watching AI vs AI", [
        "Pause with Space, then use Step (or Enter) to advance one move at a time.",
    ]),
]


class HelpOverlay:
    """How-to-play guide shown on request (the ? button or F1)."""

    def __init__(self):
        self.visible = False
        self.card = pygame.Rect(0, 0, 680, 600)
        self.btn_close = Button(pygame.Rect(0, 0, 150, 42), "Got it", variant="primary", callback=self.close)

    def open(self) -> None:
        self.visible = True

    def close(self) -> None:
        self.visible = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_F1):
            self.close()
        elif event.type == pygame.MOUSEBUTTONDOWN and not self.card.collidepoint(event.pos):
            self.close()
        else:
            self.btn_close.handle_event(event)
        return True

    def render(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        self.card.center = surface.get_rect().center
        theme.draw_overlay(surface)
        theme.draw_card(surface, self.card, radius=16)
        x = self.card.x + 32
        theme.draw_text(surface, "How to play", theme.serif(26), col.TEXT, (x, self.card.y + 38), "midleft")
        y = self.card.y + 74
        head = theme.font(theme.SIZE_BODY, bold=True)
        body = theme.font(theme.SIZE_BODY)
        for title, lines in HELP_SECTIONS:
            theme.draw_text(surface, title, head, col.PRIMARY, (x, y))
            y += 24
            for text in lines:
                wrapped = wrap_text(body, text, self.card.width - 90)
                theme.aa_circle(surface, col.PRIMARY, (x + 6, y + 11), 3)
                for line in wrapped:
                    theme.draw_text(surface, line, body, col.TEXT_MUTED, (x + 18, y))
                    y += 21
                y += 2
            y += 8
        self.btn_close.rect.bottomright = (self.card.right - 24, self.card.bottom - 20)
        self.btn_close.render(surface)
