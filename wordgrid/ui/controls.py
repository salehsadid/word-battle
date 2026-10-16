import pygame
from typing import Optional, Callable, List, Any
from wordgrid.ui.colors import (
    COLOR_BTN_DEFAULT,
    COLOR_BTN_HOVER,
    COLOR_BTN_PRIMARY,
    COLOR_BTN_PRIMARY_HOVER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_PANEL_BORDER,
)


class Button:
    """Interactive button with smooth hover and click feedback."""

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        font: pygame.font.Font,
        bg_color: pygame.Color = COLOR_BTN_DEFAULT,
        hover_color: pygame.Color = COLOR_BTN_HOVER,
        text_color: pygame.Color = COLOR_TEXT_PRIMARY,
        is_primary: bool = False,
        callback: Optional[Callable[[], None]] = None,
    ):
        self.rect = rect
        self.text = text
        self.font = font
        self.bg_color = COLOR_BTN_PRIMARY if is_primary else bg_color
        self.hover_color = COLOR_BTN_PRIMARY_HOVER if is_primary else hover_color
        self.text_color = text_color
        self.callback = callback
        self.is_hovered = False
        self.enabled = True

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True
        return False

    def render(self, surface: pygame.Surface) -> None:
        color = self.hover_color if (self.is_hovered and self.enabled) else self.bg_color
        if not self.enabled:
            color = pygame.Color(color.r // 2, color.g // 2, color.b // 2)

        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, self.rect, width=1, border_radius=6)

        txt_surf = self.font.render(self.text, True, self.text_color if self.enabled else COLOR_TEXT_MUTED)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)


class OptionSelector:
    """Horizontal selector cycling through options."""

    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        options: List[str],
        initial_index: int,
        font: pygame.font.Font,
        small_font: pygame.font.Font,
        on_change: Optional[Callable[[int, str], None]] = None,
    ):
        self.rect = rect
        self.label = label
        self.options = options
        self.index = initial_index % len(options) if options else 0
        self.font = font
        self.small_font = small_font
        self.on_change = on_change

        # Left / Right navigation buttons
        btn_w = 32
        self.left_rect = pygame.Rect(rect.x + rect.width - 2 * btn_w - 10, rect.y + 4, btn_w, rect.height - 8)
        self.right_rect = pygame.Rect(rect.x + rect.width - btn_w - 4, rect.y + 4, btn_w, rect.height - 8)

    @property
    def selected_value(self) -> str:
        if 0 <= self.index < len(self.options):
            return self.options[self.index]
        return ""

    def set_index(self, index: int, notify: bool = True) -> None:
        if self.options:
            self.index = index % len(self.options)
            if notify and self.on_change:
                self.on_change(self.index, self.selected_value)

    def set_value(self, value: str, notify: bool = True) -> bool:
        if value in self.options:
            self.index = self.options.index(value)
            if notify and self.on_change:
                self.on_change(self.index, self.selected_value)
            return True
        return False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.left_rect.collidepoint(event.pos):
                self.index = (self.index - 1) % len(self.options)
                if self.on_change:
                    self.on_change(self.index, self.selected_value)
                return True
            elif self.right_rect.collidepoint(event.pos):
                self.index = (self.index + 1) % len(self.options)
                if self.on_change:
                    self.on_change(self.index, self.selected_value)
                return True
            elif self.rect.collidepoint(event.pos):
                # Clicking the selector card advances or steps
                if event.pos[0] < self.rect.centerx:
                    self.index = (self.index - 1) % len(self.options)
                else:
                    self.index = (self.index + 1) % len(self.options)
                if self.on_change:
                    self.on_change(self.index, self.selected_value)
                return True
        return False

    def render(self, surface: pygame.Surface) -> None:
        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.rect.collidepoint(mouse_pos)
        bg = COLOR_BTN_HOVER if is_hover else COLOR_BTN_DEFAULT

        # Background
        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, self.rect, width=1, border_radius=6)

        # Label
        lbl_surf = self.small_font.render(self.label, True, COLOR_TEXT_MUTED)
        surface.blit(lbl_surf, (self.rect.x + 12, self.rect.y + 6))

        # Value
        val_surf = self.font.render(self.selected_value, True, COLOR_TEXT_PRIMARY)
        surface.blit(val_surf, (self.rect.x + 12, self.rect.y + 24))

        # Arrow buttons
        l_color = COLOR_BTN_HOVER if self.left_rect.collidepoint(mouse_pos) else COLOR_BTN_DEFAULT
        r_color = COLOR_BTN_HOVER if self.right_rect.collidepoint(mouse_pos) else COLOR_BTN_DEFAULT

        pygame.draw.rect(surface, l_color, self.left_rect, border_radius=4)
        pygame.draw.rect(surface, r_color, self.right_rect, border_radius=4)

        l_txt = self.font.render("<", True, COLOR_TEXT_PRIMARY)
        r_txt = self.font.render(">", True, COLOR_TEXT_PRIMARY)
        surface.blit(l_txt, l_txt.get_rect(center=self.left_rect.center))
        surface.blit(r_txt, r_txt.get_rect(center=self.right_rect.center))
