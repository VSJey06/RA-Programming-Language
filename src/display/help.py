"""Help system for the RA Language interpreter.

Deprecated: HELP_TEXT is no longer the documentation source.
The Syntax Library (display/syntax_library) is now the single
source of truth.  show_help() redirects to it.
"""

from display.syntax_library import render_all, render_category_by_name


def show_help(category: str = "") -> None:
    """Print RA syntax reference from the Syntax Library.

    When *category* is provided, only that category is shown.
    """
    if category:
        rendered = render_category_by_name(category)
        if rendered is not None:
            print(rendered)
        else:
            print(f"Unknown category: {category!r}")
            print("Available: Variables, Print, PAC System, Stack, Queue, Dequeue, "
                  "Special Values, Methods, Classes, Objects, OOP Library, Database, "
                  "Check / Exception Handling, Key / Switch, Loops, Conditions, "
                  "Blocks, PF Framework, AI Library, REPL Commands")
        return
    print(render_all())
