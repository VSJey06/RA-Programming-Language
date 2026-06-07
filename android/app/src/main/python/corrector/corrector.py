"""Dynamic Error Interpreter for the RA REPL.

Architecture
------------
Instead of hardcoded pre-validation rules, the corrector now:

1. Runs a fast **pattern-based pre-check** on every line — catches wrong
   case, missing colon, unknown ``@`` declarations, Key-without-value,
   and missing library imports.  This lives in ``_pattern_check()`` and
   uses data from ``patterns.py`` so new keywords are zero-code.

2. For **block openers** the pattern check is sufficient — the body will
   be validated when the block closes.

3. For **single-line statements** the corrector then tries a **deep
   validate** — it tokenizes, parses, and executes the line.  If any
   exception is raised, the ``Translator`` converts it into a friendly
   RA error message using the ``Formatter``.

The translator catches ``ParseError``, ``RuntimeError``, ``SyntaxError``,
and ``ImportError`` — anything the parser or runtime may throw.  Because
translation is driven by data in ``patterns.py``, future language features
automatically benefit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from lexer.tokenizer import tokenize
from parser.parser import ParseError, Parser

from corrector.formatter import (
    syntax_error as _fmt_syntax,
    import_error as _fmt_import,
    case_error as _fmt_case,
    unknown_decl as _fmt_unknown,
    runtime_error as _fmt_runtime,
)
from corrector.patterns import (
    CASE_EXCEPTIONS,
    CASE_MAP,
    CLOSE_CASE_MAP,
    CLOSE_TOKENS,
    SYNTAX_RULES,
    LIBRARY_MAP,
    BLOCK_OPENERS,
)
from corrector.translator import Translator

if TYPE_CHECKING:
    from runtime.runtime import Runtime


class Corrector:
    """Gatekeeper that blocks common syntax mistakes while dynamically
    translating deeper parser/runtime errors into friendly messages.

    Usage
    -----
        corrector = Corrector()
        if not corrector.validate(line, runtime):
            continue   # error already printed, go back to prompt
    """

    def __init__(self) -> None:
        self.translator = Translator()

    def validate(self, line: str, runtime: Optional[Runtime] = None) -> bool:
        """Return True when *line* is acceptable, False when blocked.

        When blocked, a formatted error message is printed.

        Parameters
        ----------
        line : str
            Raw input line from the REPL.
        runtime : Runtime or None
            Current runtime instance (needed for library checks).
        """
        s = line.strip()
        if not s:
            return True

        # Close tokens always pass
        if s in CLOSE_TOKENS:
            return True

        # Phase 1: Fast pattern-based pre-check (case, colon, key, library, @)
        if not self._pattern_check(s, runtime):
            return False

        # Phase 2: Block openers — pattern check is sufficient
        if Corrector._is_block_opener(s):
            return True

        # Phase 3: Single-line statements — deep parse+execute
        return self._deep_validate(line, runtime)

    # ── Phase 1: Pattern-based pre-check ───────────────────────────────

    @staticmethod
    def _pattern_check(s: str, runtime: Optional[Runtime]) -> bool:
        """Run all pattern-based checks.  Return False to block the line."""

        # 1a. Case sensitivity for keywords
        if Corrector._reject_case(s):
            return False

        # 1b. Close-token case sensitivity
        if Corrector._reject_bad_close_case(s):
            return False

        # 1c. Unknown @ declaration
        suggestion = Corrector._unknown_decl(s)
        if suggestion is not None:
            _fmt_unknown(suggestion)
            return False

        # 1d. Key without value
        if s in ("Key", "Key:"):
            _fmt_syntax("Key requires a value.", "Key.variable:")
            return False

        # 1e. Close token skip (exact match only, after case check)
        if s in CLOSE_TOKENS:
            return True

        # 1f. Syntax — missing colon
        for prefix, exact, message, hint in SYNTAX_RULES:
            if exact:
                if s == prefix:
                    _fmt_syntax(message, hint)
                    return False
            else:
                if s.startswith(prefix) and not s.endswith(":"):
                    _fmt_syntax(message, hint)
                    return False

        # 1g. Library dependency
        if not Corrector._check_library(s, runtime):
            return False

        return True

    # ── Phase 3: Deep validate ─────────────────────────────────────────

    def _deep_validate(self, line: str, runtime: Optional[Runtime]) -> bool:
        """Tokenize and parse *line*; translate any parse errors.

        Execution is left to the REPL to avoid double-execution.
        This catches syntax errors that the pattern check misses
        (e.g. malformed expressions, unexpected token sequences).
        """
        try:
            tokens = tokenize(line)
            Parser(tokens).parse()
            return True
        except Exception as exc:
            correction = self.translator.translate_exception(exc, line, runtime)
            if correction is not None:
                Corrector._print_correction(correction)
            return False

    @staticmethod
    def _print_correction(correction) -> None:
        """Route a *Correction* to the appropriate formatter."""
        etype = correction.error_type
        if etype == "SyntaxError":
            if correction.suggestions and correction.keyword:
                _fmt_case(correction.keyword, correction.suggestions[0])
            elif correction.suggestions:
                _fmt_syntax(correction.message, correction.suggestions[0])
            elif correction.hint:
                _fmt_syntax(correction.message, correction.hint)
            else:
                _fmt_syntax(correction.message)
        elif etype == "ImportError":
            library = correction.suggestions[0] if correction.suggestions else "?"
            _fmt_import(correction.message, library)
        else:
            _fmt_runtime(correction.message, correction.suggestions)

    # ── Internal pattern matchers ──────────────────────────────────────

    @staticmethod
    def _is_block_opener(s: str) -> bool:
        """Return True if *s* looks like a block opener line.

        Matches the same patterns as ``_OPENER_MAP`` in autoclose.py.
        """
        if s.startswith("Db") and s.endswith(":"):
            return True
        if s.startswith(".run:"):
            return True
        if s.startswith(".fun:"):
            return True
        if s.startswith("@Cls.") and s.endswith(":"):
            return True
        if s.startswith("M.") and s.endswith(":"):
            return True
        if s.startswith("? For"):
            return True
        if s.startswith("? While"):
            return True
        if s.startswith("! If"):
            return True
        if s.startswith("pH:"):
            return True
        if s.startswith("fF:") or (s.startswith("fF") and "." in s and s.endswith(":")):
            return True
        if s.startswith("Check") and s.endswith(":"):
            return True
        if s.startswith("Key") and s.endswith(":"):
            return True
        if s.startswith("Con") and s.endswith(":"):
            return True
        if s.startswith("En") and s.endswith(":"):
            return True
        return False

    @staticmethod
    def _reject_case(s: str) -> bool:
        """Return True and print error when *s* uses a keyword in wrong case."""
        # Skip tokens that are valid in lowercase (e.g. db.next, db.break)
        if s in CASE_EXCEPTIONS:
            return False
        s_lower = s.lower()
        for kw_lower, correct in CASE_MAP.items():
            if not s_lower.startswith(kw_lower):
                continue
            kw_len = len(kw_lower)
            if kw_lower[-1] not in (".", ":"):
                if kw_len < len(s_lower) and s_lower[kw_len] not in (":", "."):
                    continue
            if not s.startswith(correct):
                keyword_name = correct.rstrip(".:")
                suggestion = correct + s[kw_len:]
                _fmt_case(keyword_name, suggestion)
                return True
        return False

    @staticmethod
    def _reject_bad_close_case(s: str) -> bool:
        """Return True and print error when *s* is a close token in wrong case."""
        s_lower = s.lower()
        for wrong, correct in CLOSE_CASE_MAP.items():
            if s_lower == wrong and s != correct:
                _fmt_case(correct.split(".")[0], correct)
                return True
        return False

    @staticmethod
    def _unknown_decl(s: str) -> Optional[str]:
        """Return suggestion when ``@Name:`` is used instead of ``@Cls.Name:``."""
        if s.startswith("@") and s.endswith(":") and not s.startswith("@Cls.") and not s.startswith("@."):
            name = s[1:-1]
            if name:
                return f"@Cls.{name}:"
        return None

    @staticmethod
    def _check_library(s: str, runtime: Optional[Runtime]) -> bool:
        """Return False when a required library is not active."""
        # PF-dependent blocks
        if s == "pH:" or s.startswith("fF:") or (s.startswith("fF.") and ":" in s):
            if runtime is not None and hasattr(runtime, "_pf_engine") and not runtime._pf_engine.active:
                _fmt_import("PF library not imported.", "PF")
                return False
            return True
        # OOP-dependent blocks
        if s in ("Con:", "En:") or s.startswith("Obj."):
            if runtime is not None and hasattr(runtime, "_oop_active") and not runtime._oop_active:
                _fmt_import("OOP library not imported.", "OOP")
                return False
            return True
        return True
