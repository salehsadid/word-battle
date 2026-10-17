"""Reusable UI controls in the soft light theme."""

import time
import pygame
from typing import Callable, List, Optional, Sequence
from wordgrid.ui import colors as col
from wordgrid.ui import theme


def wrap_text(font: pygame.font.Font, text: str, width: int, max_lines: int = 0) -> List[str]:
    """Greedy word wrap; the last line is ellipsised when max_lines is exceeded."""
    lines: List[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = theme.truncate(font, lines[-1] + " ...", width)
    return lines


def _hovered(rect: pygame.Rect) -> bool:
    return rect.collidepoint(pygame.mouse.get_pos())


class Button:
    """Rounded button. Variants: primary, secondary, ghost, danger. Optional vector icon."""

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        font: Optional[pygame.font.Font] = None,
        callback: Optional[Callable[[], None]] = None,
        variant: str = "secondary",
        icon: Optional[str] = None,
        is_primary: bool = False,
        enabled: bool = True,
        tooltip: Optional[str] = None,
    ):
        self.rect = rect
        self.text = text
        self.font = font or theme.font(theme.SIZE_BODY, bold=True)
        self.callback = callback
        self.variant = "primary" if is_primary else variant
        self.icon = icon
        self.enabled = enabled
        self.visible = True
        self.tooltip = tooltip

    @property
    def is_hovered(self) -> bool:
        return self.visible and self.enabled and _hovered(self.rect)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not (self.enabled and self.visible):
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            if self.callback:
                self.callback()
            return True
        return False

    def _colors(self):
        hover = self.is_hovered
        if not self.enabled:
            return col.SURFACE_ALT, col.BORDER, col.TEXT_SUBTLE
        if self.variant == "primary":
            return (col.PRIMARY_HOVER if hover else col.PRIMARY), None, col.TEXT_ON_ACCENT
        if self.variant == "danger":
            return (col.DANGER if hover else col.DANGER_SOFT), None, (col.TEXT_ON_ACCENT if hover else col.DANGER)
        if self.variant == "ghost":
            return (col.SURFACE_ALT if hover else None), None, col.PRIMARY
        return (col.SURFACE_ALT if hover else col.SURFACE), col.BORDER, col.TEXT

    def render(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        fill, border, fg = self._colors()
        radius = min(10, self.rect.height // 2)
        if fill is not None:
            if self.variant in ("primary", "secondary") and self.enabled:
                theme.aa_rect(surface, col.SHADOW, self.rect.move(0, 2), border_radius=radius)
            theme.aa_rect(surface, fill, self.rect, border_radius=radius)
        if border is not None:
            theme.aa_rect(surface, border, self.rect, width=1, border_radius=radius)

        icon_size = max(12, min(18, self.rect.height - 18))
        text_surf = self.font.render(self.text, True, fg) if self.text else None
        total = (icon_size if self.icon else 0) + (text_surf.get_width() if text_surf else 0)
        if self.icon and text_surf:
            total += 8
        x = self.rect.centerx - total // 2
        if self.icon:
            theme.draw_icon(surface, self.icon, (x + icon_size // 2, self.rect.centery), icon_size, fg)
            x += icon_size + (8 if text_surf else 0)
        if text_surf:
            surface.blit(text_surf, text_surf.get_rect(midleft=(x, self.rect.centery)))


class SegmentedControl:
    """A row of mutually exclusive options, all visible at once."""

    def __init__(
        self,
        rect: pygame.Rect,
        options: Sequence[str],
        index: int = 0,
        font: Optional[pygame.font.Font] = None,
        on_change: Optional[Callable[[int, str], None]] = None,
        accent: Optional[pygame.Color] = None,
    ):
        self.rect = rect
        self.options = list(options)
        self.accent = accent or col.PRIMARY
        self.index = index
        self.font = font or theme.semibold(theme.SIZE_BODY)
        self.bold_font = theme.font(theme.SIZE_BODY, bold=True)
        self.on_change = on_change
        self.enabled = True

    @property
    def value(self) -> str:
        return self.options[self.index]

    def set_value(self, value: str, notify: bool = True) -> None:
        if value in self.options:
            self.index = self.options.index(value)
            if notify and self.on_change:
                self.on_change(self.index, value)

    def _segment(self, i: int) -> pygame.Rect:
        n = len(self.options)
        inner = self.rect.inflate(-6, -6)
        w = inner.width / n
        return pygame.Rect(round(inner.x + i * w), inner.y, round(w), inner.height)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            for i in range(len(self.options)):
                if self._segment(i).collidepoint(event.pos):
                    if i != self.index:
                        self.index = i
                        if self.on_change:
                            self.on_change(i, self.options[i])
                    return True
        return False

    def render(self, surface: pygame.Surface) -> None:
        theme.aa_rect(surface, col.SURFACE_ALT, self.rect, border_radius=10)
        theme.aa_rect(surface, col.BORDER, self.rect, width=1, border_radius=10)
        mouse = pygame.mouse.get_pos()
        for i, label in enumerate(self.options):
            seg = self._segment(i)
            selected = i == self.index
            if selected:
                theme.aa_rect(surface, col.SHADOW, seg.move(0, 1), border_radius=8)
                theme.aa_rect(surface, col.SURFACE, seg, border_radius=8)
                if self.enabled:
                    theme.aa_rect(surface, self.accent, seg, width=1, border_radius=8)
            elif self.enabled and seg.collidepoint(mouse):
                theme.aa_rect(surface, col.SURFACE_SUNK, seg, border_radius=8)
            if not self.enabled:
                color = col.TEXT_SUBTLE
            else:
                color = self.accent if selected else col.TEXT_MUTED
            fnt = self.bold_font if selected else self.font
            theme.draw_text(surface, label, fnt, color, seg.center, "center", max_width=seg.width - 8)


class UnderlineTabs(SegmentedControl):
    """Text tabs with an underline under the active one (same interface as SegmentedControl)."""

    def _segment(self, i: int) -> pygame.Rect:
        x = self.rect.x
        for j in range(i):
            x += self.font.size(self.options[j])[0] + 36
        w = self.font.size(self.options[i])[0] + 20
        return pygame.Rect(x, self.rect.y, w, self.rect.height)

    def render(self, surface: pygame.Surface) -> None:
        pygame.draw.line(surface, col.BORDER, (self.rect.x, self.rect.bottom - 1), (self.rect.right, self.rect.bottom - 1))
        mouse = pygame.mouse.get_pos()
        for i, label in enumerate(self.options):
            seg = self._segment(i)
            selected = i == self.index
            color = col.PRIMARY if selected else (col.TEXT if seg.collidepoint(mouse) else col.TEXT_MUTED)
            theme.draw_text(surface, label, self.bold_font if selected else self.font, color,
                            (seg.x + 10, seg.centery - 2), "midleft")
            if selected:
                theme.aa_rect(surface, col.PRIMARY, (seg.x + 6, seg.bottom - 3, seg.width - 12, 3), border_radius=2)


class Stepper:
    """Numeric value with - / + buttons; the value can never leave [minimum, maximum]."""

    def __init__(
        self,
        rect: pygame.Rect,
        value: float,
        minimum: float,
        maximum: float,
        step: float = 1,
        on_change: Optional[Callable[[float], None]] = None,
        fmt: Optional[Callable[[float], str]] = None,
    ):
        self.rect = rect
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.value = value
        self.on_change = on_change
        self.fmt = fmt or (lambda v: f"{v:g}")
        self.enabled = True
        self.is_float = isinstance(step, float)

    def _buttons(self):
        size = self.rect.height - 8
        minus = pygame.Rect(self.rect.x + 4, self.rect.y + 4, size, size)
        plus = pygame.Rect(self.rect.right - 4 - size, self.rect.y + 4, size, size)
        return minus, plus

    def set_value(self, value: float, notify: bool = True) -> None:
        value = max(self.minimum, min(self.maximum, value))
        value = round(value, 2) if self.is_float else int(round(value))
        if value != self.value:
            self.value = value
            if notify and self.on_change:
                self.on_change(value)

    def set_range(self, minimum: float, maximum: float) -> None:
        self.minimum, self.maximum = minimum, maximum
        self.set_value(self.value)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            minus, plus = self._buttons()
            if minus.collidepoint(event.pos):
                self.set_value(self.value - self.step)
                return True
            if plus.collidepoint(event.pos):
                self.set_value(self.value + self.step)
                return True
        elif event.type == pygame.MOUSEWHEEL and _hovered(self.rect):
            self.set_value(self.value + self.step * event.y)
            return True
        return False

    def render(self, surface: pygame.Surface) -> None:
        theme.aa_rect(surface, col.SURFACE, self.rect, border_radius=10)
        theme.aa_rect(surface, col.BORDER, self.rect, width=1, border_radius=10)
        minus, plus = self._buttons()
        for rect, sign, active in ((minus, "-", self.value > self.minimum), (plus, "+", self.value < self.maximum)):
            usable = active and self.enabled
            hover = usable and rect.collidepoint(pygame.mouse.get_pos())
            theme.aa_rect(surface, col.SURFACE_SUNK if hover else col.SURFACE_ALT, rect, border_radius=8)
            c = col.PRIMARY if usable else col.TEXT_SUBTLE
            cx, cy = rect.center
            pygame.draw.line(surface, c, (cx - 6, cy), (cx + 6, cy), 2)
            if sign == "+":
                pygame.draw.line(surface, c, (cx, cy - 6), (cx, cy + 6), 2)
        color = col.TEXT if self.enabled else col.TEXT_SUBTLE
        theme.draw_text(surface, self.fmt(self.value), theme.font(theme.SIZE_BODY, bold=True), color,
                        self.rect.center, "center")


class Slider:
    """Horizontal slider with the value shown on the right."""

    VALUE_W = 46

    def __init__(
        self,
        rect: pygame.Rect,
        value: float,
        minimum: float,
        maximum: float,
        step: float = 0.1,
        on_change: Optional[Callable[[float], None]] = None,
        fmt: Optional[Callable[[float], str]] = None,
    ):
        self.rect = rect
        self.value = value
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.on_change = on_change
        self.fmt = fmt or (lambda v: f"{v:.1f}")
        self.dragging = False
        self.enabled = True

    @property
    def track(self) -> pygame.Rect:
        return pygame.Rect(self.rect.x + 8, self.rect.centery - 2, self.rect.width - self.VALUE_W - 20, 4)

    def _set_from_x(self, x: int) -> None:
        t = self.track
        frac = max(0.0, min(1.0, (x - t.x) / max(1, t.width)))
        raw = self.minimum + frac * (self.maximum - self.minimum)
        value = round(round(raw / self.step) * self.step, 3)
        if value != self.value:
            self.value = value
            if self.on_change:
                self.on_change(value)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False
        hit = self.track.inflate(16, 24)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and hit.collidepoint(event.pos):
            self.dragging = True
            self._set_from_x(event.pos[0])
            return True
        if event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_x(event.pos[0])
            return True
        if event.type == pygame.MOUSEBUTTONUP and self.dragging:
            self.dragging = False
            return True
        return False

    def render(self, surface: pygame.Surface) -> None:
        t = self.track
        frac = (self.value - self.minimum) / max(1e-9, self.maximum - self.minimum)
        kx = t.x + int(frac * t.width)
        theme.aa_rect(surface, col.SURFACE_SUNK, t, border_radius=2)
        accent = col.PRIMARY if self.enabled else col.TEXT_SUBTLE
        theme.aa_rect(surface, accent, (t.x, t.y, kx - t.x, t.height), border_radius=2)
        theme.aa_circle(surface, col.SHADOW, (kx, t.centery + 1), 9)
        theme.aa_circle(surface, col.SURFACE, (kx, t.centery), 9)
        theme.aa_circle(surface, accent, (kx, t.centery), 9, 2)
        theme.draw_text(surface, self.fmt(self.value), theme.font(theme.SIZE_BODY, bold=True), col.TEXT,
                        (self.rect.right, self.rect.centery), "midright")


class Toggle:
    """On / off switch."""

    def __init__(self, rect: pygame.Rect, value: bool, on_change: Optional[Callable[[bool], None]] = None):
        self.rect = rect
        self.value = value
        self.on_change = on_change
        self.enabled = True

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 \
                and self.rect.collidepoint(event.pos):
            self.value = not self.value
            if self.on_change:
                self.on_change(self.value)
            return True
        return False

    def render(self, surface: pygame.Surface) -> None:
        on = self.value
        track = col.PRIMARY if (on and self.enabled) else (col.BORDER_STRONG if self.enabled else col.SURFACE_SUNK)
        r = self.rect.height // 2
        theme.aa_rect(surface, track, self.rect, border_radius=r)
        kx = self.rect.right - r if on else self.rect.x + r
        theme.aa_circle(surface, col.SURFACE, (kx, self.rect.centery), r - 3)


class ChoiceCard:
    """Large selectable card with icons, a title and a description."""

    def __init__(
        self,
        rect: pygame.Rect,
        title: str,
        description: str,
        icons: Sequence[str],
        callback: Optional[Callable[[], None]] = None,
    ):
        self.rect = rect
        self.title = title
        self.description = description
        self.icons = list(icons)
        self.callback = callback
        self.selected = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            if self.callback:
                self.callback()
            return True
        return False

    def render(self, surface: pygame.Surface) -> None:
        hover = _hovered(self.rect)
        if self.selected:
            theme.draw_card(surface, self.rect, fill=col.SURFACE, border=col.PRIMARY, width=2)
            theme.aa_rect(surface, col.PRIMARY, (self.rect.x + 2, self.rect.y + 14, 4, self.rect.height - 28),
                             border_radius=2)
        else:
            theme.draw_card(surface, self.rect, border=col.BORDER_STRONG if hover else col.BORDER, shadow=False)
        x = self.rect.x + 22
        theme.draw_text(surface, self.title, theme.serif(21), col.PRIMARY if self.selected else col.TEXT,
                        (x, self.rect.y + 18))
        fnt = theme.font(theme.SIZE_CAPTION)
        y = self.rect.y + 54
        for line in wrap_text(fnt, self.description, self.rect.width - 44, max_lines=2):
            theme.draw_text(surface, line, fnt, col.TEXT_MUTED, (x, y))
            y += 19


class TextInput:
    """Single-line text / number field with focus, caret and error highlighting."""

    def __init__(
        self,
        rect: pygame.Rect,
        label: str = "",
        text: str = "",
        font: Optional[pygame.font.Font] = None,
        small_font: Optional[pygame.font.Font] = None,
        kind: str = "text",  # "text", "int" or "float"
        max_chars: int = 16,
        placeholder: str = "",
        on_change: Optional[Callable[[str], None]] = None,
    ):
        self.rect = rect
        self.label = label
        self.text = text
        self.font = font or theme.font(theme.SIZE_BODY)
        self.small_font = small_font or theme.font(theme.SIZE_CAPTION)
        self.kind = kind
        self.max_chars = max_chars
        self.placeholder = placeholder
        self.on_change = on_change
        self.focused = False
        self.error = False
        self.enabled = True

    def _accepts(self, ch: str) -> bool:
        if self.kind == "int":
            return ch.isdigit() or (ch == "-" and not self.text)
        if self.kind == "float":
            return ch.isdigit() or (ch == "." and "." not in self.text) or (ch == "-" and not self.text)
        return ch.isprintable()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            was = self.focused
            self.focused = self.rect.collidepoint(event.pos)
            return self.focused or was
        if event.type == pygame.KEYDOWN and self.focused:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                self.focused = False
                return True
            elif event.key == pygame.K_TAB:
                return False  # let the owner move focus
            elif event.unicode and len(self.text) < self.max_chars and self._accepts(event.unicode):
                self.text += event.unicode
            else:
                return True
            if self.on_change:
                self.on_change(self.text)
            return True
        return False

    def render(self, surface: pygame.Surface) -> None:
        fill = col.SURFACE if self.enabled else col.SURFACE_ALT
        theme.aa_rect(surface, fill, self.rect, border_radius=10)
        if self.error:
            border, width = col.DANGER, 2
        elif self.focused:
            border, width = col.PRIMARY, 2
        else:
            border, width = (col.BORDER_STRONG if _hovered(self.rect) else col.BORDER), 1
        theme.aa_rect(surface, border, self.rect, width=width, border_radius=10)

        x = self.rect.x + 14
        if self.label:
            theme.draw_text(surface, self.label, self.small_font, col.TEXT_MUTED, (x, self.rect.y + 4))
            vy_center = self.rect.y + self.rect.height * 0.65
        else:
            vy_center = self.rect.centery
        shown = self.text if self.text else self.placeholder
        color = col.TEXT if (self.text and self.enabled) else col.TEXT_SUBTLE
        r = theme.draw_text(surface, shown, self.font, color, (x, vy_center), "midleft",
                            max_width=self.rect.width - 28)
        if self.focused and int(time.time() * 2) % 2 == 0:
            cx = x + (self.font.size(self.text)[0] if self.text else 0) + 1
            pygame.draw.line(surface, col.PRIMARY, (cx, r.top + 2), (cx, r.bottom - 2), 2)


class OptionSelector:
    """Compact selector cycling through options with < and > (used when options are many)."""

    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        options: List[str],
        initial_index: int,
        font: Optional[pygame.font.Font] = None,
        small_font: Optional[pygame.font.Font] = None,
        on_change: Optional[Callable[[int, str], None]] = None,
    ):
        self.rect = rect
        self.label = label
        self.options = options
        self.index = initial_index % len(options) if options else 0
        self.font = font or theme.font(theme.SIZE_BODY, bold=True)
        self.small_font = small_font or theme.font(theme.SIZE_CAPTION)
        self.on_change = on_change
        self.enabled = True

    @property
    def left_rect(self) -> pygame.Rect:
        size = self.rect.height - 10
        return pygame.Rect(self.rect.right - 2 * size - 10, self.rect.y + 5, size, size)

    @property
    def right_rect(self) -> pygame.Rect:
        size = self.rect.height - 10
        return pygame.Rect(self.rect.right - size - 5, self.rect.y + 5, size, size)

    @property
    def selected_value(self) -> str:
        return self.options[self.index] if 0 <= self.index < len(self.options) else ""

    def set_index(self, index: int, notify: bool = True) -> None:
        if self.options:
            self.index = index % len(self.options)
            if notify and self.on_change:
                self.on_change(self.index, self.selected_value)

    def set_value(self, value: str, notify: bool = True) -> bool:
        if value in self.options:
            self.set_index(self.options.index(value), notify)
            return True
        return False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled or not self.options:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.left_rect.collidepoint(event.pos):
                self.set_index(self.index - 1)
                return True
            if self.right_rect.collidepoint(event.pos) or self.rect.collidepoint(event.pos):
                self.set_index(self.index + 1)
                return True
        return False

    def render(self, surface: pygame.Surface) -> None:
        theme.aa_rect(surface, col.SURFACE, self.rect, border_radius=10)
        theme.aa_rect(surface, col.BORDER, self.rect, width=1, border_radius=10)
        x = self.rect.x + 14
        if self.label:
            theme.draw_text(surface, self.label, self.small_font, col.TEXT_MUTED, (x, self.rect.y + 4))
            cy = self.rect.y + self.rect.height * 0.65
        else:
            cy = self.rect.centery
        theme.draw_text(surface, self.selected_value, self.font, col.TEXT if self.enabled else col.TEXT_SUBTLE,
                        (x, cy), "midleft", max_width=self.left_rect.x - x - 8)
        for rect, icon in ((self.left_rect, "back"), (self.right_rect, "chevron")):
            hover = self.enabled and rect.collidepoint(pygame.mouse.get_pos())
            theme.aa_rect(surface, col.SURFACE_SUNK if hover else col.SURFACE_ALT, rect, border_radius=8)
            theme.draw_icon(surface, icon, rect.center, 14, col.PRIMARY if self.enabled else col.TEXT_SUBTLE)
