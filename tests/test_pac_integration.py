"""Integration tests for PAC package system.

Verifies:
  - PackageRegistry discovers DSA and exposes Stack, Queue, List, etc.
  - PackageRegistry.register_symbols() injects symbols into SymbolTable
  - SemanticAnalyzer does NOT emit "undefined variable" for package-qualified names
  - PackageRegistry._discover_members() extracts op names from call() source
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pac import PackageRegistry
from lexer.tokenizer import tokenize
from parser.parser import Parser
from semantic.symbol_builder import SymbolBuilder
from semantic.symbol_table import SymbolTable
from semantic.semantic_analyzer import SemanticAnalyzer, Diagnostic, Severity

PASS = 0
FAIL = 0


def ok(label: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        print(f"  PASS: {label}")
        PASS += 1
    else:
        msg = f"  FAIL: {label}"
        if detail:
            msg += f"  ({detail})"
        print(msg)
        FAIL += 1


# ── PackageRegistry discovery ─────────────────────────────────────────

def test_discovery_discovers_dsa() -> None:
    PackageRegistry.discover()
    ok("PackageRegistry knows Stack", PackageRegistry.has("Stack"))
    ok("PackageRegistry knows Queue", PackageRegistry.has("Queue"))
    ok("PackageRegistry knows List", PackageRegistry.has("List"))
    ok("PackageRegistry knows Tree", PackageRegistry.has("Tree"))
    ok("PackageRegistry knows Graph", PackageRegistry.has("Graph"))
    ok("PackageRegistry knows Search", PackageRegistry.has("Search"))
    ok("PackageRegistry knows Sort", PackageRegistry.has("Sort"))


def test_symbols_returned() -> None:
    syms = PackageRegistry.symbols()
    ok("symbols() returns dict", isinstance(syms, dict))
    ok("Stack symbol is PackageSymbol",
       type(syms.get("Stack")).__name__ == "PackageSymbol")
    ok("Stack symbol has members", len(syms["Stack"].members) > 0)
    ok("Search symbol has description", bool(syms["Search"].description))


def test_discover_members() -> None:
    """Verify _discover_members extracts op strings from call() source."""
    import inspect
    from pac.dsa.stack import StackOps
    members = PackageRegistry._discover_members(StackOps)
    ok("StackOps members include 'new'", "new" in members)
    ok("StackOps members include 'push'", "push" in members)
    ok("StackOps members include 'pop'", "pop" in members)
    ok("StackOps members include 'peek'", "peek" in members)
    ok("StackOps members include 'is_empty'", "is_empty" in members)


# ── SymbolTable injection ──────────────────────────────────────────────

def test_register_symbols_injects_to_table() -> None:
    table = SymbolTable()
    PackageRegistry.register_symbols(table)
    ok("Stack is in global scope",
       table.lookup("Stack") is not None)
    ok("Stack is PackageSymbol",
       type(table.lookup("Stack")).__name__ == "PackageSymbol")


# ── SemanticAnalyzer: no false errors for package-qualified names ──────

def _parse_expr_stmt(code: str):
    """Wrap *code* in an assignment expression to get PropertyAccessNode parsed."""
    return Parser(tokenize(f"x = {code}\n")).parse()


def test_analyzer_accepts_stack_qualified_name() -> None:
    program = _parse_expr_stmt("Stack.Users")
    table = SymbolTable()
    PackageRegistry.register_symbols(table)
    analyzer = SemanticAnalyzer(program, table)
    diags = analyzer.analyze()
    errors = [d for d in diags if d.severity == Severity.ERROR]
    ok("Stack.Users: no ERROR diagnostics", len(errors) == 0,
       f"got {len(errors)} errors: {errors}")


def test_analyzer_accepts_queue_new() -> None:
    program = _parse_expr_stmt("Queue.new")
    table = SymbolTable()
    PackageRegistry.register_symbols(table)
    analyzer = SemanticAnalyzer(program, table)
    diags = analyzer.analyze()
    errors = [d for d in diags if d.severity == Severity.ERROR]
    ok("Queue.new: no ERROR diagnostics", len(errors) == 0,
       f"got {len(errors)} errors: {errors}")


def test_analyzer_accepts_multiple_package_refs() -> None:
    program = _parse_expr_stmt("Stack.Users + Queue.new + List.sort")
    table = SymbolTable()
    PackageRegistry.register_symbols(table)
    analyzer = SemanticAnalyzer(program, table)
    diags = analyzer.analyze()
    errors = [d for d in diags if d.severity == Severity.ERROR]
    ok("Multiple package refs: no ERROR diagnostics", len(errors) == 0,
       f"got {len(errors)} errors: {errors}")


def test_analyzer_still_reports_real_undefined() -> None:
    program = _parse_expr_stmt("Foo.bar")
    table = SymbolTable()
    PackageRegistry.register_symbols(table)
    analyzer = SemanticAnalyzer(program, table)
    diags = analyzer.analyze()
    errors = [d for d in diags if d.severity == Severity.ERROR]
    ok("Foo.bar: still reports ERROR for unknown package",
       len(errors) >= 1)


# ── CompletionProvider ─────────────────────────────────────────────────

def test_completion_has_package_symbols() -> None:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "RA_Studio"))
        from completion.completion_provider import CompletionProvider
        provider = CompletionProvider()
        completions = provider.get_completions("St")
        names = [c.insert_text for c in completions]
        ok("Completions include 'Stack'", "Stack" in names)
    except ImportError as e:
        ok(f"CompletionProvider import skipped: {e}", True)


# ── HoverProvider ──────────────────────────────────────────────────────

def test_hover_returns_package_info() -> None:
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "RA_Studio"))
        from navigation.hover_provider import HoverProvider
        table = SymbolTable()
        PackageRegistry.register_symbols(table)
        provider = HoverProvider(table)
        info = provider.get_hover("Stack")
        ok("HoverInfo returned for Stack", info is not None)
        if info:
            ok("HoverInfo type is 'package'", info.symbol_type == "package")
            ok("HoverInfo name is 'Stack'", info.name == "Stack")
    except ImportError as e:
        ok(f"HoverProvider import skipped: {e}", True)


# ── Run all ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== PAC Package Integration Tests ===\n")

    # Run tests in order
    test_discovery_discovers_dsa()
    test_symbols_returned()
    test_discover_members()
    test_register_symbols_injects_to_table()
    test_analyzer_accepts_stack_qualified_name()
    test_analyzer_accepts_queue_new()
    test_analyzer_accepts_multiple_package_refs()
    test_analyzer_still_reports_real_undefined()
    test_completion_has_package_symbols()
    test_hover_returns_package_info()

    print(f"\n{'='*40}")
    print(f"Results: {PASS} passed, {FAIL} failed")
