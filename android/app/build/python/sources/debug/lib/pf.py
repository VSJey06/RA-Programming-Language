"""
pf.py — Program Flow (PF) library engine for RA.

Manages PF activation, pH (Program Handler) registration order,
Mode A (1 pH → 1 fF) and Mode B (1 pH → N fF with explicit bindings),
and fF (Function Flow) automatic execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from parser.ra_ast import (
    CheckNode,
    ClassNode,
    FunctionFlowNode,
    MethodInvokeNode,
    MethodNode,
    Node,
    ObjectNode,
    ProgramHandlerNode,
    SwitchNode,
)

if TYPE_CHECKING:
    from runtime.runtime import Runtime


class PFEngine:
    """Engine for the PF (Program Flow) library.

    Supports two modes:

    * **Mode A** — single unbound ``fF:`` block.
    * **Mode B** — one or more explicitly-bound ``fF.<target>:`` blocks.

    Attributes
    ----------
    active      : bool — ``True`` after a ``PF`` statement.
    ph_entries  : set[str] — pH-registered entry names (e.g. ``"M.Login"``).
    ff_nodes    : list[FunctionFlowNode] — collected fF blocks (deferred).
    """

    def __init__(self) -> None:
        self.active = False
        self.ph_entries: set[str] = set()
        self.ff_nodes: list[FunctionFlowNode] = []

    # ── PF activation ──────────────────────────────────────────────────

    def activate(self) -> None:
        """Mark PF as active and reset all prior PF state.

        Calling ``PF`` starts a fresh session — any pH entries or fF
        blocks registered in a previous PF session are discarded.
        """
        self.active = True
        self.ph_entries.clear()
        self.ff_nodes.clear()

    def require_active(self) -> None:
        """Raise ``RuntimeError`` if PF has not been activated."""
        if not self.active:
            raise RuntimeError(
                "PF library not activated.  "
                "Add 'PF' at the top of your program."
            )

    # ── pH registration ────────────────────────────────────────────────

    def register_ph(self, node: ProgramHandlerNode) -> None:
        """Extract and record pH entry names from *node*.

        Each item in the pH body is converted to a string key:

        * ``@Cls.User`` → ``"@Cls.User"``
        * ``Obj.User.Admin`` → ``"Obj.User.Admin"``
        * ``M.Login`` → ``"M.Login"``
        """
        self.require_active()
        self.ph_entries.clear()
        for item in node.body:
            if isinstance(item, ClassNode):
                self.ph_entries.add(f"@Cls.{item.name}")
            elif isinstance(item, ObjectNode):
                self.ph_entries.add(f"Obj.{item.class_name}.{item.var_name}")
            elif isinstance(item, MethodNode):
                self.ph_entries.add(f"M.{item.name}")

    # ── fF registration ────────────────────────────────────────────────

    def register_ff(self, node: FunctionFlowNode) -> None:
        """Record an fF block for deferred execution."""
        self.require_active()
        self.ff_nodes.append(node)

    # ── Cross-validation ───────────────────────────────────────────────

    def validate_dependency(self, ph_seen: bool, ff_seen: bool) -> None:
        """Raise ``RuntimeError`` if pH/fF dependency or bindings are invalid.

        Mode A: checks that both pH and fF exist.
        Mode B: additionally validates every fF target exists in pH entries.
        """
        if ph_seen and not ff_seen:
            raise RuntimeError(
                "pH requires fF block.  "
                "Add an 'fF:' block after 'pH:'."
            )
        if ff_seen and not ph_seen:
            raise RuntimeError(
                "fF requires pH block.  "
                "Add a 'pH:' block before 'fF:'."
            )

        # Validate explicit bindings (Mode B)
        for ff_node in self.ff_nodes:
            if ff_node.target is not None and ff_node.target not in self.ph_entries:
                raise RuntimeError(
                    f"PF flow target '{ff_node.target}' not found "
                    f"in pH block"
                )

    # ── Flow execution ─────────────────────────────────────────────────

    def execute_flow(self, runtime: Runtime, body: list[Node]) -> None:
        """Execute an fF body sequentially (top-to-bottom).

        Each ``MethodInvokeNode`` uses the *class name* as the object
        reference; the engine resolves it to an actual object variable
        name before dispatching.

        ``CheckNode`` and ``SwitchNode`` are also supported — any
        ``MethodInvokeNode`` inside them is resolved the same way.
        """
        for item in body:
            if isinstance(item, MethodInvokeNode):
                actual = self._resolve_obj_var(runtime, item)
                runtime._execute_method_invoke(actual)
            elif isinstance(item, CheckNode):
                self._resolve_body(runtime, item.body)
                self._resolve_body(runtime, item.valid_body)
                self._resolve_body(runtime, item.invalid_body)
                runtime._execute_check(item)
            elif isinstance(item, SwitchNode):
                for case in item.cases:
                    self._resolve_body(runtime, case.body)
                self._resolve_body(runtime, item.default_body)
                runtime._execute_switch(item)

    @staticmethod
    def _resolve_body(runtime: Runtime, body: list[Node]) -> None:
        """Resolve all ``MethodInvokeNode`` objects within *body* in-place."""
        for i, stmt in enumerate(body):
            if isinstance(stmt, MethodInvokeNode):
                body[i] = PFEngine._resolve_obj_var(runtime, stmt)

    @staticmethod
    def _resolve_obj_var(
        runtime: Runtime, node: MethodInvokeNode,
    ) -> MethodInvokeNode:
        """Resolve a class-name reference to an object variable name.

        ``User.Login`` means "find an object variable of class ``User``
        and call method ``Login`` on it".  We search the global scope
        and local scopes for a variable whose object registry entry has
        ``__class__ == node.object_name``.
        """
        class_name = node.object_name

        # Search global scope first
        for var_name, obj_ref in runtime.global_scope.items():
            if runtime.object_registry.exists(obj_ref):
                obj = runtime.object_registry.get(obj_ref)
                if obj.get("__class__") == class_name:
                    return MethodInvokeNode(
                        method_name=node.method_name,
                        object_name=var_name,
                        line=node.line,
                    )

        # Search local scopes (outer-to-inner)
        for scope in runtime._locals:
            for var_name, obj_ref in scope.items():
                if runtime.object_registry.exists(obj_ref):
                    obj = runtime.object_registry.get(obj_ref)
                    if obj.get("__class__") == class_name:
                        return MethodInvokeNode(
                            method_name=node.method_name,
                            object_name=var_name,
                            line=node.line,
                        )

        raise RuntimeError(
            f"No object of class '{class_name}' found for fF call "
            f"'{class_name}.{node.method_name}'"
        )
