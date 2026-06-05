"""Tests for .fun: local function blocks."""

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
    src = ".fun:\n  p.\"Hello\"\nf.close\n"
    prog = Parser(tokenize(src)).parse()
    ok(".fun: parses", len(prog.body) == 1)
    ok(".fun: is FunctionBlockNode", prog.body[0].__class__.__name__ == "FunctionBlockNode")
    ok(".fun: body has 1 stmt", len(prog.body[0].body) == 1)


def test_parse_implicit_close() -> None:
    src = ".fun:\n  I x = 1\n"
    prog = Parser(tokenize(src)).parse()
    ok(".fun: implicit close (EOF)", prog.body[0].auto_close)


def test_parse_explicit_close() -> None:
    src = ".fun:\n  I x = 1\nf.close\n"
    prog = Parser(tokenize(src)).parse()
    ok(".fun: explicit close", not prog.body[0].auto_close)


def test_stray_f_close() -> None:
    try:
        Parser(tokenize("f.close\n")).parse()
        ok("stray f.close raises ParseError", False)
    except ParseError:
        ok("stray f.close raises ParseError", True)


# ── Runtime tests ─────────────────────────────────────────────────────────

import io

def test_exec_basic() -> None:
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(".fun:\n  p.42\nf.close\n")).parse())
    sys.stdout = sys.__stdout__
    ok(".fun: prints 42", buf.getvalue().strip() == "42")


def test_exec_add() -> None:
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(".fun:\n  I a=20\n  I b=50\n  p a+b\nf.close\n")).parse())
    sys.stdout = sys.__stdout__
    ok(".fun: prints a+b=70", buf.getvalue().strip() == "70")


def test_local_scope_isolation() -> None:
    rt = Runtime()
    rt.execute(Parser(tokenize(".fun:\n  I x=5\nf.close\n")).parse())
    try:
        rt.execute(Parser(tokenize("p x\n")).parse())
        ok("local scope isolation: raises error", False)
    except RAError as e:
        ok("local scope isolation: raises RuntimeError",
           "is not defined" in str(e))


def test_nested_in_run() -> None:
    buf = io.StringIO()
    sys.stdout = buf
    src = ".run:\n  .fun:\n    I a=10\n    I b=20\n    p a+b\n  f.close\nr.close\n"
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok(".run: nested .fun: prints 30", buf.getvalue().strip() == "30")


def test_nested_fun_in_fun() -> None:
    buf = io.StringIO()
    sys.stdout = buf
    src = ".fun:\n  I outer=1\n  .fun:\n    I inner=2\n    p outer\n  f.close\nf.close\n"
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok("nested .fun: outer visible in inner", buf.getvalue().strip() == "1")


def test_outer_var_not_leaked() -> None:
    rt = Runtime()
    with io.StringIO() as buf:
        sys.stdout = buf
        rt.execute(Parser(tokenize(".fun:\n  I temp=100\n  p temp\nf.close\n")).parse())
        sys.stdout = sys.__stdout__
    try:
        rt.execute(Parser(tokenize("p temp\n")).parse())
        ok("temp var not leaked after f.close", False)
    except RAError:
        ok("temp var not leaked after f.close", True)


def test_fun_in_for_loop() -> None:
    buf = io.StringIO()
    sys.stdout = buf
    src = ".fun:\n  ? For.i=1;4,\n    .fun:\n      p.i\n    f.close\n  #\nf.close\n"
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok(".fun: in for loop prints 1\\n2\\n3", buf.getvalue().strip() == "1\n2\n3")


def test_fun_in_condition() -> None:
    buf = io.StringIO()
    sys.stdout = buf
    src = ".fun:\n  I a=10\n  ! If.a>5,\n    .fun:\n      p.\"big\"\n    f.close\n  #\nf.close\n"
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok(".fun: in if prints big", buf.getvalue().strip() == "big")


# ── AutoCloser tests ──────────────────────────────────────────────────────

def test_autoclose_valid() -> None:
    AutoCloser().validate(".fun:\n  p.\"x\"\nf.close\n")
    ok("AutoCloser .fun: valid", True)


def test_autoclose_missing_close() -> None:
    try:
        AutoCloser().validate(".fun:\n  p.\"x\"\n")
        ok("AutoCloser missing f.close", False)
    except SyntaxError:
        ok("AutoCloser missing f.close", True)


def test_autoclose_nested_run() -> None:
    closed = ".run:\n  .fun:\n    p.\"hi\"\n  f.close\nr.close\n"
    AutoCloser().validate(closed)
    ok("AutoCloser nested .run/.fun valid", True)


# ── Tokenizer tests ───────────────────────────────────────────────────────

def test_tokenize_fclose() -> None:
    tokens = tokenize("f.close\n")
    ok("f.close is FUN_CLOSE", any(t.type.name == "FUN_CLOSE" for t in tokens))


def test_tokenize_dot_fun() -> None:
    tokens = tokenize(".fun:\n")
    names = [t.type.name for t in tokens]
    ok(".fun: produces DOT,IDENTIFIER,COLON",
       names[:3] == ["DOT", "IDENTIFIER", "COLON"])


# ── AST dump tests ────────────────────────────────────────────────────────

def test_ast_dump() -> None:
    prog = Parser(tokenize(".fun:\n  I x=1\nf.close\n")).parse()
    out = dump(prog)
    ok("AST dump contains FunctionBlockNode", "FunctionBlockNode" in out)
    ok("AST dump shows stmts=1", "stmts=1" in out)


# ── Run all ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("------------------------------------------------------------")
    print("FunctionBlock (.fun:) tests")
    print("------------------------------------------------------------")
    test_parse_basic()
    test_parse_implicit_close()
    test_parse_explicit_close()
    test_stray_f_close()
    test_exec_basic()
    test_exec_add()
    test_local_scope_isolation()
    test_nested_in_run()
    test_nested_fun_in_fun()
    test_outer_var_not_leaked()
    test_fun_in_for_loop()
    test_fun_in_condition()
    test_autoclose_valid()
    test_autoclose_missing_close()
    test_autoclose_nested_run()
    test_tokenize_fclose()
    test_tokenize_dot_fun()
    test_ast_dump()

    print("------------------------------------------------------------")
    print(f"Total: {PASS} passed, {FAIL} failed")
    print("------------------------------------------------------------")
    sys.exit(1 if FAIL else 0)
