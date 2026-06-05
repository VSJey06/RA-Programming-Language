"""Tests for .run: immediate execution blocks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lexer.tokenizer import tokenize
from parser.parser import Parser, ParseError
from parser.ra_ast import dump
from runtime.runtime import Runtime
from runtime.runtime import RuntimeError as RAError
from runtime.autoclose import AutoCloser

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

def test_parse_basic() -> None:
    src = ".run:\n  p.\"Hello\"\nr.close\n"
    prog = Parser(tokenize(src)).parse()
    ok(".run: parses", len(prog.body) == 1)
    ok(".run: is RunBlockNode", prog.body[0].__class__.__name__ == "RunBlockNode")
    ok(".run: body has 1 stmt", len(prog.body[0].body) == 1)


def test_parse_for_loop() -> None:
    src = ".run:\n  ? For.i=1;4,\n    p.i\n  #\nr.close\n"
    prog = Parser(tokenize(src)).parse()
    ok(".run: for loop body has 1 stmt", len(prog.body[0].body) == 1)


def test_parse_if_condition() -> None:
    src = ".run:\n  I a=10\n  ! If.a>5,\n    p.\"big\"\n  #\nr.close\n"
    prog = Parser(tokenize(src)).parse()
    ok(".run: with if body has 2 stmts", len(prog.body[0].body) == 2)


def test_parse_implicit_close() -> None:
    src = ".run:\n  I x = 1\n"
    prog = Parser(tokenize(src)).parse()
    ok(".run: implicit close (EOF)", prog.body[0].auto_close)


def test_stray_dot() -> None:
    try:
        Parser(tokenize(".something\n")).parse()
        ok("stray DOT raises ParseError", False)
    except ParseError:
        ok("stray DOT raises ParseError", True)


def test_stray_r_close() -> None:
    try:
        Parser(tokenize("r.close\n")).parse()
        ok("stray r.close raises ParseError", False)
    except ParseError:
        ok("stray r.close raises ParseError", True)


# ── Runtime tests ─────────────────────────────────────────────────────────

import io

def test_exec_basic() -> None:
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(".run:\n  p.\"Hello\"\nr.close\n")).parse())
    sys.stdout = sys.__stdout__
    ok(".run: prints Hello", buf.getvalue().strip() == "Hello")


def test_exec_for() -> None:
    buf = io.StringIO()
    sys.stdout = buf
    src = ".run:\n  ? For.i=1;4,\n    p.i\n  #\nr.close\n"
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok(".run: for prints 1\\n2\\n3", buf.getvalue().strip() == "1\n2\n3")


def test_exec_assignment() -> None:
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(".run:\n  I x = 42\n  p x\nr.close\n")).parse())
    sys.stdout = sys.__stdout__
    ok(".run: prints 42", buf.getvalue().strip() == "42")


def test_exec_if_condition() -> None:
    buf = io.StringIO()
    sys.stdout = buf
    src = ".run:\n  I a=10\n  I b=5\n  ! If.a>b,\n    p.\"a wins\"\n  #\nr.close\n"
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok(".run: if prints a wins", buf.getvalue().strip() == "a wins")


def test_exec_nested_db() -> None:
    buf = io.StringIO()
    sys.stdout = buf
    src = ".run:\n  Db.Test:\n    S name=\"X\"\n  db.close\n  I v=1\n  p v\nr.close\n"
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok(".run: Db nested prints 1", buf.getvalue().strip() == "1")


# ── AutoCloser tests ──────────────────────────────────────────────────────

def test_autoclose_valid() -> None:
    AutoCloser().validate(".run:\n  p.\"x\"\nr.close\n")
    ok("AutoCloser .run: valid", True)


def test_autoclose_missing_close() -> None:
    try:
        AutoCloser().validate(".run:\n  p.\"x\"\n")
        ok("AutoCloser missing r.close", False)
    except SyntaxError:
        ok("AutoCloser missing r.close", True)


def test_autoclose_nested() -> None:
    closed = ".run:\n  Db.Test:\n    S n=\"a\"\n  db.close\nr.close\n"
    AutoCloser().validate(closed)
    ok("AutoCloser nested valid", True)


# ── Run all ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("------------------------------------------------------------")
    print("RunBlock (.run:) tests")
    print("------------------------------------------------------------")
    test_parse_basic()
    test_parse_for_loop()
    test_parse_if_condition()
    test_parse_implicit_close()
    test_stray_dot()
    test_stray_r_close()
    test_exec_basic()
    test_exec_for()
    test_exec_assignment()
    test_exec_if_condition()
    test_exec_nested_db()
    test_autoclose_valid()
    test_autoclose_missing_close()
    test_autoclose_nested()

    print("------------------------------------------------------------")
    print(f"Total: {PASS} passed, {FAIL} failed")
    print("------------------------------------------------------------")
    sys.exit(1 if FAIL else 0)
