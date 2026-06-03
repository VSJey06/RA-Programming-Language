"""
main.py — Entry point for the RA Language interpreter.

Usage
-----
    python main.py              # interactive REPL
    python main.py script.ra    # execute a .ra source file
"""

from __future__ import annotations

import argparse
import sys

from lexer.tokenizer import tokenize
from parser.parser import ParseError, Parser
from runtime.autoclose import AutoCloseManager
from runtime.runtime import Runtime
from runtime.runtime import RuntimeError as RAError

REPL_BANNER = """\
RA Language REPL
Type 'exit' to quit.\
"""


def _read_file(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _validate_blocks(source: str) -> None:
    mgr = AutoCloseManager()
    for line in source.splitlines():
        s = line.strip()
        if not s:
            continue

        if s.startswith("!") and not s.startswith("!"):
            mgr.push("!")
        elif s.startswith("?") and not s.startswith("?"):
            mgr.push("?")
        elif s.startswith("M.") and ":" in s:
            mgr.push("/")
        elif s.startswith("Db:") or s.startswith("Db :"):
            mgr.push("Db")
        elif s.startswith("@Cls."):
            mgr.push("@")
        elif s == "#":
            mgr.pop("#.close")
        elif s == "/":
            mgr.pop("/.close")
        elif s == "@":
            mgr.pop("@.close")
        elif s == "db.close":
            mgr.pop("Db.close")
        elif s.startswith("!"):
            mgr.pop("!.close")

    if mgr.expected_closer() is not None:
        raise ValueError(f"Unclosed block: expected {mgr.expected_closer()!r}")


def _run_source(source: str) -> None:
    """Tokenize, parse, and execute *source*."""
    tokens = tokenize(source)
    ast = Parser(tokens).parse()
    Runtime().execute(ast)


def _run_file(path: str) -> int:
    try:
        source = _read_file(path)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        _validate_blocks(source)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        _run_source(source)
    except ParseError as exc:
        print(f"SyntaxError: {exc}", file=sys.stderr)
        return 1
    except RAError as exc:
        print(f"RuntimeError: {exc}", file=sys.stderr)
        return 1

    return 0


def _repl() -> int:
    print(REPL_BANNER)
    print()
    runtime = Runtime()

    while True:
        try:
            line = input("RA > ")
        except EOFError:
            print()
            break

        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "exit":
            break

        try:
            tokens = tokenize(stripped)
            ast = Parser(tokens).parse()
            runtime.execute(ast)
        except ParseError as exc:
            print(f"SyntaxError: {exc}")
        except RAError as exc:
            print(f"RuntimeError: {exc}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ra",
        description="RA Language interpreter",
    )
    parser.add_argument(
        "file",
        nargs="?",
        metavar="FILE",
        help=".ra source file to execute (omit for REPL)",
    )
    args = parser.parse_args(argv)

    if args.file:
        return _run_file(args.file)

    return _repl()


if __name__ == "__main__":
    sys.exit(main())
