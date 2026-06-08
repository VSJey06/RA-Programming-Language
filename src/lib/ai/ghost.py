"""
ghost.py — Ghost-text input handler for RA REPL.

Provides inline ghost text autocomplete (like GitHub Copilot / Cursor)
using the Windows Console API.  Falls back to a [TAB] hint when the
console cannot display styled text inline.
"""

from __future__ import annotations

import ctypes
import msvcrt
import sys
from ctypes import wintypes

STD_OUTPUT_HANDLE = -11

kernel32 = ctypes.windll.kernel32


class COORD(ctypes.Structure):
    _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]


class SMALL_RECT(ctypes.Structure):
    _fields_ = [("Left", wintypes.SHORT), ("Top", wintypes.SHORT),
                ("Right", wintypes.SHORT), ("Bottom", wintypes.SHORT)]


class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
    _fields_ = [("dwSize", COORD), ("dwCursorPosition", COORD),
                ("wAttributes", wintypes.WORD), ("srWindow", SMALL_RECT),
                ("dwMaximumWindowSize", COORD)]


# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------

def _ghost_available() -> bool:
    try:
        kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        return True
    except Exception:
        return False


def _cursor_pos() -> tuple[int, int]:
    info = CONSOLE_SCREEN_BUFFER_INFO()
    kernel32.GetConsoleScreenBufferInfo(
        kernel32.GetStdHandle(STD_OUTPUT_HANDLE), ctypes.byref(info))
    return info.dwCursorPosition.X, info.dwCursorPosition.Y


def _set_cursor(x: int, y: int) -> None:
    kernel32.SetConsoleCursorPosition(
        kernel32.GetStdHandle(STD_OUTPUT_HANDLE), COORD(x, y))


def _write_ghost_text(text: str) -> None:
    """Write *text* in dim gray at the cursor and restore the cursor position."""
    if not text:
        return
    h = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    info = CONSOLE_SCREEN_BUFFER_INFO()
    kernel32.GetConsoleScreenBufferInfo(h, ctypes.byref(info))
    ox, oy = info.dwCursorPosition.X, info.dwCursorPosition.Y
    attr = info.wAttributes

    kernel32.SetConsoleTextAttribute(h, 8)          # dark gray
    written = wintypes.DWORD(0)
    kernel32.WriteConsoleW(h, text, len(text),
                           ctypes.byref(written), None)
    kernel32.SetConsoleTextAttribute(h, attr)       # restore
    _set_cursor(ox, oy)


# ---------------------------------------------------------------------------
# Core ghost reader
# ---------------------------------------------------------------------------

def read_line(prompt: str,
              suggest_fn: callable) -> str:
    """Read a line from stdin with inline ghost-text suggestions.

    *suggest_fn(buffer)* → ghost text (str) or *None*.

    Tab           – accept the full ghost text.
    Right Arrow   – accept the next token only.
    Ctrl+C        – raise KeyboardInterrupt.
    Ctrl+D        – return empty string (EOF).

    Falls back to a ``[TAB] <suggestion>`` hint when the Windows Console
    API is unavailable.
    """
    if not _ghost_available():
        return _read_line_fallback(prompt, suggest_fn)

    buffer = ""
    ghost = ""

    sys.stdout.write(prompt)
    sys.stdout.flush()

    # initial ghost at empty prompt
    ghost = suggest_fn("") or ""
    if ghost:
        _write_ghost_text(ghost)

    while True:
        ch = msvcrt.getch()

        # --- Enter -----------------------------------------------------------
        if ch == b"\r":
            _clear_line(prompt, buffer, ghost)
            sys.stdout.write("\n")
            sys.stdout.flush()
            return buffer

        # --- Tab → accept full ghost -----------------------------------------
        if ch == b"\t":
            if ghost:
                buffer += ghost
                ghost = suggest_fn(buffer) or ""
                _redraw(prompt, buffer, ghost)
            continue

        # --- Arrow keys (prefix 0xE0 on Windows) ----------------------------
        if ch == b"\xe0":
            ch2 = msvcrt.getch()
            if ch2 == b"M":          # Right arrow → accept next token
                if ghost:
                    trimmed = ghost.lstrip()
                    sp = trimmed.find(" ")
                    token = trimmed[:sp] if sp != -1 else trimmed
                    lead = len(ghost) - len(trimmed)
                    accepted = ghost[:lead] + token
                    buffer += accepted
                    ghost = suggest_fn(buffer) or ""
                    _redraw(prompt, buffer, ghost)
            continue

        # --- Backspace -------------------------------------------------------
        if ch == b"\x08":
            if buffer:
                buffer = buffer[:-1]
                ghost = suggest_fn(buffer) or ""
                _redraw(prompt, buffer, ghost)
            continue

        # --- Ctrl+C / Ctrl+D -------------------------------------------------
        if ch == b"\x03":
            _clear_line(prompt, buffer, ghost)
            sys.stdout.write("\n")
            sys.stdout.flush()
            raise KeyboardInterrupt

        if ch == b"\x1a" or ch == b"\x04":          # Ctrl+Z / Ctrl+D
            _clear_line(prompt, buffer, ghost)
            sys.stdout.write("\n")
            sys.stdout.flush()
            return ""

        # --- Regular character -----------------------------------------------
        try:
            char = ch.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if not char.isprintable():
            continue
        buffer += char
        ghost = suggest_fn(buffer) or ""
        _redraw(prompt, buffer, ghost)


# ---------------------------------------------------------------------------
# Fallback reader (no console API)
# ---------------------------------------------------------------------------

def _read_line_fallback(prompt: str,
                        suggest_fn: callable) -> str:
    """Show ``[TAB] <suggestion>`` when ghost text is unavailable."""
    buffer = ""
    ghost_hint = ""

    sys.stdout.write(prompt)
    sys.stdout.flush()

    while True:
        ch = msvcrt.getch()

        if ch == b"\r":
            _clear_line(prompt, buffer, ghost_hint)
            sys.stdout.write("\n")
            sys.stdout.flush()
            return buffer

        if ch == b"\t":
            ghost = suggest_fn(buffer) or ""
            if ghost:
                buffer += ghost
                ghost_hint = _hint(suggest_fn(buffer))
                _redraw_fb(prompt, buffer, ghost_hint)
            continue

        if ch == b"\x08":
            if buffer:
                buffer = buffer[:-1]
            ghost_hint = _hint(suggest_fn(buffer))
            _redraw_fb(prompt, buffer, ghost_hint)
            continue

        if ch in (b"\x03", b"\x1a", b"\x04"):
            _clear_line(prompt, buffer, ghost_hint)
            sys.stdout.write("\n")
            sys.stdout.flush()
            if ch == b"\x03":
                raise KeyboardInterrupt
            return ""

        try:
            char = ch.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if not char.isprintable():
            continue
        buffer += char
        ghost_hint = _hint(suggest_fn(buffer))
        _redraw_fb(prompt, buffer, ghost_hint)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _hint(ghost: str | None) -> str:
    return f" [TAB] {ghost}" if ghost else ""


def _clear_line(prompt: str, buffer: str, extra: str = "") -> None:
    total = len(prompt) + len(buffer) + len(extra)
    sys.stdout.write("\r" + " " * total + "\r")


def _redraw(prompt: str, buffer: str, ghost: str) -> None:
    _clear_line(prompt, buffer, ghost)
    sys.stdout.write(prompt + buffer)
    sys.stdout.flush()
    if ghost:
        _write_ghost_text(ghost)


def _redraw_fb(prompt: str, buffer: str, hint: str) -> None:
    _clear_line(prompt, buffer, hint)
    line = prompt + buffer + hint
    sys.stdout.write(line)
    sys.stdout.flush()
    # move cursor back before the hint
    if hint:
        cx, cy = _cursor_pos()
        _set_cursor(cx - len(hint), cy)
