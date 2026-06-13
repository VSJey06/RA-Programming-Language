"""Runtime tests for Dequeue V1.5 properties.

Covers:
  - rows, colms (grid dimensions)
  - row.N, colm.N (row/column accessors)
  - diagonal.* (8 directional rays)
  - find:value, exists:value (search)
  - clear (destructive clear)
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


# ── Rows / Colms ─────────────────────────────────────────────────


def test_rows_empty() -> None:
    rt = run("Dequeue.D\nD.rows\n")
    ok("rows = 0 on empty dequeue", rt.global_scope.get("_") == 0)


def test_rows_after_inserts() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.insert:2\nD.insert:3\nD.insert:4\nD.insert:5\nD.rows\n")
    ok("rows = 2 after 5 inserts", rt.global_scope.get("_") == 2)


def test_colms_empty() -> None:
    rt = run("Dequeue.D\nD.colms\n")
    ok("colms = 4 on empty dequeue (default)", rt.global_scope.get("_") == 4)


def test_colms_after_inserts() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.insert:2\nD.insert:3\nD.insert:4\nD.insert:5\nD.colms\n")
    ok("colms = 4 after 5 inserts", rt.global_scope.get("_") == 4)


# ── Row / Colm accessors ─────────────────────────────────────────


def test_row_1() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.insert:30\nD.insert:40\nD.row.1\n")
    ok("row.1 returns space-separated values",
       rt.global_scope.get("_") == "10 20 30 40")


def test_row_out_of_range() -> None:
    try:
        run("Dequeue.D\nD.row.5\n")
        ok("row out of range raises", False)
    except RuntimeError:
        ok("row out of range raises", True)


def test_colm_1() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.insert:30\nD.insert:40\nD.insert:50\nD.colm.1\n")
    ok("colm.1 returns first column values",
       rt.global_scope.get("_") == "10 50")


def test_colm_out_of_range() -> None:
    try:
        run("Dequeue.D\nD.insert:1\nD.colm.5\n")
        ok("colm out of range raises", False)
    except RuntimeError:
        ok("colm out of range raises", True)


# ── Diagonal ─────────────────────────────────────────────────────


def test_diagonal_x() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.insert:30\nD.insert:40\nD.insert:50\nD.insert:60\nD.insert:70\nD.insert:80\nD.diagonal.x\n")
    ok("diagonal.x = first column top->bottom",
       rt.global_scope.get("_") == "10 50")


def test_diagonal_y() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.insert:30\nD.insert:40\nD.insert:50\nD.insert:60\nD.insert:70\nD.insert:80\nD.diagonal.y\n")
    ok("diagonal.y = first row left->right",
       rt.global_scope.get("_") == "10 20 30 40")


def test_diagonal_minus_x() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.insert:30\nD.insert:40\nD.insert:50\nD.insert:60\nD.insert:70\nD.insert:80\nD.diagonal.-x\n")
    ok("diagonal.-x = last col bottom->top",
       rt.global_scope.get("_") == "80 40")


def test_diagonal_minus_y() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.insert:30\nD.insert:40\nD.insert:50\nD.insert:60\nD.insert:70\nD.insert:80\nD.diagonal.-y\n")
    ok("diagonal.-y = last row right->left",
       rt.global_scope.get("_") == "80 70 60 50")


def test_diagonal_x_y() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.insert:2\nD.insert:3\nD.insert:4\nD.insert:5\nD.insert:6\nD.insert:7\nD.insert:8\nD.diagonal.x-y\n")
    ok("diagonal.x-y = top-right -> bottom-left",
       rt.global_scope.get("_") == "4 7")


def test_diagonal_y_x() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.insert:2\nD.insert:3\nD.insert:4\nD.insert:5\nD.insert:6\nD.insert:7\nD.insert:8\nD.diagonal.y-x\n")
    ok("diagonal.y-x = bottom-left -> top-right",
       rt.global_scope.get("_") == "5 2")


def test_diagonal_minus_x_y() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.insert:2\nD.insert:3\nD.insert:4\nD.insert:5\nD.insert:6\nD.insert:7\nD.insert:8\nD.diagonal.-x-y\n")
    ok("diagonal.-x-y = bottom-right -> top-left",
       rt.global_scope.get("_") == "8 3")


def test_diagonal_minus_y_x() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.insert:2\nD.insert:3\nD.insert:4\nD.insert:5\nD.insert:6\nD.insert:7\nD.insert:8\nD.diagonal.-y-x\n")
    ok("diagonal.-y-x = top-left -> bottom-right",
       rt.global_scope.get("_") == "1 6")


def test_diagonal_empty_grid() -> None:
    rt = run("Dequeue.D\nD.diagonal.x\n")
    ok("diagonal.x on empty grid returns empty string",
       rt.global_scope.get("_") == "")


# ── Find / Exists ────────────────────────────────────────────────


def test_find_exists() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.insert:30\nD.find:20\n")
    ok("find:20 returns '1,2'", rt.global_scope.get("_") == "1,2")


def test_find_not_found() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.insert:30\nD.find:99\n")
    ok("find:99 returns '- -'", rt.global_scope.get("_") == "- -")


def test_find_first_occurrence() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.insert:10\nD.find:10\n")
    ok("find:10 returns first occurrence '1,1'",
       rt.global_scope.get("_") == "1,1")


def test_exists_true() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.exists:20\n")
    ok("exists:20 returns True", rt.global_scope.get("_") is True)


def test_exists_false() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.exists:99\n")
    ok("exists:99 returns False", rt.global_scope.get("_") is False)


def test_exists_empty_grid() -> None:
    rt = run("Dequeue.D\nD.exists:1\n")
    ok("exists:1 on empty grid returns False",
       rt.global_scope.get("_") is False)


# ── Clear ────────────────────────────────────────────────────────


def test_clear_empties_grid() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.clear\nD.count\n")
    ok("count = 0 after clear", rt.global_scope.get("_") == 0)


def test_clear_then_insert() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.clear\nD.insert:99\nD.get.1,1\n")
    ok("insert after clear works", rt.global_scope.get("_") == 99)


def test_clear_empty_dequeue() -> None:
    rt = run("Dequeue.D\nD.clear\nD.rows\n")
    ok("clear on empty dequeue is safe", rt.global_scope.get("_") == 0)


# ── Print / Assignment support (find/exists) ─────────────────────


def test_print_find() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.insert:30\np D.find:20\n")
    ok("p D.find:20 prints and stores '1,2'",
       rt.global_scope.get("_") == "1,2")


def test_print_exists_true() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.insert:30\np D.exists:20\n")
    ok("p D.exists:20 prints and stores True",
       rt.global_scope.get("_") is True)


def test_print_exists_false() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nD.insert:30\np D.exists:99\n")
    ok("p D.exists:99 prints and stores False",
       rt.global_scope.get("_") is False)


def test_assign_find() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nS loc = D.find:20\n")
    ok("S loc = D.find:20 stores coordinate",
       rt.global_scope.get("loc") == "1,2")


def test_assign_exists() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nI ok = D.exists:20\n")
    ok("I ok = D.exists:20 stores True",
       rt.global_scope.get("ok") is True)


# ── Expression-level access (via assignment) ─────────────────────


def test_row_in_assignment() -> None:
    rt = run("Dequeue.D\nD.insert:10\nD.insert:20\nI r1 = D.row.1\n")
    ok("I r1 = D.row.1 stores row string",
       rt.global_scope.get("r1") == "10 20 NV NV")


def test_diagonal_in_assignment() -> None:
    rt = run("Dequeue.D\nD.insert:1\nD.insert:2\nD.insert:3\nD.insert:4\nD.insert:5\nD.insert:6\nD.insert:7\nD.insert:8\nI d = D.diagonal.x-y\n")
    ok("I d = D.diagonal.x-y stores diagonal string",
       rt.global_scope.get("d") == "4 7")


# ── Run ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_rows_empty()
    test_rows_after_inserts()
    test_colms_empty()
    test_colms_after_inserts()
    test_row_1()
    test_row_out_of_range()
    test_colm_1()
    test_colm_out_of_range()
    test_diagonal_x()
    test_diagonal_y()
    test_diagonal_minus_x()
    test_diagonal_minus_y()
    test_diagonal_x_y()
    test_diagonal_y_x()
    test_diagonal_minus_x_y()
    test_diagonal_minus_y_x()
    test_diagonal_empty_grid()
    test_find_exists()
    test_find_not_found()
    test_find_first_occurrence()
    test_exists_true()
    test_exists_false()
    test_exists_empty_grid()
    test_clear_empties_grid()
    test_clear_then_insert()
    test_clear_empty_dequeue()
    test_row_in_assignment()
    test_diagonal_in_assignment()
    test_print_find()
    test_print_exists_true()
    test_print_exists_false()
    test_assign_find()
    test_assign_exists()

    total = PASS + FAIL
    print(f"\n{'=' * 60}")
    print(f"  {PASS} passed, {FAIL} failed out of {total} tests")
    sys.exit(0 if FAIL == 0 else 1)
