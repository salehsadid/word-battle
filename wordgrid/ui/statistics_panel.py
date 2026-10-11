import pygame
from typing import Dict, Any, Optional
from wordgrid.game.state import GameState
from wordgrid.ui.colors import (
    COLOR_PANEL_BG,
    COLOR_PANEL_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_P1,
    COLOR_P2,
    COLOR_HIGHLIGHT_WORD,
    COLOR_LAST_MOVE,
)


class StatisticsPanel:
    """Renders scores, current turn, move metrics, and AI search statistics."""

    def __init__(
        self,
        rect: pygame.Rect,
        title_font: pygame.font.Font,
        font: pygame.font.Font,
        small_font: pygame.font.Font,
    ):
        self.rect = rect
        self.title_font = title_font
        self.font = font
        self.small_font = small_font

    def render(
        self,
        surface: pygame.Surface,
        state: GameState,
        p1_name: str,
        p2_name: str,
        ai_stats: Optional[Dict[str, Any]] = None,
    ) -> None:
        # Background
        pygame.draw.rect(surface, COLOR_PANEL_BG, self.rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, self.rect, width=1, border_radius=8)

        x = self.rect.x + 16
        y = self.rect.y + 14

        # Title
        title_surf = self.title_font.render("Match Status", True, COLOR_TEXT_PRIMARY)
        surface.blit(title_surf, (x, y))
        y += 34

        # Player 1 Box
        is_p1_turn = (state.current_player == 1 and not state.is_terminal)
        p1_color = COLOR_P1 if is_p1_turn else COLOR_TEXT_MUTED
        p1_badge = " [TURN]" if is_p1_turn else ""
        p1_txt = self.font.render(f"P1: {p1_name}{p1_badge}", True, p1_color)
        surface.blit(p1_txt, (x, y))
        p1_score_txt = self.title_font.render(f"{state.scores.get(1, 0)} pts", True, COLOR_P1)
        surface.blit(p1_score_txt, (self.rect.right - 16 - p1_score_txt.get_width(), y))
        y += 28

        # Player 2 Box
        is_p2_turn = (state.current_player == 2 and not state.is_terminal)
        p2_color = COLOR_P2 if is_p2_turn else COLOR_TEXT_MUTED
        p2_badge = " [TURN]" if is_p2_turn else ""
        p2_txt = self.font.render(f"P2: {p2_name}{p2_badge}", True, p2_color)
        surface.blit(p2_txt, (x, y))
        p2_score_txt = self.title_font.render(f"{state.scores.get(2, 0)} pts", True, COLOR_P2)
        surface.blit(p2_score_txt, (self.rect.right - 16 - p2_score_txt.get_width(), y))
        y += 34

        # Divider line
        pygame.draw.line(surface, COLOR_PANEL_BORDER, (x, y), (self.rect.right - 16, y))
        y += 12

        # Game mode & moves
        moves_surf = self.small_font.render(
            f"Mode: {state.game_mode}  |  Moves: {state.move_count}",
            True,
            COLOR_TEXT_MUTED,
        )
        surface.blit(moves_surf, (x, y))
        y += 22

        # Last Move
        if state.last_move:
            r, c, ch = state.last_move
            last_txt = f"Last Move: '{ch}' placed at ({r}, {c})"
        else:
            last_txt = "Last Move: None"
        surface.blit(self.small_font.render(last_txt, True, COLOR_TEXT_PRIMARY), (x, y))
        y += 22

        # Newly Completed Words
        if state.last_scored_words:
            scored_strs = [f"{w} (+{l})" for w, l in state.last_scored_words]
            words_txt = f"Newly Scored: {', '.join(scored_strs)}"
            surface.blit(self.small_font.render(words_txt, True, COLOR_HIGHLIGHT_WORD), (x, y))
        else:
            surface.blit(self.small_font.render("Newly Scored: (none)", True, COLOR_TEXT_MUTED), (x, y))
        y += 30

        # Divider line
        pygame.draw.line(surface, COLOR_PANEL_BORDER, (x, y), (self.rect.right - 16, y))
        y += 12

        # AI Search Metrics
        ai_hdr = self.font.render("AI Search Metrics", True, COLOR_TEXT_PRIMARY)
        surface.blit(ai_hdr, (x, y))
        y += 24

        if ai_stats:
            agent_type = ai_stats.get("agent", "AI")
            time_sec = ai_stats.get("elapsed_time", 0.0)
            surface.blit(self.small_font.render(f"Algorithm: {agent_type}", True, COLOR_TEXT_PRIMARY), (x, y))
            y += 18
            surface.blit(self.small_font.render(f"Search Time: {time_sec * 1000:.1f} ms", True, COLOR_TEXT_PRIMARY), (x, y))
            y += 18

            if "nodes_visited" in ai_stats:
                surface.blit(self.small_font.render(f"Nodes Visited: {ai_stats['nodes_visited']}", True, COLOR_TEXT_PRIMARY), (x, y))
                y += 18
            if "cutoffs" in ai_stats:
                surface.blit(self.small_font.render(f"Alpha-Beta Cutoffs: {ai_stats['cutoffs']}", True, COLOR_TEXT_PRIMARY), (x, y))
                y += 18
            if "simulations" in ai_stats:
                surface.blit(self.small_font.render(f"MCTS Simulations: {ai_stats['simulations']}", True, COLOR_TEXT_PRIMARY), (x, y))
                y += 18
            if "best_score" in ai_stats:
                surface.blit(self.small_font.render(f"Eval Value: {ai_stats['best_score']:.2f}", True, COLOR_TEXT_PRIMARY), (x, y))
                y += 18
            elif "selected_move_q" in ai_stats:
                surface.blit(self.small_font.render(f"MCTS Move Q: {ai_stats['selected_move_q']:.3f}", True, COLOR_TEXT_PRIMARY), (x, y))
                y += 18
        else:
            surface.blit(self.small_font.render("No AI search data available yet.", True, COLOR_TEXT_MUTED), (x, y))
            y += 20

        # Game Over Banner if finished
        if state.is_terminal:
            y = self.rect.bottom - 60
            banner_rect = pygame.Rect(x, y, self.rect.width - 32, 44)
            pygame.draw.rect(banner_rect.inflate(4, 4), COLOR_PANEL_BORDER, banner_rect, border_radius=6)
            if state.winner == 1:
                winner_text = f"GAME OVER: {p1_name} WINS!"
                b_color = COLOR_P1
            elif state.winner == 2:
                winner_text = f"GAME OVER: {p2_name} WINS!"
                b_color = COLOR_P2
            else:
                winner_text = "GAME OVER: DRAW!"
                b_color = COLOR_HIGHLIGHT_WORD

            pygame.draw.rect(surface, b_color, banner_rect, border_radius=6)
            txt_w = self.font.render(winner_text, True, COLOR_PANEL_BG)
            surface.blit(txt_w, txt_w.get_rect(center=banner_rect.center))
