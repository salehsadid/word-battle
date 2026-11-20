"""Flat newspaper-puzzle palette: white paper, black ink, grey rules, one yellow and one green."""

import pygame

C = pygame.Color

# Surfaces
BG = C("#F4F1EA")             # window background (paper; the paper image is drawn over it when present)
SURFACE = C("#FFFFFF")        # sheets and panels
SURFACE_ALT = C("#F2F2EF")    # hover fills, empty states
SURFACE_SUNK = C("#E6E6E3")   # tracks, pressed keys
BORDER = C("#D3D6DA")         # hairlines
BORDER_STRONG = C("#878A8C")  # control outlines
SHADOW = C("#D3D6DA")         # kept for compatibility; the flat theme draws no shadows

# Text
TEXT = C("#121213")
TEXT_MUTED = C("#4F5257")
TEXT_SUBTLE = C("#787C7E")
TEXT_ON_ACCENT = C("#FFFFFF")

# Accents
PRIMARY = C("#121213")        # black ink: primary buttons, selected options
PRIMARY_HOVER = C("#3A3A3C")
PRIMARY_SOFT = C("#EDEDEA")
P1 = C("#2F6BD3")             # blue
P1_SOFT = C("#E9F0FB")
P2 = C("#D9483B")             # red
P2_SOFT = C("#FBEAE8")
SUCCESS = C("#6AAA64")        # scored words
SUCCESS_SOFT = C("#E3F1E1")
SUCCESS_INK = C("#2E6B2A")     # readable green text on SUCCESS_SOFT
AMBER = C("#F7DA21")          # newest letter
AMBER_SOFT = C("#FDF5C7")
DANGER = C("#C9372C")
DANGER_SOFT = C("#FBEAE8")

# Board
BOARD_BG = C("#FFFFFF")
CELL_EMPTY = C("#FFFFFF")
CELL_HOVER = C("#F2F2EF")
TILE_FACE = C("#FFFFFF")
TILE_EDGE = C("#878A8C")
TILE_TEXT = C("#121213")

# Translucent overlay (RGBA tuple, used on SRCALPHA surfaces)
OVERLAY = (18, 18, 19, 110)


def player_color(pid: int) -> pygame.Color:
    return P1 if pid == 1 else P2


def player_soft(pid: int) -> pygame.Color:
    return P1_SOFT if pid == 1 else P2_SOFT
