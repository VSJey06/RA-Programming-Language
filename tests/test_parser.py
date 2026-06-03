"""Regression tests for the RA recursive-descent parser.

Covers all block constructs, auto-close semantics, structural boundaries,
For ranges, property access chains, nested constructs, and error handling.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lexer.tokenizer import tokenize
from lexer.tokens import TokenType
from parser.parser import Parser, ParseError
from parser.ra_ast import (
    DbNode,
    MethodNode,
    ClassNode,
    IfNode,
    ElseIfNode,
    ElseNode,
    ForNode,
    WhileNode,
    PrintNode,
    AssignmentNode,
    BinaryOpNode,
    PropertyAccessNode,
    ObjectNode,
    IdentifierNode,
    LiteralNode,
    ProgramNode,
    Node,
    NodeVisitor,
    dump,
)


def parse(src: str) -> ProgramNode:
    return Parser(tokenize(src)).parse()


def first(prog: ProgramNode) -> Node:
    return prog.body[0]


PASS = 0
FAIL = 0


def ok(label: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS: {label}")
    else:
        FAIL += 1
        msg = f"  FAIL: {label}" + (f"  -- {detail}" if detail else "")
        print(msg)


# ---------------------------------------------------------------------------
# 1. Db block -- explicit & auto close
# ---------------------------------------------------------------------------
print("-" * 60)
print("1. Db block")
print("-" * 60)

prog = parse("@Db:\n  p \"hello\"\ndb.close\n")
n = first(prog)
ok("Db explicit close", isinstance(n, DbNode) and not n.auto_close)

prog = parse("@Db:\n  p \"hello\"\n")
n = first(prog)
ok("Db implicit close (EOF)", isinstance(n, DbNode) and n.auto_close)

prog = parse("@Db:\n  p \"a\"\n@Db:\n  p \"b\"\ndb.close\n")
outer = prog.body[0]
ok("Nested Db inside Db", isinstance(outer, DbNode) and outer.auto_close
   and len(outer.body) == 2 and isinstance(outer.body[1], DbNode)
   and not outer.body[1].auto_close)

prog = parse("Db:\n  p \"ok\"\ndb.close\n")
n = first(prog)
ok("Db bare (no @ prefix)", isinstance(n, DbNode) and n.name == "db" and not n.auto_close)

# ---------------------------------------------------------------------------
# 2. Class block -- explicit & auto close
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("2. Class block")
print("-" * 60)

prog = parse("@Cls.Car:\n  p \"ok\"\n@\n")
n = first(prog)
ok("Class explicit @", isinstance(n, ClassNode) and n.name == "Car" and not n.auto_close)

prog = parse("@Cls.Car:\n  p \"ok\"\n")
n = first(prog)
ok("Class implicit close (EOF)", isinstance(n, ClassNode) and n.name == "Car" and n.auto_close)

prog = parse("@Cls.Car:\n  p \"a\"\n@Cls.Bike:\n  p \"b\"\n@\n")
ok("Class auto-closed by sibling", len(prog.body) == 2)
n0 = prog.body[0]
ok("Car auto_close=True (sibling boundary)", isinstance(n0, ClassNode) and n0.name == "Car" and n0.auto_close)
n1 = prog.body[1]
ok("Bike explicit @", isinstance(n1, ClassNode) and n1.name == "Bike" and not n1.auto_close)

# ---------------------------------------------------------------------------
# 3. Method -- explicit & auto close
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("3. Method")
print("-" * 60)

prog = parse("@Db:\n  M.drive:\n    p \"vroom\"\n  /\n")
db = first(prog)
m = db.body[0]
ok("Method explicit /", isinstance(m, MethodNode) and m.name == "drive" and not m.auto_close)

prog = parse("@Db:\n  M.drive:\n    p \"vroom\"\n")
db = first(prog)
m = db.body[0]
ok("Method implicit close (EOF)", isinstance(m, MethodNode) and m.name == "drive" and m.auto_close)

prog = parse("@Db:\n  M.drive:\n    p \"a\"\n  M.honk:\n    p \"beep\"\n  /\n")
db = first(prog)
drive = db.body[0]
ok("Nested methods in Db", isinstance(drive, MethodNode) and drive.name == "drive" and drive.auto_close)
ok("drive body has 2 stmts (p + nested honk)", len(drive.body) == 2)
honk = drive.body[1]
ok("honk is nested method", isinstance(honk, MethodNode) and honk.name == "honk" and not honk.auto_close)

# ---------------------------------------------------------------------------
# 4. If / ElseIf / Else chains
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("4. If / ElseIf / Else")
print("-" * 60)

prog = parse("! If.x > 5,\n  p \"big\"\n#\n")
n = first(prog)
ok("If only", isinstance(n, IfNode) and not n.has_elseifs and not n.has_else)

prog = parse("! If.x > 5,\n  p \"big\"\n#\n! Else\n  p \"small\"\n#\n")
n = first(prog)
ok("If with Else", isinstance(n, IfNode) and not n.has_elseifs and n.has_else)

prog = parse("! If.x < 3,\n  p \"low\"\n#\n!! x < 7,\n  p \"mid\"\n#\n!! x < 10,\n  p \"high\"\n#\n")
n = first(prog)
ok("Chained ElseIf (count)", isinstance(n, IfNode) and len(n.elseifs) == 2)
ok("Chained ElseIf no else", isinstance(n, IfNode) and not n.has_else)

prog = parse("! If.x < 3,\n  p \"low\"\n#\n!! x < 7,\n  p \"mid\"\n#\n! Else\n  p \"big\"\n#\n")
n = first(prog)
ok("Full chain: If + ElseIf + Else", isinstance(n, IfNode)
   and len(n.elseifs) == 1 and n.has_else)

prog = parse("@Db:\n  M.drive:\n    ! If.x > 5,\n      p \"fast\"\n    #\n  /\n")
db = first(prog)
m = db.body[0]
inner_if = m.body[0]
ok("If inside method body", isinstance(inner_if, IfNode))

# ---------------------------------------------------------------------------
# 5. For / While loops
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("5. For / While loops")
print("-" * 60)

prog = parse("? For.i=0;10,\n  p \"loop\"\n#\n")
n = first(prog)
ok("For loop type", isinstance(n, ForNode))
ok("For loop variable", isinstance(n, ForNode) and n.variable == "i")
ok("For range is BinaryOp", isinstance(n.iterable, BinaryOpNode))
ok("For range operator ';'", isinstance(n.iterable, BinaryOpNode) and n.iterable.operator == ";")
ok("For range left 0", isinstance(n.iterable, BinaryOpNode)
   and isinstance(n.iterable.left, LiteralNode) and n.iterable.left.value == 0)
ok("For range right 10", isinstance(n.iterable, BinaryOpNode)
   and isinstance(n.iterable.right, LiteralNode) and n.iterable.right.value == 10)

prog = parse("? While.x < 10,\n  p \"loop\"\n#\n")
n = first(prog)
ok("While loop type", isinstance(n, WhileNode))

prog = parse("@Db:\n  M.go:\n    ? For.i=0;3,\n      p i\n    #\n  /\n")
db = first(prog)
m = db.body[0]
inner_for = m.body[0]
ok("For inside method body", isinstance(inner_for, ForNode))

# ---------------------------------------------------------------------------
# 6. For range with expression boundaries
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("6. For range expressions")
print("-" * 60)

prog = parse("? For.i= 1 + 2 ; 10 - 3 ,\n  p i\n#\n")
n = first(prog)
ok("For range complex start", isinstance(n, ForNode))
ok("For range start BinaryOp", isinstance(n.iterable, BinaryOpNode) and n.iterable.operator == ";")
start = n.iterable.left
end = n.iterable.right
ok("For start is 1+2", isinstance(start, BinaryOpNode) and start.operator == "+"
   and isinstance(start.left, LiteralNode) and start.left.value == 1
   and isinstance(start.right, LiteralNode) and start.right.value == 2)
ok("For end is 10-3", isinstance(end, BinaryOpNode) and end.operator == "-"
   and isinstance(end.left, LiteralNode) and end.left.value == 10
   and isinstance(end.right, LiteralNode) and end.right.value == 3)

# ---------------------------------------------------------------------------
# 7. Property access chains
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("7. Property access chains")
print("-" * 60)

prog = parse("S.name : a.b.c\n")
n = first(prog)
ok("Property chain assignment", isinstance(n, AssignmentNode))
val = n.value
ok("3-level chain", isinstance(val, PropertyAccessNode) and val.property == "c")
mid = val.object
ok("mid level", isinstance(mid, PropertyAccessNode) and mid.property == "b")
root = mid.object
ok("base identifier a", isinstance(root, IdentifierNode) and root.name == "a")

prog = parse("p person.name.first\n")
n = first(prog)
ok("Print property chain", isinstance(n, PrintNode))
val = n.value
ok("Print val is PropertyAccess", isinstance(val, PropertyAccessNode) and val.property == "first")

# ---------------------------------------------------------------------------
# 8. Object instantiation inside methods and blocks
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("8. Object instantiation in nested scopes")
print("-" * 60)

prog = parse("Obj.Car == my_car\n")
n = first(prog)
ok("Top-level Obj", isinstance(n, ObjectNode) and n.class_name == "Car" and n.var_name == "my_car")

prog = parse("@Db:\n  M.build:\n    p \"start\"\n    Obj.Wheel == w\n    p \"done\"\n  /\n")
db = first(prog)
m = db.body[0]
ok("Method body has 3 stmts (Obj was bug)", isinstance(m, MethodNode) and len(m.body) == 3)
ok("Obj inside method body", isinstance(m.body[1], ObjectNode)
   and m.body[1].class_name == "Wheel" and m.body[1].var_name == "w")

prog = parse("! If.x > 5,\n  Obj.Engine == e\n  p \"done\"\n#\n")
n = first(prog)
ok("Obj inside If body", isinstance(n, IfNode))
ok("If then_body[0] is Obj", isinstance(n.then_body[0], ObjectNode)
   and n.then_body[0].class_name == "Engine")

prog = parse("? For.i=0;3,\n  Obj.Part == p\n  db.next\n#\n")
n = first(prog)
ok("Obj inside For body", isinstance(n, ForNode))
ok("For body[0] is Obj", isinstance(n.body[0], ObjectNode)
   and n.body[0].class_name == "Part")

prog = parse("? While.x < 5,\n  Obj.Part == p\n#\n")
n = first(prog)
ok("Obj inside While body", isinstance(n, WhileNode) and isinstance(n.body[0], ObjectNode))

prog = parse("@Cls.Car:\n  Obj.Wheel == w\n@\n")
n = first(prog)
ok("Obj inside class body", isinstance(n, ClassNode) and isinstance(n.members[0], ObjectNode))

# ---------------------------------------------------------------------------
# 9. Nested methods in class body
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("9. Nested methods in class")
print("-" * 60)

prog = parse("@Cls.Car:\n  M.drive:\n    p \"go\"\n  /\n  M.honk:\n    p \"beep\"\n  /\n@\n")
n = first(prog)
ok("Class with 2 methods", isinstance(n, ClassNode) and len(n.members) == 2)
ok("First method drive", isinstance(n.members[0], MethodNode) and n.members[0].name == "drive")
ok("Second method honk", isinstance(n.members[1], MethodNode) and n.members[1].name == "honk")

prog = parse("@Cls.Car:\n  M.init:\n    S.speed : 0\n    Obj.Wheel == w\n    p \"ready\"\n  /\n@\n")
n = first(prog)
m = n.members[0]
ok("Method body with typed-assign + obj + print", len(m.body) == 3)

# ---------------------------------------------------------------------------
# 10. Error handling -- invalid tokens in wrong contexts
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("10. Error handling")
print("-" * 60)


def should_fail(src: str, label: str) -> None:
    try:
        parse(src)
        ok(label, False)
    except ParseError:
        ok(label, True)


should_fail("db.close\n", "db.close outside Db")
should_fail("/\n", "/ outside method")
should_fail("#\n", "# outside block")
should_fail("! something\n", "! without If")
should_fail("? whatever\n", "? without For/While")

prog = parse("")
ok("Empty program", len(prog.body) == 0)

# ---------------------------------------------------------------------------
# 11. Nested constructs
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("11. Nested constructs")
print("-" * 60)

prog = parse("M.test:\n  @Cls.Car:\n    p \"test\"\n  @\n/\n")
m = first(prog)
ok("Class inside method", isinstance(m, MethodNode) and len(m.body) == 1
   and isinstance(m.body[0], ClassNode) and m.body[0].name == "Car"
   and not m.body[0].auto_close)

prog = parse("M.outer:\n  M.inner:\n    p \"deep\"\n  /\n/\n")
m = first(prog)
ok("Nested method", isinstance(m, MethodNode) and m.name == "outer"
   and len(m.body) == 1 and isinstance(m.body[0], MethodNode)
   and m.body[0].name == "inner" and not m.body[0].auto_close)

prog = parse("M.test:\n  @Db:\n    p \"inside\"\n    db.close\n/\n")
m = first(prog)
ok("Db inside method", isinstance(m, MethodNode) and len(m.body) == 1
   and isinstance(m.body[0], DbNode) and not m.body[0].auto_close)

prog = parse("! If.x > 5,\n  @Cls.Car:\n    p \"test\"\n  @\n#\n")
n0 = first(prog)
ok("Class inside If body", isinstance(n0, IfNode)
   and len(n0.then_body) == 1 and isinstance(n0.then_body[0], ClassNode)
   and n0.then_body[0].name == "Car" and not n0.then_body[0].auto_close)

prog = parse("? For.i=0;10,\n  @Cls.Car:\n    p \"test\"\n  @\n#\n")
n0 = first(prog)
ok("Class inside For body", isinstance(n0, ForNode)
   and len(n0.body) == 1 and isinstance(n0.body[0], ClassNode)
   and n0.body[0].name == "Car")

prog = parse("? While.x < 10,\n  @Cls.Car:\n    p \"test\"\n  @\n#\n")
n0 = first(prog)
ok("Class inside While body", isinstance(n0, WhileNode)
   and len(n0.body) == 1 and isinstance(n0.body[0], ClassNode)
   and n0.body[0].name == "Car")

prog = parse("@Db:\n  M.a:\n    p \"one\"\n  M.b:\n    p \"two\"\n  M.c:\n    p \"three\"\n  /\n")
db = first(prog)
a = db.body[0]
b = a.body[1]
ok("Deeply nested methods", isinstance(a, MethodNode) and a.name == "a" and a.auto_close
   and isinstance(b, MethodNode) and b.name == "b" and isinstance(b.body[1], MethodNode)
   and b.body[1].name == "c")

# ---------------------------------------------------------------------------
# 12. Line numbers on ElseIf nodes
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("12. ElseIf line numbers")
print("-" * 60)

prog = parse("! If.x > 5,\n  p \"a\"\n#\n!! x > 10,\n  p \"b\"\n#\n")
n = first(prog)
ok("If line=1", n.line == 1)
ok("ElseIf line=4", n.elseifs[0].line == 4)

prog = parse("! If.x < 3,\n  p \"a\"\n#\n!! x < 7,\n  p \"b\"\n#\n!! x < 10,\n  p \"c\"\n#\n! Else\n  p \"d\"\n#\n")
n = first(prog)
ok("Chained ElseIf[0] line=4", n.elseifs[0].line == 4)
ok("Chained ElseIf[1] line=7", n.elseifs[1].line == 7)

# ---------------------------------------------------------------------------
# 13. Property chain on binary RHS
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("13. Property chain on binary RHS")
print("-" * 60)

prog = parse("x == person.age\n")
n = first(prog)
ok("x == person.age is BinaryOp", isinstance(n, BinaryOpNode) and n.operator == "==")
ok("Left is identifier x", isinstance(n.left, IdentifierNode) and n.left.name == "x")
ok("Right is property access", isinstance(n.right, PropertyAccessNode) and n.right.property == "age")
root = n.right.object
ok("Right root is person", isinstance(root, IdentifierNode) and root.name == "person")

prog = parse("total + obj.value\n")
n = first(prog)
ok("total + obj.value", isinstance(n, BinaryOpNode) and n.operator == "+")
ok("RHS is prop access", isinstance(n.right, PropertyAccessNode) and n.right.property == "value")

# ---------------------------------------------------------------------------
# 14. Relation assignment validation
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("14. Relation assignment validation")
print("-" * 60)


should_fail("I.a.b.c : 5\n", "relation path >2 parts raises error")

# ---------------------------------------------------------------------------
# 15. Orphan literal rejection
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("15. Orphan literal rejection")
print("-" * 60)

should_fail("\"hello\"\n", "standalone string raises error")
should_fail("42\n", "standalone integer raises error")

# ---------------------------------------------------------------------------
# 16. ElseNode verification
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("16. ElseNode verification")
print("-" * 60)

prog = parse("! If.x > 5,\n  p \"big\"\n#\n! Else\n  p \"small\"\n#\n")
n = first(prog)
ok("If else_node is ElseNode", isinstance(n, IfNode) and n.has_else
   and isinstance(n.else_node, ElseNode))
ok("ElseNode body length", isinstance(n.else_node, ElseNode) and len(n.else_node.body) == 1)
ok("ElseNode auto_close=False", isinstance(n.else_node, ElseNode) and not n.else_node.auto_close)

prog = parse("! If.x > 5,\n  p \"big\"\n#\n! Else\n  p \"small\"\n")
n = first(prog)
ok("ElseNode auto_close=True (no #)", isinstance(n, IfNode) and n.has_else
   and isinstance(n.else_node, ElseNode) and n.else_node.auto_close)

prog = parse("! If.x > 5,\n  p \"big\"\n#\n")
n = first(prog)
ok("If without else_node=None", isinstance(n, IfNode) and not n.has_else
   and n.else_node is None)

# ---------------------------------------------------------------------------
# 17. Auto-close verification for all 8 block types
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("17. Auto-close for all 8 block types")
print("-" * 60)

# 1) Db auto_close
prog = parse("@Db:\n  p \"a\"\n")
n = first(prog)
ok("Db auto_close=True", isinstance(n, DbNode) and n.auto_close)
prog = parse("@Db:\n  p \"a\"\ndb.close\n")
n = first(prog)
ok("Db auto_close=False", isinstance(n, DbNode) and not n.auto_close)

# 2) Class auto_close
prog = parse("@Cls.Car:\n  p \"a\"\n")
n = first(prog)
ok("Class auto_close=True", isinstance(n, ClassNode) and n.auto_close)
prog = parse("@Cls.Car:\n  p \"a\"\n@\n")
n = first(prog)
ok("Class auto_close=False", isinstance(n, ClassNode) and not n.auto_close)

# 3) Method auto_close
prog = parse("M.a:\n  p \"a\"\n")
n = first(prog)
ok("Method auto_close=True", isinstance(n, MethodNode) and n.auto_close)
prog = parse("M.a:\n  p \"a\"\n/\n")
n = first(prog)
ok("Method auto_close=False", isinstance(n, MethodNode) and not n.auto_close)

# 4) If auto_close
prog = parse("! If.x > 5,\n  p \"a\"\n")
n = first(prog)
ok("If auto_close=True", isinstance(n, IfNode) and n.auto_close)
prog = parse("! If.x > 5,\n  p \"a\"\n#\n")
n = first(prog)
ok("If auto_close=False", isinstance(n, IfNode) and not n.auto_close)

# 5) ElseIf auto_close
prog = parse("! If.x > 5,\n  p \"a\"\n#\n!! x > 10,\n  p \"b\"\n")
n = first(prog)
ok("ElseIf auto_close=True", isinstance(n, IfNode) and len(n.elseifs) == 1
   and n.elseifs[0].auto_close)
prog = parse("! If.x > 5,\n  p \"a\"\n#\n!! x > 10,\n  p \"b\"\n#\n")
n = first(prog)
ok("ElseIf auto_close=False", isinstance(n, IfNode) and len(n.elseifs) == 1
   and not n.elseifs[0].auto_close)

# 6) Else auto_close
prog = parse("! If.x > 5,\n  p \"a\"\n#\n! Else\n  p \"b\"\n")
n = first(prog)
ok("ElseNode auto_close=True (no #)", isinstance(n, IfNode) and n.has_else
   and isinstance(n.else_node, ElseNode) and n.else_node.auto_close)
prog = parse("! If.x > 5,\n  p \"a\"\n#\n! Else\n  p \"b\"\n#\n")
n = first(prog)
ok("ElseNode auto_close=False (with #)", isinstance(n, IfNode) and n.has_else
   and isinstance(n.else_node, ElseNode) and not n.else_node.auto_close)

# 7) For auto_close
prog = parse("? For.i=0;10,\n  p \"a\"\n")
n = first(prog)
ok("For auto_close=True", isinstance(n, ForNode) and n.auto_close)
prog = parse("? For.i=0;10,\n  p \"a\"\n#\n")
n = first(prog)
ok("For auto_close=False", isinstance(n, ForNode) and not n.auto_close)

# 8) While auto_close
prog = parse("? While.x < 10,\n  p \"a\"\n")
n = first(prog)
ok("While auto_close=True", isinstance(n, WhileNode) and n.auto_close)
prog = parse("? While.x < 10,\n  p \"a\"\n#\n")
n = first(prog)
ok("While auto_close=False", isinstance(n, WhileNode) and not n.auto_close)

# ---------------------------------------------------------------------------
# 18. Visitor / walk() / dump() compatibility
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("18. Visitor / walk() compatibility")
print("-" * 60)

prog = parse("! If.x > 5,\n  p \"big\"\n#\n@Cls.Car:\n  p \"ok\"\n@\n")
all_nodes = list(prog.walk())
ok("walk returns list", isinstance(all_nodes, list) and len(all_nodes) > 0)
dumped = dump(prog)
ok("dump returns str", isinstance(dumped, str) and len(dumped) > 0)

class MethodCollector(NodeVisitor):
    def __init__(self):
        self.methods: list[MethodNode] = []
    def visit_MethodNode(self, node: MethodNode) -> None:
        self.methods.append(node)
        self.generic_visit(node)

prog = parse("@Db:\n  M.a:\n    p 1\n  /\n")
collector = MethodCollector()
collector.visit(prog)
ok("Visitor finds MethodNode", len(collector.methods) == 1
   and collector.methods[0].name == "a")

# ---------------------------------------------------------------------------
# 19. AST module self-test -- run inline
# ---------------------------------------------------------------------------
print()
print("-" * 60)
print("19. AST module self-test")
print("-" * 60)

from parser.ra_ast import _summary

n_test = IdentifierNode(name="test", line=1)
s = _summary(n_test)
ok("_summary returns string", isinstance(s, str) and "IdentifierNode" in s)

n_test2 = BinaryOpNode(
    operator=";",
    left=LiteralNode(value=0, kind=TokenType.INTEGER, line=1),
    right=LiteralNode(value=10, kind=TokenType.INTEGER, line=2),
    line=1,
)
ok("BinaryOpNode repr", "op=';'" in repr(n_test2))
ok("children includes left+right", len(n_test2.children) == 2)

d = dump(n_test2)
ok("dump works", isinstance(d, str) and "BinaryOpNode" in d)

ok("WhileNode auto_close defaults", WhileNode(condition=n_test, line=1).auto_close == False)
ok("ForNode auto_close defaults", ForNode(variable="i", iterable=n_test, line=1).auto_close == False)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print("=" * 60)
print(f"  {PASS} passed, {FAIL} failed")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
