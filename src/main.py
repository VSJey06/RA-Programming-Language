"""
main.py — Entry point for the RA Language interpreter.

Usage
-----
    python main.py                    # launch interactive REPL
    python main.py script.ra          # execute a .ra source file
    python main.py --debug script.ra  # execute with AST dump
    python main.py --version          # print version and exit
    python main.py --help             # print usage and exit

REPL commands
-------------
    .help   — show available REPL commands
    .vars   — list all variables in the current scope
    .clear  — discard the current input buffer
    .reset  — wipe the runtime (variables, classes, objects)
    .exit   — quit  (also: Ctrl-D / Ctrl-C twice)

RA block syntax reminder
------------------------
    ! If.cond,  …  #          if / !! elseif / ! Else … #
    ? For.i=0;n,  …  #        for range
    ? While.cond,  …  #       while
    M.name:  …  /             method definition
    @Cls.Name:  …  @          class definition
    Db:  …  db.close          database block
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Optional

# ── Imports from the RA package ───────────────────────────────────────────────
#
# Project layout expected by the parser's own imports:
#
#   src/
#   ├── main.py
#   ├── lexer/
#   │   ├── tokens.py        (Token, TokenType)
#   │   └── tokenizer.py     (tokenize)
#   ├── parser/
#   │   ├── parser.py        (Parser, ParseError)
#   │   └── ra_ast.py        (ProgramNode, dump, …)
#   └── runtime/
#       └── runtime.py       (Runtime, RuntimeError → RAError)

from lexer.tokenizer import tokenize              # list[Token] ← str
from parser.parser import ParseError, Parser      # recursive-descent parser
from parser.ra_ast import ProgramNode, dump       # AST root + pretty-printer
from runtime.runtime import Runtime
from runtime.runtime import RuntimeError as RAError

# ── Version & display constants ───────────────────────────────────────────────

VERSION = "0.1.0"

BANNER = """\
╭──────────────────────────────────────╮
│   RA Language  v{ver:<22}│
│   Type .help for REPL commands       │
╰──────────────────────────────────────╯""".format(ver=VERSION)

HELP_TEXT = """\
REPL commands:
  .help    show this message
  .vars    list all variables currently in scope
  .clear   discard the current (possibly incomplete) input buffer
  .reset   wipe the runtime — clears variables, classes, and objects
  .exit    quit  (also Ctrl-D or Ctrl-C)

Input rules:
  • A blank line flushes and executes the current buffer.
  • Multi-line blocks accumulate until explicitly closed:
      If/ElseIf/Else → closed by  #
      For / While    → closed by  #
      Method (M.)    → closed by  /
      Class (@Cls.)  → closed by  @
      Db block       → closed by  db.close"""

# ── Core execution ────────────────────────────────────────────────────────────


def _parse(source: str) -> ProgramNode:
    """Tokenize *source* and return a parsed ``ProgramNode``.

    Parameters
    ----------
    source : str — raw RA source text.

    Raises
    ------
    ParseError — when the parser encounters a syntax error.
    """
    tokens = tokenize(source)
    return Parser(tokens).parse()


def run_code(source: str, runtime: Runtime, *, debug: bool = False) -> None:
    """Parse *source* and execute it against *runtime*.

    Parameters
    ----------
    source  : str     — raw RA source text.
    runtime : Runtime — interpreter that holds the execution context.
    debug   : bool    — when ``True``, print the AST before running.

    Raises
    ------
    ParseError — forwarded from the parser on malformed input.
    RAError    — forwarded from the runtime on execution errors.
    """
    ast = _parse(source)

    if debug:
        _dump_ast(ast)

    runtime.execute(ast)


def run_file(path: str, *, debug: bool = False) -> int:
    """Load and execute a ``.ra`` source file.

    Parameters
    ----------
    path  : str  — filesystem path to the source file.
    debug : bool — when ``True``, print the AST before running.

    Returns
    -------
    int — 0 on success, 1 on any error.
    """
    if not os.path.isfile(path):
        _print_error(f"file not found: {path!r}")
        return 1

    if not path.endswith(".ra"):
        _print_warn(f"file does not carry a .ra extension: {path!r}")

    try:
        source = _read_file(path)
    except OSError as exc:
        _print_error(f"cannot read file: {exc}")
        return 1

    runtime = Runtime()

    try:
        run_code(source, runtime, debug=debug)
    except ParseError as exc:
        _report_parse_error(exc, source)
        return 1
    except RAError as exc:
        _print_error(str(exc))
        return 1
    except Exception as exc:  # noqa: BLE001
        _print_error(f"unexpected error: {exc}")
        return 1

    return 0


# ── REPL ──────────────────────────────────────────────────────────────────────


def repl(*, debug: bool = False) -> None:
    """Start an interactive Read-Eval-Print Loop.

    A single ``Runtime`` is shared across all inputs so that variable
    assignments and class definitions persist between entries.

    Parameters
    ----------
    debug : bool — when ``True``, print the AST for every executed chunk.
    """
    print(BANNER)
    print()

    runtime = Runtime()
    buffer: list[str] = []
    _ctrl_c_count = 0

    while True:
        prompt = "RA>  " if not buffer else "...> "

        try:
            line = input(prompt)
            _ctrl_c_count = 0
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            _ctrl_c_count += 1
            if _ctrl_c_count >= 2:
                print("Interrupted — exiting.")
                break
            if buffer:
                buffer.clear()
                print("Buffer cleared.  (Press Ctrl-C again or type .exit to quit.)")
            else:
                print("Press Ctrl-C again or type .exit to quit.")
            continue

        stripped = line.strip()

        # ── REPL commands ────────────────────────────────────────────────

        if stripped in (".exit", "exit"):
            break

        if stripped == ".help":
            print(HELP_TEXT)
            continue

        if stripped == ".vars":
            _show_scope(runtime)
            continue

        if stripped == ".clear":
            buffer.clear()
            print("Buffer cleared.")
            continue

        if stripped == ".reset":
            runtime = Runtime()
            buffer.clear()
            print("Runtime reset.")
            continue

        # ── Accumulate & dispatch ────────────────────────────────────────

        buffer.append(line)
        source = "\n".join(buffer)

        if not _is_complete(source):
            continue

        _execute_buffer(source, runtime, debug=debug)
        buffer.clear()


# ── Completeness heuristic (RA keyword delimiters) ────────────────────────────

# RA uses keyword-based terminators — NOT braces.
_BLOCK_OPENER = re.compile(
    r"""^(?:
        !\s+\w      |   # ! If ...
        \?\s+\w     |   # ? For ... / ? While ...
        M\.\w+\s*:  |   # M.name:
        Db\s*:      |   # Db:
        @Cls\.\w+       # @Cls.Name:
    )""",
    re.VERBOSE,
)
_BLOCK_CLOSERS = frozenset({"#", "/", "@", "db.close"})


def _is_complete(source: str) -> bool:
    """Return ``True`` when *source* is a complete, dispatchable unit.

    Tracks unmatched block openers vs explicit block closers.
    A blank (empty) last line always triggers immediate dispatch —
    the parser's auto-close will handle any still-open constructs.

    Parameters
    ----------
    source : str — accumulated REPL input so far.
    """
    lines = source.split("\n")
    last = lines[-1].rstrip()

    # A blank line always flushes — auto-close handles the rest.
    if last == "":
        return True

    # Walk non-empty lines and track depth.
    depth = 0
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if _BLOCK_OPENER.match(s):
            depth += 1
        if s in _BLOCK_CLOSERS:
            depth = max(0, depth - 1)

    # Balanced (or no openers at all) → ready to execute.
    return depth == 0


# ── Execution helper ──────────────────────────────────────────────────────────


def _execute_buffer(source: str, runtime: Runtime, *, debug: bool) -> None:
    """Parse and execute *source*, printing a friendly message on failure."""
    source = source.strip()
    if not source:
        return

    try:
        run_code(source, runtime, debug=debug)
    except ParseError as exc:
        _report_parse_error(exc, source)
    except RAError as exc:
        _print_error(str(exc))
    except Exception as exc:  # noqa: BLE001
        _print_error(f"unexpected error: {exc}")


# ── Display helpers ───────────────────────────────────────────────────────────


def _show_scope(runtime: Runtime) -> None:
    """Pretty-print all variables in ``global_scope``."""
    scope = runtime.global_scope
    if not scope:
        print("  (no variables defined)")
        return
    col = max(len(k) for k in scope)
    for name, value in sorted(scope.items()):
        print(f"  {name:<{col}}  =  {value!r}")


def _dump_ast(ast: ProgramNode) -> None:
    """Print the AST using ra_ast's own ``dump()`` pretty-printer."""
    print("── AST ──────────────────────────────────────────────────────────")
    print(dump(ast))
    print("─────────────────────────────────────────────────────────────────")


def _report_parse_error(exc: ParseError, source: str) -> None:
    """Display a ``ParseError`` with a source snippet and column caret.

    ``ParseError`` carries a ``.token`` with ``.line`` and (optionally)
    ``.col`` attributes set by the tokenizer.

    Parameters
    ----------
    exc    : ParseError — the parser exception.
    source : str        — original source text (used for line snippets).
    """
    lines = source.splitlines()
    token = exc.token
    lineno: int = getattr(token, "line", 0)
    col: Optional[int] = getattr(token, "col", None)

    # exc.__str__() already contains "[line N] ParseError: …" from __init__
    print(str(exc), file=sys.stderr)

    if lineno and 1 <= lineno <= len(lines):
        print(f"  {lines[lineno - 1]}", file=sys.stderr)
        if col and col > 0:
            print(f"  {' ' * (col - 1)}^", file=sys.stderr)


def _print_error(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)


def _print_warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def _read_file(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ── CLI ───────────────────────────────────────────────────────────────────────


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ra",
        description="RA Language interpreter",
        epilog="Run without arguments to launch the interactive REPL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "file",
        nargs="?",
        metavar="FILE",
        help=".ra source file to execute (omit to start the REPL)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="print the parsed AST before executing",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"RA Language {VERSION}",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point.

    Parameters
    ----------
    argv : list[str] | None
        Argument vector (defaults to ``sys.argv[1:]`` when *None*).

    Returns
    -------
    int — process exit code (0 = success, non-zero = error).
    """
    args = _build_arg_parser().parse_args(argv)

    if args.file:
        return run_file(args.file, debug=args.debug)

    repl(debug=args.debug)
    return 0


if __name__ == "__main__":
    sys.exit(main())
