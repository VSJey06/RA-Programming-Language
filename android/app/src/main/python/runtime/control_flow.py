"""
control_flow.py — Control-flow execution for the RA runtime.

Handles if/elseif/else chains, while loops, and for-range loops.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from parser.ra_ast import (
    BinaryOpNode,
    ForNode,
    IfNode,
    WhileNode,
)

if TYPE_CHECKING:
    from runtime.executor import Executor
    from runtime.runtime import Runtime


class ControlFlowEngine:
    """Executes conditional and looping constructs.

    Parameters
    ----------
    runtime  : Runtime   — interpreter that owns the execution context.
    executor : Executor  — shared node-execution helper.
    """

    def __init__(self, runtime: Runtime, executor: Executor) -> None:
        self._runtime = runtime
        self._executor = executor

    # ── If / ElseIf / Else ──────────────────────────────────────────────

    def execute_if(self, node: IfNode) -> None:
        """Execute an if/elseif/else chain.

        Parameters
        ----------
        node : IfNode — the conditional construct to execute.
        """
        if self._runtime.evaluate(node.condition):
            self._executor.execute_nodes(node.then_body)
            return

        for elseif in node.elseifs:
            if self._runtime.evaluate(elseif.condition):
                self._executor.execute_nodes(elseif.body)
                return

        if node.else_node is not None:
            self._executor.execute_nodes(node.else_node.body)

    # ── While loop ──────────────────────────────────────────────────────

    def execute_while(self, node: WhileNode) -> None:
        """Execute a while loop.

        Re-evaluates *condition* before every iteration.

        Parameters
        ----------
        node : WhileNode — the loop construct to execute.
        """
        while self._runtime.evaluate(node.condition):
            self._executor.execute_nodes(node.body)

    # ── For loop (range) ────────────────────────────────────────────────

    def execute_for(self, node: ForNode) -> None:
        """Execute a for-range loop.

        Expects ``node.iterable`` to be a ``BinaryOpNode`` with operator
        ``";"``, where ``left`` is the start value and ``right`` is the
        exclusive end value.

        The loop variable is assigned into ``global_scope`` on every
        iteration.

        Parameters
        ----------
        node : ForNode — the loop construct to execute.

        Raises
        ------
        RuntimeError — when ``iterable`` is not a ``";"`` binary op.
        """
        if not (
            isinstance(node.iterable, BinaryOpNode)
            and node.iterable.operator == ";"
        ):
            from runtime.runtime import RuntimeError

            raise RuntimeError(
                "For loop requires a range expression (start;end)"
            )

        start = self._runtime.evaluate(node.iterable.left)
        end = self._runtime.evaluate(node.iterable.right)

        from runtime.runtime import RuntimeError

        if not isinstance(start, int) or not isinstance(end, int):
            raise RuntimeError(
                "For loop range values must be integers"
            )

        for i in range(start, end):
            self._runtime.global_scope[node.variable] = i
            self._executor.execute_nodes(node.body)
