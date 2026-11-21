# Score cards, match info strip and the AI / last-move insight panel.

import time
import pygame
from typing import Any, Dict, List, Optional
from wordgrid.game.state import GameState
from wordgrid.config import MODE_LABELS, MODE_REACH_GOAL_SCORE, MODE_MOVE_LIMIT
from wordgrid.ui import colors as col
from wordgrid.ui import theme
from wordgrid.ui.controls import wrap_text

POPUP_SECONDS = 1.6


# 1-based, human friendly cell name.
def cell_label(r: int, c: int) -> str:
    return f"row {r + 1}, col {c + 1}"


# Plain-language summary of an AI move.
def friendly_ai_text(stats: Dict[str, Any], name: str, opponent: str) -> str:
    move = stats.get("selected_move")
    if not move:
        return f"{name} made a move."
    r, c, ch = move
    where = cell_label(r, c)
    word = stats.get("word")
    points = stats.get("immediate_score", 0)
    denied = stats.get("denied_points", 0)
    if word:
        text = f"{name} played {ch} at {where}, making {word} for +{points}."
    elif denied:
        text = f"{name} placed {ch} at {where} to block a square worth up to +{denied}."
    else:
        text = f"{name} placed {ch} at {where}. No word this turn."
    return text


# One line of technical details: time, positions searched, simulations.
def ai_details_text(stats: Dict[str, Any]) -> str:
    # The panel title already names the AI, so the line starts with the numbers
    parts = [f"{stats.get('elapsed_time', 0.0) * 1000:,.0f} ms"]
    if "nodes_visited" in stats:
        parts.append(f"{stats['nodes_visited']:,} positions")
        if stats.get("cutoffs"):
            parts.append(f"{stats['cutoffs']:,} pruned")
    elif "simulations" in stats:
        parts.append(f"{stats['simulations']:,} simulations")
    if "win_probability" in stats:
        parts.append(f"win chance {stats['win_probability']:.0%}")
    return "  ·  ".join(parts)


# Two player score cards with turn highlight, move counters and '+N' pop-ups.
class StatisticsPanel:

    # Score panel with no '+points' popups yet.
    def __init__(self, rect: pygame.Rect, title_font=None, font=None, small_font=None):
        self.rect = rect
        self.popups: List[Dict[str, Any]] = []

    # Show a short '+points' popup for a player.
    def add_score_popup(self, player: int, points: int) -> None:
        self.popups = [p for p in self.popups if p["player"] != player]
        self.popups.append({"player": player, "points": points, "t0": time.time()})

    # Remove all popups.
    def clear(self) -> None:
        self.popups.clear()

    # Draw one player's score card.
    def _card(self, surface, rect, state: GameState, pid: int, name: str, role: str) -> None:
        accent = col.player_color(pid)
        active = state.current_player == pid and not state.is_terminal
        winner = state.is_terminal and state.winner == pid
        if active or winner:
            theme.draw_card(surface, rect, border=col.TEXT, width=2)
        else:
            theme.draw_card(surface, rect, border=col.BORDER_STRONG)

        x = rect.x + 18
        status = "to move" if active else ("winner" if winner else "")
        status_w = 0
        if status:
            sr_ = theme.draw_label(surface, status, (rect.right - 14, rect.y + 17), color=col.TEXT, anchor="topright")
            status_w = sr_.width + 10
        title = theme.draw_text(surface, name, theme.serif(20), col.TEXT, (x + 20, rect.y + 12),
                                max_width=rect.width - 60 - status_w)
        theme.draw_swatch(surface, accent, (x + 6, title.centery + 1), 12)
        theme.draw_text(surface, role, theme.font(theme.SIZE_CAPTION), col.TEXT_MUTED, (x, rect.y + 40),
                        max_width=rect.width - 34)

        score = state.scores.get(pid, 0)
        sr = theme.draw_text(surface, str(score), theme.font(40, bold=True), col.TEXT, (x - 2, rect.y + 60))
        theme.draw_text(surface, "points", theme.font(theme.SIZE_CAPTION), col.TEXT_MUTED,
                        (sr.right + 6, sr.bottom - 26))

        moves = state.moves_made_by(pid)
        moves_txt = f"{moves} of {state.move_limit} moves" if state.game_mode == MODE_MOVE_LIMIT else \
            f"{moves} move{'s' if moves != 1 else ''}"
        theme.draw_text(surface, moves_txt, theme.font(theme.SIZE_CAPTION), col.TEXT_MUTED,
                        (rect.right - 14, sr.bottom - 26), "topright")

        if state.game_mode == MODE_REACH_GOAL_SCORE and state.goal_score > 0:
            bar = pygame.Rect(rect.x + 18, rect.bottom - 16, rect.width - 36, 4)
            pygame.draw.rect(surface, col.BORDER, bar)
            frac = min(1.0, score / state.goal_score)
            if frac > 0:
                pygame.draw.rect(surface, accent, (bar.x, bar.y, max(4, int(bar.width * frac)), bar.height))

        now = time.time()
        for pop in self.popups:
            age = now - pop["t0"]
            if pop["player"] != pid or age > POPUP_SECONDS:
                continue
            surf = theme.font(theme.SIZE_TITLE, bold=True).render(f"+{pop['points']}", True, col.SUCCESS)
            surf.set_alpha(max(0, int(255 * (1 - age / POPUP_SECONDS))))
            surface.blit(surf, (sr.right + 56, sr.y + 4 - int(age * 12)))

    # Draw both score cards and any popups.
    def render(self, surface, state: GameState, names: Dict[int, str], roles: Dict[int, str]) -> None:
        self.popups = [p for p in self.popups if time.time() - p["t0"] <= POPUP_SECONDS]
        gap = 14
        w = (self.rect.width - gap) // 2
        for pid in (1, 2):
            rect = pygame.Rect(self.rect.x + (pid - 1) * (w + gap), self.rect.y, w, self.rect.height)
            self._card(surface, rect, state, pid, names[pid], roles[pid])


# One line: termination rule, squares left, move number.
def render_info_strip(surface, rect: pygame.Rect, state: GameState) -> None:
    mode = MODE_LABELS.get(state.game_mode, state.game_mode)
    if state.game_mode == MODE_REACH_GOAL_SCORE:
        mode = f"First to {state.goal_score} points"
    elif state.game_mode == MODE_MOVE_LIMIT:
        mode = f"{state.move_limit} moves each"
    else:
        mode = "Fill the board"
    left = state.empty_cell_count
    parts = [mode, f"{left} square{'s' if left != 1 else ''} left",
             f"Move {state.move_count + (0 if state.is_terminal else 1)}"]
    theme.draw_text(surface, "     ·     ".join(parts), theme.semibold(theme.SIZE_BODY), col.TEXT_MUTED,
                    (rect.x + 4, rect.centery), "midleft")


# Explains the latest move: a friendly sentence, plus optional technical details.
class InsightPanel:

    # Panel that explains the last move.
    def __init__(self, rect: pygame.Rect):
        self.rect = rect

    # Draw the title, explanation and optional details.
    def render(
        self,
        surface,
        title: str,
        sentence: str,
        details: Optional[str],
        accent,
        thinking: bool = False,
    ) -> None:
        theme.draw_card(surface, self.rect, border=col.BORDER_STRONG)
        x = self.rect.x + 18
        y = self.rect.y + 14
        theme.draw_swatch(surface, accent, (x + 5, y + 10), 10)
        theme.draw_text(surface, title, theme.serif(19), col.TEXT, (x + 18, y - 2))
        y += 30
        body = theme.font(theme.SIZE_BODY)
        width = self.rect.width - 36
        if thinking:
            dots = "." * (int(time.time() * 3) % 4)
            theme.draw_text(surface, f"{sentence}{dots}", body, col.TEXT_MUTED, (x, y))
            return
        max_lines = 2 if details else 3
        for line in wrap_text(body, sentence, width, max_lines=max_lines):
            theme.draw_text(surface, line, body, col.TEXT, (x, y))
            y += 21
        if details:
            y = self.rect.bottom - 24
            theme.draw_text(surface, details, theme.font(theme.SIZE_CAPTION), col.TEXT_SUBTLE, (x, y), max_width=width)
