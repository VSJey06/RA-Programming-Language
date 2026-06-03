"""
main.py — Entry point for the RA Language interpreter.

Usage
-----
    python main.py script.ra
"""

from __future__ import annotations

import argparse
import sys

from lexer.tokenizer import tokenize
from parser.parser import ParseError, Parser
from runtime.autoclose import AutoCloseManager
from runtime.runtime import Runtime
from runtime.runtime import RuntimeError as RAError


def _read_file(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _validate_blocks(source: str) -> None:
    """Run AutoCloseManager validation over *source*.

    Scans the source line-by-line, pushes block openers and pops
    closers, raising ``ValueError`` on any mismatch.

    Parameters
    ----------
    source : str — raw RA source text.

    Raises
    ------
    ValueError — when a block closer does not match the expected one.
    """
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


def _print_error(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Parameters
    ----------
    argv : list[str] | None
        Argument vector (defaults to ``sys.argv[1:]`` when *None*).

    Returns
    -------
    int — process exit code (0 = success, 1 = error).
    """
    parser = argparse.ArgumentParser(
        prog="ra",
        description="RA Language interpreter",
    )
    parser.add_argument(
        "file",
        metavar="FILE",
        help=".ra source file to execute",
    )
    args = parser.parse_args(argv)

    try:
        source = _read_file(args.file)
    except OSError as exc:
        _print_error(str(exc))
        return 1

    try:
        _validate_blocks(source)
    except ValueError as exc:
        _print_error(str(exc))
        return 1

    try:
        tokens = tokenize(source)
        ast = Parser(tokens).parse()
        Runtime().execute(ast)
    except ParseError as exc:
        _print_error(str(exc))
        return 1
    except RAError as exc:
        _print_error(str(exc))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
