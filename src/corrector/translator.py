"""Dynamic error translator — converts parser/runtime exceptions into
user-friendly RA language messages using pattern-driven rules.

The translator does NOT pre-validate input.  It reacts to exceptions
raised by the parser or runtime, analyzes the error + the original line,
and produces a ``Correction`` value object that the formatter can render.

New language features automatically benefit as long as their error
signatures follow the existing patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from lexer.tokenizer import TokenizeError

from parser.parser import ParseError

from corrector.patterns import CASE_MAP, CLOSE_CASE_MAP

if TYPE_CHECKING:
    from runtime.runtime import Runtime


@dataclass
class Correction:
    """A friendly error correction produced by the translator.

    Attributes
    ----------
    error_type : str
        One of ``"SyntaxError"``, ``"ImportError"``, ``"RuntimeError"``.
    message : str
        Human-readable error description.
    hint : str or None
        Optional suggestion / expected form.
    suggestions : list[str] or None
        Optional alternative suggestions (used by ImportError / RuntimeError
        and case corrections).
    keyword : str or None
        The keyword name for case corrections (e.g. ``"pH"``).
    """
    error_type: str = "SyntaxError"
    message: str = ""
    hint: str | None = None
    suggestions: list[str] | None = None
    keyword: str | None = None


# ── Translator ───────────────────────────────────────────────────────────

class Translator:
    """Translates internal exceptions into user-friendly Corrections.

    Usage
    -----
        correction = Translator().translate_exception(exc, line, runtime)
        if correction:
            formatter.print(correction)
    """

    @staticmethod
    def translate_exception(
        exc: Exception,
        line: str,
        runtime: Any = None,
    ) -> Correction | None:
        """Return a ``Correction`` for *exc*, or None if untranslatable."""
        if isinstance(exc, TokenizeError):
            return Translator._translate_tokenize(exc, line)
        if isinstance(exc, ParseError):
            return Translator._translate_parse(exc, line)
        if isinstance(exc, RuntimeError) and "not activated" in str(exc).lower():
            return Correction("ImportError", "PF library not imported.", suggestions=["PF"])
        if isinstance(exc, RuntimeError):
            return Correction("RuntimeError", getattr(exc, "message", str(exc)))
        if isinstance(exc, RuntimeError):
            return Correction("RuntimeError", str(exc))
        if isinstance(exc, SyntaxError):
            return Correction("SyntaxError", exc.msg if hasattr(exc, "msg") else str(exc))
        if isinstance(exc, ImportError):
            return Correction("ImportError", str(exc))
        # Fallback: unknown exception type
        return Correction("SyntaxError", str(exc))

    # ── TokenizeError translation ─────────────────────────────────────

    @staticmethod
    def _translate_tokenize(exc: TokenizeError, line: str) -> Correction:
        msg = getattr(exc, "message", str(exc))
        return Correction("SyntaxError", msg, hint=line.strip())

    # ── ParseError translation ─────────────────────────────────────────

    @staticmethod
    def _translate_parse(exc: ParseError, line: str) -> Correction:
        """Translate a ``ParseError`` into a friendly correction.

        Strategy:
          1. Try case correction on the line (wrong-case keyword).
          2. Try close-token case correction.
          3. Try unknown ``@`` declaration detection.
          4. Fall back to the raw parser message.
        """
        s = line.strip()

        # 1. Case correction for keywords (prefix match only)
        for wrong, correct in CASE_MAP.items():
            if s.lower().startswith(wrong):
                replacement_end = len(wrong)
                suggestion = correct + s[replacement_end:]
                kw = wrong.rstrip(".:")
                return Correction(
                    "SyntaxError",
                    f"Invalid keyword '{kw}'",
                    hint=None,
                    suggestions=[suggestion],
                    keyword=kw,
                )

        # 2. Close-token case correction
        stripped = s.lower()
        for wrong, correct in CLOSE_CASE_MAP.items():
            if stripped == wrong:
                kw = wrong.split(".")[0]
                return Correction(
                    "SyntaxError",
                    f"Invalid keyword '{kw}'",
                    hint=None,
                    suggestions=[correct],
                    keyword=kw,
                )

        # 3. Unknown @ declaration  (e.g. @Person: → @Cls.Person:)
        if s.startswith("@") and s.endswith(":") and not s.startswith("@Cls.") and not s.startswith("@."):
            name = s[1:-1]
            if name:
                return Correction(
                    "SyntaxError",
                    "Unknown declaration.",
                    hint=None,
                    suggestions=[f"@Cls.{name}:"],
                )

        # 4. Fallback — raw parser message, stripped of token info
        msg = exc.message if hasattr(exc, "message") else str(exc)
        return Correction("SyntaxError", msg)

    # ── RuntimeError translation ───────────────────────────────────────

    @staticmethod
    def _translate_runtime(exc: RuntimeError, line: str) -> Correction:
        """Translate a ``RuntimeError`` into a friendly correction."""
        msg = getattr(exc, "message", str(exc))
        return Correction("RuntimeError", msg)
