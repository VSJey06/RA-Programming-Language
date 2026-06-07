"""Terminal screen-clearing for the RA REPL."""

import os
import subprocess


def clear_screen(banner: str = "") -> None:
    """Clear the terminal and optionally re-print *banner*."""
    subprocess.run(
        "cls" if os.name == "nt" else "clear",
        shell=True,
    )
    if banner:
        print(banner)
        print()
