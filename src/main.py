"""
main.py — Entry point for the RA Language interpreter.

Usage
-----
    python main.py                  # classic terminal REPL
    python main.py script.ra        # execute a .ra source file
    python main.py --ide            # GUI IDE (Tkinter)
"""

from __future__ import annotations

import argparse
import os
import sys

from lexer.tokenizer import TokenizeError, tokenize
from parser.parser import ParseError, Parser
from runtime.autoclose import AutoCloser
from runtime.runtime import Runtime
from runtime.runtime import RuntimeError as RAError

from lib.ai.assist import MentorEngine as Assist


def _read_file(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _validate_blocks(source: str) -> None:
    AutoCloser().validate(source)


def _run_source(source: str) -> None:
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
    except SyntaxError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    try:
        _run_source(source)
    except TokenizeError as exc:
        print(f"SyntaxError: {exc.message}", file=sys.stderr)
        return 1
    except ParseError as exc:
        print(f"SyntaxError: {exc}", file=sys.stderr)
        return 1
    except RAError as exc:
        print(f"RuntimeError: {exc}", file=sys.stderr)
        return 1
    return 0


def _repl() -> int:
    from display.layout import launch as launch_layout
    Assist.ensure_loaded()
    return launch_layout()


# ── IDE mode (GUI Terminal) ──────────────────────────────────

def _repl_ide() -> int:
    from display.ra_terminal import launch as launch_terminal
    Assist.ensure_loaded()
    return launch_terminal()


# ── Entry point ───────────────────────────────────────────────

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
    parser.add_argument(
        "--ide",
        action="store_true",
        help="Launch GUI IDE (Tkinter) instead of terminal REPL",
    )
    args = parser.parse_args(argv)

    if args.file:
        return _run_file(args.file)

    if args.ide:
        return _repl_ide()

    return _repl()


if __name__ == "__main__":
    sys.exit(main())
