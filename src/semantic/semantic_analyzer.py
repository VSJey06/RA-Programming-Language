"""SemanticAnalyzer — AST visitor that produces compile-time diagnostics.

Walks a ProgramNode alongside a pre-built SymbolTable and detects
common semantic issues such as undefined references and duplicate
declarations.
"""

from __future__ import annotations

from typing import Any, Optional

from parser.ra_ast import (
    AssignmentNode,
    ClassNode,
    IdentifierNode,
    MethodInvokeNode,
    MethodNode,
    Node,
    NodeVisitor,
    ObjectNode,
    ProgramNode,
    PropertyAccessNode,
)
from semantic.diagnostic import Diagnostic, Severity
from semantic.scope import ClassScope, MethodScope, Scope
from semantic.symbol import ClassSymbol, ObjectSymbol, PackageSymbol, VariableSymbol
from semantic.symbol_table import SymbolTable


class SemanticAnalyzer(NodeVisitor):
    """Checks a parsed program for semantic errors.

    Usage
    -----
        analyzer = SemanticAnalyzer(program_node, symbol_table)
        diags   = analyzer.analyze()
    """

    def __init__(self, program: ProgramNode, table: SymbolTable) -> None:
        self._program = program
        self._table = table
        self._diagnostics: list[Diagnostic] = []
        self._scope: Scope = table.global_scope

        # Tracking sets for duplicate detection (SemanticAnalyzer's own tracking,
        # not SymbolTable — SymbolBuilder pre-populates scopes before we walk)
        self._seen_classes: set[str] = set()
        self._seen_methods: dict[str, set[str]] = {}  # class_name -> set of method names
        self._seen_vars: dict[int, set[str]] = {}  # scope_id -> set of variable names
        self._stack_names: set[str] = set()  # stack names created via Stack.X
        self._queue_names: set[str] = set()  # queue names created via Queue.X
        self._dequeue_names: set[str] = set()  # dequeue names created via Dequeue.X

    # ── Public entry point ──────────────────────────────────────────────

    def analyze(self) -> list[Diagnostic]:
        """Walk the AST and return all collected diagnostics."""
        self.visit(self._program)
        return self._diagnostics

    # ── Diagnostics helpers ─────────────────────────────────────────────

    def _error(self, message: str, node: Node) -> None:
        self._diagnostics.append(
            Diagnostic(message=message, severity=Severity.ERROR,
                       line=node.line, column=node.col)
        )

    # ── Scope helpers ───────────────────────────────────────────────────

    def _scope_by_node(self, scope: Scope, node: Node) -> Optional[Scope]:
        """Find the direct child of *scope* whose symbol's node is *node*."""
        for child in scope.children:
            sym = getattr(child, "class_symbol",
                          getattr(child, "method_symbol", None))
            if sym is not None and sym.node is node:
                return child
        return None

    def _enter(self, node: Node) -> None:
        child = self._scope_by_node(self._scope, node)
        if child is not None:
            self._scope = child

    def _leave(self) -> None:
        if self._scope.parent is not None:
            self._scope = self._scope.parent

    # ── Root ────────────────────────────────────────────────────────────

    def visit_ProgramNode(self, node: ProgramNode) -> None:
        self.generic_visit(node)

    # ── Class declarations ──────────────────────────────────────────────

    def visit_ClassNode(self, node: ClassNode) -> None:
        if node.name in self._seen_classes:
            self._error(f"Class '{node.name}' already defined", node)
        self._seen_classes.add(node.name)
        self._enter(node)
        self.generic_visit(node)
        self._leave()

    # ── Method declarations ─────────────────────────────────────────────

    def visit_MethodNode(self, node: MethodNode) -> None:
        current_class = self._current_class()
        if current_class is not None:
            seen = self._seen_methods.setdefault(current_class.name, set())
            if node.name in seen:
                self._error(f"Method '{node.name}' already defined", node)
            seen.add(node.name)
        self._enter(node)
        self.generic_visit(node)
        self._leave()

    def _current_class(self) -> Optional[Any]:
        """Walk up scope chain to find enclosing ClassSymbol, if any."""
        scope = self._scope
        while scope is not None:
            if isinstance(scope, ClassScope):
                return scope.class_symbol
            scope = scope.parent
        return None

    # ── Variable declarations ───────────────────────────────────────────

    def visit_AssignmentNode(self, node: AssignmentNode) -> None:
        if node.is_declaration:
            scope_id = id(self._scope)
            seen = self._seen_vars.setdefault(scope_id, set())
            if node.name in seen:
                self._error(f"Variable '{node.name}' already defined", node)
            seen.add(node.name)
        self.generic_visit(node)

    # ── Object instantiation ────────────────────────────────────────────

    def visit_ObjectNode(self, node: ObjectNode) -> None:
        cls = self._table.global_scope.lookup(node.class_name)
        if cls is None or not isinstance(cls, ClassSymbol):
            self._error(f"Undefined class '{node.class_name}'", node)
        self.generic_visit(node)

    # ── Method invocation ───────────────────────────────────────────────

    def visit_MethodInvokeNode(self, node: MethodInvokeNode) -> None:
        if node.object_name is not None:
            obj = self._scope.lookup(node.object_name)
            if obj is None:
                self._error(f"Undefined object '{node.object_name}'", node)
        self.generic_visit(node)

    # ── Variable references ─────────────────────────────────────────────

    def visit_IdentifierNode(self, node: IdentifierNode) -> None:
        name = node.name
        # Skip single-character identifiers (common loop vars, etc.)
        if len(name) == 1:
            self.generic_visit(node)
            return
        # Skip package command names (resolved via PackageRegistry)
        if self._is_package_name(name):
            return
        # Skip built-in EMPTY value
        if name == "EMPTY":
            return
        # Skip stack / queue / dequeue names created via Stack.X / Queue.X / Dequeue.X
        if name in self._stack_names or name in self._queue_names or name in self._dequeue_names:
            return
        existing = self._scope.lookup(name)
        if existing is None:
            self._error(f"Undefined variable '{name}'", node)
        self.generic_visit(node)

    # ── Property access (object.property) ──────────────────────────────

    def visit_PropertyAccessNode(self, node: PropertyAccessNode) -> None:
        obj_name = getattr(node.object, "name", None)
        if obj_name == "Dequeue":
            self._dequeue_names.add(node.property)
            return
        if obj_name == "Queue":
            self._queue_names.add(node.property)
            return
        if obj_name == "Stack":
            self._stack_names.add(node.property)
            return
        if obj_name and self._is_package_name(obj_name):
            return
        self.generic_visit(node)

    def _is_package_name(self, name: str) -> bool:
        """Check if *name* is a known PAC package command."""
        try:
            from pac import PackageRegistry
            return PackageRegistry.has(name)
        except ImportError:
            return False

    # ── Remaining nodes — recurse only ──────────────────────────────────

    def generic_visit(self, node: Node) -> None:
        for child in node.children:
            self.visit(child)

    def _noop(self, node: Node) -> None:
        self.generic_visit(node)

    visit_PrintNode = _noop
    visit_BinaryOpNode = _noop
    visit_LiteralNode = _noop
    visit_BooleanNode = _noop
    visit_IfNode = _noop
    visit_ElseIfNode = _noop
    visit_ElseNode = _noop
    visit_ForNode = _noop
    visit_WhileNode = _noop
    visit_ReturnNode = _noop
    visit_RunBlockNode = _noop
    visit_FunctionBlockNode = _noop
    visit_OOPNode = _noop
    visit_PFNode = _noop
    visit_AINode = _noop
    visit_CovBlockNode = _noop
    visit_ExpoBlockNode = _noop
    visit_CallBlockNode = _noop
    visit_GenerateNode = _noop
    visit_ProgramHandlerNode = _noop
    visit_FunctionFlowNode = _noop
    visit_ConstructorNode = _noop
    visit_EncapsulationNode = _noop
    visit_DbSaveNode = _noop
    visit_DbLoadNode = _noop
    visit_DbNextNode = _noop
    visit_DbBreakNode = _noop
    visit_MethodCallNode = _noop
    visit_PropertyAssignmentNode = _noop
    visit_CheckNode = _noop
    visit_SwitchNode = _noop
    visit_CaseNode = _noop
    visit_DbNode = _noop
    visit_RelationAssignmentNode = _noop
