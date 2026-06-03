"""
runtime.py — Interpreter for the RA language.

Walks an AST (from ``parser.ra_ast``) and executes it immediately.
"""

from __future__ import annotations

from typing import Any

from parser.ra_ast import (
    AssignmentNode,
    BinaryOpNode,
    ClassNode,
    DbNode,
    ForNode,
    IdentifierNode,
    IfNode,
    LiteralNode,
    MethodCallNode,
    MethodInvokeNode,
    MethodNode,
    Node,
    ObjectNode,
    PrintNode,
    PropertyAccessNode,
    PropertyAssignmentNode,
    ProgramNode,
    RelationAssignmentNode,
    WhileNode,
)
from runtime.control_flow import ControlFlowEngine
from runtime.db_engine import DatabaseEngine
from runtime.executor import Executor
from runtime.structural.class_system import ClassRegistry
from runtime.structural.method_system import MethodRegistry
from runtime.structural.object_system import ObjectRegistry


class RuntimeError(Exception):
    """Raised when the interpreter encounters a runtime error."""

    def __init__(self, message: str) -> None:
        super().__init__(f"RuntimeError: {message}")


class Runtime:
    """Simple tree-walking interpreter for the RA language.

    Attributes
    ----------
    global_scope : dict[str, Any] — mutable variable store.
    """

    def __init__(self) -> None:
        self.global_scope: dict[str, Any] = {}
        self.executor = Executor(self)
        self.control_flow = ControlFlowEngine(self, self.executor)
        self.class_registry = ClassRegistry()
        self.method_registry = MethodRegistry()
        self.object_registry = ObjectRegistry()
        self.db_engine = DatabaseEngine()

    # ── Entry point ──────────────────────────────────────────────────────

    def execute(self, program_node: ProgramNode) -> None:
        """Execute a full ``ProgramNode``.

        Walks ``ProgramNode.body`` sequentially and runs every statement.
        """
        for node in program_node.body:
            self.execute_node(node)

    # ── Statement dispatch ───────────────────────────────────────────────

    def execute_node(self, node: Node) -> None:
        """Execute a statement node.

        Dispatches based on the runtime type of *node*.
        Raises ``RuntimeError`` for unsupported node types.
        """
        if isinstance(node, DbNode):
            self._execute_db(node)
        elif isinstance(node, PrintNode):
            self._execute_print(node)
        elif isinstance(node, AssignmentNode):
            self._execute_assignment(node)
        elif isinstance(node, IfNode):
            self.control_flow.execute_if(node)
        elif isinstance(node, ForNode):
            self.control_flow.execute_for(node)
        elif isinstance(node, WhileNode):
            self.control_flow.execute_while(node)
        elif isinstance(node, ClassNode):
            self._execute_class(node)
        elif isinstance(node, MethodNode):
            self._execute_method(node)
        elif isinstance(node, ObjectNode):
            self._execute_object(node)
        elif isinstance(node, PropertyAssignmentNode):
            self._execute_property_assignment(node)
        elif isinstance(node, RelationAssignmentNode):
            self._execute_relation_assignment(node)
        elif isinstance(node, MethodInvokeNode):
            self._execute_method_invoke(node)
        elif isinstance(node, MethodCallNode):
            self.method_registry.invoke(self, node.method)
        else:
            raise RuntimeError(f"Node type not implemented: {type(node).__name__}")

    # ── Expression evaluation ────────────────────────────────────────────

    def evaluate(self, node: Node) -> Any:
        """Evaluate an expression node and return its value.

        Raises ``RuntimeError`` for unsupported node types.
        """
        if isinstance(node, LiteralNode):
            return node.value
        if isinstance(node, IdentifierNode):
            return self._lookup_identifier(node)
        if isinstance(node, BinaryOpNode):
            return self._eval_binary_op(node)
        if isinstance(node, PropertyAccessNode):
            return self._evaluate_property_access(node)
        raise RuntimeError(f"Node type not implemented: {type(node).__name__}")

    # ── Internal helpers ─────────────────────────────────────────────────

    def _execute_db(self, node: DbNode) -> None:
        """Execute all statements inside a Db block."""
        for child in node.body:
            self.execute_node(child)

    def _execute_print(self, node: PrintNode) -> None:
        """Evaluate the print expression and write the result to stdout."""
        value = self.evaluate(node.value)
        print(value)

    def _execute_assignment(self, node: AssignmentNode) -> None:
        """Evaluate the right-hand side and store it in ``global_scope``."""
        value = self.evaluate(node.value)
        self.global_scope[node.name] = value

    # ── Class / Method / Object ────────────────────────────────────────────

    def _execute_class(self, node: ClassNode) -> None:
        """Register a class definition."""
        self.class_registry.register(node)

    def _execute_method(self, node: MethodNode) -> None:
        """Register a method definition."""
        self.method_registry.register(node)

    def _execute_method_invoke(self, node: MethodInvokeNode) -> None:
        """Look up a method by name and execute its body."""
        try:
            method = self.method_registry.get(node.method_name)
        except Exception:
            raise RuntimeError(
                f"Method '{node.method_name}' is not defined"
            )
        self.executor.execute_nodes(method.body)

    def _execute_object(self, node: ObjectNode) -> None:
        """Instantiate an object from a registered class."""
        if not self.class_registry.exists(node.class_name):
            raise RuntimeError(f"Class '{node.class_name}' is not defined")
        self.object_registry.create(
            node.var_name, node.class_name, self.class_registry,
        )
        self.global_scope[node.var_name] = node.var_name

    def _lookup_identifier(self, node: IdentifierNode) -> Any:
        """Resolve an identifier in ``global_scope``.

        Raises ``RuntimeError`` when the variable is not defined.
        """
        try:
            return self.global_scope[node.name]
        except KeyError:
            raise RuntimeError(f"Variable '{node.name}' is not defined")

    def _execute_property_assignment(self, node: PropertyAssignmentNode) -> None:
        """Assign a value to an object property."""
        value = self.evaluate(node.value)
        self.object_registry.set_property(
            node.object_name,
            node.property_name,
            value,
        )

    def _execute_relation_assignment(self, node: RelationAssignmentNode) -> None:
        """Assign a value to an object property via relation syntax.

        ``S.Ken.name: "John"`` sets ``Ken.name = "John"``.

        Note
        ----
        The parser stores parts[0] as ``property_name`` and parts[1] as
        ``entity_name`` (grammar ``S.prop.entity``).  Semantically parts[0]
        is the object name and parts[1] is the property name, so the
        arguments are swapped before calling ``set_property``.
        """
        value = self.evaluate(node.value)
        self.object_registry.set_property(
            node.property_name,  # actual object name (parts[0])
            node.entity_name,    # actual property name (parts[1])
            value,
        )

    def _evaluate_property_access(self, node: PropertyAccessNode) -> Any:
        """Evaluate a property access expression (object.property)."""
        obj_ref = self.evaluate(node.object)
        obj = self.object_registry.get(obj_ref)
        try:
            return obj[node.property]
        except KeyError:
            raise RuntimeError(
                f"Property '{node.property}' not found on object"
            )

    def _eval_binary_op(self, node: BinaryOpNode) -> Any:
        """Evaluate a binary operator expression."""
        left = self.evaluate(node.left)
        right = self.evaluate(node.right)
        op = node.operator

        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == ">=":
            return left >= right
        if op == "<=":
            return left <= right

        raise RuntimeError(f"Unknown binary operator: {op!r}")
