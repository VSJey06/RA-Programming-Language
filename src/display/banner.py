"""REPL banner for the RA Language interpreter."""

REPL_BANNER = """\
|--------------------------------------|
|                                      |
|  RA  V.1.0.5                         |
|  ----------------------------------  |
|  Commands                            |
|  help  - Show language guide         |
|  exit  - Exit RA                     |
|  clear - Clear terminal screen       |
|  reset - Reboot RA runtime           |
|                                      |
|--------------------------------------|"""


def get_banner() -> str:
    """Return the REPL banner string."""
    return REPL_BANNER
