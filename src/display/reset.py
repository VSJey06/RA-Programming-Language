"""Runtime-reset for the RA REPL."""

from runtime.runtime import Runtime


def reset_runtime() -> Runtime:
    """Create and return a fresh Runtime, printing a confirmation."""
    print("RA Runtime restarted.")
    return Runtime()
