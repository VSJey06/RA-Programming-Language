"""REPL banner for the RA Language interpreter — Rich-styled Panel."""

from __future__ import annotations

from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich import box


_REPL_BANNER_TEXT = """\
RA Language v1.0.5

OOP • DSA • AI • PAC

Stack • Queue • Dequeue
"""


def get_banner_plain() -> str:
    """Return the banner as a plain text version string."""
    return "RA Language v1.0.5"


def get_banner() -> Panel:
    """Return a Rich-styled banner Panel."""
    content = Text()
    content.append("RA Language v1.0.5\n", style="bold bright_cyan")
    content.append("\n")
    content.append("OOP • DSA • AI • PAC\n", style="yellow")
    content.append("\n")
    content.append("Stack • Queue • Dequeue", style="green")

    return Panel(
        Align.center(content),
        border_style="bright_blue",
        padding=(1, 2),
        box=box.ROUNDED,
    )
