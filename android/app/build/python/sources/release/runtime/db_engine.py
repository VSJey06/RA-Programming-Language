"""
db_engine.py — Lightweight in-memory database engine for the RA runtime.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

class DatabaseEngine:
    """In-memory database registry.

    Each named database stores key-value pairs in a dictionary.

    Attributes
    ----------
    _databases : dict[str, dict[str, Any]]
    _data_dir  : Path — directory for on-disk persistence.
    """

    def __init__(self, data_dir: str | None = None) -> None:
        self._databases: dict[str, dict[str, Any]] = {}
        self._data_dir: Path = (
            Path(data_dir)
            if data_dir is not None
            else Path(__file__).resolve().parent.parent / "data"
        )

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
        """Persist *name* to disk as ``src/data/<name>.json``.

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

        self._data_dir.mkdir(exist_ok=True)
        path = self._data_dir / f"{name}.json"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self._databases[name], fh, indent=4, ensure_ascii=False)

    def load_database(self, name: str) -> None:
        """Load *name* from disk as ``src/data/<name>.json``.

        Parameters
        ----------
        name : str — database name to load.

        Raises
        ------
        RuntimeError — when the file does not exist.
        """
        from runtime.runtime import RuntimeError

        path = self._data_dir / f"{name}.json"
        if not path.exists():
            raise RuntimeError(
                f"Database file '{name}.json' not found at '{path}'"
            )
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self._databases[name] = data
