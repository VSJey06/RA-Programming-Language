"""
executor.py — Shared execution helper for the RA runtime.

Provides a reusable ``execute_nodes`` method that steps through a
list of AST nodes and dispatches each one to the runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from parser.ra_ast import Node

if TYPE_CHECKING:
    from runtime.runtime import Runtime


class Executor:
    """Helper that executes lists of AST nodes via a ``Runtime``.

    Parameters
    ----------
    runtime : Runtime
        The interpreter instance that owns the execution context.
    """

    def __init__(self, runtime: Runtime) -> None:
        self._runtime = runtime

    def execute_nodes(self, nodes: list[Node]) -> None:
        """Execute every node in *nodes* in order.

        Parameters
        ----------
        nodes : list[Node]
            AST nodes to execute sequentially.
        """
        for node in nodes:
            self._runtime.execute_node(node)
