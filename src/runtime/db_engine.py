"""
db_engine.py — Lightweight in-memory database engine for the RA runtime.
"""

from __future__ import annotations

from typing import Any, Optional


class DatabaseEngine:
    """Simple in-memory key-value database engine.

    Attributes
    ----------
    data : dict[str, Any] — internal key-value store.
    """

    def __init__(self) -> None:
        self.data: dict[str, Any] = {}
        self._active: Optional[str] = None

    def open(self, name: str) -> None:
        """Open (or switch to) a named database.

        Parameters
        ----------
        name : str — database name.
        """
        self._active = name

    def close(self) -> None:
        """Close the active database and clear its state."""
        self._active = None

    def insert(self, key: str, value: Any) -> None:
        """Insert a key-value pair into the active database.

        Parameters
        ----------
        key   : str — record key.
        value : Any — record value.
        """
        self.data[key] = value

    def select(self, key: str) -> Optional[Any]:
        """Retrieve a value by key.

        Parameters
        ----------
        key : str — record key.

        Returns
        -------
        Any or None — the stored value, or None when the key does not exist.
        """
        return self.data.get(key)
