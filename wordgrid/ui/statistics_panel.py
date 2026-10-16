import pygame
from typing import Dict, Any, Optional
from wordgrid.game.state import GameState
from wordgrid.ui.colors import (
    COLOR_PANEL_BG,
    COLOR_PANEL_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_DIM,
    COLOR_P1,
    COLOR_P2,
    COLOR_HIGHLIGHT_WORD,
    COLOR_LAST_MOVE,
    COLOR_CARD_BG,
    COLOR_CARD_BORDER,
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
        try:
            self.score_font = pygame.font.SysFont("Segoe UI", 22, bold=True)
        except Exception:
            self.score_font = title_font

    def render(
        self,
        surface: pygame.Surface,
        state: GameState,
        p1_name: str,
        p2_name: str,
        ai_stats: Optional[Dict[str, Any]] = None,
        ai_searching: bool = False,
    ) -> None:
        # Background & border
        pygame.draw.rect(surface, COLOR_PANEL_BG, self.rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_PANEL_BORDER, self.rect, width=1, border_radius=8)

        x = self.rect.x + 16
        y = self.rect.y + 12

        # Header: Game Over Banner or Match Status
        if state.is_terminal:
            banner_rect = pygame.Rect(x, y, self.rect.width - 32, 32)
            p1_score = state.scores.get(1, 0)
            p2_score = state.scores.get(2, 0)
            if state.winner == 1:
                winner_text = f"WINNER: {p1_name.upper()}! ({p1_score} - {p2_score})"
                b_color = COLOR_P1
                txt_color = COLOR_PANEL_BG
            elif state.winner == 2:
                winner_text = f"WINNER: {p2_name.upper()}! ({p2_score} - {p1_score})"
                b_color = COLOR_P2
                txt_color = COLOR_PANEL_BG
            else:
                winner_text = f"MATCH DRAW! ({p1_score} - {p2_score})"
                b_color = COLOR_HIGHLIGHT_WORD
                txt_color = COLOR_PANEL_BG

            pygame.draw.rect(surface, b_color, banner_rect, border_radius=6)
            txt_w = self.font.render(winner_text, True, txt_color)
            surface.blit(txt_w, txt_w.get_rect(center=banner_rect.center))
            y += 38
        else:
            title_surf = self.title_font.render("Match Status", True, COLOR_TEXT_PRIMARY)
            surface.blit(title_surf, (x, y))

            # Turn indicator badge on top right of header
            turn_name = p1_name if state.current_player == 1 else p2_name
            turn_color = COLOR_P1 if state.current_player == 1 else COLOR_P2
            turn_badge = f"Turn: {turn_name}"
            turn_surf = self.small_font.render(turn_badge, True, turn_color)
            badge_r = pygame.Rect(
                self.rect.right - 16 - turn_surf.get_width() - 14,
                y + 3,
                turn_surf.get_width() + 14,
                22,
            )
            badge_bg = pygame.Color(12, 74, 110, 80) if state.current_player == 1 else pygame.Color(124, 45, 18, 80)
            pygame.draw.rect(surface, badge_bg, badge_r, border_radius=11)
            pygame.draw.rect(surface, turn_color, badge_r, width=1, border_radius=11)
            surface.blit(turn_surf, (badge_r.x + 7, badge_r.y + 2))
            y += 34

        # Side-by-side Player Score Cards with generous breathing room
        card_w = (self.rect.width - 32 - 12) // 2
        card_h = 56

        # Player 1 Card
        p1_r = pygame.Rect(x, y, card_w, card_h)
        is_p1_turn = (state.current_player == 1 and not state.is_terminal)
        p1_bg = pygame.Color(12, 74, 110, 70) if is_p1_turn else COLOR_CARD_BG
        p1_border = COLOR_P1 if is_p1_turn else COLOR_CARD_BORDER
        pygame.draw.rect(surface, p1_bg, p1_r, border_radius=6)
        pygame.draw.rect(surface, p1_border, p1_r, width=2 if is_p1_turn else 1, border_radius=6)

        p1_title = f"P1: {p1_name}"
        if len(p1_title) > 15:
            p1_title = p1_title[:13] + ".."
        surface.blit(self.small_font.render(p1_title, True, COLOR_P1), (p1_r.x + 10, p1_r.y + 6))
        p1_score = f"{state.scores.get(1, 0)} pts"
        surface.blit(self.score_font.render(p1_score, True, COLOR_TEXT_PRIMARY), (p1_r.x + 10, p1_r.y + 26))

        # Player 2 Card
        p2_r = pygame.Rect(x + card_w + 12, y, card_w, card_h)
        is_p2_turn = (state.current_player == 2 and not state.is_terminal)
        p2_bg = pygame.Color(124, 45, 18, 70) if is_p2_turn else COLOR_CARD_BG
        p2_border = COLOR_P2 if is_p2_turn else COLOR_CARD_BORDER
        pygame.draw.rect(surface, p2_bg, p2_r, border_radius=6)
        pygame.draw.rect(surface, p2_border, p2_r, width=2 if is_p2_turn else 1, border_radius=6)

        p2_title = f"P2: {p2_name}"
        if len(p2_title) > 15:
            p2_title = p2_title[:13] + ".."
        surface.blit(self.small_font.render(p2_title, True, COLOR_P2), (p2_r.x + 10, p2_r.y + 6))
        p2_score = f"{state.scores.get(2, 0)} pts"
        surface.blit(self.score_font.render(p2_score, True, COLOR_TEXT_PRIMARY), (p2_r.x + 10, p2_r.y + 26))

        y += card_h + 8

        # Divider
        pygame.draw.line(surface, COLOR_PANEL_BORDER, (x, y), (self.rect.right - 16, y))
        y += 8

        # Mode and Moves row
        mode_text = f"Mode: {state.game_mode}  •  Move #{state.move_count}"
        surface.blit(self.small_font.render(mode_text, True, COLOR_TEXT_MUTED), (x, y))
        y += 18

        # Last Move Info
        if state.last_move:
            lr, lc, lch = state.last_move
            last_msg = f"Last Move: '{lch}' at ({lr}, {lc})"
            if state.last_scored_words:
                scored_strs = [f"{w} (+{l})" for w, l in state.last_scored_words]
                last_msg += f"  ★ {', '.join(scored_strs)}"
                surface.blit(self.small_font.render(last_msg, True, COLOR_HIGHLIGHT_WORD), (x, y))
            elif getattr(state, "last_blocked_words", None):
                blocked_str = ", ".join(f"'{w}'" for w in state.last_blocked_words)
                last_msg += f"  • {blocked_str} already chosen (0 pts)"
                surface.blit(self.small_font.render(last_msg, True, COLOR_LAST_MOVE), (x, y))
            else:
                surface.blit(self.small_font.render(last_msg, True, COLOR_TEXT_PRIMARY), (x, y))
        else:
            surface.blit(self.small_font.render("Last Move: None (Game starting)", True, COLOR_TEXT_MUTED), (x, y))
        y += 20

        # Divider
        pygame.draw.line(surface, COLOR_PANEL_BORDER, (x, y), (self.rect.right - 16, y))
        y += 10

        # AI Search Metrics / Searching Indicator
        if ai_searching:
            cur_p = state.current_player
            p_col = COLOR_P1 if cur_p == 1 else COLOR_P2
            agent_name = p1_name if cur_p == 1 else p2_name
            l1 = f"Calculating: {agent_name} is searching..."
            surface.blit(self.small_font.render(l1, True, p_col), (x, y))
            y += 16
            surface.blit(self.small_font.render("Adversarial search in progress...", True, COLOR_TEXT_MUTED), (x, y))
        elif ai_stats:
            agent_type = ai_stats.get("agent", "AI")
            time_ms = ai_stats.get("elapsed_time", 0.0) * 1000
            l1 = f"AI Search: {agent_type} • {time_ms:.1f} ms"
            surface.blit(self.small_font.render(l1, True, COLOR_TEXT_PRIMARY), (x, y))
            y += 16

            if "nodes_visited" in ai_stats:
                nodes = ai_stats["nodes_visited"]
                cutoffs = ai_stats.get("cutoffs", 0)
                eval_val = ai_stats.get("best_score", 0.0)
                l2 = f"Nodes: {nodes}  •  Cutoffs: {cutoffs}  •  Eval: {eval_val:+.2f}"
                surface.blit(self.small_font.render(l2, True, COLOR_TEXT_MUTED), (x, y))
            elif "simulations" in ai_stats:
                sims = ai_stats["simulations"]
                q_val = ai_stats.get("selected_move_q", 0.0)
                l2 = f"Simulations: {sims}  •  Move Q: {q_val:.3f}"
                surface.blit(self.small_font.render(l2, True, COLOR_TEXT_MUTED), (x, y))
        else:
            waiting_txt = "Waiting for next move..." if not state.is_terminal else "Match completed."
            surface.blit(self.small_font.render(waiting_txt, True, COLOR_TEXT_MUTED), (x, y))
