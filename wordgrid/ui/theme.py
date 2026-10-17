"""Fonts and drawing helpers shared by every screen (cards, text, icons, tooltips)."""

import math
import pygame
from typing import Dict, Tuple
from wordgrid.ui import colors as col

_FONTS: Dict[Tuple[str, int, bool], pygame.font.Font] = {}

# Typography: a classic serif for titles and tiles, a clean sans for everything else.
SERIF = "georgia,cambria,constantia,palatinolinotype"
SANS = "segoeui,calibri,arial"
SANS_SEMIBOLD = "segoeuisemibold,segoeui,calibri,arial"

# Type scale (larger than before for readability)
SIZE_DISPLAY = 36
SIZE_TITLE = 24
SIZE_HEADING = 18
SIZE_BODY = 16
SIZE_CAPTION = 14

RADIUS = 10
RADIUS_SMALL = 6

# Classic letter-tile values, shown small on logo tiles
LETTER_POINTS = {
    **dict.fromkeys("AEILNORSTU", 1), **dict.fromkeys("DG", 2), **dict.fromkeys("BCMP", 3),
    **dict.fromkeys("FHVWY", 4), "K": 5, **dict.fromkeys("JX", 8), **dict.fromkeys("QZ", 10),
}


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


def _load(family: str, size: int, bold: bool) -> pygame.font.Font:
    key = (family, size, bold)
    if key not in _FONTS:
        try:
            _FONTS[key] = pygame.font.SysFont(family, size, bold=bold)
        except Exception:
            _FONTS[key] = pygame.font.Font(None, int(size * 1.35))
    return _FONTS[key]


def font(size: int, bold: bool = False) -> pygame.font.Font:
    """Sans-serif UI font. Small regular text uses semibold so it stays legible."""
    if bold:
        return _load(SANS, size, True)
    if size <= SIZE_CAPTION:
        return _load(SANS_SEMIBOLD, size, False)
    return _load(SANS, size, False)


def semibold(size: int) -> pygame.font.Font:
    """Semibold sans: sturdier than regular, lighter than bold."""
    return _load(SANS_SEMIBOLD, size, False)


def serif(size: int, bold: bool = True) -> pygame.font.Font:
    """Serif display font for titles, headlines and letter tiles."""
    return _load(SERIF, size, bold)


def draw_tile(surface, rect: pygame.Rect, letter: str, show_points: bool = False) -> None:
    """A single cream letter tile with an optional point value."""
    radius = max(4, rect.height // 7)
    aa_rect(surface, col.TILE_EDGE, rect.move(0, max(2, rect.height // 14)), border_radius=radius)
    aa_rect(surface, col.TILE_FACE, rect, border_radius=radius)
    draw_text(surface, letter, serif(int(rect.height * 0.6)), col.TILE_TEXT,
              (rect.centerx - (rect.width * 0.04 if show_points else 0), rect.centery), "center")
    if show_points and letter in LETTER_POINTS:
        draw_text(surface, str(LETTER_POINTS[letter]), _load(SANS, max(9, rect.height // 4), True), col.TILE_TEXT,
                  (rect.right - rect.width * 0.1, rect.bottom - rect.height * 0.06), "bottomright")


def draw_logo(surface, pos, tile: int = 34, gap: int = 4) -> pygame.Rect:
    """'WORD' as letter tiles followed by 'Battle' in serif: the app's wordmark."""
    x, y = pos
    for ch in "WORD":
        draw_tile(surface, pygame.Rect(x, y, tile, tile), ch)
        x += tile + gap
    r = draw_text(surface, "Battle", serif(int(tile * 0.95)), col.TEXT, (x + gap * 2, y + tile // 2 + 1), "midleft")
    return pygame.Rect(pos[0], y, r.right - pos[0], tile + 3)


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


def draw_card(surface, rect, fill=None, border=None, radius: int = RADIUS, shadow: bool = True, width: int = 1):
    """Rounded card with an optional soft drop shadow."""
    if shadow:
        aa_rect(surface, col.SHADOW, rect.move(0, 2), border_radius=radius)
    aa_rect(surface, fill if fill is not None else col.SURFACE, rect, border_radius=radius)
    if border is not False:
        aa_rect(surface, border if border is not None else col.BORDER, rect, width=width, border_radius=radius)


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
    aa_rect(surface, col.TEXT, rect, border_radius=6)
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
