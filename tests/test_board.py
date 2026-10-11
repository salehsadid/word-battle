import pytest
from wordgrid.game.board import Board


def test_board_initialization():
    board = Board(size=5)
    assert board.size == 5
    assert not board.is_full()
    assert len(board.get_empty_cells()) == 25
    for r in range(5):
        for c in range(5):
            assert board.is_empty(r, c)
            assert board.get(r, c) is None


def test_board_invalid_size():
    with pytest.raises(ValueError):
        Board(size=1)


def test_board_set_and_get():
    board = Board(size=3)
    board.set(0, 0, "A")
    assert board.get(0, 0) == "A"
    assert not board.is_empty(0, 0)
    assert len(board.get_empty_cells()) == 8


def test_board_case_normalization():
    board = Board(size=3)
    board.set(1, 1, "c")
    assert board.get(1, 1) == "C"


def test_board_invalid_placement():
    board = Board(size=3)
    with pytest.raises(IndexError):
        board.set(-1, 0, "A")
    with pytest.raises(IndexError):
        board.set(0, 3, "A")
    with pytest.raises(ValueError):
        board.set(0, 0, "1")
    with pytest.raises(ValueError):
        board.set(0, 0, "AB")


def test_board_clear_cell():
    board = Board(size=3)
    board.set(0, 0, "Z")
    assert board.get(0, 0) == "Z"
    board.clear_cell(0, 0)
    assert board.is_empty(0, 0)


def test_board_is_full():
    board = Board(size=2)
    assert not board.is_full()
    board.set(0, 0, "A")
    board.set(0, 1, "B")
    board.set(1, 0, "C")
    assert not board.is_full()
    board.set(1, 1, "D")
    assert board.is_full()
    assert len(board.get_empty_cells()) == 0


def test_board_copy_independence():
    b1 = Board(size=3)
    b1.set(0, 0, "X")
    b2 = b1.copy()
    assert b2.get(0, 0) == "X"
    b2.set(0, 0, "Y")
    assert b1.get(0, 0) == "X"
    assert b2.get(0, 0) == "Y"
