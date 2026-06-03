"""
autoclose.py — Auto-close block manager for the RA parser.

Tracks open blocks via a stack and provides the expected closing
token for each open block.  Used by the parser before AST generation
to auto-inject missing terminators.
"""

from __future__ import annotations

from typing import Optional

_CLOSER_MAP: dict[str, str] = {
    "Db": "Db.close",
    "@":  "@.close",
    "/":  "/.close",
    "#":  "#.close",
    "!":  "!.close",
    "?":  "?.close",
}


class AutoCloseManager:
    """Tracks open blocks and their expected closers.

    Attributes
    ----------
    _stack : list[str] — open-block tokens in LIFO order.
    """

    def __init__(self) -> None:
        self._stack: list[str] = []

    def push(self, token: str) -> None:
        """Open a new block.

        Parameters
        ----------
        token : str — the block-open marker (e.g. ``"Db"``).
        """
        self._stack.append(token)

    def pop(self, closer: str) -> None:
        """Close the current block and validate *closer*.

        Parameters
        ----------
        closer : str — the closer token that was encountered.

        Raises
        ------
        ValueError — when *closer* does not match the expected closer.
        """
        if not self._stack:
            raise ValueError(
                f"Unexpected closer {closer!r} — no open block"
            )
        expected = self.expected_closer()
        if closer != expected:
            raise ValueError(
                f"Expected {expected!r} but found {closer!r}"
            )
        self._stack.pop()

    def expected_closer(self) -> Optional[str]:
        """Return the closer expected by the current (top) block.

        Returns
        -------
        str or None — the closer string, or *None* when the stack is empty.
        """
        if not self._stack:
            return None
        return _CLOSER_MAP.get(self._stack[-1])
