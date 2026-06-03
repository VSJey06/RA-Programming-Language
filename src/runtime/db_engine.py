"""
db_engine.py — Lightweight in-memory database engine for the RA runtime.
"""

from __future__ import annotations

from typing import Any


class DatabaseEngine:
    """Simple in-memory database connection manager.

    Each connection stores arbitrary metadata in a dictionary.

    Attributes
    ----------
    connections : dict[str, dict[str, Any]] — active connections.
    """

    def __init__(self) -> None:
        self.connections: dict[str, dict[str, Any]] = {}

    def open(self, name: str) -> None:
        """Register a new database connection.

        Parameters
        ----------
        name : str — connection name.
        """
        self.connections[name] = {}

    def close(self, name: str) -> None:
        """Remove a database connection.

        Parameters
        ----------
        name : str — connection name.
        """
        self.connections.pop(name, None)

    def exists(self, name: str) -> bool:
        """Return True if a connection with *name* exists."""
        return name in self.connections

    def get(self, name: str) -> dict[str, Any]:
        """Return the metadata dict for a connection."""
        return self.connections[name]

    def list_connections(self) -> list[str]:
        """Return the names of all active connections."""
        return list(self.connections)
