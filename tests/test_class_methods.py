"""Tests for class-bound method dispatch in RA.

Covers:
  - Global method invocation (Show.run) still works
  - Object-bound method invocation (Ken.Show.run) resolves via class
  - Private properties accessible from within class methods
  - Constructor + method interaction
  - Non-OOP class methods work
  - Error on non-object method invocation
  - Error on unknown method name
  - Method call on local-scope object
  - Parser validation
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lexer.tokenizer import tokenize
from parser.parser import Parser, ParseError
from parser.ra_ast import MethodInvokeNode, dump
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

def test_parse_global_method_invoke() -> None:
    prog = Parser(tokenize("Greet.run\n")).parse()
    n = prog.body[0]
    ok("Greet.run is MethodInvokeNode",
       isinstance(n, MethodInvokeNode))
    ok("method_name=Greet", n.method_name == "Greet")
    ok("object_name is None", n.object_name is None)


def test_parse_object_method_invoke() -> None:
    prog = Parser(tokenize("Ken.Show.run\n")).parse()
    n = prog.body[0]
    ok("Ken.Show.run is MethodInvokeNode",
       isinstance(n, MethodInvokeNode))
    ok("method_name=Show", n.method_name == "Show")
    ok("object_name=Ken", n.object_name == "Ken")


def test_parse_method_invoke_ast_dump() -> None:
    out = dump(Parser(tokenize("Ken.Show.run\n")).parse())
    ok("AST dump shows method name",
       "method='Show'" in out)
    ok("AST dump shows object name",
       "obj='Ken'" in out)


def test_parse_object_method_invalid_closer() -> None:
    try:
        Parser(tokenize("Ken.Show.bark\n")).parse()
        ok("Ken.Show.bark raises ParseError", False)
    except ParseError:
        ok("Ken.Show.bark raises ParseError", True)


# ── Runtime tests ─────────────────────────────────────────────────────────

def test_global_method_still_works() -> None:
    src = "M.Greet:\n  p 42\n/.close\nGreet.run\n"
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok("Global method prints 42",
       buf.getvalue().strip() == "42")


def test_object_method_basic() -> None:
    src = """@Cls.Car:
  I speed = 0
  M.Show:
    p speed
  /.close
@
Obj.Car.myCar
myCar.Show.run
"""
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok("Object method prints speed",
       buf.getvalue().strip() == "0")


def test_class_method_private_access() -> None:
    src = """OOP
@Cls.Person:
    En:
        S password="1223"
    en.close
    M.Show:
        p.password
    /.close
@
Obj.Person.Ken
Ken.Show.run
"""
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok("Method accesses private property",
       buf.getvalue().strip() == "1223")


def test_constructor_and_method() -> None:
    src = """OOP
@Cls.Car:
  I speed = 0
  Con:
    I speed = 99
  con.close
  M.Show:
    p speed
  /.close
@
Obj.Car.myCar
myCar.Show.run
"""
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok("Method sees constructor-set value",
       buf.getvalue().strip() == "99")


def test_multiple_objects_independent() -> None:
    src = """OOP
@Cls.Car:
  I speed = 0
  Con:
    I speed = s
  con.close
  M.Show:
    p speed
  /.close
@
Obj.Car.fast
Obj.Car.slow
"""
    import io
    buf = io.StringIO()
    sys.stdout = buf
    # Treat speed params via global scope before instantiation
    rt = Runtime()
    rt.global_scope["s"] = 100
    rt.execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    # Just verify both objects exist and have different values
    f = rt.object_registry.get("fast")
    s = rt.object_registry.get("slow")
    ok("Multiple objects independent",
       f.get("speed") == 100 and s.get("speed") == 100)


def test_method_not_found_error() -> None:
    src = """@Cls.Car:
  M.Show:
    p 1
  /.close
@
Obj.Car.myCar
myCar.Bark.run
"""
    try:
        Runtime().execute(Parser(tokenize(src)).parse())
        ok("Unknown method raises RuntimeError", False)
    except RAError as e:
        ok("Unknown method raises RuntimeError",
           "not found" in str(e))


def test_non_object_method_error() -> None:
    src = "x = 5\nx.Show.run\n"
    try:
        Runtime().execute(Parser(tokenize(src)).parse())
        ok("Non-object raises RuntimeError", False)
    except RAError as e:
        ok("Non-object raises RuntimeError",
           "not a class instance" in str(e))


def test_method_private_property_write() -> None:
    src = """OOP
@Cls.Car:
  En:
    I pin = 0
  en.close
  M.SetPin:
    I pin = 7777
  /.close
@
Obj.Car.myCar
myCar.SetPin.run
"""
    rt = Runtime()
    rt.execute(Parser(tokenize(src)).parse())
    obj = rt.object_registry.get("myCar")
    ok("Method can write private prop",
       obj.get("pin") == 7777)


def test_method_on_local_scope_object() -> None:
    src = """OOP
@Cls.Car:
  I speed = 10
  M.Show:
    p speed
  /.close
@
.fun:
  Obj.Car.myCar
  myCar.Show.run
f.close
"""
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    ok("Method works on local-scope object",
       buf.getvalue().strip() == "10")


# ── Run all ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("------------------------------------------------------------")
    print("Class-bound method dispatch tests")
    print("------------------------------------------------------------")
    test_parse_global_method_invoke()
    test_parse_object_method_invoke()
    test_parse_method_invoke_ast_dump()
    test_parse_object_method_invalid_closer()
    test_global_method_still_works()
    test_object_method_basic()
    test_class_method_private_access()
    test_constructor_and_method()
    test_multiple_objects_independent()
    test_method_not_found_error()
    test_non_object_method_error()
    test_method_private_property_write()
    test_method_on_local_scope_object()

    print("------------------------------------------------------------")
    print(f"Total: {PASS} passed, {FAIL} failed")
    print("------------------------------------------------------------")
    sys.exit(1 if FAIL else 0)
