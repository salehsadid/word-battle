"""Background image for the settings screen and soft frosted-glass cards drawn over it.

The image is scaled to cover the window once per size and cached; each glass card pre-renders the
blurred patch of background behind it, so a frame costs only a few blits.
"""

import pygame
from typing import Dict, Optional, Tuple
from wordgrid.config import MENU_BACKGROUND_PATH
from wordgrid.ui import colors as col
from wordgrid.ui import theme

GLASS_TINT = (255, 252, 247, 150)      # milky white, lets the scene glow through
GLASS_HIGHLIGHT = 70                   # extra white at the top edge, fading downwards
GLASS_EDGE = (255, 255, 255, 190)      # bright hairline rim
SHADOW_ALPHA = 42

_BACKDROPS: Dict[Tuple[int, int], pygame.Surface] = {}
_GLASS: Dict[tuple, Tuple[pygame.Surface, pygame.Surface]] = {}
_image: Optional[pygame.Surface] = None
_image_failed = False


def _blur(surf: pygame.Surface, factor: int) -> pygame.Surface:
    """Cheap blur: shrink, then scale back up with smoothing."""
    w, h = surf.get_size()
    small = pygame.transform.smoothscale(surf, (max(1, w // factor), max(1, h // factor)))
    return pygame.transform.smoothscale(small, (w, h))


def _load_image() -> Optional[pygame.Surface]:
    global _image, _image_failed
    if _image is None and not _image_failed:
        try:
            _image = pygame.image.load(str(MENU_BACKGROUND_PATH))
        except (pygame.error, FileNotFoundError):
            _image_failed = True
    return _image


def backdrop(size: Tuple[int, int]) -> pygame.Surface:
    """The background image scaled to cover a window of this size (cached)."""
    if size not in _BACKDROPS:
        surf = pygame.Surface(size)
        surf.fill(col.BG)
        image = _load_image()
        if image is not None:
            scale = max(size[0] / image.get_width(), size[1] / image.get_height())
            scaled = pygame.transform.smoothscale(
                image, (round(image.get_width() * scale), round(image.get_height() * scale)))
            surf.blit(scaled, scaled.get_rect(center=(size[0] // 2, size[1] // 2)))
        _BACKDROPS[size] = surf.convert() if pygame.display.get_surface() else surf
    return _BACKDROPS[size]


def draw_backdrop(surface: pygame.Surface) -> None:
    surface.blit(backdrop(surface.get_size()), (0, 0))


def _shadow(size: Tuple[int, int], radius: int, spread: int = 20) -> pygame.Surface:
    surf = pygame.Surface((size[0] + spread * 2, size[1] + spread * 2), pygame.SRCALPHA)
    pygame.draw.rect(surf, (60, 40, 20, SHADOW_ALPHA), (spread, spread, *size), border_radius=radius)
    return _blur(_blur(surf, 6), 3)


def _glass(bg: pygame.Surface, rect: pygame.Rect, radius: int) -> pygame.Surface:
    glass = pygame.Surface(rect.size, pygame.SRCALPHA)
    area = rect.clip(bg.get_rect())
    glass.blit(_blur(_blur(bg.subsurface(area).copy(), 14), 4), (area.x - rect.x, area.y - rect.y))

    tint = pygame.Surface(rect.size, pygame.SRCALPHA)
    tint.fill(GLASS_TINT)
    glass.blit(tint, (0, 0))
    sheen = pygame.Surface((1, 64), pygame.SRCALPHA)
    for y in range(64):
        sheen.set_at((0, y), (255, 255, 255, round(GLASS_HIGHLIGHT * (1 - y / 63) ** 2)))
    glass.blit(pygame.transform.smoothscale(sheen, (rect.width, min(rect.height, 90))), (0, 0))

    # Smooth corners: cut with a supersampled mask (pure white, so only alpha changes)
    ss = theme.SUPERSAMPLE
    big = pygame.Surface((rect.width * ss, rect.height * ss), pygame.SRCALPHA)
    big.fill((255, 255, 255, 0))
    pygame.draw.rect(big, (255, 255, 255, 255), big.get_rect(), border_radius=radius * ss)
    glass.blit(pygame.transform.smoothscale(big, rect.size), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    theme.aa_rect(glass, GLASS_EDGE, glass.get_rect(), width=1, border_radius=radius)
    return glass


def draw_glass_card(surface: pygame.Surface, rect: pygame.Rect, radius: int = 16) -> None:
    """A soft frosted-glass card: the background behind it is blurred, brightened and rimmed in white."""
    key = (tuple(rect), radius, surface.get_size())
    if key not in _GLASS:
        _GLASS[key] = (_shadow(rect.size, radius), _glass(backdrop(surface.get_size()), rect, radius))
    shadow, glass = _GLASS[key]
    surface.blit(shadow, (rect.x - 20, rect.y - 14))
    surface.blit(glass, rect.topleft)
