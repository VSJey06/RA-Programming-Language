"""
db_engine.py — Lightweight in-memory database engine for the RA runtime.
"""

from __future__ import annotations

import json
import os
from typing import Any


class DatabaseEngine:
    """In-memory database registry.

    Each named database stores key-value pairs in a dictionary.

    Attributes
    ----------
    _databases : dict[str, dict[str, Any]]
    """

    def __init__(self) -> None:
        self._databases: dict[str, dict[str, Any]] = {}

    def register_database(self, name: str) -> None:
        """Create a new empty database with *name* (no-op if already exists)."""
        if name not in self._databases:
            self._databases[name] = {}

    def has_database(self, name: str) -> bool:
        """Return True if a database with *name* exists."""
        return name in self._databases

    def set_value(self, database_name: str, key: str, value: Any) -> None:
        """Set *key* to *value* in the named database."""
        self._databases[database_name][key] = value

    def get_database(self, name: str) -> dict[str, Any]:
        """Return the entire database dict for *name*."""
        return self._databases[name]

    def save_database(self, name: str) -> None:
        """Persist *name* to disk as ``data/<name>.json``.

        Parameters
        ----------
        name : str — database name to save.

        Raises
        ------
        RuntimeError — when no database with *name* exists.
        """
        from runtime.runtime import RuntimeError

        if name not in self._databases:
            raise RuntimeError(f"Database '{name}' does not exist")

        os.makedirs("data", exist_ok=True)
        path = os.path.join("data", f"{name}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self._databases[name], fh, indent=4, ensure_ascii=False)

    def load_database(self, name: str) -> None:
        """Load *name* from disk as ``data/<name>.json``.

        Parameters
        ----------
        name : str — database name to load.

        Raises
        ------
        RuntimeError — when the file does not exist.
        """
        from runtime.runtime import RuntimeError

        path = os.path.join("data", f"{name}.json")
        if not os.path.exists(path):
            raise RuntimeError(
                f"Database file '{name}.json' not found at '{path}'"
            )
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self._databases[name] = data
