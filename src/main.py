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
from runtime.autoclose import AutoCloser
from runtime.runtime import Runtime
from runtime.runtime import RuntimeError as RAError

REPL_BANNER = """\
RA Language REPL
Type 'exit' to quit.\
"""

def _is_block_opener(line: str) -> str | None:
    s = line.strip()
    if s.startswith("Db:"):
        return "db.close"
    if s.startswith("@Cls."):
        return "@.close"
    if s.startswith("M."):
        return "/.close"
    if s.startswith("? For"):
        return "#"
    if s.startswith("? While"):
        return "#"
    if s.startswith("! If"):
        return "#"
    return None


def _execute_source(source: str, runtime: Runtime) -> None:
    """Tokenize, parse, and execute *source* against *runtime*."""
    try:
        tokens = tokenize(source)
        ast = Parser(tokens).parse()
        runtime.execute(ast)
    except ParseError as exc:
        print(f"SyntaxError: {exc}")
    except RAError as exc:
        print(f"RuntimeError: {exc}")


def _read_file(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _validate_blocks(source: str) -> None:
    AutoCloser().validate(source)


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
    except SyntaxError as exc:
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
    buffer: list[str] = []
    closer_stack: list[str] = []

    while True:
        prompt = "...> " if closer_stack else "RA > "
        try:
            line = input(prompt)
        except EOFError:
            print()
            break

        stripped = line.strip()

        if not stripped:
            continue

        if not closer_stack and stripped == "exit":
            break

        if not closer_stack:
            expected = _is_block_opener(stripped)
            if expected is not None:
                closer_stack.append(expected)
                buffer.append(line)
                continue

        buffer.append(line)

        if closer_stack:
            if stripped == closer_stack[-1]:
                closer_stack.pop()
                if not closer_stack:
                    _execute_source("\n".join(buffer), runtime)
                    buffer.clear()
            else:
                expected = _is_block_opener(stripped)
                if expected is not None:
                    closer_stack.append(expected)
        else:
            _execute_source(line, runtime)
            buffer.clear()

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
