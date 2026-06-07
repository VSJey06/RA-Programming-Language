"""
method_system.py — Method registry for the RA runtime.

Stores parsed ``MethodNode`` definitions so they can be looked up
and invoked later.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from parser.ra_ast import MethodNode

if TYPE_CHECKING:
    from runtime.runtime import Runtime


class MethodRegistry:
    """Registry that stores method definitions by name.

    Methods are not executed here — only their AST definitions are kept
    for later dispatch by the interpreter.

    Attributes
    ----------
    _methods : dict[str, MethodNode] — internal method store.
    """

    def __init__(self) -> None:
        self._methods: dict[str, MethodNode] = {}

    def register(self, method_node: MethodNode) -> None:
        """Store a method definition.

        Parameters
        ----------
        method_node : MethodNode
            The parsed AST node for the method definition.
        """
        self._methods[method_node.name] = method_node

    def exists(self, name: str) -> bool:
        """Return True if a method with *name* has been registered."""
        return name in self._methods

    def get(self, name: str) -> MethodNode:
        """Retrieve a registered method definition by name.

        Parameters
        ----------
        name : str — method name to look up.

        Returns
        -------
        MethodNode — the stored method definition.

        Raises
        ------
        RuntimeError — when *name* has not been registered.
        """
        try:
            return self._methods[name]
        except KeyError:
            raise RuntimeError(f"Method '{name}' is not registered")

    def invoke(self, runtime: Runtime, method_name: str) -> None:
        """Execute a registered method by name.

        Parameters
        ----------
        runtime     : Runtime — the interpreter context to execute within.
        method_name : str     — name of the method to invoke.

        Raises
        ------
        RuntimeError — when *method_name* has not been registered.
        """
        method_node = self.get(method_name)
        runtime.executor.execute_nodes(method_node.body)

    def all_methods(self) -> dict[str, MethodNode]:
        """Return a copy of every registered method definition.

        Returns
        -------
        dict[str, MethodNode]
        """
        return dict(self._methods)
