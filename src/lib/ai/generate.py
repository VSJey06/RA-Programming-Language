import json
from pathlib import Path
import re

_SYNTAX_CACHE: dict | None = None


def _load_syntax() -> dict:
    global _SYNTAX_CACHE
    if _SYNTAX_CACHE is None:
        path = Path(__file__).parent / "syntax.json"
        _SYNTAX_CACHE = json.loads(path.read_text(encoding="utf-8"))
    return _SYNTAX_CACHE


def Gen(description: str) -> str:
    q = description.strip()
    if not q:
        return "AIError:\n\n  Empty prompt."
    _load_syntax()
    desc_lower = q.lower()

    if "class" in desc_lower:
        name = _extract_name(q, default="GeneratedClass")
        props, methods = _extract_members(desc_lower)
        return _build_class(name, props, methods)

    if "method" in desc_lower:
        name = _extract_name(q, default="GeneratedMethod")
        return _build_method(name)

    return _build_class("GeneratedClass", [("S", "name")], [])


def _extract_name(text: str, default: str = "GeneratedClass") -> str:
    m = re.search(r"(\w+)\s+(?:class|method)", text, re.IGNORECASE)
    if m:
        return m.group(1).capitalize()
    m = re.search(r"(?:class|method)\s+(\w+)", text, re.IGNORECASE)
    if m:
        return m.group(1).capitalize()
    return default


_TYPE_KEYWORDS: dict[str, str] = {
    "name": "S", "email": "S", "phone": "S", "address": "S",
    "title": "S", "description": "S", "text": "S",
    "username": "S", "password": "S",
    "age": "I", "salary": "I", "marks": "I", "score": "I",
    "count": "I", "id": "I", "number": "I", "int": "I",
    "price": "I", "cost": "I", "amount": "I", "quantity": "I",
    "stock": "I",
}

_METHOD_MARKERS: set[str] = {
    "method", "methods",
    "function", "functions",
    "action", "actions",
    "behavior", "behaviors",
    "operation", "operations",
}

# Plural variants — propagate method status to preceding bare words
_PLURAL_METHOD_MARKERS: set[str] = {
    "methods", "functions", "actions", "behaviors", "operations",
}


def _extract_members(desc: str) -> tuple[list[tuple[str, str]], list[str]]:
    m = re.search(r"\bwith\b\s*(.+)", desc)
    if not m:
        return [("S", "name")], []
    chunk = m.group(1)

    # Normalize concatenated "and" patterns (e.g. "andregister" → "and register")
    chunk = re.sub(r"\band(?=[A-Za-z])", "and ", chunk)

    # Split on commas, &, + (not and) to get segments
    segments = re.split(r"\s*(?:,|&|\+)\s*", chunk)

    # Flatten each segment into words, splitting on 'and' then spaces
    all_words: list[str] = []
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        parts = re.split(r"\s+and\s+", seg, flags=re.IGNORECASE)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            all_words.extend(part.split())

    # Walk backwards: method markers apply to preceding word(s)
    props: list[tuple[str, str]] = []
    methods: list[str] = []
    seen_props: set[str] = set()
    seen_methods: set[str] = set()
    plural_marker_seen = False

    i = len(all_words) - 1
    while i >= 0:
        w = all_words[i].strip().rstrip(".")
        if not w:
            i -= 1
            continue
        wl = w.lower()
        if wl in _METHOD_MARKERS:
            plural_marker_seen = wl in _PLURAL_METHOD_MARKERS
            i -= 1
            continue
        if plural_marker_seen:
            name = w.capitalize()
            if name not in seen_methods:
                seen_methods.add(name)
                methods.append(name)
            i -= 1
            continue
        nxt = all_words[i + 1].lower().rstrip(".") if i + 1 < len(all_words) else ""
        if nxt in _METHOD_MARKERS and nxt not in _PLURAL_METHOD_MARKERS:
            name = w.capitalize()
            if name not in seen_methods:
                seen_methods.add(name)
                methods.append(name)
            i -= 1
            continue
        if w not in seen_props:
            seen_props.add(w)
            kw = _TYPE_KEYWORDS.get(w, "S")
            props.append((kw, w))
        i -= 1

    if not props and not methods:
        props.append(("S", "name"))
    props.reverse()
    return props, methods


def _build_class(name: str, props: list[tuple[str, str]], methods: list[str]) -> str:
    indent = _load_syntax().get("indent", "    ")
    lines = [f"@Cls.{name}:"]
    for kw, pname in props:
        lines.append(f"{indent}{kw} {pname}")
    if methods and props:
        lines.append("")
    for i, mname in enumerate(methods):
        if i > 0:
            lines.append("")
        lines.append(f"{indent}M.{mname}:")
        lines.append(f"{indent*2}p \"{mname}\"")
        lines.append(f"{indent}/.close")
    lines.append("@.close")
    return "\n".join(lines) + "\n"


def _build_method(name: str) -> str:
    lines = [f"M.{name}:", f"    p \"{name}\"", "/.close"]
    return "\n".join(lines) + "\n"
