"""Runtime tests for Dequeue V1 operations.

Covers:
  - Dequeue creation (Dequeue.D)
  - Insert (left→right, top→bottom)
  - Remove by coordinate (remove.X,Y → __)
  - Get by coordinate (get.X,Y)
  - Properties (size, count, space, empty)
  - Space operations (first, last, sFirst, bLast, coord)
  - NV behavior (system-created unused cells)
  - Dynamic row expansion
  - Error cases
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lexer.tokenizer import tokenize
from parser.parser import Parser
from runtime.runtime import Runtime, RuntimeError
from runtime.empty import EMPTY, NV

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
    rt = Runtime()
    rt.execute(Parser(tokenize(code)).parse())
    return rt


# ── Creation ────────────────────────────────────────────────────────

def test_dequeue_create() -> None:
    rt = run("Dequeue.D\n")
    ok("Dequeue.D creates D", rt.dequeue_engine.has("D"))


def test_dequeue_create_multiple() -> None:
    rt = run("Dequeue.A\nDequeue.B\n")
    ok("A and B exist",
       rt.dequeue_engine.has("A") and rt.dequeue_engine.has("B"))


# ── Insert ──────────────────────────────────────────────────────────

def test_insert_and_get() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.get.1,1\n")
    ok("get.1,1 returns 10", rt.global_scope.get("_") == 10)


def test_insert_left_to_right() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.get.1,2\n")
    ok("get.1,2 returns 20 (second insert)", rt.global_scope.get("_") == 20)


def test_insert_top_to_bottom() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.insert:2\nD.insert:3\nD.insert:4\nD.insert:5\nD.get.2,1\n")
    ok("get.2,1 returns 5 (second row)", rt.global_scope.get("_") == 5)


def test_insert_string() -> None:
    rt = run('Dequeue.D\nD.insert:"Ken"\nD.get.1,1\n')
    ok("insert string returns 'Ken'", rt.global_scope.get("_") == "Ken")


# ── Remove ──────────────────────────────────────────────────────────

def test_remove_replaces_with_empty() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.remove.1,1\nD.get.1,1\n")
    ok("removed cell is EMPTY", rt.global_scope.get("_") is EMPTY)


def test_remove_leaves_other_cells() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.remove.1,1\nD.get.1,2\n")
    ok("cell (1,2) unchanged after remove", rt.global_scope.get("_") == 20)


def test_remove_never_nv() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.remove.1,1\n")
    grid = rt.dequeue_engine._get("D")
    ok("removed cell is EMPTY not NV", grid[0][0] is EMPTY)


# ── Get ─────────────────────────────────────────────────────────────

def test_get_to_var() -> None:
    rt = run("Dequeue.D\nD.insert:42\nI x = D.get.1,1\n")
    ok("x = 42 via get.1,1", rt.global_scope.get("x") == 42)


def test_get_second_row() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.insert:2\nD.insert:3\nD.insert:4\nD.insert:5\nI y = D.get.2,1\n")
    ok("y = 5 via get.2,1", rt.global_scope.get("y") == 5)


# ── Properties ──────────────────────────────────────────────────────

def test_dequeue_size() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.insert:2\nD.size\n")
    ok("size = 8 (2 rows x 4 cols)", rt.global_scope.get("_") == 8)


def test_dequeue_count() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.insert:2\nD.count\n")
    ok("count = 2", rt.global_scope.get("_") == 2)


def test_dequeue_space() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.space\n")
    ok("space = 7 (one cell filled, 7 Nv)", rt.global_scope.get("_") == 7)


def test_dequeue_empty_after_create() -> None:
    rt = run("Dequeue.D\nD.empty\n")
    ok("new dequeue is empty", rt.global_scope.get("_") is True)


def test_dequeue_not_empty_after_insert() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.empty\n")
    ok("dequeue with data is not empty", rt.global_scope.get("_") is False)


# ── Space operations ────────────────────────────────────────────────

def test_space_first() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.remove.1,1\nD.space.first:99\nD.get.1,1\n")
    ok("space.first fills first empty with 99", rt.global_scope.get("_") == 99)


def test_space_last() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.insert:2\nD.remove.1,2\nD.insert:3\nD.remove.1,3\n"
             "D.space.last:88\nD.get.1,2\n")
    # After inserts and removes, last empty is at (1,3)
    ok("space.last fills last empty", rt.global_scope.get("_") == 88)


def test_space_sFirst() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.remove.1,1\nD.insert:2\nD.remove.1,2\n"
             "D.space.sFirst:77\n")
    grid = rt.dequeue_engine._get("D")
    # Two empties at (1,1) and (1,2); sFirst fills (1,2)
    ok("space.sFirst fills second empty slot", grid[0][1] == 77)


def test_space_bLast() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.remove.1,1\nD.insert:2\nD.remove.1,2\n"
             "D.space.bLast:66\n")
    grid = rt.dequeue_engine._get("D")
    # Two empties at (1,1) and (1,2); bLast fills (1,1)
    ok("space.bLast fills second-last empty slot", grid[0][0] == 66)


def test_space_coord() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.insert:2\nD.remove.1,2\nD.space.1,2:55\nD.get.1,2\n")
    ok("space.1,2 fills specific cell", rt.global_scope.get("_") == 55)


# ── NV behavior ─────────────────────────────────────────────────────

def test_new_row_has_nv() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.insert:2\nD.insert:3\nD.insert:4\nD.insert:5\n")
    grid = rt.dequeue_engine._get("D")
    ok("second row first cell has value", grid[1][0] == 5)
    ok("second row unused cell is NV", grid[1][1] is NV)
    ok("second row last cell is NV", grid[1][3] is NV)


def test_nv_is_fillable_by_space_first() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.space.first:9\nD.get.1,2\n")
    ok("space fills Nv cell at (1,2)", rt.global_scope.get("_") == 9)


# ── Dynamic row expansion ──────────────────────────────────────────

def test_dynamic_row_expansion() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.insert:2\nD.insert:3\nD.insert:4\nD.insert:5\n")
    grid = rt.dequeue_engine._get("D")
    ok("grid has 2 rows after 5 inserts", len(grid) == 2)
    ok("row 2 has 4 columns", len(grid[1]) == 4)


# ── Error cases ────────────────────────────────────────────────────

def test_get_out_of_range() -> None:
    try:
        run("Dequeue.D\nD.insert:1\nD.get.2,1\n")
        ok("get out of range raises", False)
    except RuntimeError:
        ok("get out of range raises", True)


def test_remove_out_of_range() -> None:
    try:
        run("Dequeue.D\nD.insert:1\nD.remove.5,1\n")
        ok("remove out of range raises", False)
    except RuntimeError:
        ok("remove out of range raises", True)


# ── Run ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_dequeue_create()
    test_dequeue_create_multiple()
    test_insert_and_get()
    test_insert_left_to_right()
    test_insert_top_to_bottom()
    test_insert_string()
    test_remove_replaces_with_empty()
    test_remove_leaves_other_cells()
    test_remove_never_nv()
    test_get_to_var()
    test_get_second_row()
    test_dequeue_size()
    test_dequeue_count()
    test_dequeue_space()
    test_dequeue_empty_after_create()
    test_dequeue_not_empty_after_insert()
    test_space_first()
    test_space_last()
    test_space_sFirst()
    test_space_bLast()
    test_space_coord()
    test_new_row_has_nv()
    test_nv_is_fillable_by_space_first()
    test_dynamic_row_expansion()
    test_get_out_of_range()
    test_remove_out_of_range()

    total = PASS + FAIL
    print(f"\n{'=' * 60}")
    print(f"  {PASS} passed, {FAIL} failed out of {total} tests")
    sys.exit(0 if FAIL == 0 else 1)
