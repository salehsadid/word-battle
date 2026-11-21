# Generates wordgrid/assets/images/paper_background.png: newsprint paper with a faint crossword grid.
#
# The image is procedural (no stock photo), so it can be rebuilt or tweaked at any time:
#
# python scripts/make_paper_background.py

import os
import random
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
import pygame

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "wordgrid" / "assets" / "images" / "paper_background.png"

W, H = 1650, 1140          # 1.5x the 1100x760 window, so it stays sharp when the window is enlarged
PAPER = (244, 241, 234)
INK = (18, 18, 19)
CELL = 48                  # crossword square size in pixels
SQUARES = 15               # a standard 15 x 15 grid
LINE_ALPHA = 26            # grid lines (0-255)
BLOCK_ALPHA = 20           # filled squares (0-255)


# A 15 x 15 crossword grid with rotationally symmetric black squares, printed very faintly.
def crossword(pick: random.Random) -> pygame.Surface:
    size = CELL * SQUARES + 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    for r in range(SQUARES):
        for c in range(SQUARES):
            if pick.random() < 0.17:
                for rr, cc in ((r, c), (SQUARES - 1 - r, SQUARES - 1 - c)):
                    surf.fill((*INK, BLOCK_ALPHA), (cc * CELL + 1, rr * CELL + 1, CELL, CELL))
    for i in range(SQUARES + 1):
        surf.fill((*INK, LINE_ALPHA), (i * CELL, 0, 2, size))
        surf.fill((*INK, LINE_ALPHA), (0, i * CELL, size, 2))
    return surf


# Low-frequency mottling: small random field scaled up smoothly.
def smooth_noise(rng: np.random.Generator, scale: int, amplitude: float) -> np.ndarray:
    small = rng.normal(0.0, 1.0, (H // scale + 2, W // scale + 2)).astype(np.float32)
    surf = pygame.surfarray.make_surface(np.repeat(((small - small.min()) / np.ptp(small) * 255).T[..., None], 3, 2))
    big = pygame.transform.smoothscale(surf, (W, H))
    field = pygame.surfarray.array3d(big)[..., 0].T.astype(np.float32) / 255.0
    return (field - 0.5) * 2 * amplitude


# Generate the paper-texture background image.
def main() -> None:
    pygame.init()
    rng = np.random.default_rng(7)
    img = np.empty((H, W, 3), dtype=np.float32)
    img[:] = PAPER

    # Paper: soft mottling plus fine grain
    img += smooth_noise(rng, 90, 3.0)[..., None]
    img += smooth_noise(rng, 18, 1.5)[..., None]
    img += rng.normal(0.0, 2.2, (H, W))[..., None]

    # Very light vignette towards the corners
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    img *= (1.0 - 0.035 * np.clip(d - 0.6, 0, None))[..., None]

    out = np.clip(img, 0, 255).astype(np.uint8)
    surf = pygame.surfarray.make_surface(out.transpose(1, 0, 2))

    # Two faint printed crosswords, slightly rotated and running off the corners
    for seed, angle, center in ((11, -7, (W * 0.93, H * 0.12)), (5, 5, (W * 0.06, H * 0.92))):
        grid = crossword(random.Random(seed))
        grid = pygame.transform.rotozoom(grid, angle, 1.0)
        surf.blit(grid, grid.get_rect(center=(round(center[0]), round(center[1]))))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surf, str(OUT))
    print(f"Saved {OUT.relative_to(ROOT)} ({W}x{H})")


if __name__ == "__main__":
    main()
