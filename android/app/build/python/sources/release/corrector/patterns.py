"""Correction patterns — data-driven rules for the error translator.

All keyword-case mappings, syntax rules, library requirements, and close
tokens live here as plain data.  The translator uses these patterns to
convert internal exceptions into user-friendly RA language messages.

Adding a new keyword or block type requires only adding entries here;
no corrector logic changes are needed.
"""

from __future__ import annotations

# ── Case correction ──────────────────────────────────────────────────────
# Maps wrong-case prefix → correct-case prefix.
# The translator uses these to suggest the right keyword spelling.
CASE_MAP: dict[str, str] = {
    "@cls.": "@Cls.",
    "m.":    "M.",
    "check": "Check",
    "key.":  "Key.",
    "ph":    "pH",
    "ff":    "fF",
    "con":   "Con",
    "en":    "En",
}

# Close tokens with wrong case → correct case.
CLOSE_CASE_MAP: dict[str, str] = {
    "en.close":   "En.close",
    "con.close":  "Con.close",
    "key.close":  "Key.close",
    "check.close": "Check.close",
    "ph.close":   "pH.close",
    "ff.close":   "f.close",
}

# Lowercase keywords that are valid as-is (not case-corrected).
# The ``db.`` prefix in ``CASE_MAP`` would otherwise block these.
CASE_EXCEPTIONS: frozenset[str] = frozenset({
    "db.next",
    "db.break",
    "db.close",
})

# ── Close tokens ─────────────────────────────────────────────────────────
# Exact-match tokens that close a multiline block.
CLOSE_TOKENS: frozenset[str] = frozenset({
    "db.close", "r.close", "f.close", "@.close", "/.close",
    "#", "pH.close", "Check.close", "Key.close", "Con.close", "En.close",
})

# ── Syntax rules ─────────────────────────────────────────────────────────
# Each entry: (prefix, exact_match, error_message, hint)
#   exact_match=True  → the line must EQUAL prefix to trigger
#   exact_match=False → the line must START WITH prefix and NOT end with ':'
SYNTAX_RULES: list[tuple[str, bool, str, str]] = [
    ("M.",    False, "Method declaration requires ':'",      "M.Name:"),
    ("@Cls.", False, "Class declaration requires ':'",       "@Cls.Name:"),
    ("Check",  True, "Check block requires ':'",             "Check:"),
    ("Key.",   False, "Key expression requires ':'",          "Key.value:"),
    ("pH",     True, "pH block requires ':'",                "pH:"),
    ("fF",     True, "fF block requires ':'",                "fF:"),
    ("fF.",    False, "fF target requires ':'",              "fF.target:"),
    ("Con",    True, "Constructor requires ':'",             "Con:"),
    ("En",     True, "Encapsulation requires ':'",           "En:"),
    ("Db.",    False, "Database block requires ':'",         "Db.Name:"),
]

# ── Library requirements ────────────────────────────────────────────────
# Maps a keyword → the library it requires.
LIBRARY_MAP: dict[str, str] = {
    "pH":  "PF",
    "fF":  "PF",
    "Con": "OOP",
    "En":  "OOP",
    "Obj": "OOP",
}

# Keywords that start a block (used by REPL _is_block_opener equivalent).
BLOCK_OPENERS: dict[str, str] = {
    "Db":     "db.close",
    "pH":     "pH.close",
    "fF":     "f.close",
    ".run":   "r.close",
    ".fun":   "f.close",
    "@Cls.":  "@.close",
    "M.":     "/.close",
    "? For":  "#",
    "? While":"#",
    "! If":   "#",
    "Check":   "Check.close",
    "Key":     "Key.close",
    "Con":     "Con.close",
    "En":      "En.close",
}
