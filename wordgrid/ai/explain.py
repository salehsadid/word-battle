from typing import Any, Dict
from wordgrid.game.state import GameState
from wordgrid.game.rules import GameRules, Move
from wordgrid.game.scoring import WordValidatorProtocol, direction_label
from wordgrid.ai.move_ordering import OpportunityScanner


def describe_move(
    rules: GameRules,
    state: GameState,
    move: Move,
    validator: WordValidatorProtocol,
) -> Dict[str, Any]:
    """Facts about a chosen move used for AI explanations (does not mutate state).

    Returns keys: immediate_score, word, direction, denied_points, opponent_best_reply, summary.
    """
    scanner = OpportunityScanner(rules.scoring)
    r, c, ch = move

    cell_opts = scanner.letter_options(state, r, c, validator)
    cell_best = max((p for p, _ in cell_opts.values()), default=0)

    nxt = rules.apply_move(state, move, validator)
    scored = nxt.last_scored_occurrences
    immediate = scored[0][1] if scored else 0
    word = scored[0][0] if scored else None
    direction = direction_label(scored[0][2]) if scored else None
    reply = 0 if nxt.is_terminal else scanner.best_immediate_score(nxt, validator)

    parts = []
    if word:
        parts.append(f"Plays '{ch}' at ({r}, {c}) forming {word} ({direction}) for +{immediate}.")
    else:
        parts.append(f"Plays '{ch}' at ({r}, {c}); no new word (0 pts).")
    if cell_best > immediate:
        parts.append(f"Takes a cell where +{cell_best} was available, denying it.")
    if nxt.is_terminal:
        parts.append("This move ends the match.")
    elif reply > 0:
        parts.append(f"Opponent's best reply is worth +{reply}.")
    else:
        parts.append("Leaves the opponent no scoring reply.")

    return {
        "immediate_score": immediate,
        "word": word,
        "direction": direction,
        "denied_points": max(0, cell_best - immediate),
        "opponent_best_reply": reply,
        "summary": " ".join(parts),
    }
