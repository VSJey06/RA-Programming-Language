"""
class_system.py — Class registry for the RA runtime.

Stores parsed ``ClassNode`` definitions so they can be looked up
and instantiated later.
"""

from __future__ import annotations

from parser.ra_ast import ClassNode


class ClassRegistry:
    """Registry that stores class definitions by name.

    Classes are not instantiated here — only their AST definitions are
    kept for later use by the interpreter.

    Attributes
    ----------
    _classes : dict[str, ClassNode] — internal class store.
    """

    def __init__(self) -> None:
        self._classes: dict[str, ClassNode] = {}

    def register(self, class_node: ClassNode) -> None:
        """Store a class definition.

        Parameters
        ----------
        class_node : ClassNode
            The parsed AST node for the class definition.
        """
        self._classes[class_node.name] = class_node

    def exists(self, name: str) -> bool:
        """Return True if a class with *name* has been registered."""
        return name in self._classes

    def get(self, name: str) -> ClassNode:
        """Retrieve a registered class definition by name.

        Parameters
        ----------
        name : str — class name to look up.

        Returns
        -------
        ClassNode — the stored class definition.

        Raises
        ------
        RuntimeError — when *name* has not been registered.
        """
        try:
            return self._classes[name]
        except KeyError:
            raise RuntimeError(f"Class '{name}' is not registered")

    def all_classes(self) -> dict[str, ClassNode]:
        """Return a copy of every registered class definition.

        Returns
        -------
        dict[str, ClassNode]
        """
        return dict(self._classes)
