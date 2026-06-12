"""StackEngine — runtime container for named stacks.

Each stack is a list that may contain arbitrary RA values or the
``EMPTY`` sentinel.  Operations never shrink the list — ``pop``
replaces the last occupied slot with ``EMPTY``, and ``push`` always
appends.
"""

from __future__ import annotations

from typing import Any

from runtime.empty import EMPTY


class StackError(RuntimeError):
    """Raised when a stack operation encounters an error."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class StackEngine:
    """Manages all runtime stacks."""

    def __init__(self) -> None:
        self._stacks: dict[str, list[Any]] = {}

    # ── Lifecycle ─────────────────────────────────────────────────

    def create(self, name: str) -> None:
        """Create a new empty stack named *name*."""
        if name not in self._stacks:
            self._stacks[name] = []

    def has(self, name: str) -> bool:
        """Return ``True`` if *name* is a registered stack."""
        return name in self._stacks

    def _get(self, name: str) -> list[Any]:
        if name not in self._stacks:
            raise StackNotFound(name)
        return self._stacks[name]

    # ── Core operations ───────────────────────────────────────────

    def push(self, name: str, value: Any) -> None:
        """Append *value* — never reuses EMPTY slots."""
        if name not in self._stacks:
            self._stacks[name] = []
        self._stacks[name].append(value)

    def pop(self, name: str) -> Any:
        """Return last occupied value; replace slot with EMPTY."""
        stack = self._get(name)
        for i in range(len(stack) - 1, -1, -1):
            if stack[i] is not EMPTY:
                val = stack[i]
                stack[i] = EMPTY
                return val
        raise StackError(f"Cannot pop from empty stack '{name}'")

    def peek(self, name: str) -> Any:
        """Return last occupied value without modifying the stack."""
        stack = self._get(name)
        for i in range(len(stack) - 1, -1, -1):
            if stack[i] is not EMPTY:
                return stack[i]
        raise StackError(f"Cannot peek at empty stack '{name}'")

    # ── Properties ────────────────────────────────────────────────

    def size(self, name: str) -> int:
        """Return total number of slots."""
        return len(self._get(name))

    def count(self, name: str) -> int:
        """Return number of occupied (non-EMPTY) slots."""
        return sum(1 for v in self._get(name) if v is not EMPTY)

    def space(self, name: str) -> int:
        """Return number of EMPTY slots."""
        return sum(1 for v in self._get(name) if v is EMPTY)

    def empty(self, name: str) -> bool:
        """Return ``True`` when every slot is EMPTY or the stack has no data."""
        stack = self._get(name)
        if not stack:
            return True
        return all(v is EMPTY for v in stack)

    # ── Space operations (fill Nth EMPTY slot) ─────────────────────

    def space_insert(self, name: str, value: Any) -> None:
        """Fill the first EMPTY slot (alias for ``space_first``)."""
        self._fill_empty(name, value, "first")

    def space_first(self, name: str, value: Any) -> None:
        """Fill the first EMPTY slot."""
        self._fill_empty(name, value, "first")

    def space_last(self, name: str, value: Any) -> None:
        """Fill the last EMPTY slot."""
        self._fill_empty(name, value, "last")

    def space_sFirst(self, name: str, value: Any) -> None:
        """Fill the second EMPTY slot."""
        self._fill_empty(name, value, "sFirst")

    def space_bLast(self, name: str, value: Any) -> None:
        """Fill the before-last EMPTY slot."""
        self._fill_empty(name, value, "bLast")

    def space_mid(self, name: str, value: Any) -> None:
        """Fill the middle EMPTY slot."""
        self._fill_empty(name, value, "mid")

    def space_fMid(self, name: str, value: Any) -> None:
        """Fill the first-middle (left-of-centre) EMPTY slot."""
        self._fill_empty(name, value, "fMid")

    def space_lMid(self, name: str, value: Any) -> None:
        """Fill the last-middle (right-of-centre) EMPTY slot."""
        self._fill_empty(name, value, "lMid")

    def space_midL(self, name: str, value: Any) -> None:
        """Alias for ``space_fMid`` (left-of-centre)."""
        self._fill_empty(name, value, "fMid")

    def space_midR(self, name: str, value: Any) -> None:
        """Alias for ``space_lMid`` (right-of-centre)."""
        self._fill_empty(name, value, "lMid")

    # ── Internal ──────────────────────────────────────────────────

    def _fill_empty(self, name: str, value: Any, position: str) -> None:
        stack = self._get(name)
        indices = [i for i, v in enumerate(stack) if v is EMPTY]
        if not indices:
            raise StackError(f"No EMPTY slot in stack '{name}'")

        n = len(indices)
        idx = None

        if position == "first":
            idx = indices[0]
        elif position == "last":
            idx = indices[-1]
        elif position == "sFirst":
            if n < 2:
                raise StackError(
                    f"Stack '{name}' needs at least 2 EMPTY slots for sFirst"
                )
            idx = indices[1]
        elif position == "bLast":
            if n < 2:
                raise StackError(
                    f"Stack '{name}' needs at least 2 EMPTY slots for bLast"
                )
            idx = indices[-2]
        elif position == "mid":
            idx = indices[n // 2]
        elif position == "fMid":
            idx = indices[(n - 1) // 2]
        elif position == "lMid":
            idx = indices[n // 2]
        else:
            raise StackError(f"Unknown space position '{position}'")

        stack[idx] = value
