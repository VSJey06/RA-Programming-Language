"""Smart code formatter / indentation for RA Language."""

import re

_INDENT = "    "

_BLOCK_OPENERS = re.compile(
    r"^\s*("
    r"@Cls\.|"
    r"M\.|"
    r"Con:|"
    r"En:|"
    r"Db[.\s:]|"
    r"Check:|"
    r"Valid:|"
    r"Invalid:|"
    r"Key[.\s]|"
    r"c\.|"
    r"def:|"
    r"\? For|"
    r"\? While|"
    r"! If|"
    r"! Else|"
    r"PF\b|"
    r"pH:|"
    r"fF[.\s:]|"
    r"\.run:|"
    r"\.fun:"
    r")"
)

_BLOCK_CLOSERS = re.compile(
    r"^\s*("
    r"/\.close|"
    r"@\.close|"
    r"Con\.close|"
    r"En\.close|"
    r"Db\.close|"
    r"Check\.close|"
    r"Key\.close|"
    r"r\.close|"
    r"f\.close|"
    r"pH\.close|"
    r"#"
    r")"
)

_OPENER_LINES = frozenset({
    "Con:", "En:", "Check:", "Valid:", "Invalid:", "def:",
    "PF",
})

_COMMENT_OR_BLANK = re.compile(r"^\s*(#.*)?$")


def _indent_level(line: str) -> int:
    raw = line.rstrip("\n")
    return (len(raw) - len(raw.lstrip())) // len(_INDENT)


def _is_opener(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s in _OPENER_LINES:
        return True
    if _BLOCK_OPENERS.match(s):
        return True
    return False


def _is_closer(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if _BLOCK_CLOSERS.match(s):
        return True
    return False


def _is_comment_or_blank(line: str) -> bool:
    return bool(_COMMENT_OR_BLANK.match(line))


def auto_indent_line(prev_line: str, next_line: str = "") -> str:
    base = _indent_level(prev_line)

    if _is_opener(prev_line):
        base += 1

    if next_line and _is_closer(next_line):
        base = max(0, base - 1)

    return _INDENT * max(0, base)


def format_source(source: str) -> str:
    lines = source.split("\n")
    out: list[str] = []
    indent = 0

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped or _is_comment_or_blank(line):
            out.append(line)
            continue

        if _is_closer(stripped):
            indent = max(0, indent - 1)

        out.append(_INDENT * indent + stripped)

        if _is_opener(stripped):
            indent += 1

    return "\n".join(out)
