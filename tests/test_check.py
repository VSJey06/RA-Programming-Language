"""Tests for RA Check / Valid / Invalid error-handling blocks.

Covers:
  - Parser: Check block parses correctly
  - Parser: Valid section
  - Parser: Invalid section
  - Parser: Valid + Invalid together
  - Parser: Auto-close at EOF
  - Parser: Stray Check.close raises ParseError
  - Runtime: Error triggers Invalid block with 'error' variable
  - Runtime: Success triggers Valid block
  - Runtime: No Valid/Invalid sections (bare Check)
  - Runtime: Error message in 'error' variable
  - Tokenizer: Check, Valid, Invalid, Check.close tokens
  - AST dump
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lexer.tokenizer import tokenize
from parser.parser import Parser, ParseError
from parser.ra_ast import CheckNode, dump
from runtime.runtime import Runtime
from runtime.runtime import RuntimeError as RAError

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


# ── Parser tests ──────────────────────────────────────────────────────────

def test_parse_check_bare() -> None:
    prog = Parser(tokenize("Check:\n  p 1\nCheck.close\n")).parse()
    n = prog.body[0]
    ok("Bare Check parses", isinstance(n, CheckNode))
    ok("Body has 1 stmt", len(n.body) == 1)
    ok("No valid_body", len(n.valid_body) == 0)
    ok("No invalid_body", len(n.invalid_body) == 0)
    ok("Not auto_close", not n.auto_close)


def test_parse_check_valid() -> None:
    prog = Parser(tokenize(
        "Check:\n  p 1\nValid:\n  p 2\nCheck.close\n",
    )).parse()
    n = prog.body[0]
    ok("Check+Valid parses", isinstance(n, CheckNode))
    ok("Body has 1 stmt", len(n.body) == 1)
    ok("Valid has 1 stmt", len(n.valid_body) == 1)
    ok("No invalid", len(n.invalid_body) == 0)


def test_parse_check_invalid() -> None:
    prog = Parser(tokenize(
        "Check:\n  p 1\nInvalid:\n  p.error\nCheck.close\n",
    )).parse()
    n = prog.body[0]
    ok("Check+Invalid parses", isinstance(n, CheckNode))
    ok("Body has 1 stmt", len(n.body) == 1)
    ok("No valid", len(n.valid_body) == 0)
    ok("Invalid has 1 stmt", len(n.invalid_body) == 1)


def test_parse_check_both() -> None:
    prog = Parser(tokenize(
        "Check:\n  p 1\nValid:\n  p 2\nInvalid:\n  p.error\nCheck.close\n",
    )).parse()
    n = prog.body[0]
    ok("Check+Valid+Invalid parses", isinstance(n, CheckNode))
    ok("Body has 1 stmt", len(n.body) == 1)
    ok("Valid has 1 stmt", len(n.valid_body) == 1)
    ok("Invalid has 1 stmt", len(n.invalid_body) == 1)


def test_parse_check_auto_close() -> None:
    prog = Parser(tokenize("Check:\n  p 1\n")).parse()
    ok("Check auto close", prog.body[0].auto_close)


def test_stray_check_close() -> None:
    try:
        Parser(tokenize("Check.close\n")).parse()
        ok("Stray Check.close raises ParseError", False)
    except ParseError:
        ok("Stray Check.close raises ParseError", True)


# ── Tokenizer tests ───────────────────────────────────────────────────────

def test_token_check() -> None:
    names = [t.type.name for t in tokenize("Check:\n")]
    ok("Check: is CHECK COLON", names[:2] == ["CHECK", "COLON"])


def test_token_check_close() -> None:
    names = [t.type.name for t in tokenize("Check.close\n")]
    ok("Check.close is CHECK_CLOSE", names[0] == "CHECK_CLOSE")


def test_token_valid() -> None:
    names = [t.type.name for t in tokenize("Valid:\n")]
    ok("Valid: is VALID COLON", names[:2] == ["VALID", "COLON"])


def test_token_invalid() -> None:
    names = [t.type.name for t in tokenize("Invalid:\n")]
    ok("Invalid: is INVALID COLON", names[:2] == ["INVALID", "COLON"])


# ── Runtime tests ─────────────────────────────────────────────────────────

def test_check_error_triggers_invalid() -> None:
    src = "Check:\n  p.unknown\nInvalid:\n  p.error\nCheck.close\n"
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    out = buf.getvalue().strip()
    ok("Error triggers Invalid", "RuntimeError" in out or "not defined" in out)


def test_check_success_triggers_valid() -> None:
    src = "Check:\n  I x = 10\nValid:\n  p x\nInvalid:\n  p.error\nCheck.close\n"
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok("Success triggers Valid", buf.getvalue().strip() == "10")


def test_check_bare_success() -> None:
    src = "Check:\n  p 7\nCheck.close\n"
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok("Bare Check executes body", buf.getvalue().strip() == "7")


def test_error_variable_scope() -> None:
    """The 'error' variable should not leak outside the Invalid block."""
    src = "Check:\n  p.unknown\nInvalid:\n  p.error\nCheck.close\n"
    rt = Runtime()
    rt.execute(Parser(tokenize(src)).parse())
    ok("error not in global scope",
       "error" not in rt.global_scope)


def test_check_syntax_error_caught() -> None:
    """Check block should catch ParseError too."""
    # A variable that doesn't exist triggers RuntimeError
    src = "Check:\n  x = 1\n  p y\nInvalid:\n  p 99\nCheck.close\n"
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok("RuntimeError caught by Invalid", buf.getvalue().strip() == "99")


# ── AST dump tests ────────────────────────────────────────────────────────

def test_ast_dump_check() -> None:
    out = dump(Parser(tokenize(
        "Check:\n  p 1\nValid:\n  p 2\nInvalid:\n  p.error\nCheck.close\n",
    )).parse())
    ok("AST dump has CheckNode", "CheckNode" in out)


# ── Run all ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("------------------------------------------------------------")
    print("Check / Valid / Invalid tests")
    print("------------------------------------------------------------")
    test_parse_check_bare()
    test_parse_check_valid()
    test_parse_check_invalid()
    test_parse_check_both()
    test_parse_check_auto_close()
    test_stray_check_close()
    test_token_check()
    test_token_check_close()
    test_token_valid()
    test_token_invalid()
    test_check_error_triggers_invalid()
    test_check_success_triggers_valid()
    test_check_bare_success()
    test_error_variable_scope()
    test_check_syntax_error_caught()
    test_ast_dump_check()

    print("------------------------------------------------------------")
    print(f"Total: {PASS} passed, {FAIL} failed")
    print("------------------------------------------------------------")
    sys.exit(1 if FAIL else 0)
