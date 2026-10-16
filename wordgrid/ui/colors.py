"""Soft, light, warm-neutral palette used across the whole UI."""

import pygame

C = pygame.Color

# Surfaces
BG = C("#F5F3EF")             # window background (warm off-white)
SURFACE = C("#FFFFFF")        # cards and panels
SURFACE_ALT = C("#F0EDE7")    # inputs, segmented tracks, subtle fills
SURFACE_SUNK = C("#E7E3DC")   # pressed / track backgrounds
BORDER = C("#DCD6CC")         # hairlines
BORDER_STRONG = C("#CBC4B8")
SHADOW = C("#E9E5DD")

# Text
TEXT = C("#1F2126")
TEXT_MUTED = C("#4B5059")
TEXT_SUBTLE = C("#6F747D")
TEXT_ON_ACCENT = C("#FFFFFF")

# Accents
PRIMARY = C("#3D5A80")        # muted navy
PRIMARY_HOVER = C("#334D6E")
PRIMARY_SOFT = C("#E4EAF2")
P1 = C("#4A7FA7")             # dusty blue
P1_SOFT = C("#E3EDF5")
P2 = C("#C0785A")             # terracotta
P2_SOFT = C("#F7E9E2")
SUCCESS = C("#5B9A7A")        # sage green
SUCCESS_SOFT = C("#E2F0E8")
AMBER = C("#D9A441")          # newest letter
AMBER_SOFT = C("#FAF0D9")
DANGER = C("#C25B56")
DANGER_SOFT = C("#F7E3E1")

# Board
BOARD_BG = C("#E9E4DB")
CELL_EMPTY = C("#F4F1EB")
CELL_HOVER = C("#E6ECF3")
TILE_FACE = C("#FCF7EC")
TILE_EDGE = C("#E0D3BA")
TILE_TEXT = C("#2E271D")

# Translucent overlay (RGBA tuple, used on SRCALPHA surfaces)
OVERLAY = (43, 45, 51, 120)


def player_color(pid: int) -> pygame.Color:
    return P1 if pid == 1 else P2


def player_soft(pid: int) -> pygame.Color:
    return P1_SOFT if pid == 1 else P2_SOFT
