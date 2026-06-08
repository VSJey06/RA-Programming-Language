"""
runtime.py — Interpreter for the RA language.

Walks an AST (from ``parser.ra_ast``) and executes it immediately.
"""

from __future__ import annotations

from typing import Any

from parser.ra_ast import (
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
    DbLoadNode,
    DbNode,
    DbSaveNode,
    EncapsulationNode,
    ExpoBlockNode,
    ForNode,
    FunctionBlockNode,
    GenerateNode,
    FunctionFlowNode,
    IdentifierNode,
    IfNode,
    LiteralNode,
    MethodCallNode,
    MethodInvokeNode,
    MethodNode,
    Node,
    ObjectNode,
    OOPNode,
    PFNode,
    PrintNode,
    ProgramHandlerNode,
    ProgramNode,
    PropertyAccessNode,
    PropertyAssignmentNode,
    RelationAssignmentNode,
    RunBlockNode,
    SwitchNode,
    WhileNode,
)
from parser.parser import ParseError
from lib.ai.cov import run_cov
from lib.ai.expo import run_expo
from lib.ai.call import Call
from lib.ai.generate import Gen
from lib.pf import PFEngine
from runtime.control_flow import ControlFlowEngine
from runtime.db_engine import DatabaseEngine
from runtime.executor import Executor
from runtime.structural.class_system import ClassRegistry
from runtime.structural.method_system import MethodRegistry
from runtime.structural.object_system import ObjectRegistry


class RuntimeError(Exception):
    """Raised when the interpreter encounters a runtime error."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(f"RuntimeError: {message}")


class Runtime:
    """Simple tree-walking interpreter for the RA language.

    Attributes
    ----------
    global_scope : dict[str, Any] — mutable variable store.
    _locals     : list[dict[str, Any]] — local scope stack for ``.fun:`` blocks.
    """

    def __init__(self) -> None:
        self.global_scope: dict[str, Any] = {}
        self._locals: list[dict[str, Any]] = []
        self._active_db: str | None = None
        self._oop_active: bool = False
        self._active_object: str | None = None
        self._private_props: dict[str, set[str]] = {}
        self._object_classes: dict[str, str] = {}
        self.executor = Executor(self)
        self.control_flow = ControlFlowEngine(self, self.executor)
        self.class_registry = ClassRegistry()
        self.method_registry = MethodRegistry()
        self.object_registry = ObjectRegistry()
        self.db_engine = DatabaseEngine()
        self._pf_engine = PFEngine()
        self._pending_ff_nodes: list[FunctionFlowNode] = []
        self._pf_activated = False
        self.ai_enabled: bool = False

    # ── Entry point ──────────────────────────────────────────────────────

    def execute(self, program_node: ProgramNode) -> None:
        """Execute a full ``ProgramNode``.

        Walks ``ProgramNode.body`` sequentially and runs every statement.
        fF (Function Flow) bodies are deferred until after the full program
        has been scanned so that dependency validation (pH ↔ fF) and class/
        object registration happen before flow execution.
        """
        for node in program_node.body:
            if isinstance(node, FunctionFlowNode):
                try:
                    self._pf_engine.require_active()
                    self._pf_engine.register_ff(node)
                except Exception as e:
                    if not isinstance(e, RuntimeError):
                        raise RuntimeError(str(e))
                    raise
                self._pending_ff_nodes.append(node)
                continue

            self.execute_node(node)
            if isinstance(node, PFNode):
                self._pf_activated = True

        # Execute pending fF flows when PF is active and both pH and fF exist
        if self._pf_activated and self._pending_ff_nodes:
            ph_registered = bool(self._pf_engine.ph_entries)
            ff_registered = bool(self._pf_engine.ff_nodes)
            if ph_registered and ff_registered:
                try:
                    self._pf_engine.validate_dependency(ph_registered, ff_registered)
                except Exception as e:
                    if not isinstance(e, RuntimeError):
                        raise RuntimeError(str(e))
                    raise
                for ff_node in self._pending_ff_nodes:
                    self._pf_engine.execute_flow(self, ff_node.body)
                self._pending_ff_nodes.clear()

    # ── Statement dispatch ───────────────────────────────────────────────

    def execute_node(self, node: Node) -> None:
        """Execute a statement node.

        Dispatches based on the runtime type of *node*.
        Raises ``RuntimeError`` for unsupported node types.
        """
        if isinstance(node, DbNode):
            self._execute_db(node)
        elif isinstance(node, RunBlockNode):
            self._execute_run_block(node)
        elif isinstance(node, FunctionBlockNode):
            self._execute_function_block(node)
        elif isinstance(node, OOPNode):
            self._oop_active = True
        elif isinstance(node, ConstructorNode):
            # At statement level a bare ConstructorNode is a no-op;
            # it is only meaningful inside a class body where
            # _execute_object invokes it.
            pass
        elif isinstance(node, EncapsulationNode):
            # Similarly a no-op at statement level.
            pass
        elif isinstance(node, DbSaveNode):
            self._execute_db_save(node)
        elif isinstance(node, DbLoadNode):
            self._execute_db_load(node)
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
        elif isinstance(node, CheckNode):
            self._execute_check(node)
        elif isinstance(node, SwitchNode):
            self._execute_switch(node)
        elif isinstance(node, PFNode):
            self._pf_engine.activate()
        elif isinstance(node, AINode):
            self.ai_enabled = True
        elif isinstance(node, CovBlockNode):
            self._execute_cov_block(node)
        elif isinstance(node, ExpoBlockNode):
            self._execute_expo_block(node)
        elif isinstance(node, CallBlockNode):
            self._execute_call_block(node)
        elif isinstance(node, GenerateNode):
            self._execute_gen_block(node)
        elif isinstance(node, ProgramHandlerNode):
            self._execute_ph(node)
        elif isinstance(node, FunctionFlowNode):
            self._execute_ff(node)
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
        if isinstance(node, BooleanNode):
            return bool(self.evaluate(node.expr))
        raise RuntimeError(f"Node type not implemented: {type(node).__name__}")

    # ── Internal helpers ─────────────────────────────────────────────────

    def _execute_db(self, node: DbNode) -> None:
        """Execute all statements inside a Db block.

        Typed assignments are stored in the named database.
        """
        db_name = node.name
        if not self.db_engine.has_database(db_name):
            self.db_engine.register_database(db_name)
        saved = self._active_db
        self._active_db = db_name
        for child in node.body:
            self.execute_node(child)
        self._active_db = saved

    def _execute_db_save(self, node: DbSaveNode) -> None:
        """Persist the named database to disk and confirm."""
        self.db_engine.save_database(node.database_name)
        print(f"Database '{node.database_name}' saved.")

    def _execute_db_load(self, node: DbLoadNode) -> None:
        """Load the named database from disk and restore into global scope."""
        self.db_engine.load_database(node.database_name)
        for key, value in self.db_engine.get_database(node.database_name).items():
            self.global_scope[key] = value
        print(f"Database '{node.database_name}' loaded.")

    def _execute_run_block(self, node: RunBlockNode) -> None:
        """Execute the statements inside a ``.run:`` block immediately."""
        for child in node.body:
            self.execute_node(child)

    def _execute_function_block(self, node: FunctionBlockNode) -> None:
        """Execute the statements inside a ``.fun:`` block with a local scope.

        A new empty scope is created for the block; all variable assignments
        go into this local scope.  When the block exits the scope is
        discarded, so any variables declared inside are no longer visible.
        """
        self._locals.append({})
        try:
            for child in node.body:
                self.execute_node(child)
        finally:
            self._locals.pop()

    def _execute_cov_block(self, node: CovBlockNode) -> None:
        """Execute a ``.cov:`` coverage command.

        Requires the AI library to be active.
        """
        if not self.ai_enabled:
            raise RuntimeError("AI library not imported. Required: AI")
        out_path = run_cov(node.language, node.path)
        print("Conversion Complete")
        print(f"Source:\n{node.path}")
        print(f"Output:\n{out_path}")

    def _execute_expo_block(self, node: ExpoBlockNode) -> None:
        """Execute a ``.expo:`` export command.

        Requires the AI library to be active.
        """
        if not self.ai_enabled:
            raise RuntimeError("AI library not imported. Required: AI")
        out_path = run_expo(node.language, node.path)
        print("Export Complete")
        print(f"Source:\n{node.path}")
        print(f"Output:\n{out_path}")

    def _execute_call_block(self, node: CallBlockNode) -> None:
        """Execute a ``.Call:`` query command.

        Requires the AI library to be active.
        """
        if not self.ai_enabled:
            raise RuntimeError("AI library not imported. Required: AI")
        answer = Call(node.question)
        print(answer)

    def _execute_gen_block(self, node: GenerateNode) -> None:
        """Execute a ``.Gen:`` generation command.

        Requires the AI library to be active.
        """
        if not self.ai_enabled:
            raise RuntimeError("AI library not imported. Required: AI")
        result = Gen(node.description)
        print(result)

    def _execute_print(self, node: PrintNode) -> None:
        """Evaluate the print expression and write the result to stdout."""
        value = self.evaluate(node.value)
        if value is None:
            print("null")
        else:
            print(value)

    def _execute_assignment(self, node: AssignmentNode) -> None:
        """Evaluate the right-hand side and store it in the current scope.

        If inside a constructor (``_active_object`` is set) the value is
        stored as a property on the new object.
        If inside a ``.fun:`` block the variable goes into the local scope;
        otherwise it goes into ``global_scope``.
        If inside a Db block the value is also stored in the active database.
        """
        value = self.evaluate(node.value)
        if self._active_object is not None:
            self.object_registry.set_property(
                self._active_object, node.name, value,
            )
            if self._active_db is not None:
                self.db_engine.set_value(self._active_db, node.name, value)
            return
        target = self._locals[-1] if self._locals else self.global_scope
        target[node.name] = value
        if self._active_db is not None:
            self.db_engine.set_value(self._active_db, node.name, value)

    # ── Check / Valid / Invalid ──────────────────────────────────────────

    def _execute_check(self, node: CheckNode) -> None:
        """Execute a Check block with error recovery.

        If *body* raises an exception the ``Invalid`` block runs and
        ``error`` becomes available.  On success the ``Valid`` block runs.
        """
        try:
            for stmt in node.body:
                self.execute_node(stmt)
        except (RuntimeError, SyntaxError, ParseError) as e:
            if node.invalid_body:
                target = self._locals[-1] if self._locals else self.global_scope
                saved = target.get("error")
                target["error"] = getattr(e, "message", str(e))
                try:
                    for stmt in node.invalid_body:
                        self.execute_node(stmt)
                finally:
                    if saved is not None:
                        target["error"] = saved
                    else:
                        target.pop("error", None)
            return
        else:
            if node.valid_body:
                for stmt in node.valid_body:
                    self.execute_node(stmt)

    # ── Switch / case / def ───────────────────────────────────────────────

    def _execute_switch(self, node: SwitchNode) -> None:
        """Execute a Key / case / def block.

        Evaluate the key, compare against each case condition in order,
        execute the first match, then stop.  Falls through to default
        when no case matches.
        """
        key_value = self.evaluate(node.value)

        for case in node.cases:
            case_value = self.evaluate(case.condition)
            if key_value == case_value:
                for stmt in case.body:
                    self.execute_node(stmt)
                return

        if node.default_body:
            for stmt in node.default_body:
                self.execute_node(stmt)

    # ── PF / Program Handler / Function Flow ─────────────────────────────

    def _execute_ph(self, node: ProgramHandlerNode) -> None:
        """Execute a Program Handler (pH) block.

        Registers the execution order and validates PF is active.
        pH does not execute anything — it is a blueprint.
        """
        try:
            self._pf_engine.require_active()
            self._pf_engine.register_ph(node)
        except Exception as e:
            if not isinstance(e, RuntimeError):
                raise RuntimeError(str(e))
            raise

    def _execute_ff(self, node: FunctionFlowNode) -> None:
        """Register an fF block.

        Execution is deferred until after the full program has been
        scanned so that dependency validation and class/object
        registration happen first.
        """
        self._pf_engine.register_ff(node)
        self._pending_ff_nodes.append(node)

    # ── Class / Method / Object ────────────────────────────────────────────

    def _execute_class(self, node: ClassNode) -> None:
        """Register a class definition.

        When OOP is active, scan the class body for an
        ``EncapsulationNode`` and record its property names as private.
        """
        self.class_registry.register(node)

        if not self._oop_active:
            return

        for member in node.members:
            if isinstance(member, EncapsulationNode):
                props: set[str] = set()
                for stmt in member.body:
                    if isinstance(stmt, AssignmentNode):
                        props.add(stmt.name)
                if props:
                    self._private_props[node.name] = props
                break

    def _execute_method(self, node: MethodNode) -> None:
        """Register a method definition."""
        self.method_registry.register(node)

    def _execute_method_invoke(self, node: MethodInvokeNode) -> None:
        """Execute a method invocation — global or class-bound.

        Global: ``Show.run``           — look up in ``MethodRegistry``.
        Class-bound: ``Ken.Show.run``  — find method on the object's class,
                                          execute with ``_active_object`` set
                                          so private properties are accessible.
        """
        if node.object_name is not None:
            # Resolve object variable name
            name = node.object_name
            obj_ref: str | None = None
            for scope in reversed(self._locals):
                if name in scope:
                    obj_ref = scope[name]
                    break
            if obj_ref is None:
                obj_ref = self.global_scope.get(name)
            if obj_ref is None:
                raise RuntimeError(f"Variable '{name}' is not defined")
            class_name = self._object_classes.get(obj_ref)
            if class_name is None:
                raise RuntimeError(
                    f"'{node.object_name}' is not a class instance"
                )
            class_node = self.class_registry.get(class_name)
            method_node: MethodNode | None = None
            for member in class_node.members:
                if isinstance(member, MethodNode) and member.name == node.method_name:
                    method_node = member
                    break
            if method_node is None:
                raise RuntimeError(
                    f"Method '{node.method_name}' not found "
                    f"in class '{class_name}'"
                )
            saved = self._active_object
            self._active_object = obj_ref
            try:
                self.executor.execute_nodes(method_node.body)
            finally:
                self._active_object = saved
        else:
            try:
                method = self.method_registry.get(node.method_name)
            except Exception:
                raise RuntimeError(
                    f"Method '{node.method_name}' is not defined"
                )
            self.executor.execute_nodes(method.body)

    def _execute_object(self, node: ObjectNode) -> None:
        """Instantiate an object from a registered class.

        When OOP is active the constructor body is executed immediately
        and encapsulation properties are copied to the new object.
        """
        if not self.class_registry.exists(node.class_name):
            raise RuntimeError(f"Class '{node.class_name}' is not defined")
        self.object_registry.create(
            node.var_name, node.class_name, self.class_registry,
        )
        target = self._locals[-1] if self._locals else self.global_scope
        target[node.var_name] = node.var_name
        self._object_classes[node.var_name] = node.class_name

        if not self._oop_active:
            return

        # Copy encapsulation (private) property defaults
        if node.class_name in self._private_props:
            class_node = self.class_registry.get(node.class_name)
            for member in class_node.members:
                if isinstance(member, EncapsulationNode):
                    for stmt in member.body:
                        if isinstance(stmt, AssignmentNode):
                            val = self.evaluate(stmt.value)
                            self.object_registry.set_property(
                                node.var_name, stmt.name, val,
                            )
                    break

        # Execute constructor body
        class_node = self.class_registry.get(node.class_name)
        for member in class_node.members:
            if isinstance(member, ConstructorNode):
                saved = self._active_object
                self._active_object = node.var_name
                try:
                    for stmt in member.body:
                        self.execute_node(stmt)
                finally:
                    self._active_object = saved
                break

    def _lookup_identifier(self, node: IdentifierNode) -> Any:
        """Resolve an identifier in the local scopes first, then global.

        If inside a constructor (``_active_object`` is set), the new
        object's properties are searched before local scopes.

        Local scopes (pushed by ``.fun:`` blocks) are searched last-in-
        first-out so that inner blocks shadow outer ones correctly.
        Raises ``RuntimeError`` when the variable is not defined.
        """
        if self._active_object is not None:
            obj = self.object_registry.get(self._active_object)
            if node.name in obj:
                return obj[node.name]
        for scope in reversed(self._locals):
            if node.name in scope:
                return scope[node.name]
        try:
            return self.global_scope[node.name]
        except KeyError:
            raise RuntimeError(f"Variable '{node.name}' is not defined")

    def _execute_property_assignment(self, node: PropertyAssignmentNode) -> None:
        """Assign a value to an object property.

        When OOP is active, private properties cannot be written from
        outside the class.
        """
        # Encapsulation guard — skip when inside a method of the same object
        if (self._oop_active
                and self._active_object != node.object_name):
            class_name = self._object_classes.get(node.object_name)
            if (class_name
                    and class_name in self._private_props
                    and node.property_name in self._private_props[class_name]):
                raise RuntimeError(
                    f"Property '{node.property_name}' is private"
                )
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
        """Evaluate a property access expression (object.property).

        When OOP is active, private properties cannot be read from outside
        the class (i.e. when not inside a constructor of the same class).
        """
        obj_ref = self.evaluate(node.object)
        obj = self.object_registry.get(obj_ref)

        # Encapsulation guard — skip when inside a method of the same object
        if (self._oop_active
                and self._active_object != obj_ref):
            class_name = self._object_classes.get(obj_ref)
            if (class_name
                    and class_name in self._private_props
                    and node.property in self._private_props[class_name]):
                raise RuntimeError(
                    f"Property '{node.property}' is private"
                )

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
