"""SymbolBuilder — AST visitor that populates a SymbolTable.

Walks a ProgramNode and collects every named declaration into scopes
without performing any semantic checks or runtime changes.
"""

from __future__ import annotations

from typing import Optional

from parser.ra_ast import (
    AICallNode,
    AINode,
    AssignmentNode,
    BinaryOpNode,
    BooleanNode,
    CallBlockNode,
    CaseNode,
    CheckNode,
    ClassNode,
    ConstructorNode,
    CovBlockNode,
    DbBreakNode,
    DbLoadNode,
    DbNextNode,
    DbNode,
    DbSaveNode,
    ElseIfNode,
    ElseNode,
    EncapsulationNode,
    ExpoBlockNode,
    ForNode,
    FunctionBlockNode,
    FunctionFlowNode,
    GenerateNode,
    IdentifierNode,
    IfNode,
    LiteralNode,
    MethodCallNode,
    MethodInvokeNode,
    MethodNode,
    Node,
    NodeVisitor,
    ObjectNode,
    OOPNode,
    PFNode,
    PrintNode,
    ProgramHandlerNode,
    ProgramNode,
    PropertyAccessNode,
    PropertyAssignmentNode,
    RelationAssignmentNode,
    ReturnNode,
    RunBlockNode,
    SwitchNode,
    WhileNode,
)
from semantic.scope import (
    ClassScope,
    DatabaseScope,
    GlobalScope,
    MethodScope,
    Scope,
)
from semantic.symbol import (
    ClassSymbol,
    DatabaseSymbol,
    MethodSymbol,
    ObjectSymbol,
    VariableSymbol,
)
from semantic.symbol_table import SymbolTable


class SymbolBuilder(NodeVisitor):
    """Builds a SymbolTable by visiting every AST node.

    Usage
    -----
        builder = SymbolBuilder()
        table   = builder.build(program_node)
    """

    def __init__(self) -> None:
        self.table = SymbolTable()
        self._scope: Scope = self.table.global_scope

    def build(self, program: ProgramNode) -> SymbolTable:
        """Walk *program* and return the populated SymbolTable."""
        self.visit(program)
        return self.table

    # ── Scope helpers ─────────────────────────────────────────────────

    def _enter(self, child_scope: Scope) -> None:
        child_scope.parent = self._scope
        self._scope.children.append(child_scope)
        self._scope = child_scope

    def _leave(self) -> None:
        if self._scope.parent is not None:
            self._scope = self._scope.parent

    # ── Root ──────────────────────────────────────────────────────────

    def visit_ProgramNode(self, node: ProgramNode) -> None:
        for stmt in node.body:
            self.visit(stmt)

    # ── Class definitions ─────────────────────────────────────────────

    def visit_ClassNode(self, node: ClassNode) -> None:
        sym = ClassSymbol(name=node.name, node=node)
        self._scope.define(sym)
        class_scope = ClassScope(class_symbol=sym)
        self._enter(class_scope)
        for member in node.members:
            self.visit(member)
        self._leave()

    # ── Method definitions ────────────────────────────────────────────

    def visit_MethodNode(self, node: MethodNode) -> None:
        sym = MethodSymbol(name=node.name, node=node)
        self._scope.define(sym)
        # Register the method in the enclosing class (if inside a class scope)
        if isinstance(self._scope, ClassScope):
            self._scope.class_symbol.methods.append(sym)
        method_scope = MethodScope(method_symbol=sym)
        self._enter(method_scope)
        for stmt in node.body:
            self.visit(stmt)
        self._leave()

    # ── Variable declarations ─────────────────────────────────────────

    def visit_AssignmentNode(self, node: AssignmentNode) -> None:
        if node.is_declaration:
            sym = VariableSymbol(
                name=node.name,
                node=node,
                var_type=node.type_name,
            )
            self._scope.define(sym)
            # Also register in the enclosing class / method scopes
            if isinstance(self._scope, MethodScope):
                self._scope.method_symbol.variables.append(sym)
            elif isinstance(self._scope, ClassScope):
                self._scope.class_symbol.variables.append(sym)
        self.generic_visit(node)

    def visit_RelationAssignmentNode(self, node: RelationAssignmentNode) -> None:
        sym = VariableSymbol(
            name=node.property_name,
            node=node,
            var_type=node.type_name,
        )
        self._scope.define(sym)
        if isinstance(self._scope, ClassScope):
            self._scope.class_symbol.variables.append(sym)
        self.generic_visit(node)

    # ── Object instantiation ──────────────────────────────────────────

    def visit_ObjectNode(self, node: ObjectNode) -> None:
        sym = ObjectSymbol(
            name=node.var_name,
            node=node,
            class_name=node.class_name,
        )
        self._scope.define(sym)
        self.generic_visit(node)

    # ── Database blocks ───────────────────────────────────────────────

    def visit_DbNode(self, node: DbNode) -> None:
        sym = DatabaseSymbol(name=node.name, node=node)
        self._scope.define(sym)
        db_scope = DatabaseScope(db_symbol=sym)
        self._enter(db_scope)
        for stmt in node.body:
            self.visit(stmt)
        self._leave()

    # ── Remaining nodes — recurse with no symbol registration ─────────

    def generic_visit(self, node: Node) -> None:
        for child in node.children:
            self.visit(child)

    def _noop(self, node: Node) -> None:
        self.generic_visit(node)

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
    visit_IfNode = _noop
    visit_ElseIfNode = _noop
    visit_ElseNode = _noop
    visit_ForNode = _noop
    visit_WhileNode = _noop
    visit_PrintNode = _noop
    visit_ReturnNode = _noop
    visit_AICallNode = _noop
    visit_MethodCallNode = _noop
    visit_MethodInvokeNode = _noop
    visit_PropertyAssignmentNode = _noop
    visit_CheckNode = _noop
    visit_SwitchNode = _noop
    visit_CaseNode = _noop
    visit_IdentifierNode = _noop
    visit_LiteralNode = _noop
    visit_BinaryOpNode = _noop
    visit_PropertyAccessNode = _noop
    visit_BooleanNode = _noop
