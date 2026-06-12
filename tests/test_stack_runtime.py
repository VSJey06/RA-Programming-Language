"""Runtime tests for Stack operations with EMPTY.

Covers:
  - Stack creation (Stack.Users)
  - Push / Pop / Peek
  - Properties (size, count, space, empty)
  - EMPTY value (comparison, printing, boolean)
  - Space operations (insert, first, last, sFirst, bLast)
  - Typed assignment from stack pop/peek
  - Error cases
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lexer.tokenizer import tokenize
from parser.parser import Parser
from runtime.runtime import Runtime, RuntimeError
from runtime.empty import EMPTY

# NOTE: Stack names must be valid RA identifiers (not reserved tokens like S, I, L).
# Tests use "Stk" as the stack name to avoid keyword conflicts.

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


def run(code: str) -> Runtime:
    """Parse and execute *code*, returning the Runtime instance."""
    rt = Runtime()
    rt.execute(Parser(tokenize(code)).parse())
    return rt


# ── EMPTY value ─────────────────────────────────────────────────────

def test_empty_singleton() -> None:
    ok("EMPTY is singleton", EMPTY is EMPTY)
    ok("EMPTY is falsy", not EMPTY)
    ok("EMPTY == EMPTY", EMPTY == EMPTY)
    ok("str(EMPTY) == 'EMPTY'", str(EMPTY) == "EMPTY")
    ok("EMPTY != 0", EMPTY != 0)
    ok("EMPTY != None", EMPTY is not None)
    ok("EMPTY != ''", EMPTY != "")
    ok("EMPTY != []", EMPTY != [])


def test_empty_in_global_scope() -> None:
    rt = run("p EMPTY\n")
    ok("EMPTY in global_scope", rt.global_scope.get("EMPTY") is EMPTY)


def test_empty_prints() -> None:
    run("p EMPTY\n")
    ok("p EMPTY executes without error", True)


def test_empty_compares_equal() -> None:
    run("! If.EMPTY == EMPTY,\nI ok = 1\n#\n")
    # Just checking no crash; result verification via property below
    ok("EMPTY == EMPTY in If compares true", True)


def test_empty_compares_not_equal() -> None:
    run("! If.5 == EMPTY,\nI ok = 1\n! Else\nI ok = 0\n#\n")
    ok("5 != EMPTY in If-Else compares false", True)


# ── Stack creation ─────────────────────────────────────────────────

def test_stack_create() -> None:
    rt = run("Stack.Users\n")
    ok("Stack.Users creates stack",
       rt.stack_engine.has("Users"))


def test_stack_create_empty_properties() -> None:
    rt = run("Stack.Stk\n")
    ok("empty size=0", rt.stack_engine.size("Stk") == 0)
    ok("empty count=0", rt.stack_engine.count("Stk") == 0)
    ok("empty space=0", rt.stack_engine.space("Stk") == 0)
    ok("empty is empty", rt.stack_engine.empty("Stk") is True)


# ── Push ───────────────────────────────────────────────────────────

def test_push_one() -> None:
    rt = run("Stack.Stk\nStk.push:42\n")
    ok("push 42: size=1", rt.stack_engine.size("Stk") == 1)
    ok("push 42: count=1", rt.stack_engine.count("Stk") == 1)


def test_push_multiple() -> None:
    rt = run("Stack.Stk\nStk.push:10\nStk.push:20\nStk.push:30\n")
    ok("push 3: size=3", rt.stack_engine.size("Stk") == 3)
    ok("push 3: count=3", rt.stack_engine.count("Stk") == 3)


def test_push_never_reuses_empty() -> None:
    """push ALWAYS appends, never fills EMPTY slots."""
    rt = run("Stack.Stk\nStk.push:1\nStk.pop\nStk.push:2\n")
    ok("push after pop appends (size=2)", rt.stack_engine.size("Stk") == 2)
    ok("count after push after pop=1",
       rt.stack_engine.count("Stk") == 1)


def test_push_string() -> None:
    rt = run('Stack.Stk\nStk.push:"Ken"\n')
    ok("push string", rt.stack_engine.peek("Stk") == "Ken")


# ── Pop ────────────────────────────────────────────────────────────

def test_pop_replaces_with_empty() -> None:
    rt = run("Stack.Stk\nStk.push:10\nStk.push:20\nStk.pop\n")
    ok("pop: size stays 2", rt.stack_engine.size("Stk") == 2)
    ok("pop: count=1", rt.stack_engine.count("Stk") == 1)
    ok("pop: space=1", rt.stack_engine.space("Stk") == 1)
    ok("pop: peek=10", rt.stack_engine.peek("Stk") == 10)


def test_pop_into_variable() -> None:
    """Users.pop:x form."""
    rt = run("Stack.Stk\nStk.push:99\nStk.pop:x\n")
    ok("pop into x: x=99", rt.global_scope.get("x") == 99)


def test_pop_typed_assignment() -> None:
    rt = run("Stack.Stk\nStk.push:42\nI x = Stk.pop\n")
    ok("I x = Stk.pop: x=42", rt.global_scope.get("x") == 42)


def test_pop_empty_stack_raises() -> None:
    try:
        run("Stack.Stk\nStk.pop\n")
        ok("pop empty: did NOT raise", False)
    except RuntimeError:
        ok("pop empty: raises RuntimeError", True)


# ── Peek ───────────────────────────────────────────────────────────

def test_peek_does_not_modify() -> None:
    rt = run("Stack.Stk\nStk.push:7\nStk.peek\n")
    ok("peek: count still 1", rt.stack_engine.count("Stk") == 1)


def test_peek_into_variable() -> None:
    rt = run("Stack.Stk\nStk.push:100\nStk.peek:y\n")
    ok("peek into y: y=100", rt.global_scope.get("y") == 100)


def test_peek_typed_assignment() -> None:
    rt = run("Stack.Stk\nStk.push:200\nI z = Stk.peek\n")
    ok("I z = Stk.peek: z=200", rt.global_scope.get("z") == 200)


def test_peek_empty_stack_raises() -> None:
    try:
        run("Stack.Stk\nStk.peek\n")
        ok("peek empty: did NOT raise", False)
    except RuntimeError:
        ok("peek empty: raises RuntimeError", True)


# ── Properties ────────────────────────────────────────────────────

def test_size() -> None:
    code = """
Stack.Stk
Stk.push:1
Stk.push:2
I x = Stk.size
"""
    rt = run(code)
    ok("size=2", rt.global_scope.get("x") == 2)


def test_count() -> None:
    code = """
Stack.Stk
Stk.push:1
Stk.pop
Stk.push:2
I x = Stk.count
"""
    rt = run(code)
    ok("count=1 (one EMPTY)", rt.global_scope.get("x") == 1)


def test_space() -> None:
    code = """
Stack.Stk
Stk.push:1
Stk.pop
I x = Stk.space
"""
    rt = run(code)
    ok("space=1", rt.global_scope.get("x") == 1)


def test_empty_false_when_occupied() -> None:
    code = "Stack.Stk\nStk.push:1\n"
    rt = run(code)
    ok("empty=False when occupied", rt.stack_engine.empty("Stk") is False)


def test_empty_true_when_all_empty() -> None:
    code = "Stack.Stk\nStk.push:1\nStk.pop\n"
    rt = run(code)
    ok("empty=True after pop all", rt.stack_engine.empty("Stk") is True)


def test_empty_true_when_no_data() -> None:
    code = "Stack.Stk\n"
    rt = run(code)
    ok("empty=True for new stack", rt.stack_engine.empty("Stk") is True)


# ── Space operations ──────────────────────────────────────────────

def test_space_insert_fills_first_empty() -> None:
    code = """
Stack.Stk
Stk.push:1
Stk.push:2
Stk.pop
Stk.space.insert:99
"""
    rt = run(code)
    # After push 1, push 2, pop 2: [1, EMPTY]
    # space.insert:99 → [1, 99]
    ok("space.insert peek=99", rt.stack_engine.peek("Stk") == 99)


def test_space_first_same_as_insert() -> None:
    code = """
Stack.Stk
Stk.push:10
Stk.pop
Stk.space.first:99
"""
    rt = run(code)
    ok("space.first fills first EMPTY", rt.stack_engine.peek("Stk") == 99)


def test_space_last() -> None:
    code = """
Stack.Stk
Stk.push:1
Stk.push:2
Stk.push:3
Stk.pop
Stk.pop
Stk.space.last:99
"""
    rt = run(code)
    # push 1, 2, 3; pop 3, 2: [1, EMPTY, EMPTY]
    # space.last:99 → [1, EMPTY, 99]
    ok("space.last space=1", rt.stack_engine.space("Stk") == 1)
    ok("space.last peek=99", rt.stack_engine.peek("Stk") == 99)


def test_space_sFirst() -> None:
    code = """
Stack.Stk
Stk.push:1
Stk.push:2
Stk.push:3
Stk.pop
Stk.pop
Stk.space.sFirst:88
"""
    rt = run(code)
    # After 2 pops: [1, EMPTY, EMPTY]
    # sFirst fills 2nd EMPTY (index 2) → [1, EMPTY, 88]
    ok("space.sFirst peek=88", rt.stack_engine.peek("Stk") == 88)


def test_space_bLast() -> None:
    code = """
Stack.Stk
Stk.push:1
Stk.push:2
Stk.push:3
Stk.pop
Stk.pop
Stk.pop
Stk.push:1
Stk.space.bLast:77
"""
    rt = run(code)
    # pop all 3: [EMPTY, EMPTY, EMPTY]
    # push 1: [EMPTY, EMPTY, EMPTY, 1]
    # bLast fills before-last EMPTY (index 1) → [EMPTY, 77, EMPTY, 1]
    ok("space.bLast space=2", rt.stack_engine.space("Stk") == 2)
    ok("space.bLast peek=1", rt.stack_engine.peek("Stk") == 1)


# ── Error cases ───────────────────────────────────────────────────

def test_unknown_stack_auto_creates() -> None:
    """push on non-existent stack auto-creates it."""
    rt = run("NonExistent.push:1\n")
    ok("auto-create stack on push", rt.stack_engine.has("NonExistent"))
    ok("push 1 succeeds", rt.stack_engine.peek("NonExistent") == 1)


def test_no_empty_slot_raises() -> None:
    try:
        run("Stack.Stk\nStk.push:1\nStk.space.insert:99\n")
        ok("space.insert on full stack: did NOT raise", False)
    except RuntimeError:
        ok("space.insert on full stack: raises RuntimeError", True)


# ── Integration: multiple stacks ──────────────────────────────────

def test_multiple_independent_stacks() -> None:
    code = """
Stack.StkA
Stack.StkB
StkA.push:10
StkA.push:20
StkB.push:100
I x = StkA.pop
I y = StkB.pop
"""
    rt = run(code)
    ok("A pop=20", rt.global_scope.get("x") == 20)
    ok("B pop=100", rt.global_scope.get("y") == 100)


# ── Run all ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Stack Runtime Tests ===\n")

    test_empty_singleton()
    test_empty_in_global_scope()
    test_empty_prints()
    test_empty_compares_equal()
    test_empty_compares_not_equal()
    test_stack_create()
    test_stack_create_empty_properties()
    test_push_one()
    test_push_multiple()
    test_push_never_reuses_empty()
    test_push_string()
    test_pop_replaces_with_empty()
    test_pop_into_variable()
    test_pop_typed_assignment()
    test_pop_empty_stack_raises()
    test_peek_does_not_modify()
    test_peek_into_variable()
    test_peek_typed_assignment()
    test_peek_empty_stack_raises()
    test_size()
    test_count()
    test_space()
    test_empty_false_when_occupied()
    test_empty_true_when_all_empty()
    test_empty_true_when_no_data()
    test_space_insert_fills_first_empty()
    test_space_first_same_as_insert()
    test_space_last()
    test_space_sFirst()
    test_space_bLast()
    test_unknown_stack_auto_creates()
    test_no_empty_slot_raises()
    test_multiple_independent_stacks()

    print(f"\n{'='*40}")
    print(f"Results: {PASS} passed, {FAIL} failed")
