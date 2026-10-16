import pytest
import pygame
from wordgrid.game.board import Board
from wordgrid.game.state import GameState
from wordgrid.game.rules import GameRules
from wordgrid.game.engine import GameEngine
from wordgrid.ui.word_history_panel import WordHistoryPanel, MatchedWordRecord


class DummyValidator:
    def __init__(self, valid_words):
        self.valid_words = set(valid_words)

    def is_valid_word(self, word: str) -> bool:
        return word.upper() in self.valid_words


def test_engine_matched_words_tracking():
    validator = DummyValidator(["CAT", "CATS"])
    engine = GameEngine(validator=validator)

    # Move 1: P1 plays 'C' at (0, 0)
    engine.make_move((0, 0, "C"))
    assert len(engine.matched_words) == 0

    # Move 2: P2 plays 'A' at (0, 1)
    engine.make_move((0, 1, "A"))
    assert len(engine.matched_words) == 0

    # Move 3: P1 plays 'T' at (0, 2) -> forms CAT (+3)
    engine.make_move((0, 2, "T"))
    assert len(engine.matched_words) == 1
    match1 = engine.matched_words[0]
    assert match1["word"] == "CAT"
    assert match1["length"] == 3
    assert match1["player"] == 1
    assert match1["occurrence"] == ("H", 0, 0, 0, 2)

    # Move 4: P2 plays 'S' at (0, 3) -> forms CATS (+4)
    engine.make_move((0, 3, "S"))
    assert len(engine.matched_words) == 2
    match2 = engine.matched_words[1]
    assert match2["word"] == "CATS"
    assert match2["length"] == 4
    assert match2["player"] == 2
    assert match2["occurrence"] == ("H", 0, 0, 0, 3)

    # Reset clears history
    engine.reset()
    assert len(engine.matched_words) == 0


def test_word_history_panel_management():
    pygame.init()
    font = pygame.font.Font(None, 20)
    small_font = pygame.font.Font(None, 14)
    panel = WordHistoryPanel(
        rect=pygame.Rect(590, 300, 470, 360),
        title_font=font,
        font=font,
        small_font=small_font,
    )

    assert len(panel.items) == 0

    # Add match for Player 1 (Saleh)
    panel.add_match(
        word="CAT",
        length=3,
        player=1,
        player_name="Saleh",
        move_number=3,
        move=(0, 2, "T"),
        occurrence_key=("H", 0, 0, 0, 2),
    )
    assert len(panel.items) == 1
    assert panel.items[0].word == "CAT"
    assert panel.items[0].player_name == "Saleh"
    assert panel.items[0].length == 3

    # Add match for Player 2 (AlphaBeta)
    panel.add_match(
        word="CATS",
        length=4,
        player=2,
        player_name="AlphaBeta",
        move_number=4,
        move=(0, 3, "S"),
        occurrence_key=("H", 0, 0, 0, 3),
    )
    assert len(panel.items) == 2
    # Newest is first
    assert panel.items[0].word == "CATS"
    assert panel.items[0].player_name == "AlphaBeta"
    assert panel.items[1].word == "CAT"
    assert panel.items[1].player_name == "Saleh"

    # Surface render test
    surf = pygame.Surface((1100, 760))
    panel.render(surf)

    # Clear test
    panel.clear()
    assert len(panel.items) == 0
    assert panel.scroll_y == 0.0
