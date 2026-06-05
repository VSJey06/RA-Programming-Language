"""
autoclose.py — Block-level validation for RA source text.

Scans source lines for block openers and closers and verifies
they are properly nested using a stack.
"""

from __future__ import annotations

_OPENER_MAP: dict[str, str] = {
    "Db": "Db.close",
    ".run": "r.close",
    ".fun": "f.close",
    "@":  "@.close",
    "/":  "/.close",
    "#":  "#.close",
    "?":  "?.close",
    "!":  "!.close",
}


class AutoCloser:
    """Validates block open/close pairing for RA source text.

    Attributes
    ----------
    _stack : list[str] — open-block tokens in LIFO order.
    """

    def __init__(self) -> None:
        self._stack: list[str] = []

    def validate(self, source: str) -> None:
        """Scan *source* and verify all blocks are properly closed.

        Parameters
        ----------
        source : str — raw RA source text.

        Raises
        ------
        SyntaxError — when a block is unclosed or a closer is unmatched.
        """
        self._stack.clear()

        for line in source.splitlines():
            s = line.strip()
            if not s:
                continue

            opener = self._match_opener(s)
            if opener is not None:
                self._stack.append(opener)
                continue

            closer = self._match_closer(s)
            if closer is not None:
                self._pop(closer)

        if self._stack:
            block = self._stack[-1]
            raise SyntaxError(
                f"Missing closing statement for {block}"
            )

    def _match_opener(self, line: str) -> str | None:
        for opener in _OPENER_MAP:
            if line.startswith(f"{opener}:"):
                return opener
        return None

    def _match_closer(self, line: str) -> str | None:
        for opener, close_token in _OPENER_MAP.items():
            if line == close_token:
                return close_token
        return None

    def _pop(self, closer: str) -> None:
        if not self._stack:
            raise SyntaxError(
                f"Unexpected closing statement {closer}"
            )
        expected = _OPENER_MAP[self._stack[-1]]
        if closer != expected:
            raise SyntaxError(
                f"Unexpected closing statement {closer}"
            )
        self._stack.pop()
