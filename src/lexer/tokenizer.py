"""
tokenizer.py — Lexer for the RA language
Converts raw source text into a flat list of Token objects.

Supported constructs
--------------------
  Keywords    : S  I  L  Cls  Obj  M  Db  db.next  db.break  db.close  AI  p
  Symbols     : =  .  :  ==  ,  @  !  ?  #  /
  Literals    : STRING  INTEGER  IDENTIFIER
  Comments    : # …  (rest of line is ignored after the HASH token)

Pattern examples correctly tokenized
--------------------------------------
  Db:              → DB  COLON
  @Cls.Person:     → AT  CLS  DOT  IDENTIFIER("Person")  COLON
  M.calculate:     → M   DOT  IDENTIFIER("calculate")    COLON
  db.next          → DB_NEXT
  db.break         → DB_BREAK
  db.close         → DB_CLOSE
"""

from __future__ import annotations

from typing import Any

from lexer.tokens import KEYWORDS, SYMBOLS, Token, TokenType


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class TokenizeError(Exception):
    """Raised when the lexer encounters something it cannot handle."""

    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"[line {line}, col {column}] TokenizeError: {message}")
        self.line   = line
        self.column = column


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

class Tokenizer:
    """
    Single-pass, character-by-character lexer for the RA language.

    Usage
    -----
        t = Tokenizer(source_code)
        tokens = t.tokenize()
    """

    # Recognised suffixes for the compound db.* keywords
    _DB_SUFFIXES: frozenset[str] = frozenset({"next", "break", "close"})

    # Escape sequences inside string literals
    _ESCAPES: dict[str, str] = {
        "n": "\n", "t": "\t", "r": "\r",
        "\\": "\\", "'": "'", '"': '"', "0": "\0",
    }

    def __init__(self, source: str) -> None:
        self.source  = source
        self.pos     = 0          # current index into source
        self.line    = 1          # 1-based line counter
        self.column  = 1          # 1-based column counter

    # ── Low-level character helpers ──────────────────────────────────────────

    def _current(self) -> str:
        """Return the character at the current position, or NUL at EOF."""
        return self.source[self.pos] if self.pos < len(self.source) else "\0"

    def _peek(self, offset: int = 1) -> str:
        """Return the character offset positions ahead, or NUL at EOF."""
        idx = self.pos + offset
        return self.source[idx] if idx < len(self.source) else "\0"

    def _advance(self) -> str:
        """Consume and return the current character, updating line/column."""
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line  += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _skip_whitespace(self) -> None:
        """Advance past spaces, tabs, carriage returns, and newlines."""
        while self._current() in (" ", "\t", "\r", "\n"):
            self._advance()

    # ── Token factory ────────────────────────────────────────────────────────

    def _tok(
        self,
        ttype:  TokenType,
        value:  Any,
        line:   int,
        column: int,
    ) -> Token:
        return Token(type=ttype, value=value, line=line, column=column)

    # ── Scanners ─────────────────────────────────────────────────────────────

    def _scan_comment(self, line: int, col: int) -> Token:
        """
        Emit a HASH token and discard everything up to (not including)
        the newline so the next iteration picks up the next line cleanly.
        """
        self._advance()                          # consume '#'
        while self._current() not in ("\n", "\0"):
            self._advance()
        return self._tok(TokenType.HASH, "#", line, col)

    def _scan_string(self, quote: str, line: int, col: int) -> Token:
        """
        Consume a single- or double-quoted string literal.
        Supports backslash escape sequences.
        Raises TokenizeError on an unterminated literal.
        """
        self._advance()          # opening quote
        buf: list[str] = []

        while True:
            ch = self._current()
            if ch == "\0":
                raise TokenizeError("Unterminated string literal", line, col)
            if ch == "\\":
                self._advance()  # backslash
                esc = self._advance()
                buf.append(self._ESCAPES.get(esc, esc))
            elif ch == quote:
                self._advance()  # closing quote
                break
            else:
                buf.append(self._advance())

        return self._tok(TokenType.STRING, "".join(buf), line, col)

    def _scan_number(self, line: int, col: int) -> Token:
        """
        Consume a contiguous run of decimal digits.
        The value is stored as a Python int.
        """
        buf: list[str] = []
        while self._current().isdigit():
            buf.append(self._advance())
        return self._tok(TokenType.INTEGER, int("".join(buf)), line, col)

    def _scan_word(self, line: int, col: int) -> Token:
        """
        Consume a word (letters, digits, underscores) and classify it as:

          1. A compound db.* keyword  (db.next / db.break / db.close)
          2. A plain keyword          (Db, Cls, M, AI, …)
          3. An identifier            (everything else)

        The compound keywords use lowercase 'db'; plain keyword 'Db' (capital D)
        is the database-block opener and is handled by the regular KEYWORDS table.
        """
        buf: list[str] = []
        while self._current().isalnum() or self._current() == "_":
            buf.append(self._advance())
        word = "".join(buf)

        # ── Compound db.* detection ──────────────────────────────────────
        #   Only lowercase 'db' triggers this path.  'Db' (capital) falls
        #   through to the plain KEYWORDS lookup.
        if word == "db" and self._current() == ".":
            # Snapshot state so we can backtrack if suffix doesn't match
            snap_pos = self.pos
            snap_col = self.column
            self._advance()          # consume '.'

            suffix_buf: list[str] = []
            while self._current().isalpha():
                suffix_buf.append(self._advance())
            suffix = "".join(suffix_buf)

            compound = f"db.{suffix}"
            if compound in KEYWORDS:
                return self._tok(KEYWORDS[compound], compound, line, col)

            # Unknown suffix → backtrack; 'db' becomes a plain IDENTIFIER
            self.pos    = snap_pos
            self.column = snap_col

        # ── Plain keyword or identifier ──────────────────────────────────
        if word in KEYWORDS:
            return self._tok(KEYWORDS[word], word, line, col)

        return self._tok(TokenType.IDENTIFIER, word, line, col)

    def _scan_symbol(self, line: int, col: int) -> Token:
        """
        Perform longest-match (up to 2 chars) symbol recognition.
        Returns an UNKNOWN token for any unrecognised character, allowing the
        caller to continue rather than crash.
        """
        two = self.source[self.pos: self.pos + 2]
        if len(two) == 2 and two in SYMBOLS:
            self._advance()
            self._advance()
            return self._tok(SYMBOLS[two], two, line, col)

        one = self._current()
        if one in SYMBOLS:
            self._advance()
            return self._tok(SYMBOLS[one], one, line, col)

        # Unrecognised — consume, log as UNKNOWN (error-recovery)
        ch = self._advance()
        return self._tok(TokenType.UNKNOWN, ch, line, col)

    # ── Main entry point ─────────────────────────────────────────────────────

    def tokenize(self) -> list[Token]:
        """
        Scan the entire source string and return a list of Token objects.
        The last element is always Token(EOF).

        Raises
        ------
        TokenizeError
            On an unterminated string literal.
        """
        tokens: list[Token] = []

        while True:
            self._skip_whitespace()

            line, col = self.line, self.column
            ch = self._current()

            # ── End of file ──────────────────────────────────────────────
            if ch == "\0":
                tokens.append(self._tok(TokenType.EOF, None, line, col))
                break

            # ── Comment  # … EOL ─────────────────────────────────────────
            if ch == "#":
                tokens.append(self._scan_comment(line, col))
                continue

            # ── String literals ──────────────────────────────────────────
            if ch in ('"', "'"):
                tokens.append(self._scan_string(ch, line, col))
                continue

            # ── Integer literals ─────────────────────────────────────────
            if ch.isdigit():
                tokens.append(self._scan_number(line, col))
                continue

            # ── Keywords / identifiers (+ compound db.*) ─────────────────
            if ch.isalpha() or ch == "_":
                tokens.append(self._scan_word(line, col))
                continue

            # ── Compound @.close ─────────────────────────────────────────
            if ch == "@" and self.source[self.pos:self.pos + 7] == "@.close":
                for _ in range(7):
                    self._advance()
                tokens.append(self._tok(TokenType.AT_CLOSE, "@.close", line, col))
                continue

            # ── Compound /.close ──────────────────────────────────────────
            if ch == "/" and self.source[self.pos:self.pos + 7] == "/.close":
                for _ in range(7):
                    self._advance()
                tokens.append(self._tok(TokenType.METHOD_CLOSE, "/.close", line, col))
                continue

            # ── Symbols & operators ───────────────────────────────────────
            tokens.append(self._scan_symbol(line, col))

        return tokens


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def tokenize(source: str) -> list[Token]:
    """Shorthand: ``tokenize(src)`` instead of ``Tokenizer(src).tokenize()``."""
    return Tokenizer(source).tokenize()


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))

    _SAMPLE = """
# RA language sample
Db:
    db.next
    db.break
    db.close

@Cls.Person:
    S name = "Alice"
    I age  = 30

M.calculate:
    I result = 100
    p result

Obj person = Person
AI response = "summarise this"
x == y
x = 42
"""

    print("=" * 60)
    print("RA Tokenizer — self-test")
    print("=" * 60)

    _tokens = tokenize(_SAMPLE)
    for tok in _tokens:
        print(tok)
