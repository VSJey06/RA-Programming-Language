"""Launcher metadata for the RA Language interpreter.

Future use: cross-platform RA / ra startup support.
"""

LAUNCHER_INFO: dict[str, object] = {
    "name": "RA",
    "version": "1.0.3",
    "aliases": ("ra", "RA"),
}


def launcher_info() -> dict[str, object]:
    """Return launcher metadata dictionary."""
    return LAUNCHER_INFO
