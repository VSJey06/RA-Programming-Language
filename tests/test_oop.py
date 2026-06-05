"""Tests for RA v1.1.0 Phase 1 OOP features.

Covers:
  - OOP library activation
  - Constructor (Con: … con.close) auto-execution during object creation
  - Encapsulation (En: … en.close) private property blocking
  - Tokenization of new keywords
  - Parser validation
  - Constructor without OOP is no-op
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lexer.tokenizer import tokenize
from parser.parser import Parser, ParseError
from parser.ra_ast import dump
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

def test_parse_oop() -> None:
    src = "OOP\n"
    prog = Parser(tokenize(src)).parse()
    ok("OOP parses", len(prog.body) == 1)
    ok("OOP is OOPNode", prog.body[0].__class__.__name__ == "OOPNode")


def test_parse_constructor() -> None:
    src = "Con:\n  I x = 1\ncon.close\n"
    prog = Parser(tokenize(src)).parse()
    n = prog.body[0]
    ok("Con parses", n.__class__.__name__ == "ConstructorNode")
    ok("Con body has 1 stmt", len(n.body) == 1)


def test_parse_constructor_auto_close() -> None:
    src = "Con:\n  I x = 1\n"
    prog = Parser(tokenize(src)).parse()
    ok("Con auto close", prog.body[0].auto_close)


def test_parse_encapsulation() -> None:
    src = "En:\n  I secret = 42\nen.close\n"
    prog = Parser(tokenize(src)).parse()
    n = prog.body[0]
    ok("En parses", n.__class__.__name__ == "EncapsulationNode")
    ok("En body has 1 stmt", len(n.body) == 1)


def test_parse_encapsulation_auto_close() -> None:
    src = "En:\n  I x = 1\n"
    prog = Parser(tokenize(src)).parse()
    ok("En auto close", prog.body[0].auto_close)


def test_parse_full_oop_class() -> None:
    src = """OOP
@Cls.Car:
  I speed = 0
  En:
    I secret = 99
  en.close
  Con:
    I speed = 10
  con.close
@
"""
    prog = Parser(tokenize(src)).parse()
    car = prog.body[1]
    ok("Class has 3 members", len(car.members) == 3)
    ok("Member 0 is AssignmentNode",
       car.members[0].__class__.__name__ == "AssignmentNode")
    ok("Member 1 is EncapsulationNode",
       car.members[1].__class__.__name__ == "EncapsulationNode")
    ok("Member 2 is ConstructorNode",
       car.members[2].__class__.__name__ == "ConstructorNode")


def test_stray_con_close() -> None:
    try:
        Parser(tokenize("con.close\n")).parse()
        ok("stray con.close raises ParseError", False)
    except ParseError:
        ok("stray con.close raises ParseError", True)


def test_stray_en_close() -> None:
    try:
        Parser(tokenize("en.close\n")).parse()
        ok("stray en.close raises ParseError", False)
    except ParseError:
        ok("stray en.close raises ParseError", True)


# ── Runtime tests ─────────────────────────────────────────────────────────

def test_oop_activates() -> None:
    rt = Runtime()
    rt.execute(Parser(tokenize("OOP\n")).parse())
    ok("OOP activates", rt._oop_active)


def test_constructor_executes() -> None:
    src = """OOP
@Cls.Car:
  I speed = 0
  Con:
    I speed = 10
  con.close
@
Obj.Car.myCar
"""
    rt = Runtime()
    rt.execute(Parser(tokenize(src)).parse())
    obj = rt.object_registry.get("myCar")
    ok("Constructor set speed to 10", obj.get("speed") == 10)


def test_constructor_without_oop_is_noop() -> None:
    src = """@Cls.Car:
  I speed = 0
  Con:
    I speed = 10
  con.close
@
Obj.Car.myCar
"""
    rt = Runtime()
    rt.execute(Parser(tokenize(src)).parse())
    obj = rt.object_registry.get("myCar")
    ok("Without OOP speed stays 0", obj.get("speed") == 0)


def test_encapsulation_blocks_read() -> None:
    src = """OOP
@Cls.Car:
  En:
    I pin = 1234
  en.close
@
Obj.Car.myCar
"""
    rt = Runtime()
    rt.execute(Parser(tokenize(src)).parse())
    try:
        # Access private property from outside
        from parser.ra_ast import PropertyAccessNode, IdentifierNode
        rt.evaluate(
            PropertyAccessNode(
                object=IdentifierNode(name="myCar", line=99),
                property="pin",
                line=99,
            )
        )
        ok("encapsulation blocks read", False)
    except RAError as e:
        ok("encapsulation blocks read", "private" in str(e))


def test_encapsulation_blocks_write() -> None:
    src = """OOP
@Cls.Car:
  En:
    I pin = 0
  en.close
@
Obj.Car.myCar
"""
    rt = Runtime()
    rt.execute(Parser(tokenize(src)).parse())
    try:
        from parser.ra_ast import PropertyAssignmentNode
        rt.execute_node(
            PropertyAssignmentNode(
                object_name="myCar",
                property_name="pin",
                value=99,
                line=99,
            )
        )
        ok("encapsulation blocks write", False)
    except RAError as e:
        ok("encapsulation blocks write", "private" in str(e))


def test_constructor_sets_private_prop() -> None:
    src = """OOP
@Cls.Car:
  En:
    I pin = 0
  en.close
  Con:
    I pin = 4321
  con.close
@
Obj.Car.myCar
"""
    rt = Runtime()
    rt.execute(Parser(tokenize(src)).parse())
    obj = rt.object_registry.get("myCar")
    ok("Constructor sets private pin to 4321", obj.get("pin") == 4321)


def test_encapsulation_default_value() -> None:
    src = """OOP
@Cls.Car:
  En:
    I pin = 9999
  en.close
  Con:
  con.close
@
Obj.Car.myCar
"""
    rt = Runtime()
    rt.execute(Parser(tokenize(src)).parse())
    obj = rt.object_registry.get("myCar")
    ok("Private prop has default 9999", obj.get("pin") == 9999)


# ── Tokenizer tests ───────────────────────────────────────────────────────

def test_tokenize_oop() -> None:
    tokens = tokenize("OOP\n")
    ok("OOP is OOP", any(t.type.name == "OOP" for t in tokens))


def test_tokenize_con_close() -> None:
    tokens = tokenize("Con.close\n")
    ok("Con.close is CON_CLOSE",
       any(t.type.name == "CON_CLOSE" for t in tokens))


def test_tokenize_con_lowercase_close() -> None:
    tokens = tokenize("con.close\n")
    ok("con.close is also CON_CLOSE",
       any(t.type.name == "CON_CLOSE" for t in tokens))


def test_tokenize_en_close() -> None:
    tokens = tokenize("En.close\n")
    ok("En.close is EN_CLOSE",
       any(t.type.name == "EN_CLOSE" for t in tokens))


def test_tokenize_en_lowercase_close() -> None:
    tokens = tokenize("en.close\n")
    ok("en.close is also EN_CLOSE",
       any(t.type.name == "EN_CLOSE" for t in tokens))


def test_tokenize_con_colon() -> None:
    tokens = tokenize("Con:\n")
    names = [t.type.name for t in tokens]
    ok("Con: is CON COLON", names[:2] == ["CON", "COLON"])


def test_tokenize_en_colon() -> None:
    tokens = tokenize("En:\n")
    names = [t.type.name for t in tokens]
    ok("En: is EN COLON", names[:2] == ["EN", "COLON"])


# ── AST dump tests ────────────────────────────────────────────────────────

def test_ast_dump_oop() -> None:
    out = dump(Parser(tokenize("OOP\n")).parse())
    ok("AST dump has OOPNode", "OOPNode" in out)


def test_ast_dump_constructor() -> None:
    out = dump(Parser(tokenize("Con:\n  I x=1\ncon.close\n")).parse())
    ok("AST dump has ConstructorNode", "ConstructorNode" in out)


def test_ast_dump_encapsulation() -> None:
    out = dump(Parser(tokenize("En:\n  I x=1\nen.close\n")).parse())
    ok("AST dump has EncapsulationNode", "EncapsulationNode" in out)


# ── Run all ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("------------------------------------------------------------")
    print("OOP Phase 1 tests")
    print("------------------------------------------------------------")
    test_parse_oop()
    test_parse_constructor()
    test_parse_constructor_auto_close()
    test_parse_encapsulation()
    test_parse_encapsulation_auto_close()
    test_parse_full_oop_class()
    test_stray_con_close()
    test_stray_en_close()
    test_oop_activates()
    test_constructor_executes()
    test_constructor_without_oop_is_noop()
    test_encapsulation_blocks_read()
    test_encapsulation_blocks_write()
    test_constructor_sets_private_prop()
    test_encapsulation_default_value()
    test_tokenize_oop()
    test_tokenize_con_close()
    test_tokenize_con_lowercase_close()
    test_tokenize_en_close()
    test_tokenize_en_lowercase_close()
    test_tokenize_con_colon()
    test_tokenize_en_colon()
    test_ast_dump_oop()
    test_ast_dump_constructor()
    test_ast_dump_encapsulation()

    print("------------------------------------------------------------")
    print(f"Total: {PASS} passed, {FAIL} failed")
    print("------------------------------------------------------------")
    sys.exit(1 if FAIL else 0)
