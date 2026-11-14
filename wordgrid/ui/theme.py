"""Fonts and drawing helpers shared by every screen (cards, text, icons, tooltips)."""

import math
import os
import pygame
from typing import Dict, Tuple
from wordgrid.ui import colors as col

_FONTS: Dict[Tuple[str, int], pygame.font.Font] = {}

# Typography, newspaper-puzzle style: Georgia Bold for titles, Franklin Gothic for labels and
# letter tiles, Segoe UI for running text. Font files are loaded by name because pygame's SysFont
# matching on Windows picks odd faces (e.g. "segoeui" -> Segoe UI Light, "arial" -> Arial Narrow).
_FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
_FACES = {
    # face: (font files to try, SysFont fallback, bold flag for the fallback)
    "sans": (["segoeui.ttf", "arial.ttf"], "segoeui,arial", False),
    "sans_semibold": (["seguisb.ttf", "segoeuib.ttf", "arialbd.ttf"], "segoeuisemibold,arial", True),
    "sans_bold": (["segoeuib.ttf", "arialbd.ttf"], "segoeui,arial", True),
    "serif_bold": (["georgiab.ttf", "timesbd.ttf"], "georgia,timesnewroman", True),
    "serif": (["georgia.ttf", "times.ttf"], "georgia,timesnewroman", False),
    "label": (["framd.ttf", "seguisb.ttf", "arialbd.ttf"], "franklingothicmedium,arial", True),
}

# Type scale
SIZE_DISPLAY = 36
SIZE_TITLE = 24
SIZE_HEADING = 18
SIZE_BODY = 16
SIZE_CAPTION = 14

RADIUS = 4
RADIUS_SMALL = 3


# Anti-aliased shapes: drawn at SUPERSAMPLE x size, smoothed down once, then cached per size and colour.
SUPERSAMPLE = 4
_MASKS: Dict[tuple, pygame.Surface] = {}
_SHAPES: Dict[tuple, pygame.Surface] = {}
_CLEAR = (255, 255, 255, 0)  # transparent *white*, so smoothing never darkens the edges


def _coloured(mask_key: tuple, mask_fn, color) -> pygame.Surface:
    color = pygame.Color(color)
    key = (mask_key, tuple(color))
    shape = _SHAPES.get(key)
    if shape is None:
        mask = _MASKS.get(mask_key)
        if mask is None:
            if len(_MASKS) > 1500:
                _MASKS.clear()
            mask = _MASKS[mask_key] = mask_fn()
        if len(_SHAPES) > 3000:
            _SHAPES.clear()
        shape = _SHAPES[key] = mask.copy()
        shape.fill(color, special_flags=pygame.BLEND_RGBA_MULT)
    return shape


def _filled_round_rect(surface, color, rect: pygame.Rect, radii) -> None:
    if rect.width > 0 and rect.height > 0:
        tl, tr, bl, br = radii
        pygame.draw.rect(surface, color, rect, 0, border_top_left_radius=tl, border_top_right_radius=tr,
                         border_bottom_left_radius=bl, border_bottom_right_radius=br)


def aa_rect(surface, color, rect, width: int = 0, border_radius: int = 0, border_top_left_radius: int = -1,
            border_top_right_radius: int = -1, border_bottom_left_radius: int = -1,
            border_bottom_right_radius: int = -1) -> pygame.Rect:
    """Drop-in for pygame.draw.rect with smooth rounded corners."""
    rect = pygame.Rect(rect)
    radii = tuple(r if r >= 0 else border_radius for r in (border_top_left_radius, border_top_right_radius,
                                                          border_bottom_left_radius, border_bottom_right_radius))
    if max(radii) <= 0 or rect.width < 3 or rect.height < 3:
        return pygame.draw.rect(surface, color, rect, width)
    size = rect.size

    def make():
        ss = SUPERSAMPLE
        big = pygame.Surface((size[0] * ss, size[1] * ss), pygame.SRCALPHA)
        big.fill(_CLEAR)
        outer = big.get_rect()
        _filled_round_rect(big, (255, 255, 255, 255), outer, [r * ss for r in radii])
        if width > 0:
            # Outline = filled shape with the inside cut away (pygame's thick outlines leave pinholes)
            inset = width * ss
            _filled_round_rect(big, _CLEAR, outer.inflate(-2 * inset, -2 * inset),
                               [max(0, r * ss - inset) for r in radii])
        return pygame.transform.smoothscale(big, size)

    surface.blit(_coloured(("rect", size, width, radii), make, color), rect)
    return rect


def aa_circle(surface, color, center, radius, width: int = 0) -> pygame.Rect:
    """Drop-in for pygame.draw.circle with smooth edges."""
    radius = int(radius)
    if radius < 2:
        return pygame.draw.circle(surface, color, center, radius, width)
    d = radius * 2 + 2

    def make():
        ss = SUPERSAMPLE
        big = pygame.Surface((d * ss, d * ss), pygame.SRCALPHA)
        big.fill(_CLEAR)
        c = (d * ss / 2, d * ss / 2)
        pygame.draw.circle(big, (255, 255, 255, 255), c, radius * ss)
        if width > 0:
            pygame.draw.circle(big, _CLEAR, c, max(0, (radius - width) * ss))
        return pygame.transform.smoothscale(big, (d, d))

    shape = _coloured(("circle", radius, width), make, color)
    return surface.blit(shape, shape.get_rect(center=(round(center[0]), round(center[1]))))


def _load(face: str, size: int) -> pygame.font.Font:
    key = (face, size)
    if key not in _FONTS:
        files, family, bold = _FACES[face]
        fnt = None
        for name in files:
            path = os.path.join(_FONT_DIR, name)
            if os.path.exists(path):
                try:
                    fnt = pygame.font.Font(path, size)
                    break
                except (pygame.error, OSError):
                    pass
        if fnt is None:
            try:
                fnt = pygame.font.SysFont(family, size, bold=bold)
            except Exception:
                fnt = pygame.font.Font(None, int(size * 1.35))
        _FONTS[key] = fnt
    return _FONTS[key]


def font(size: int, bold: bool = False) -> pygame.font.Font:
    """Sans-serif UI font. Small regular text uses semibold so it stays legible."""
    if bold:
        return _load("sans_bold", size)
    if size <= SIZE_CAPTION:
        return _load("sans_semibold", size)
    return _load("sans", size)


def semibold(size: int) -> pygame.font.Font:
    """Semibold sans: sturdier than regular, lighter than bold."""
    return _load("sans_semibold", size)


def serif(size: int, bold: bool = True) -> pygame.font.Font:
    """Georgia: titles and headlines."""
    return _load("serif_bold" if bold else "serif", size)


def label(size: int) -> pygame.font.Font:
    """Franklin Gothic: section labels, letter tiles and keys."""
    return _load("label", size)


def draw_label(surface, text: str, pos, color=None, size: int = 13, anchor: str = "topleft") -> pygame.Rect:
    """Small upper-case section label ("PLAYERS", "MATCH")."""
    return draw_text(surface, text.upper(), label(size), color if color is not None else col.TEXT_SUBTLE, pos, anchor)


def draw_logo(surface, pos, tile: int = 34, gap: int = 4) -> pygame.Rect:
    """The wordmark: 'WordBattle' set in Georgia Bold. `tile` sets the cap height (kept for old callers)."""
    r = draw_text(surface, "WordBattle", serif(int(tile * 1.1)), col.TEXT, (pos[0], pos[1] + tile // 2), "midleft")
    return pygame.Rect(pos[0], pos[1], r.width, tile)


def draw_swatch(surface, color, center, size: int = 12) -> pygame.Rect:
    """Small solid square marking a player's colour."""
    rect = pygame.Rect(0, 0, size, size)
    rect.center = (round(center[0]), round(center[1]))
    pygame.draw.rect(surface, color, rect)
    return rect


def truncate(fnt: pygame.font.Font, text: str, width: int) -> str:
    if fnt.size(text)[0] <= width:
        return text
    while text and fnt.size(text + "...")[0] > width:
        text = text[:-1]
    return text.rstrip() + "..."


def draw_text(surface, text, fnt, color, pos, anchor: str = "topleft", max_width: int = 0) -> pygame.Rect:
    if max_width:
        text = truncate(fnt, text, max_width)
    surf = fnt.render(text, True, color)
    rect = surf.get_rect(**{anchor: pos})
    surface.blit(surf, rect)
    return rect


def draw_card(surface, rect, fill=None, border=None, radius: int = RADIUS, shadow: bool = False, width: int = 1):
    """Flat panel: white fill and a hairline border (no shadow unless asked for)."""
    radius = min(radius, RADIUS)
    if shadow:
        aa_rect(surface, col.SHADOW, rect.move(0, 2), border_radius=radius)
    aa_rect(surface, fill if fill is not None else col.SURFACE, rect, border_radius=radius)
    if border is not False:
        aa_rect(surface, border if border is not None else col.BORDER, rect, width=width, border_radius=radius)


def rule(surface, x1: int, x2: int, y: int, width: int = 1, color=None) -> None:
    """Horizontal printed rule."""
    pygame.draw.rect(surface, color if color is not None else col.BORDER, (x1, y, x2 - x1, width))


def draw_overlay(surface) -> None:
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    shade.fill(col.OVERLAY)
    surface.blit(shade, (0, 0))


def draw_tooltip(surface, text: str, pos: Tuple[int, int]) -> None:
    fnt = font(SIZE_CAPTION)
    surf = fnt.render(text, True, col.TEXT_ON_ACCENT)
    rect = pygame.Rect(0, 0, surf.get_width() + 16, surf.get_height() + 8)
    rect.midbottom = (pos[0], pos[1] - 10)
    rect.clamp_ip(surface.get_rect().inflate(-8, -8))
    aa_rect(surface, col.TEXT, rect, border_radius=RADIUS_SMALL)
    surface.blit(surf, (rect.x + 8, rect.y + 4))


def draw_avatar(surface, center, radius: int, name: str, color) -> None:
    aa_circle(surface, color, center, radius)
    initials = "".join(w[0] for w in name.split()[:2]).upper() or "?"
    draw_text(surface, initials, font(max(11, radius - 2), bold=True), col.TEXT_ON_ACCENT, center, "center")


def draw_icon(surface, name: str, center, size: int, color) -> None:
    """Small vector icons (no icon font needed)."""
    cx, cy = center
    s = size / 2
    w = max(2, size // 8)
    if name == "pause":
        bw = max(3, size // 5)
        aa_rect(surface, color, (cx - s * 0.6, cy - s * 0.7, bw, s * 1.4), border_radius=1)
        aa_rect(surface, color, (cx + s * 0.6 - bw, cy - s * 0.7, bw, s * 1.4), border_radius=1)
    elif name == "play":
        pygame.draw.polygon(surface, color, [(cx - s * 0.5, cy - s * 0.7), (cx - s * 0.5, cy + s * 0.7), (cx + s * 0.7, cy)])
    elif name == "step":
        pygame.draw.polygon(surface, color, [(cx - s * 0.7, cy - s * 0.7), (cx - s * 0.7, cy + s * 0.7), (cx + s * 0.3, cy)])
        aa_rect(surface, color, (cx + s * 0.4, cy - s * 0.7, max(3, size // 6), s * 1.4), border_radius=1)
    elif name == "restart":
        r = s * 0.75
        rect = pygame.Rect(0, 0, r * 2, r * 2)
        rect.center = (cx, cy)
        pygame.draw.arc(surface, color, rect, math.radians(40), math.radians(330), w)
        ax, ay = cx + r * math.cos(math.radians(40)), cy - r * math.sin(math.radians(40))
        pygame.draw.polygon(surface, color, [(ax - s * 0.45, ay - s * 0.15), (ax + s * 0.2, ay - s * 0.35), (ax + s * 0.05, ay + s * 0.35)])
    elif name == "gear":
        for i in range(8):
            a = math.radians(i * 45)
            pygame.draw.line(surface, color, (cx + math.cos(a) * s * 0.55, cy + math.sin(a) * s * 0.55),
                             (cx + math.cos(a) * s * 0.95, cy + math.sin(a) * s * 0.95), w + 1)
        aa_circle(surface, color, (cx, cy), int(s * 0.62), w)
        aa_circle(surface, color, (cx, cy), max(2, int(s * 0.22)))
    elif name == "help":
        aa_circle(surface, color, (cx, cy), int(s * 0.95), w)
        draw_text(surface, "?", font(int(size * 0.75), bold=True), color, (cx, cy + 1), "center")
    elif name == "close":
        d = s * 0.55
        pygame.draw.line(surface, color, (cx - d, cy - d), (cx + d, cy + d), w + 1)
        pygame.draw.line(surface, color, (cx - d, cy + d), (cx + d, cy - d), w + 1)
    elif name == "back":
        d = s * 0.5
        pygame.draw.lines(surface, color, False, [(cx + d * 0.4, cy - d), (cx - d * 0.6, cy), (cx + d * 0.4, cy + d)], w + 1)
    elif name == "chevron":
        d = s * 0.45
        pygame.draw.lines(surface, color, False, [(cx - d * 0.5, cy - d), (cx + d * 0.6, cy), (cx - d * 0.5, cy + d)], w)
    elif name == "chevron_down":
        d = s * 0.45
        pygame.draw.lines(surface, color, False, [(cx - d, cy - d * 0.5), (cx, cy + d * 0.6), (cx + d, cy - d * 0.5)], w)
    elif name == "person":
        aa_circle(surface, color, (cx, cy - s * 0.35), int(s * 0.35))
        body = pygame.Rect(0, 0, s * 1.4, s * 0.75)
        body.midtop = (cx, cy + s * 0.1)
        radius = int(body.height * 0.9)
        aa_rect(surface, color, body, border_top_left_radius=radius, border_top_right_radius=radius)
    elif name == "computer":
        screen = pygame.Rect(0, 0, s * 1.7, s * 1.15)
        screen.center = (cx, cy - s * 0.15)
        aa_rect(surface, color, screen, w, border_radius=3)
        pygame.draw.line(surface, color, (cx, screen.bottom), (cx, screen.bottom + s * 0.35), w)
        pygame.draw.line(surface, color, (cx - s * 0.45, screen.bottom + s * 0.4), (cx + s * 0.45, screen.bottom + s * 0.4), w)
    elif name == "sliders":
        for i, off in enumerate((-0.5, 0.0, 0.5)):
            y = cy + off * s * 1.4
            pygame.draw.line(surface, color, (cx - s * 0.8, y), (cx + s * 0.8, y), max(2, w - 1))
            kx = cx + (-0.35, 0.4, -0.05)[i] * s * 1.4
            aa_circle(surface, color, (kx, y), max(3, int(s * 0.22)))
    elif name == "trophy":
        cup = pygame.Rect(0, 0, s * 1.1, s * 0.9)
        cup.midtop = (cx, cy - s * 0.8)
        aa_rect(surface, color, cup, border_bottom_left_radius=int(s * 0.5), border_bottom_right_radius=int(s * 0.5))
        aa_rect(surface, color, (cx - s * 0.12, cup.bottom, s * 0.24, s * 0.4))
        aa_rect(surface, color, (cx - s * 0.45, cy + s * 0.5, s * 0.9, s * 0.22), border_radius=2)
