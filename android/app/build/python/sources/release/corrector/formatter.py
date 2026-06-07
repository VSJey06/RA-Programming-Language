"""Error output formatters — standardised display for RA error messages.

Each function prints directly to stdout so the REPL can reject a line
after showing the error.  The output format is consistent across all
error types.
"""

from __future__ import annotations


def syntax_error(message: str, hint: str | None = None) -> None:
    """Print a SyntaxError with an optional ``Expected`` hint."""
    print("SyntaxError:")
    print(f"  {message}")
    if hint is not None:
        print()
        print("Expected:")
        print()
        print(f"    {hint}")
    print()


def import_error(message: str, library: str) -> None:
    """Print an ImportError with a ``Required`` library hint."""
    print("ImportError:")
    print(f"  {message}")
    print()
    print("Required:")
    print()
    print(f"    {library}")
    print()


def runtime_error(message: str, suggestions: list[str] | None = None) -> None:
    """Print a RuntimeError with optional suggestions."""
    print("RuntimeError:")
    print(f"  {message}")
    if suggestions:
        print()
        print("Suggestions:")
        for s in suggestions:
            print(f"    {s}")
    print()


def case_error(keyword: str, suggestion: str) -> None:
    """Print a case-sensitivity SyntaxError with ``Did you mean`` hint."""
    print("SyntaxError:")
    print(f"  Invalid keyword '{keyword.lower()}'")
    print()
    print("Did you mean:")
    print()
    print(f"    {suggestion}")
    print()


def unknown_decl(suggestion: str) -> None:
    """Print an unknown-declaration SyntaxError."""
    print("SyntaxError:")
    print("  Unknown declaration.")
    print()
    print("Did you mean:")
    print()
    print(f"    {suggestion}")
    print()
