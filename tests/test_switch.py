"""Tests for RA Key / case / def (switch) blocks.

Covers:
  - Parser: Switch block with cases
  - Parser: Switch with default
  - Parser: Switch with cases + default
  - Parser: Auto-close
  - Parser: Stray Key.close raises ParseError
  - Runtime: First matching case executes
  - Runtime: Default executes when no match
  - Runtime: String key matching
  - Runtime: Integer key matching
  - Runtime: Auto-stop after first match (no fall-through)
  - Tokenizer: Key, Key.close tokens
  - AST dump
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lexer.tokenizer import tokenize
from parser.parser import Parser, ParseError
from parser.ra_ast import SwitchNode, dump
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


# ── Parser tests ──────────────────────────────────────────────────────────

def test_parse_switch_cases() -> None:
    prog = Parser(tokenize(
        "Key.x:\n  c.1:\n    p 10\n  c.2:\n    p 20\nKey.close\n",
    )).parse()
    n = prog.body[0]
    ok("Switch parses", isinstance(n, SwitchNode))
    ok("Has 2 cases", len(n.cases) == 2)
    ok("No default", len(n.default_body) == 0)


def test_parse_switch_default() -> None:
    prog = Parser(tokenize(
        "Key.x:\n  def:\n    p 99\nKey.close\n",
    )).parse()
    n = prog.body[0]
    ok("Switch+default parses", isinstance(n, SwitchNode))
    ok("Has 0 cases", len(n.cases) == 0)
    ok("Has default", len(n.default_body) == 1)


def test_parse_switch_full() -> None:
    prog = Parser(tokenize(
        "Key.x:\n  c.1:\n    p 10\n  c.2:\n    p 20\n  def:\n    p 99\nKey.close\n",
    )).parse()
    n = prog.body[0]
    ok("Full switch parses", isinstance(n, SwitchNode))
    ok("Has 2 cases", len(n.cases) == 2)
    ok("Has default", len(n.default_body) == 1)


def test_parse_switch_auto_close() -> None:
    prog = Parser(tokenize("Key.x:\n  c.1:\n    p 10\n")).parse()
    ok("Switch auto close", prog.body[0].auto_close)


def test_stray_key_close() -> None:
    try:
        Parser(tokenize("Key.close\n")).parse()
        ok("Stray Key.close raises ParseError", False)
    except ParseError:
        ok("Stray Key.close raises ParseError", True)


# ── Tokenizer tests ───────────────────────────────────────────────────────

def test_token_key() -> None:
    names = [t.type.name for t in tokenize("Key.day:\n")]
    ok("Key.day: token sequence",
       names[:4] == ["KEY", "DOT", "IDENTIFIER", "COLON"])


def test_token_key_close() -> None:
    names = [t.type.name for t in tokenize("Key.close\n")]
    ok("Key.close is KEY_CLOSE", names[0] == "KEY_CLOSE")


# ── Runtime tests ─────────────────────────────────────────────────────────

def test_switch_integer_match() -> None:
    src = "I day = 2\nKey.day:\n  c.1:\n    p 10\n  c.2:\n    p 20\n  def:\n    p 30\nKey.close\n"
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok("Key=2 matches case 2", buf.getvalue().strip() == "20")


def test_switch_default() -> None:
    src = "I day = 99\nKey.day:\n  c.1:\n    p 10\n  c.2:\n    p 20\n  def:\n    p 99\nKey.close\n"
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok("No match uses default", buf.getvalue().strip() == "99")


def test_switch_no_fallthrough() -> None:
    """Only the first matching case executes."""
    src = "I x = 1\nKey.x:\n  c.1:\n    I z = 10\n  c.1:\n    I z = 20\nKey.close\np z\n"
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok("No fall-through (z=10)", buf.getvalue().strip() == "10")


def test_switch_string_key() -> None:
    src = 'S color = "red"\nKey.color:\n  c."red":\n    p 1\n  c."blue":\n    p 2\n  def:\n    p 3\nKey.close\n'
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok("String key match", buf.getvalue().strip() == "1")


def test_switch_expression_key() -> None:
    src = "I a = 5\nI b = 3\nKey.a+b:\n  c.8:\n    p 1\n  c.7:\n    p 2\n  def:\n    p 3\nKey.close\n"
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok("Expression key evaluates", buf.getvalue().strip() == "1")


# ── AST dump tests ────────────────────────────────────────────────────────

def test_ast_dump_switch() -> None:
    out = dump(Parser(tokenize(
        "Key.x:\n  c.1:\n    p 10\n  def:\n    p 99\nKey.close\n",
    )).parse())
    ok("AST dump has SwitchNode", "SwitchNode" in out)


# ── Run all ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("------------------------------------------------------------")
    print("Key / case / def (switch) tests")
    print("------------------------------------------------------------")
    test_parse_switch_cases()
    test_parse_switch_default()
    test_parse_switch_full()
    test_parse_switch_auto_close()
    test_stray_key_close()
    test_token_key()
    test_token_key_close()
    test_switch_integer_match()
    test_switch_default()
    test_switch_no_fallthrough()
    test_switch_string_key()
    test_switch_expression_key()
    test_ast_dump_switch()

    print("------------------------------------------------------------")
    print(f"Total: {PASS} passed, {FAIL} failed")
    print("------------------------------------------------------------")
    sys.exit(1 if FAIL else 0)
