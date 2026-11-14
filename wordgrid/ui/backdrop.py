"""Paper background image shared by the screens.

The image is scaled to cover the window once per size and cached, so a frame costs one blit.
"""

import pygame
from typing import Dict, Optional, Tuple
from wordgrid.config import MENU_BACKGROUND_PATH
from wordgrid.ui import colors as col

_BACKDROPS: Dict[Tuple[int, int], pygame.Surface] = {}
_image: Optional[pygame.Surface] = None
_image_failed = False


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
