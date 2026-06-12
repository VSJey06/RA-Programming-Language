"""EMPTY and NV — built-in sentinel values for the RA runtime.

EMPTY (``__`` in Dequeue notation) is a first-class value that represents
an absent/uninitialized slot.
NV (No Value) represents a system-created unused cell that has never
held a value.
"""


class _EmptyType:
    """Singleton type whose sole instance is the ``EMPTY`` sentinel."""

    _instance = None

    def __new__(cls) -> "_EmptyType":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _EmptyType)

    def __hash__(self) -> int:
        return hash("EMPTY")

    def __str__(self) -> str:
        return "EMPTY"

    def __repr__(self) -> str:
        return "EMPTY"

    def __bool__(self) -> bool:
        return False

    def __add__(self, other): raise TypeError("EMPTY does not support +")
    def __sub__(self, other): raise TypeError("EMPTY does not support -")
    def __mul__(self, other): raise TypeError("EMPTY does not support *")
    def __truediv__(self, other): raise TypeError("EMPTY does not support /")


EMPTY = _EmptyType()


class _NVType:
    """Singleton type whose sole instance is the ``NV`` sentinel."""

    _instance = None

    def __new__(cls) -> "_NVType":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _NVType)

    def __hash__(self) -> int:
        return hash("NV")

    def __str__(self) -> str:
        return "NV"

    def __repr__(self) -> str:
        return "NV"

    def __bool__(self) -> bool:
        return False


NV = _NVType()
