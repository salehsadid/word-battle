from typing import List, Tuple, Optional


# Represents an N x N grid for WordGrid.
class Board:

    # Create an empty size x size grid, or copy a given grid.
    def __init__(self, size: int = 5, grid: Optional[List[List[Optional[str]]]] = None):
        if size < 2:
            raise ValueError(f"Board size must be at least 2, got {size}")
        self.size = size
        if grid is not None:
            self.grid = [row[:] for row in grid]
        else:
            self.grid = [[None for _ in range(size)] for _ in range(size)]

    # Returns True if (row, col) is within grid bounds.
    def is_valid_coord(self, row: int, col: int) -> bool:
        return 0 <= row < self.size and 0 <= col < self.size

    # Gets letter at (row, col), or None if empty.
    def get(self, row: int, col: int) -> Optional[str]:
        if not self.is_valid_coord(row, col):
            raise IndexError(f"Coordinates ({row}, {col}) out of bounds for size {self.size}")
        return self.grid[row][col]

    # Sets letter at (row, col). Letter must be a single uppercase A-Z character.
    def set(self, row: int, col: int, letter: str) -> None:
        if not self.is_valid_coord(row, col):
            raise IndexError(f"Coordinates ({row}, {col}) out of bounds for size {self.size}")
        if not (isinstance(letter, str) and len(letter) == 1 and letter.isalpha()):
            raise ValueError(f"Letter must be a single alphabetic character, got {letter!r}")
        self.grid[row][col] = letter.upper()

    # Clears cell at (row, col). Useful for search undo operations.
    def clear_cell(self, row: int, col: int) -> None:
        if not self.is_valid_coord(row, col):
            raise IndexError(f"Coordinates ({row}, {col}) out of bounds for size {self.size}")
        self.grid[row][col] = None

    # Returns True if cell at (row, col) is empty.
    def is_empty(self, row: int, col: int) -> bool:
        return self.get(row, col) is None

    # Returns list of all currently empty (row, col) coordinate pairs.
    def get_empty_cells(self) -> List[Tuple[int, int]]:
        return [
            (r, c)
            for r in range(self.size)
            for c in range(self.size)
            if self.grid[r][c] is None
        ]

    # Returns True if no empty cells remain.
    def is_full(self) -> bool:
        return all(self.grid[r][c] is not None for r in range(self.size) for c in range(self.size))

    # Returns an independent deep copy of the board.
    def copy(self) -> "Board":
        return Board(self.size, self.grid)

    # Returns an immutable tuple representation of the board.
    def to_tuple(self) -> tuple:
        return tuple(tuple(row) for row in self.grid)

    # Board as text, with '.' for empty squares.
    def __repr__(self) -> str:
        rows_str = []
        for row in self.grid:
            rows_str.append(" ".join(ch if ch is not None else "." for ch in row))
        return "\n".join(rows_str)

    # Two boards are equal when size and letters match.
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Board):
            return False
        return self.size == other.size and self.grid == other.grid

    # Hash of the board, so it can be used in sets and as a key.
    def __hash__(self) -> int:
        return hash(self.to_tuple())
