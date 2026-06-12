"""DequeueEngine — runtime container for named 2D grid dequeues.

Dequeue V1 specification:
  - 2D grid with default width of 4 columns
  - Rows dynamically added
  - Insert left→right, top→bottom
  - Two empty states: __ (user-removed/skipped) and Nv (system-unused)
  - Coordinate removal: remove.X,Y → cell replaced with __ (never Nv)
  - Coordinate get: get.X,Y → returns cell value
  - Space operations: first, last, sFirst, bLast, X,Y coordinate
  - Both __ and Nv are fillable by space operations
"""

from __future__ import annotations

from typing import Any

from runtime.empty import EMPTY, NV


class DequeueError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _is_empty(val: Any) -> bool:
    """True if *val* is either the __ sentinel or the Nv sentinel."""
    return val is EMPTY or val is NV


class DequeueEngine:
    """Manages all runtime dequeues (2D grids)."""

    _DEFAULT_WIDTH = 4

    def __init__(self) -> None:
        self._grids: dict[str, list[list[Any]]] = {}

    def create(self, name: str) -> None:
        if name not in self._grids:
            self._grids[name] = []

    def has(self, name: str) -> bool:
        return name in self._grids

    def _get(self, name: str) -> list[list[Any]]:
        if name not in self._grids:
            raise DequeueError(f"Dequeue '{name}' is not defined")
        return self._grids[name]

    def width(self, name: str) -> int:
        """Return the grid width (column count)."""
        return self._DEFAULT_WIDTH

    # ── Insert ──────────────────────────────────────────────────────

    def insert(self, name: str, value: Any) -> None:
        """Place *value* in the first empty cell (left→right, top→bottom).

        If no empty cell exists, a new row of Nv cells is appended first.
        """
        grid = self._get(name)
        for row_idx, row in enumerate(grid):
            for col_idx in range(len(row)):
                if _is_empty(row[col_idx]):
                    row[col_idx] = value
                    return
        # No empty cell found — append a new Nv row and fill first cell
        new_row = [NV] * self._DEFAULT_WIDTH
        new_row[0] = value
        grid.append(new_row)

    # ── Remove ──────────────────────────────────────────────────────

    def remove(self, name: str, x: int, y: int) -> None:
        """Replace cell at (x, y) with __ (never Nv).

        Coordinates are 1-indexed (row *x*, column *y*).
        Expands the grid if (x, y) is outside current bounds.
        """
        grid = self._get(name)
        if x < 1:
            raise DequeueError(f"Row {x} out of range in dequeue '{name}'")
        if y < 1:
            raise DequeueError(f"Column {y} out of range in dequeue '{name}'")
        # Expand rows if needed
        while len(grid) < x:
            grid.append([NV] * self._DEFAULT_WIDTH)
        row = grid[x - 1]
        # Expand columns if needed
        while len(row) < y:
            row.append(NV)
        row[y - 1] = EMPTY

    # ── Get ─────────────────────────────────────────────────────────

    def get(self, name: str, x: int, y: int) -> Any:
        """Return the value at (x, y).

        Coordinates are 1-indexed (row *x*, column *y*).
        """
        grid = self._get(name)
        if x < 1 or x > len(grid):
            raise DequeueError(f"Row {x} out of range in dequeue '{name}'")
        row = grid[x - 1]
        if y < 1 or y > len(row):
            raise DequeueError(f"Column {y} out of range in dequeue '{name}'")
        return row[y - 1]

    # ── V1.5 Properties ─────────────────────────────────────────────

    def rows(self, name: str) -> int:
        """Return the number of rows in the grid."""
        return len(self._get(name))

    def colms(self, name: str) -> int:
        """Return the number of columns (max row length)."""
        grid = self._get(name)
        if not grid:
            return self._DEFAULT_WIDTH
        return max(len(row) for row in grid)

    def row(self, name: str, n: int) -> str:
        """Return row *n* (1-indexed) as a space-separated string."""
        grid = self._get(name)
        if n < 1 or n > len(grid):
            raise DequeueError(f"Row {n} out of range in dequeue '{name}'")
        return " ".join(str(cell) for cell in grid[n - 1])

    def colm(self, name: str, n: int) -> str:
        """Return column *n* (1-indexed) as a space-separated string."""
        grid = self._get(name)
        if n < 1:
            raise DequeueError(f"Column {n} out of range in dequeue '{name}'")
        max_cols = max(len(row) for row in grid) if grid else self._DEFAULT_WIDTH
        if n > max_cols:
            raise DequeueError(f"Column {n} out of range in dequeue '{name}'")
        return " ".join(
            str(row[n - 1]) if n - 1 < len(row) else str(NV)
            for row in grid
        )

    def diagonal(self, name: str, direction: str) -> str:
        """Traverse the grid along *direction* and return space-separated values.

        Eight directional rays (all values are 1-indexed cell coordinates):
          ``x``       — first column, top → bottom
          ``y``       — first row,    left → right
          ``-x``      — last column,  bottom → top
          ``-y``      — last row,     right → left
          ``x-y``     — top-right → bottom-left  (diagonal)
          ``-y-x``    — top-left → bottom-right  (anti-diagonal)
          ``y-x``     — bottom-left → top-right  (anti-anti-diagonal)
          ``-x-y``    — bottom-right → top-left  (reverse diagonal)
        """
        grid = self._get(name)
        if not grid:
            return ""

        values: list[str] = []

        if direction == "x":
            for row in grid:
                values.append(str(row[0]) if row else str(NV))
        elif direction == "y":
            if grid[0]:
                for cell in grid[0]:
                    values.append(str(cell))
        elif direction == "-x":
            max_col = max(len(row) for row in grid) - 1
            for row in reversed(grid):
                val = str(row[max_col]) if max_col < len(row) else str(NV)
                values.append(val)
        elif direction == "-y":
            if grid[-1]:
                for cell in reversed(grid[-1]):
                    values.append(str(cell))
        elif direction == "x-y":
            max_c = max(len(row) for row in grid) - 1
            r, c = 0, max_c
            while r < len(grid) and c >= 0:
                values.append(str(grid[r][c]) if c < len(grid[r]) else str(NV))
                r += 1
                c -= 1
        elif direction == "-y-x":
            max_c = max(len(row) for row in grid)
            r, c = 0, 0
            while r < len(grid) and c < max_c:
                values.append(str(grid[r][c]) if c < len(grid[r]) else str(NV))
                r += 1
                c += 1
        elif direction == "y-x":
            max_c = max(len(row) for row in grid)
            r, c = len(grid) - 1, 0
            while r >= 0 and c < max_c:
                values.append(str(grid[r][c]) if c < len(grid[r]) else str(NV))
                r -= 1
                c += 1
        elif direction == "-x-y":
            max_c = max(len(row) for row in grid) - 1
            r, c = len(grid) - 1, max_c
            while r >= 0 and c >= 0:
                values.append(str(grid[r][c]) if c < len(grid[r]) else str(NV))
                r -= 1
                c -= 1
        else:
            raise DequeueError(f"Unknown diagonal direction '{direction}'")

        return " ".join(values)

    def find(self, name: str, value: Any) -> str:
        """Return ``'X,Y'`` of the first occurrence of *value*, or ``'- -'``."""
        grid = self._get(name)
        for r, row in enumerate(grid):
            for c, cell in enumerate(row):
                if cell == value:
                    return f"{r + 1},{c + 1}"
        return "- -"

    def exists(self, name: str, value: Any) -> bool:
        """Return ``True`` if *value* exists anywhere in the grid."""
        grid = self._get(name)
        return any(value in row for row in grid)

    def clear(self, name: str) -> None:
        """Clear all data from the grid (destructive)."""
        self._grids[name] = []

    # ── Properties ──────────────────────────────────────────────────

    def size(self, name: str) -> int:
        """Total number of cells in the grid."""
        grid = self._get(name)
        return sum(len(row) for row in grid)

    def count(self, name: str) -> int:
        """Number of non-empty (not __ and not Nv) cells."""
        grid = self._get(name)
        return sum(1 for row in grid for cell in row if not _is_empty(cell))

    def space(self, name: str) -> int:
        """Number of empty (__ or Nv) cells."""
        grid = self._get(name)
        return sum(1 for row in grid for cell in row if _is_empty(cell))

    def empty(self, name: str) -> bool:
        """True if the grid has no non-empty cells."""
        return self.count(name) == 0

    # ── Space operations ────────────────────────────────────────────

    def space_first(self, name: str, value: Any) -> None:
        self._fill_empty(name, value, "first")

    def space_last(self, name: str, value: Any) -> None:
        self._fill_empty(name, value, "last")

    def space_sFirst(self, name: str, value: Any) -> None:
        self._fill_empty(name, value, "sFirst")

    def space_bLast(self, name: str, value: Any) -> None:
        self._fill_empty(name, value, "bLast")

    def space_coord(self, name: str, x: int, y: int, value: Any) -> None:
        """Fill the specific cell (x, y) if it is empty."""
        cell = self.get(name, x, y)
        if not _is_empty(cell):
            raise DequeueError(
                f"Cell ({x},{y}) in dequeue '{name}' is not empty"
            )
        grid = self._get(name)
        grid[x - 1][y - 1] = value

    # ── Internal ────────────────────────────────────────────────────

    def _fill_empty(self, name: str, value: Any, position: str) -> None:
        """Fill the *position* empty cell in the grid.

        Scans left→right, top→bottom.
        """
        grid = self._get(name)
        # Collect indices of all empty cells (__ or Nv)
        empty_cells: list[tuple[int, int]] = []
        for row_idx, row in enumerate(grid):
            for col_idx in range(len(row)):
                if _is_empty(row[col_idx]):
                    empty_cells.append((row_idx, col_idx))

        if not empty_cells:
            raise DequeueError(
                f"No empty cell in dequeue '{name}'"
            )

        n = len(empty_cells)

        if position == "first":
            r, c = empty_cells[0]
        elif position == "last":
            r, c = empty_cells[-1]
        elif position == "sFirst":
            if n < 2:
                raise DequeueError(
                    f"Dequeue '{name}' needs at least 2 empty cells for sFirst"
                )
            r, c = empty_cells[1]
        elif position == "bLast":
            if n < 2:
                raise DequeueError(
                    f"Dequeue '{name}' needs at least 2 empty cells for bLast"
                )
            r, c = empty_cells[-2]
        else:
            raise DequeueError(f"Unknown space position '{position}'")

        grid[r][c] = value
