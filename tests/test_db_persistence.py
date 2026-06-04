"""Tests for RA database persistence (save / load) and numeric suffixes."""

import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lexer.tokenizer import tokenize
from parser.parser import Parser, ParseError
from runtime.runtime import Runtime, RuntimeError


DATA_DIR = Path(__file__).resolve().parents[1] / "data"

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


def run(src: str) -> Runtime:
    tokens = tokenize(src)
    ast = Parser(tokens).parse()
    r = Runtime()
    r.execute(ast)
    return r


# -- Save / Load tests --------------------------------------------------------

def test_save() -> None:
    src = """Db.Personal:
  S name = "Ken"
  I age = 25
  S location = "Delhi"
db.close
Db.Personal.save
"""
    run(src)
    path = DATA_DIR / "Personal.json"
    ok("save creates file", path.exists())
    if path.exists():
        import json
        data = json.loads(path.read_text(encoding="utf-8"))
        ok("name stored", data.get("name") == "Ken")
        ok("age stored", data.get("age") == 25)
        ok("location stored", data.get("location") == "Delhi")


def test_overwrite_save() -> None:
    src = """Db.Personal:
  S name = "Ken"
  I age = 25
db.close
Db.Personal.save
Db.Personal:
  S name = "Alice"
  I age = 30
db.close
Db.Personal.save
"""
    run(src)
    import json
    data = json.loads((DATA_DIR / "Personal.json").read_text(encoding="utf-8"))
    ok("overwrite name updated", data.get("name") == "Alice")
    ok("overwrite age updated", data.get("age") == 30)


def test_load() -> None:
    # First save
    save_src = """Db.Personal:
  S name = "Ken"
  I age = 25
db.close
Db.Personal.save
"""
    run(save_src)

    # Fresh runtime and load
    rt = Runtime()
    load_src = "Db.Personal.load\n"
    tokens = tokenize(load_src)
    ast = Parser(tokens).parse()
    rt.execute(ast)

    # Check db exists in memory
    ok("loaded db exists", rt.db_engine.has_database("Personal"))
    db = rt.db_engine.get_database("Personal")
    ok("loaded name", db.get("name") == "Ken")
    ok("loaded age", db.get("age") == 25)


def test_load_missing_file() -> None:
    rt = Runtime()
    src = "Db.Nonexistent.load\n"
    tokens = tokenize(src)
    ast = Parser(tokens).parse()
    try:
        rt.execute(ast)
        ok("missing file raises error", False)
    except RuntimeError as e:
        ok("missing file raises error", True, str(e))


# -- Numeric suffix tests ---------------------------------------------------

def test_numeric_suffix_k() -> None:
    tokens = tokenize("5K")
    ok("5K = 5000", tokens[0].value == 5000)


def test_numeric_suffix_lh() -> None:
    tokens = tokenize("25Lh")
    ok("25Lh = 2500000", tokens[0].value == 2_500_000)


def test_numeric_suffix_cr() -> None:
    tokens = tokenize("3Cr")
    ok("3Cr = 30000000", tokens[0].value == 30_000_000)


def test_numeric_suffix_b() -> None:
    tokens = tokenize("2B")
    ok("2B = 2000000000", tokens[0].value == 2_000_000_000)


def test_numeric_suffix_tri() -> None:
    tokens = tokenize("1Tri")
    ok("1Tri = 1000000000000", tokens[0].value == 1_000_000_000_000)


def test_numeric_suffix_qd() -> None:
    tokens = tokenize("4Qd")
    ok("4Qd = 4000000000000000", tokens[0].value == 4_000_000_000_000_000)


def test_numeric_suffix_in_parser() -> None:
    src = """I salary = 5K
p salary
"""
    rt = run(src)
    ok("I salary = 5K stored as 5000", rt.global_scope.get("salary") == 5000)


def test_numeric_suffix_in_db_save() -> None:
    src = """Db.Employees:
  I salary = 5K
  I bonus = 2Lh
db.close
Db.Employees.save
"""
    run(src)
    import json
    data = json.loads((DATA_DIR / "Employees.json").read_text(encoding="utf-8"))
    ok("salary 5K", data.get("salary") == 5000)
    ok("bonus 2Lh", data.get("bonus") == 200_000)


def test_numeric_suffixes_in_expressions() -> None:
    src = """I total = 2Cr + 5K
p total
"""
    rt = run(src)
    ok("2Cr + 5K = 20005000", rt.global_scope.get("total") == 20_005_000)


def test_rejects_bad_suffix() -> None:
    from lexer.tokenizer import tokenize
    tokens = tokenize("5Xyz")
    ok("5Xyz parses as integer 5", tokens[0].value == 5)


# -- Run all ----------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)

    print("-" * 60)
    print("Save / Load tests")
    print("-" * 60)
    test_save()
    test_overwrite_save()
    test_load()
    test_load_missing_file()

    print("-" * 60)
    print("Numeric suffix tests")
    print("-" * 60)
    test_numeric_suffix_k()
    test_numeric_suffix_lh()
    test_numeric_suffix_cr()
    test_numeric_suffix_b()
    test_numeric_suffix_tri()
    test_numeric_suffix_qd()
    test_numeric_suffix_in_parser()
    test_numeric_suffix_in_db_save()
    test_numeric_suffixes_in_expressions()
    test_rejects_bad_suffix()

    print("-" * 60)
    print(f"Total: {PASS} passed, {FAIL} failed")
    print("-" * 60)
    sys.exit(1 if FAIL else 0)

    shutil.rmtree(DATA_DIR, ignore_errors=True)
