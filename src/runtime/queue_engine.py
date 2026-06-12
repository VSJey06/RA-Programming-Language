"""QueueEngine — runtime container for named FIFO queues.

Queue V1 specification:
  - FIFO, 1-dimensional
  - Dynamic growth (no capacity limit)
  - No .space support
  - No Nv concept
  - push (rear-append), pop (front-remove), peek (front-read)
  - size (total elements), count (same as size), empty (bool)
"""

from __future__ import annotations

from typing import Any


class QueueError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class QueueEngine:
    """Manages all runtime queues (FIFO)."""

    def __init__(self) -> None:
        self._queues: dict[str, list[Any]] = {}

    def create(self, name: str) -> None:
        if name not in self._queues:
            self._queues[name] = []

    def has(self, name: str) -> bool:
        return name in self._queues

    def _get(self, name: str) -> list[Any]:
        if name not in self._queues:
            raise QueueError(f"Queue '{name}' is not defined")
        return self._queues[name]

    def push(self, name: str, value: Any) -> None:
        if name not in self._queues:
            self._queues[name] = []
        self._queues[name].append(value)

    def pop(self, name: str) -> Any:
        q = self._get(name)
        if not q:
            raise QueueError(f"Cannot pop from empty queue '{name}'")
        return q.pop(0)

    def peek(self, name: str) -> Any:
        q = self._get(name)
        if not q:
            raise QueueError(f"Cannot peek at empty queue '{name}'")
        return q[0]

    def size(self, name: str) -> int:
        return len(self._get(name))

    def count(self, name: str) -> int:
        return len(self._get(name))

    def empty(self, name: str) -> bool:
        q = self._get(name)
        return len(q) == 0
