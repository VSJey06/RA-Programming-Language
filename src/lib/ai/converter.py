import ast
import os

from lib.ai.language_detector import detect_language


def convert(source_path: str, language: str) -> str:
    detected = detect_language(source_path, language)
    with open(source_path, encoding="utf-8-sig") as f:
        source = f.read()
    if detected == "Python":
        return _python_to_ra(source, source_path)
    raise ValueError(f"Conversion from {detected} not yet supported")


def _python_to_ra(source: str, _path: str) -> str:
    lines = source.splitlines()
    out: list[str] = []
    indent_stack: list[str] = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            out.append(line.rstrip())
            continue

        raw_indent = _indent(line)
        content = stripped

        # Close blocks that ended before this line's indent level
        while indent_stack and len(raw_indent) < len(indent_stack[-1]):
            closer = _closer_for(indent_stack.pop())
            if closer:
                out.append(closer)

        converted = _translate_py_line(content)
        if converted is not None:
            if converted.endswith(":"):
                indent_stack.append(raw_indent)
            out.append(raw_indent + converted)
        else:
            out.append(line.rstrip())

    while indent_stack:
        closer = _closer_for(indent_stack.pop())
        if closer:
            out.append(closer)

    out.append("")
    return "\n".join(out)


def _indent(line: str) -> str:
    return line[:len(line) - len(line.lstrip())]


_CLOSER_MAP: dict[str, str] = {
    "! If": "#",
    "! Else": "#",
    "? For": "#",
    "? While": "#",
    "M.": "/",
    "@Cls.": "@.close",
}


def _closer_for(opener_line: str) -> str:
    for prefix, closer in _CLOSER_MAP.items():
        if prefix in opener_line:
            return closer if closer else ""
    return ""


def _translate_py_line(line: str) -> str | None:
    if not line:
        return line

    if line.endswith(":"):
        return _translate_block_header(line)

    if line.startswith("print(") and line.endswith(")"):
        inner = line[6:-1]
        return f"p {inner}"

    if line.startswith("return "):
        expr = line[7:]
        return f"R.{expr}"

    if line.startswith("import ") or line.startswith("from "):
        return None

    if line.startswith("class "):
        return None

    if line.startswith("def "):
        return None

    if " = " in line:
        var, _, val = line.partition(" = ")
        var = var.strip()
        val = val.strip()
        if val.startswith('"') or val.startswith("'"):
            return f"S {var} = {val}"
        if val.startswith("[") or val.startswith("("):
            return f"L {var} = {val}"
        if val.replace(".", "").replace("-", "").isdigit():
            return f"I {var} = {val}"
        return f"S {var} = {val}"

    if line.startswith("if "):
        cond = line[3:]
        if cond.endswith(":"):
            cond = cond[:-1]
        return f"! If.{cond},"

    if line.startswith("elif "):
        cond = line[5:]
        if cond.endswith(":"):
            cond = cond[:-1]
        return f"!! {cond},"

    if line.startswith("else:"):
        return "! Else"

    if line.startswith("for ") and " in " in line and line.endswith(":"):
        rest = line[4:-1]
        var, _, it = rest.partition(" in ")
        var = var.strip()
        it = it.strip()
        if it.startswith("range(") and it.endswith(")"):
            args = it[6:-1].split(",")
            if len(args) == 1:
                end = int(args[0]) - 1
                return f"? For.{var}=0;{end},"
            elif len(args) == 2:
                start = int(args[0])
                end = int(args[1]) - 1
                return f"? For.{var}={start};{end},"
        return None

    if line.startswith("while ") and line.endswith(":"):
        cond = line[6:-1]
        return f"? While.{cond},"

    if line.startswith("try:") or line.startswith("except") or line.startswith("finally:"):
        return None

    if line.startswith("with ") and line.endswith(":"):
        return None

    if line.startswith("async ") or line.startswith("await "):
        return None

    if line.startswith("break"):
        return "db.break"

    if line.startswith("continue"):
        return "db.next"

    return None


def _translate_block_header(line: str) -> str | None:
    if line.startswith("def ") and line.endswith(":"):
        rest = line[4:-1]
        name = rest.split("(")[0].strip()
        return f"M.{name}:"

    if line.startswith("class ") and line.endswith(":"):
        name = line[6:-1].split("(")[0].strip()
        return f"@Cls.{name}:"

    if line.startswith("if "):
        cond = line[3:-1]
        return f"! If.{cond},"

    if line.startswith("elif "):
        cond = line[5:-1]
        return f"!! {cond},"

    if line.startswith("else:"):
        return "! Else"

    if line.startswith("for ") and " in " in line:
        rest = line[4:-1]
        var, _, it = rest.partition(" in ")
        var = var.strip()
        it = it.strip()
        if it.startswith("range(") and it.endswith(")"):
            args = it[6:-1].split(",")
            if len(args) == 1:
                end = int(args[0]) - 1
                return f"? For.{var}=0;{end},"
            elif len(args) == 2:
                start = int(args[0])
                end = int(args[1]) - 1
                return f"? For.{var}={start};{end},"

    if line.startswith("while "):
        cond = line[6:-1]
        return f"? While.{cond},"

    return line
