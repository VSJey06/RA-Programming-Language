"""REPL exit-command detection."""


def should_exit(command: str) -> bool:
    """Return True when *command* signals the REPL should stop."""
    return command == "exit"
