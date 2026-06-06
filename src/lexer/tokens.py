"""
tokens.py — Token type definitions for the RA language.

Provides the TokenType enumeration, the Token dataclass, and
lookup tables for keywords and symbols.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


# ---------------------------------------------------------------------------
# Token Types
# ---------------------------------------------------------------------------

class TokenType(Enum):
    """Every token category recognised by the RA lexer."""

    # ── Keywords ──────────────────────────────────────────────────────────
    S        = auto()   # String type declaration
    I        = auto()   # Integer type declaration
    L        = auto()   # List type declaration
    BOOLEAN_TF = auto()   # Boolean .TF suffix
    RUN_CLOSE   = auto()   # r.close (run-block terminator)
    FUN_CLOSE   = auto()   # f.close (function-block terminator)
    OOP      = auto()   # OOP library activation
    CON      = auto()   # Constructor block open  (Con)
    CON_CLOSE = auto()  # con.close / Con.close
    EN       = auto()   # Encapsulation block open  (En)
    EN_CLOSE  = auto()  # en.close / En.close
    CLS      = auto()   # Class definition  (@Cls)
    OBJ      = auto()   # Object instantiation  (Obj)
    M        = auto()   # Method definition  (M)
    DB       = auto()   # Database block open  (Db)
    DB_NEXT  = auto()   # db.next
    DB_BREAK = auto()   # db.break
    DB_CLOSE  = auto()   # db.close
    AT_CLOSE   = auto()   # @.close
    METHOD_CLOSE = auto()   # /.close
    AI       = auto()   # AI inference call
    P        = auto()   # Print / output
    R        = auto()   # Return
    CHECK    = auto()   # Check block open
    CHECK_CLOSE = auto()  # Check.close
    VALID    = auto()   # Valid section
    INVALID  = auto()   # Invalid section
    KEY      = auto()   # Key (switch) block open
    KEY_CLOSE = auto()  # Key.close
    PF       = auto()   # PF library activation
    PH       = auto()   # Program Handler pH
    PH_CLOSE = auto()   # pH.close
    FF       = auto()   # Function Flow fF

    # ── Symbols / operators ──────────────────────────────────────────────
    ASSIGN   = auto()   # =
    NEQ      = auto()   # !=
    DOT      = auto()   # .
    COLON    = auto()   # :
    EQ       = auto()   # ==
    COMMA    = auto()   # ,
    AT       = auto()   # @
    BANG     = auto()   # !
    QUESTION = auto()   # ?
    HASH     = auto()   # #
    SLASH    = auto()   # /

    # Arithmetic / comparison operators (no longer UNKNOWN)
    PLUS     = auto()   # +
    MINUS    = auto()   # -
    STAR     = auto()   # *
    PERCENT  = auto()   # %
    GT       = auto()   # >
    LT       = auto()   # <
    GTE      = auto()   # >=
    LTE      = auto()   # <=
    SEMICOLON = auto()  # ;

    # ── Literals ─────────────────────────────────────────────────────────
    STRING     = auto()   # "hello"  or  'hello'
    INTEGER    = auto()   # 42
    FLOAT      = auto()   # 3.14
    IDENTIFIER = auto()   # variable / symbol names

    # ── Meta ─────────────────────────────────────────────────────────────
    EOF     = auto()   # end-of-file sentinel
    UNKNOWN = auto()   # unrecognised character (error recovery)


# ---------------------------------------------------------------------------
# Keyword lookup table
# ---------------------------------------------------------------------------

KEYWORDS: dict[str, TokenType] = {
    "S"        : TokenType.S,
    "I"        : TokenType.I,
    "L"        : TokenType.L,
    "Cls"      : TokenType.CLS,
    "Obj"      : TokenType.OBJ,
    "M"        : TokenType.M,
    "Db"       : TokenType.DB,
    "db.next"  : TokenType.DB_NEXT,
    "db.break" : TokenType.DB_BREAK,
    "db.close" : TokenType.DB_CLOSE,
    "@.close"  : TokenType.AT_CLOSE,
    "/.close"  : TokenType.METHOD_CLOSE,
    "AI"       : TokenType.AI,
    "p"        : TokenType.P,
    "R"        : TokenType.R,
    "r.close"  : TokenType.RUN_CLOSE,
    "f.close"  : TokenType.FUN_CLOSE,
    "OOP"      : TokenType.OOP,
    "Con"      : TokenType.CON,
    "Con.close": TokenType.CON_CLOSE,
    "con.close": TokenType.CON_CLOSE,
    "En"       : TokenType.EN,
    "En.close"  : TokenType.EN_CLOSE,
    "en.close"  : TokenType.EN_CLOSE,
    "Check"     : TokenType.CHECK,
    "Check.close" : TokenType.CHECK_CLOSE,
    "Valid"     : TokenType.VALID,
    "Invalid"   : TokenType.INVALID,
    "Key"       : TokenType.KEY,
    "Key.close"  : TokenType.KEY_CLOSE,
    "PF"        : TokenType.PF,
    "pH"        : TokenType.PH,
    "pH.close"  : TokenType.PH_CLOSE,
    "fF"        : TokenType.FF,
}

# ---------------------------------------------------------------------------
# Symbol lookup table
# (longest-match ordering: 2-char entries before 1-char suffixes)
# ---------------------------------------------------------------------------

SYMBOLS: dict[str, TokenType] = {
    "==" : TokenType.EQ,
    "!=" : TokenType.NEQ,
    ">=" : TokenType.GTE,
    "<=" : TokenType.LTE,
    "="  : TokenType.ASSIGN,
    "."  : TokenType.DOT,
    ":"  : TokenType.COLON,
    ","  : TokenType.COMMA,
    "@"  : TokenType.AT,
    "!"  : TokenType.BANG,
    "?"  : TokenType.QUESTION,
    "#"  : TokenType.HASH,
    "/"  : TokenType.SLASH,
    "+"  : TokenType.PLUS,
    "-"  : TokenType.MINUS,
    "*"  : TokenType.STAR,
    "%"  : TokenType.PERCENT,
    ">"  : TokenType.GT,
    "<"  : TokenType.LT,
    ";"  : TokenType.SEMICOLON,
}


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------

@dataclass
class Token:
    """A single lexical unit produced by the RA tokenizer.

    Attributes
    ----------
    type   : TokenType — category of this token.
    value  : Any       — raw source text (or coerced Python value).
    line   : int       — 1-based line number.
    column : int       — 1-based column number.
    """

    type:   TokenType
    value:  Any
    line:   int
    column: int

    def is_keyword(self) -> bool:
        """Return True if this token is any RA keyword."""
        return self.type in _KEYWORD_SET

    def is_literal(self) -> bool:
        """Return True if this token is a literal value."""
        return self.type in _LITERAL_SET

    def is_symbol(self) -> bool:
        """Return True if this token is a symbol / operator."""
        return self.type in _SYMBOL_SET

    def __repr__(self) -> str:
        return (
            f"Token(type={self.type.name}, value={self.value!r}, "
            f"line={self.line}, col={self.column})"
        )


# ── Pre-built sets ──────────────────────────────────────────────────────

_KEYWORD_SET: frozenset[TokenType] = frozenset({
    TokenType.S, TokenType.I, TokenType.L,
    TokenType.BOOLEAN_TF, TokenType.RUN_CLOSE,
    TokenType.FUN_CLOSE,
    TokenType.OOP, TokenType.CON, TokenType.CON_CLOSE,
    TokenType.EN, TokenType.EN_CLOSE,
    TokenType.CLS, TokenType.OBJ, TokenType.M,
    TokenType.DB, TokenType.DB_NEXT, TokenType.DB_BREAK, TokenType.DB_CLOSE, TokenType.AT_CLOSE, TokenType.METHOD_CLOSE,
    TokenType.AI, TokenType.P, TokenType.R,
    TokenType.CHECK, TokenType.CHECK_CLOSE,
    TokenType.VALID, TokenType.INVALID,
    TokenType.KEY, TokenType.KEY_CLOSE,
    TokenType.PF, TokenType.PH, TokenType.PH_CLOSE, TokenType.FF,
})

_LITERAL_SET: frozenset[TokenType] = frozenset({
    TokenType.STRING,
    TokenType.INTEGER,
    TokenType.FLOAT,
    TokenType.IDENTIFIER,
})

_SYMBOL_SET: frozenset[TokenType] = frozenset({
    TokenType.ASSIGN, TokenType.NEQ,   TokenType.DOT,
    TokenType.COLON,  TokenType.EQ,    TokenType.COMMA,
    TokenType.AT,     TokenType.BANG,  TokenType.QUESTION,
    TokenType.HASH,   TokenType.SLASH,
    TokenType.PLUS,   TokenType.MINUS, TokenType.STAR,
    TokenType.PERCENT, TokenType.GT,   TokenType.LT,
    TokenType.GTE,    TokenType.LTE,   TokenType.SEMICOLON,
})
