"""
ra_ast.py — Abstract Syntax Tree node definitions for the RA language.

Every node guarantees:
  .children   — list of direct child nodes for generic tree traversal
  .line       — 1-based source line where the construct starts
  .auto_close — True when the parser injected an implicit block terminator

Node hierarchy
--------------
  Node  (abstract base)
  ├── Expression nodes
  │   ├── LiteralNode
  │   ├── IdentifierNode
  │   ├── BinaryOpNode
  │   ├── PropertyAccessNode
  │   └── BooleanNode
  └── Statement / block nodes
      ├── ProgramNode
      ├── RunBlockNode    # .run: … r.close
      ├── FunctionBlockNode  # .fun: … f.close
      ├── OOPNode         # OOP
      ├── ConstructorNode # Con: … con.close
      ├── EncapsulationNode  # En: … en.close
      ├── DbNode
      ├── ClassNode
      ├── MethodNode
      ├── ObjectNode
      ├── IfNode
      ├── ElseIfNode
      ├── ElseNode
      ├── ForNode
      ├── WhileNode
   ├── AssignmentNode
   ├── RelationAssignmentNode
   ├── PropertyAssignmentNode
   ├── MethodCallNode
      ├── ReturnNode
      ├── PrintNode
      ├── AICallNode
      ├── DbNextNode
      └── DbBreakNode
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from lexer.tokens import TokenType


# ===========================================================================
# Base node
# ===========================================================================

@dataclass
class Node(ABC):
    """Abstract base for every AST node in the RA language.

    Attributes
    ----------
    line       : 1-based line number of the opening token.
    auto_close : True when the parser injected an implicit block terminator
                 (keyword-only to avoid clashing with positional fields).
    """

    line:       int
    auto_close: bool = field(default=False, kw_only=True)

    @property
    @abstractmethod
    def children(self) -> list[Node]:
        """Every direct child node for generic tree traversal."""
        ...

    def accept(self, visitor: "NodeVisitor") -> Any:
        """Double-dispatch into *visitor*.

        Looks for ``visit_<ClassName>``; falls back to ``generic_visit``.
        """
        method = getattr(
            visitor,
            f"visit_{type(self).__name__}",
            visitor.generic_visit,
        )
        return method(self)

    def walk(self):
        """Depth-first generator yielding *self* and every descendant."""
        yield self
        for child in self.children:
            yield from child.walk()

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}"
            f"(line={self.line}, auto_close={self.auto_close})"
        )


# ===========================================================================
# Expression nodes
# ===========================================================================

@dataclass
class LiteralNode(Node):
    """A compile-time constant: a STRING or INTEGER literal.

    Attributes
    ----------
    value : str | int  — Python-native value of the literal.
    kind  : TokenType  — STRING or INTEGER.
    """

    value: Any
    kind:  TokenType

    @property
    def children(self) -> list[Node]:
        return []

    def __repr__(self) -> str:
        return (
            f"LiteralNode(kind={self.kind.name}, value={self.value!r}, "
            f"line={self.line})"
        )


@dataclass
class IdentifierNode(Node):
    """A reference to a named variable or symbol.

    Attributes
    ----------
    name : str — bare identifier text (e.g. ``"age"``, ``"Person"``).
    """

    name: str

    @property
    def children(self) -> list[Node]:
        return []

    def __repr__(self) -> str:
        return f"IdentifierNode(name={self.name!r}, line={self.line})"


@dataclass
class BinaryOpNode(Node):
    """A binary expression: ``left operator right``.

    Attributes
    ----------
    operator : str  — raw operator text (``"=="``, ``"+"``, ``">="``, ...).
    left     : Node — left-hand operand.
    right    : Node — right-hand operand.
    """

    operator: str
    left:     Node
    right:    Node

    @property
    def children(self) -> list[Node]:
        return [self.left, self.right]

    def __repr__(self) -> str:
        return f"BinaryOpNode(op={self.operator!r}, line={self.line})"


@dataclass
class PropertyAccessNode(Node):
    """A property-access chain: ``object.property``.

    Attributes
    ----------
    object   : Node — the left-hand side expression.
    property : str  — the property name (identifier after ``.``).
    """

    object:   Node
    property: str

    @property
    def children(self) -> list[Node]:
        return [self.object]

    def __repr__(self) -> str:
        return (
            f"PropertyAccessNode(prop={self.property!r}, line={self.line})"
        )


@dataclass
class BooleanNode(Node):
    """A .TF boolean evaluation suffix: ``expr.TF``

    Evaluates *expr* and returns the native Python bool.

    Attributes
    ----------
    expr : Node — the expression whose result becomes a boolean.
    """

    expr: Node

    @property
    def children(self) -> list[Node]:
        return [self.expr]

    def __repr__(self) -> str:
        return (
            f"BooleanNode(line={self.line}, auto_close={self.auto_close})"
        )


# ===========================================================================
# Program root
# ===========================================================================

@dataclass
class ProgramNode(Node):
    """The root of the AST. Contains every top-level statement in order.

    Attributes
    ----------
    body : list[Node] — ordered top-level statements.
    """

    body: list[Node] = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return self.body

    def __repr__(self) -> str:
        return (
            f"ProgramNode(statements={len(self.body)}, "
            f"line={self.line}, auto_close={self.auto_close})"
        )


@dataclass
class RunBlockNode(Node):
    """An immediate execution block: ``.run: ... r.close``

    ``auto_close=True`` means the parser injected an implicit ``r.close``.

    Attributes
    ----------
    body : list[Node] — statements executed when the block is entered.
    """

    body: list[Node] = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return self.body

    def __repr__(self) -> str:
        return (
            f"RunBlockNode(stmts={len(self.body)}, "
            f"line={self.line}, auto_close={self.auto_close})"
        )


@dataclass
class FunctionBlockNode(Node):
    """A local-scope immediate execution block: ``.fun: ... f.close``

    ``auto_close=True`` means the parser injected an implicit ``f.close``.

    Attributes
    ----------
    body : list[Node] — statements executed inside the local scope.
    """

    body: list[Node] = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return self.body

    def __repr__(self) -> str:
        return (
            f"FunctionBlockNode(stmts={len(self.body)}, "
            f"line={self.line}, auto_close={self.auto_close})"
        )


@dataclass
class OOPNode(Node):
    """Activates the built-in OOP library: ``OOP``

    A single-word statement that enables constructor, encapsulation,
    and other OOP features in the runtime.
    """

    @property
    def children(self) -> list[Node]:
        return []

    def __repr__(self) -> str:
        return f"OOPNode(line={self.line})"


@dataclass
class PFNode(Node):
    """Activates the built-in PF (Program Flow) library: ``PF``

    A single-word statement that enables pH and fF blocks.
    """

    @property
    def children(self) -> list[Node]:
        return []

    def __repr__(self) -> str:
        return f"PFNode(line={self.line})"


@dataclass
class AINode(Node):
    """Activates the built-in AI library: ``AI``

    A single-word statement that enables .cov: and .expo: blocks.
    """

    @property
    def children(self) -> list[Node]:
        return []

    def __repr__(self) -> str:
        return f"AINode(line={self.line})"


@dataclass
class CovBlockNode(Node):
    """An AI coverage block: ``.cov: <language>."<path>" cov.close``

    Attributes
    ----------
    language : str — the language or tool name (e.g. "Auto", "Pylint").
    path : str — the file path to analyse.
    """

    language: str = ""
    path: str = ""

    @property
    def children(self) -> list[Node]:
        return []

    def __repr__(self) -> str:
        return (
            f"CovBlockNode(language={self.language!r}, path={self.path!r}, "
            f"line={self.line})"
        )


@dataclass
class ExpoBlockNode(Node):
    """An AI export block: ``.expo: <language>."<path>" ex.close``

    Attributes
    ----------
    language : str — the language or tool name (e.g. "Java", "Python").
    path : str — the file path to export.
    """

    language: str = ""
    path: str = ""

    @property
    def children(self) -> list[Node]:
        return []

    def __repr__(self) -> str:
        return (
            f"ExpoBlockNode(language={self.language!r}, path={self.path!r}, "
            f"line={self.line})"
        )


@dataclass
class ProgramHandlerNode(Node):
    """A Program Handler block: ``pH: ... pH.close``

    ``auto_close=True`` means the parser injected an implicit close.

    Attributes
    ----------
    body : list[Node] — registered references (classes, objects, methods).
    """

    body: list[Node] = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return self.body

    def __repr__(self) -> str:
        return (
            f"ProgramHandlerNode(items={len(self.body)}, "
            f"line={self.line}, auto_close={self.auto_close})"
        )


@dataclass
class FunctionFlowNode(Node):
    """A Function Flow block: ``fF: ... f.close``

    ``auto_close=True`` means the parser injected an implicit close.

    Attributes
    ----------
    body   : list[Node] — ordered method-call statements to execute.
    target : str | None — explicit pH binding (e.g. ``"M.Login"``),
                          or ``None`` for Mode A (unbound).
    """

    body:   list[Node] = field(default_factory=list)
    target: Optional[str] = None

    @property
    def children(self) -> list[Node]:
        return self.body

    def __repr__(self) -> str:
        return (
            f"FunctionFlowNode(calls={len(self.body)}, "
            f"target={self.target!r}, "
            f"line={self.line}, auto_close={self.auto_close})"
        )


@dataclass
class ConstructorNode(Node):
    """A constructor block: ``Con: ... con.close``

    ``auto_close=True`` means the parser injected an implicit close.

    Attributes
    ----------
    body : list[Node] — statements that execute during object creation.
    """

    body: list[Node] = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return self.body

    def __repr__(self) -> str:
        return (
            f"ConstructorNode(stmts={len(self.body)}, "
            f"line={self.line}, auto_close={self.auto_close})"
        )


@dataclass
class EncapsulationNode(Node):
    """An encapsulation block: ``En: ... en.close``

    ``auto_close=True`` means the parser injected an implicit close.

    Attributes
    ----------
    body : list[Node] — property declarations that are private.
    """

    body: list[Node] = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return self.body

    def __repr__(self) -> str:
        return (
            f"EncapsulationNode(stmts={len(self.body)}, "
            f"line={self.line}, auto_close={self.auto_close})"
        )


# ===========================================================================
# Error-handling / switch nodes
# ===========================================================================

@dataclass
class CheckNode(Node):
    """An error-handling block: ``Check: … Valid: … Invalid: … Check.close``

    ``auto_close=True`` means the parser injected an implicit ``Check.close``.

    Attributes
    ----------
    body        : list[Node] — the checked statements.
    valid_body  : list[Node] — executed when *body* succeeds.
    invalid_body : list[Node] — executed when *body* raises an error.
    """

    body:         list[Node] = field(default_factory=list)
    valid_body:   list[Node] = field(default_factory=list)
    invalid_body: list[Node] = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return [*self.body, *self.valid_body, *self.invalid_body]

    def __repr__(self) -> str:
        return (
            f"CheckNode(stmts={len(self.body)}, "
            f"valid={len(self.valid_body)}, "
            f"invalid={len(self.invalid_body)}, "
            f"line={self.line}, auto_close={self.auto_close})"
        )


@dataclass
class CaseNode(Node):
    """A single case branch inside a ``SwitchNode``.

    Attributes
    ----------
    condition : Node        — the value to compare against the key.
    body      : list[Node]  — statements to execute on match.
    """

    condition: Node
    body:      list[Node] = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return [self.condition, *self.body]

    def __repr__(self) -> str:
        return (
            f"CaseNode(line={self.line}, auto_close={self.auto_close})"
        )


@dataclass
class SwitchNode(Node):
    """A switch / case block: ``Key.value: … c.cond: … def: … Key.close``

    Attributes
    ----------
    value        : Node          — the key expression.
    cases        : list[CaseNode] — ordered case branches.
    default_body : list[Node]    — fallback when no case matches.
    """

    value:        Node
    cases:        list[CaseNode] = field(default_factory=list)
    default_body: list[Node]     = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return [self.value, *self.cases, *self.default_body]

    def __repr__(self) -> str:
        return (
            f"SwitchNode(cases={len(self.cases)}, "
            f"line={self.line}, auto_close={self.auto_close})"
        )


# ===========================================================================
# Block / scope nodes
# ===========================================================================

@dataclass
class DbNode(Node):
    """A database block: ``Db: ... db.close``

    ``auto_close=True`` means the parser injected an implicit ``db.close``
    because the source omitted it.

    Attributes
    ----------
    name : str        — connection alias (``"db"`` or named like ``"Personal"``).
    body : list[Node] — statements executed inside the database context.
    """

    name: str
    body: list[Node] = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return self.body

    def __repr__(self) -> str:
        return (
            f"DbNode(name={self.name!r}, body_stmts={len(self.body)}, "
            f"line={self.line}, auto_close={self.auto_close})"
        )


@dataclass
class DbSaveNode(Node):
    """A database save command: ``Db.<name>.save``

    Attributes
    ----------
    database_name : str — name of the database to persist.
    """

    database_name: str

    @property
    def children(self) -> list[Node]:
        return []

    def __repr__(self) -> str:
        return (
            f"DbSaveNode(database={self.database_name!r}, "
            f"line={self.line})"
        )


@dataclass
class DbLoadNode(Node):
    """A database load command: ``Db.<name>.load``

    Attributes
    ----------
    database_name : str — name of the database to load.
    """

    database_name: str

    @property
    def children(self) -> list[Node]:
        return []

    def __repr__(self) -> str:
        return (
            f"DbLoadNode(database={self.database_name!r}, "
            f"line={self.line})"
        )


@dataclass
class ClassNode(Node):
    """A class definition: ``@Cls.Name: ... @``

    The body is terminated by a bare ``@`` token or an implicit boundary.

    Attributes
    ----------
    name    : str        — class name (identifier after ``@Cls.``).
    members : list[Node] — field declarations, methods, and nested blocks.
    """

    name:    str
    members: list[Node] = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return self.members

    def __repr__(self) -> str:
        return (
            f"ClassNode(name={self.name!r}, members={len(self.members)}, "
            f"line={self.line}, auto_close={self.auto_close})"
        )


@dataclass
class MethodNode(Node):
    """A method definition: ``M.name: ... /``

    The body is terminated by a standalone ``/`` token.

    Attributes
    ----------
    name : str        — method name (identifier after ``M.``).
    body : list[Node] — statement nodes forming the method body.
    """

    name: str
    body: list[Node] = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return self.body

    def __repr__(self) -> str:
        return (
            f"MethodNode(name={self.name!r}, "
            f"body_stmts={len(self.body)}, line={self.line}, "
            f"auto_close={self.auto_close})"
        )


@dataclass
class ObjectNode(Node):
    """Object instantiation: ``Obj.ClassName.VariableName``

    Attributes
    ----------
    var_name   : str        — name of the binding variable.
    class_name : str        — name of the class to instantiate.
    args       : list[Node] — constructor argument expressions.
    """

    var_name:   str
    class_name: str
    args:       list[Node] = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return self.args

    def __repr__(self) -> str:
        return (
            f"ObjectNode(var={self.var_name!r}, cls={self.class_name!r}, "
            f"line={self.line}, auto_close={self.auto_close})"
        )


# ===========================================================================
# Control-flow nodes
# ===========================================================================

@dataclass
class ElseNode(Node):
    """The else branch of an ``IfNode``.

    Attributes
    ----------
    body : list[Node] — statements executed when no condition is truthy.
    """

    body: list[Node] = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return self.body

    def __repr__(self) -> str:
        return (
            f"ElseNode(body_stmts={len(self.body)}, "
            f"line={self.line}, auto_close={self.auto_close})"
        )


@dataclass
class IfNode(Node):
    """A conditional branch with optional elseif and else chains.

    Attributes
    ----------
    condition : Node              — boolean guard expression.
    then_body : list[Node]        — statements when condition is truthy.
    elseifs   : list[ElseIfNode]  — elseif branches (empty if none).
    else_node : ElseNode | None   — else branch (None when absent).
    """

    condition: Node
    then_body: list[Node] = field(default_factory=list)
    elseifs:   list[ElseIfNode] = field(default_factory=list)
    else_node: Optional[ElseNode] = None

    @property
    def children(self) -> list[Node]:
        result: list[Node] = [self.condition, *self.then_body, *self.elseifs]
        if self.else_node is not None:
            result.append(self.else_node)
        return result

    @property
    def has_else(self) -> bool:
        return self.else_node is not None

    @property
    def has_elseifs(self) -> bool:
        return bool(self.elseifs)

    def __repr__(self) -> str:
        return (
            f"IfNode(has_else={self.has_else}, "
            f"elseifs={len(self.elseifs)}, line={self.line}, "
            f"auto_close={self.auto_close})"
        )


@dataclass
class ElseIfNode(Node):
    """An elseif branch inside an ``IfNode``.

    Attributes
    ----------
    condition : Node        — boolean guard expression.
    body      : list[Node]  — statements when this branch is taken.
    """

    condition: Node
    body: list[Node] = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return [self.condition, *self.body]

    def __repr__(self) -> str:
        return (
            f"ElseIfNode(line={self.line}, "
            f"auto_close={self.auto_close})"
        )


@dataclass
class ForNode(Node):
    """A for loop over a range: ``? For.var=start;end, ... #``

    Attributes
    ----------
    variable : str        — loop variable name.
    iterable : Node       — range expression (BinaryOpNode with ``";"``).
    body     : list[Node] — loop body statements.
    """

    variable: str
    iterable: Node
    body:     list[Node] = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return [self.iterable, *self.body]

    def __repr__(self) -> str:
        return (
            f"ForNode(var={self.variable!r}, line={self.line}, "
            f"auto_close={self.auto_close})"
        )


@dataclass
class WhileNode(Node):
    """A while loop: ``? While.condition, ... #``

    Attributes
    ----------
    condition : Node        — loop guard expression.
    body      : list[Node]  — loop body statements.
    """

    condition: Node
    body:      list[Node] = field(default_factory=list)

    @property
    def children(self) -> list[Node]:
        return [self.condition, *self.body]

    def __repr__(self) -> str:
        return (
            f"WhileNode(line={self.line}, auto_close={self.auto_close})"
        )


# ===========================================================================
# Statement nodes
# ===========================================================================

@dataclass
class AssignmentNode(Node):
    """A variable assignment, optionally preceded by a type keyword.

    Examples in RA source
    ---------------------
        S name = "Alice"   -> var_type=TokenType.S
        I age  = 30        -> var_type=TokenType.I
        L items = myList   -> var_type=TokenType.L
        x = 99             -> var_type=None  (plain re-assignment)

    Attributes
    ----------
    var_type : TokenType | None — S / I / L, or None for re-assignment.
    name     : str              — target variable name.
    value    : Node             — right-hand side expression.
    """

    var_type: Optional[TokenType]
    name:     str
    value:    Node

    @property
    def children(self) -> list[Node]:
        return [self.value]

    @property
    def is_declaration(self) -> bool:
        """True when a type keyword is present (first assignment)."""
        return self.var_type is not None

    @property
    def type_name(self) -> str:
        """Human-readable type label, or ``'~'`` for plain assignment."""
        return self.var_type.name if self.var_type else "~"

    def __repr__(self) -> str:
        return (
            f"AssignmentNode(type={self.type_name}, name={self.name!r}, "
            f"line={self.line}, auto_close={self.auto_close})"
        )


@dataclass
class RelationAssignmentNode(Node):
    """A typed relation assignment: ``S.prop.entity : value``

    Attributes
    ----------
    var_type      : TokenType — S, I, or L.
    property_name : str       — relation / property name.
    entity_name   : str       — entity identifier.
    value         : Node      — assigned expression.
    """

    var_type:      TokenType
    property_name: str
    entity_name:   str
    value:         Node

    @property
    def children(self) -> list[Node]:
        return [self.value]

    @property
    def type_name(self) -> str:
        return self.var_type.name

    def __repr__(self) -> str:
        return (
            f"RelationAssignmentNode(type={self.type_name}, "
            f"prop={self.property_name!r}, entity={self.entity_name!r}, "
            f"line={self.line}, auto_close={self.auto_close})"
        )


@dataclass
class PropertyAssignmentNode(Node):
    """An object property assignment: ``person.name = value``

    Attributes
    ----------
    object_name   : str  — name of the object variable.
    property_name : str  — name of the property to set.
    value         : Node — right-hand side expression.
    """

    object_name:   str
    property_name: str
    value:         Node

    @property
    def children(self) -> list[Node]:
        return [self.value]

    def __repr__(self) -> str:
        return (
            f"PropertyAssignmentNode(obj={self.object_name!r}, "
            f"prop={self.property_name!r}, line={self.line}, "
            f"auto_close={self.auto_close})"
        )


@dataclass
class MethodCallNode(Node):
    """A method-invocation statement: ``identifier : argument``

    Attributes
    ----------
    method   : str  — callee identifier.
    argument : Node — single argument expression.
    """

    method:   str
    argument: Node

    @property
    def children(self) -> list[Node]:
        return [self.argument]

    def __repr__(self) -> str:
        return (
            f"MethodCallNode(method={self.method!r}, line={self.line}, "
            f"auto_close={self.auto_close})"
        )


@dataclass(slots=True)
class MethodInvokeNode(Node):
    """A method invocation statement: ``MethodName.run`` or ``Obj.MethodName.run``

    Attributes
    ----------
    method_name : str             — method to invoke.
    object_name : str | None      — object variable (``None`` for global method).
    """

    method_name: str
    object_name: Optional[str] = None

    @property
    def children(self) -> list[Node]:
        return []

    def __repr__(self) -> str:
        return (
            f"MethodInvokeNode(method={self.method_name!r}, line={self.line}, "
            f"auto_close={self.auto_close})"
        )


@dataclass
class ReturnNode(Node):
    """A return statement: ``R.value``

    Attributes
    ----------
    value : Node — the expression whose value is returned.
    """

    value: Node

    @property
    def children(self) -> list[Node]:
        return [self.value]

    def __repr__(self) -> str:
        return (
            f"ReturnNode(line={self.line}, auto_close={self.auto_close})"
        )


@dataclass
class PrintNode(Node):
    """A print / output statement: ``p expression``

    Attributes
    ----------
    value : Node — the expression whose representation is printed.
    """

    value: Node

    @property
    def children(self) -> list[Node]:
        return [self.value]

    def __repr__(self) -> str:
        return (
            f"PrintNode(line={self.line}, auto_close={self.auto_close})"
        )


@dataclass
class AICallNode(Node):
    """An AI inference call: ``AI var_name = "prompt"``

    Attributes
    ----------
    var_name : str  — variable that receives the AI response.
    prompt   : Node — expression evaluated as the prompt string.
    """

    var_name: str
    prompt:   Node

    @property
    def children(self) -> list[Node]:
        return [self.prompt]

    def __repr__(self) -> str:
        return (
            f"AICallNode(var={self.var_name!r}, line={self.line}, "
            f"auto_close={self.auto_close})"
        )


@dataclass
class DbNextNode(Node):
    """Advance the database cursor: ``db.next``"""

    @property
    def children(self) -> list[Node]:
        return []

    def __repr__(self) -> str:
        return f"DbNextNode(line={self.line})"


@dataclass
class DbBreakNode(Node):
    """Exit the database loop: ``db.break``"""

    @property
    def children(self) -> list[Node]:
        return []

    def __repr__(self) -> str:
        return f"DbBreakNode(line={self.line})"


# ===========================================================================
# Visitor base
# ===========================================================================

class NodeVisitor(ABC):
    """Base class for AST visitors (Visitor pattern).

    Subclass and override ``visit_<NodeType>`` for the nodes you care
    about.  Unhandled nodes fall through to ``generic_visit``, which
    recurses into all children.
    """

    def visit(self, node: Node) -> Any:
        """Entry point -- dispatches to the appropriate ``visit_*``."""
        return node.accept(self)

    def generic_visit(self, node: Node) -> None:
        """Fallback: visit all children in order."""
        for child in node.children:
            self.visit(child)

    def visit_all(self, nodes: list[Node]) -> None:
        """Convenience: visit every node in a list."""
        for node in nodes:
            self.visit(node)


# ===========================================================================
# Pretty-printer
# ===========================================================================

def dump(node: Node, indent: int = 0) -> str:
    """Return a multi-line, indented string representation of an AST subtree.

    Usage
    -----
        print(dump(program_node))
    """
    lines = [f"{'  ' * indent}{_summary(node)}"]
    for child in node.children:
        lines.append(dump(child, indent + 1))
    return "\n".join(lines)


def _summary(node: Node) -> str:
    """Compact single-line label including key scalar fields."""
    cls    = type(node).__name__
    parts: list[str] = [f"line={node.line}"]

    match node:
        case LiteralNode():
            parts += [f"kind={node.kind.name}", f"value={node.value!r}"]
        case IdentifierNode():
            parts += [f"name={node.name!r}"]
        case BinaryOpNode():
            parts += [f"op={node.operator!r}"]
        case PropertyAccessNode():
            parts += [f"prop={node.property!r}"]
        case BooleanNode():
            parts += []
        case ProgramNode():
            parts += [f"stmts={len(node.body)}"]
        case RunBlockNode():
            parts += [f"stmts={len(node.body)}"]
        case FunctionBlockNode():
            parts += [f"stmts={len(node.body)}"]
        case OOPNode():
            parts += []
        case PFNode():
            parts += []
        case AINode():
            parts += []
        case CovBlockNode():
            parts += [f"lang={node.language!r}, path={node.path!r}"]
        case ExpoBlockNode():
            parts += [f"lang={node.language!r}, path={node.path!r}"]
        case ProgramHandlerNode():
            parts += [f"items={len(node.body)}"]
        case FunctionFlowNode():
            parts += [f"calls={len(node.body)}"]
            if node.target is not None:
                parts += [f"target={node.target!r}"]
        case CheckNode():
            parts += [f"stmts={len(node.body)}",
                      f"valid={len(node.valid_body)}",
                      f"invalid={len(node.invalid_body)}"]
        case SwitchNode():
            parts += [f"cases={len(node.cases)}",
                      f"default={len(node.default_body)}"]
        case CaseNode():
            parts += [f"stmts={len(node.body)}"]
        case ConstructorNode():
            parts += [f"stmts={len(node.body)}"]
        case EncapsulationNode():
            parts += [f"stmts={len(node.body)}"]
        case DbNode():
            parts += [f"name={node.name!r}", f"stmts={len(node.body)}"]
        case DbSaveNode():
            parts += [f"db={node.database_name!r}"]
        case DbLoadNode():
            parts += [f"db={node.database_name!r}"]
        case ClassNode():
            parts += [f"name={node.name!r}", f"members={len(node.members)}"]
        case MethodNode():
            parts += [f"name={node.name!r}"]
        case ObjectNode():
            parts += [f"var={node.var_name!r}", f"cls={node.class_name!r}"]
        case IfNode():
            parts += [f"has_else={node.has_else}", f"elseifs={len(node.elseifs)}"]
        case ElseIfNode():
            parts += [f"stmts={len(node.body)}"]
        case ElseNode():
            parts += [f"stmts={len(node.body)}"]
        case ForNode():
            parts += [f"var={node.variable!r}"]
        case AssignmentNode():
            parts += [f"type={node.type_name}", f"name={node.name!r}"]
        case RelationAssignmentNode():
            parts += [f"type={node.type_name}", f"prop={node.property_name!r}", f"entity={node.entity_name!r}"]
        case MethodCallNode():
            parts += [f"method={node.method!r}"]
        case MethodInvokeNode():
            parts += [f"method={node.method_name!r}"]
            if node.object_name is not None:
                parts += [f"obj={node.object_name!r}"]
        case PropertyAssignmentNode():
            parts += [f"obj={node.object_name!r}", f"prop={node.property_name!r}"]
        case AICallNode():
            parts += [f"var={node.var_name!r}"]

    if node.auto_close:
        parts.append("auto_close=True")

    return f"{cls}({', '.join(parts)})"


# ===========================================================================
# Self-test
# ===========================================================================

if __name__ == "__main__":
    _program = ProgramNode(
        line=1,
        body=[
            ClassNode(
                name="Person",
                line=1,
                members=[
                    AssignmentNode(
                        var_type=TokenType.S,
                        name="name",
                        value=LiteralNode(value="Alice", kind=TokenType.STRING, line=2),
                        line=2,
                    ),
                    AssignmentNode(
                        var_type=TokenType.I,
                        name="age",
                        value=LiteralNode(value=30, kind=TokenType.INTEGER, line=3),
                        line=3,
                    ),
                ],
            ),
            DbNode(
                name="mydb",
                line=5,
                auto_close=True,
                body=[
                    DbNextNode(line=6),
                    DbBreakNode(line=7),
                ],
            ),
            MethodNode(
                name="greet",
                line=9,
                body=[
                    PrintNode(
                        value=PropertyAccessNode(
                            object=IdentifierNode(name="person", line=10),
                            property="name",
                            line=10,
                        ),
                        line=10,
                    ),
                    ReturnNode(
                        value=IdentifierNode(name="result", line=11),
                        line=11,
                    ),
                ],
            ),
            ObjectNode(var_name="p", class_name="Person", line=13),
            IfNode(
                condition=BinaryOpNode(
                    operator="==",
                    left=IdentifierNode(name="x", line=14),
                    right=LiteralNode(value=0, kind=TokenType.INTEGER, line=14),
                    line=14,
                ),
                line=14,
                then_body=[
                    PrintNode(
                        value=LiteralNode(value="zero", kind=TokenType.STRING, line=15),
                        line=15,
                    ),
                ],
                elseifs=[
                    ElseIfNode(
                        condition=BinaryOpNode(
                            operator="==",
                            left=IdentifierNode(name="x", line=16),
                            right=LiteralNode(value=1, kind=TokenType.INTEGER, line=16),
                            line=16,
                        ),
                        line=16,
                        body=[
                            PrintNode(
                                value=LiteralNode(value="one", kind=TokenType.STRING, line=17),
                                line=17,
                            ),
                        ],
                    ),
                ],
                else_node=ElseNode(
                    body=[
                        PrintNode(
                            value=LiteralNode(value="other", kind=TokenType.STRING, line=19),
                            line=19,
                        ),
                    ],
                    line=18,
                    auto_close=False,
                ),
            ),
            ForNode(
                variable="i",
                iterable=BinaryOpNode(
                    operator=";",
                    left=LiteralNode(value=0, kind=TokenType.INTEGER, line=21),
                    right=LiteralNode(value=10, kind=TokenType.INTEGER, line=21),
                    line=21,
                ),
                line=21,
                body=[
                    PrintNode(
                        value=IdentifierNode(name="i", line=22),
                        line=22,
                    ),
                ],
            ),
            WhileNode(
                condition=BinaryOpNode(
                    operator=">",
                    left=IdentifierNode(name="x", line=24),
                    right=LiteralNode(value=0, kind=TokenType.INTEGER, line=24),
                    line=24,
                ),
                line=24,
                body=[
                    PrintNode(
                        value=IdentifierNode(name="x", line=25),
                        line=25,
                    ),
                ],
            ),
            MethodCallNode(
                method="calculateTax",
                argument=LiteralNode(value=50000, kind=TokenType.INTEGER, line=27),
                line=27,
            ),
            AICallNode(
                var_name="response",
                prompt=LiteralNode(value="summarise", kind=TokenType.STRING, line=28),
                line=28,
            ),
            RelationAssignmentNode(
                var_type=TokenType.I,
                property_name="age",
                entity_name="Jey",
                value=LiteralNode(value=25, kind=TokenType.INTEGER, line=29),
                line=29,
            ),
        ],
    )

    print("=" * 60)
    print("RA AST -- self-test dump")
    print("=" * 60)
    print(dump(_program))

    print()
    print("=" * 60)
    print("walk() -- all nodes in depth-first order")
    print("=" * 60)
    for _n in _program.walk():
        print(f"  {type(_n).__name__:<25} line={_n.line}  auto_close={_n.auto_close}")

    print()
    print("=" * 60)
    print("NodeVisitor -- collect all AssignmentNodes")
    print("=" * 60)

    class AssignmentCollector(NodeVisitor):
        def __init__(self) -> None:
            self.found: list[AssignmentNode] = []

        def visit_AssignmentNode(self, node: AssignmentNode) -> None:
            self.found.append(node)
            self.generic_visit(node)

    _collector = AssignmentCollector()
    _collector.visit(_program)
    for _a in _collector.found:
        print(f"  {_a}")
