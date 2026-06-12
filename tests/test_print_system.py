"""Runtime tests for Print System Enhancement.

Covers:
  - p.expr syntax (p.Users.size)
  - p expr syntax (p Users.size)
  - pl expr (print without newline)
  - pl.expr syntax
  - Mixed pl and p
  - Newline control
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lexer.tokenizer import tokenize
from parser.parser import Parser
from runtime.runtime import Runtime

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


def parse(code: str):
    """Parse *code* and return the AST."""
    return Parser(tokenize(code)).parse()


def node_type(code: str) -> str:
    """Return the type name of the first statement node."""
    prog = parse(code)
    return type(prog.body[0]).__name__


def print_node_details(code: str):
    """Return (no_newline, value_type) of the first statement's PrintNode."""
    prog = parse(code)
    pn = prog.body[0]
    return (pn.no_newline, type(pn.value).__name__)


# ── Feature 1: Dual print syntax ─────────────────────────────────

def test_p_expr_parses() -> None:
    ok("p Users.size parses",
       node_type("p Users.size\n") == "PrintNode")


def test_p_dot_expr_parses() -> None:
    ok("p.Users.size parses",
       node_type("p.Users.size\n") == "PrintNode")


def test_p_string_parses() -> None:
    ok('p "Hello" parses',
       node_type('p "Hello"\n') == "PrintNode")


def test_p_value_parses() -> None:
    ok("p value parses",
       node_type("p value\n") == "PrintNode")


def test_p_db_expr_parses() -> None:
    ok("p Database.Personal parses",
       node_type("p Database.Personal\n") == "PrintNode")


def test_both_forms_have_no_newline_false() -> None:
    _, vt1 = print_node_details("p Users.size\n")
    _, vt2 = print_node_details("p.Users.size\n")
    ok("p expr no_newline=False",
       print_node_details("p Users.size\n")[0] is False)
    ok("p.expr no_newline=False",
       print_node_details("p.Users.size\n")[0] is False)


# ── Feature 2: Print Line (pl) ───────────────────────────────────

def test_pl_expr_parses() -> None:
    ok("pl expr parses",
       node_type("pl value\n") == "PrintNode")


def test_pl_dot_expr_parses() -> None:
    ok("pl.expr parses",
       node_type("pl.value\n") == "PrintNode")


def test_pl_has_no_newline_true() -> None:
    ok("pl expr no_newline=True",
       print_node_details("pl value\n")[0] is True)
    ok("pl.expr no_newline=True",
       print_node_details("pl.value\n")[0] is True)


def test_pl_string_parses() -> None:
    ok('pl "Hello" parses',
       node_type('pl "Hello"\n') == "PrintNode")


# ── Feature 3 & 4: Runtime behavior ──────────────────────────────

def _capture(code: str) -> str:
    """Parse and execute *code*, capturing stdout."""
    import io, contextlib
    rt = Runtime()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rt.execute(parse(code))
    return buf.getvalue()


def test_p_prints_with_newline() -> None:
    out = _capture('p "Hello"\n')
    ok("p prints with newline", out == "Hello\n")


def test_pl_prints_without_newline() -> None:
    out = _capture('pl "Hello"\np ""\n')
    ok("pl prints without newline", out == "Hello\n")


def test_pl_pl_p_abc() -> None:
    out = _capture('pl "A"\npl "B"\npl "C"\np ""\n')
    ok("ABC output", out == "ABC\n")


def test_mixed_pl_and_p() -> None:
    out = _capture('pl "Hello "\npl "World"\np ""\n')
    ok("Hello World output", out == "Hello World\n")


def test_pl_with_dot_syntax() -> None:
    code = 'pl "Hello "\npl."World"\np ""\n'
    out = _capture(code)
    ok("pl.dot works", out == "Hello World\n")


def test_p_with_value_variable() -> None:
    out = _capture("I x = 42\np x\n")
    ok("p value prints 42", out == "42\n")


# ── Run all ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Print System Enhancement Tests ===\n")

    test_p_expr_parses()
    test_p_dot_expr_parses()
    test_p_string_parses()
    test_p_value_parses()
    test_p_db_expr_parses()
    test_both_forms_have_no_newline_false()
    test_pl_expr_parses()
    test_pl_dot_expr_parses()
    test_pl_has_no_newline_true()
    test_pl_string_parses()
    test_p_prints_with_newline()
    test_pl_prints_without_newline()
    test_pl_pl_p_abc()
    test_mixed_pl_and_p()
    test_pl_with_dot_syntax()
    test_p_with_value_variable()

    print(f"\n{'='*40}")
    print(f"Results: {PASS} passed, {FAIL} failed")
