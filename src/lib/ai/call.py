import re
from .knowledge import KnowledgeBase


_ANSWERS: dict[str, str] = {
    "obj": (
        "Obj instantiates an object from a class.\n"
        "Syntax: Obj.ClassName.VariableName"
    ),
    "@cls": (
        "@Cls defines a class blueprint.\n"
        "Syntax: @Cls.ClassName: closed with @.close"
    ),
    "m": (
        "M defines a method inside a class.\n"
        "Syntax: M.MethodName: closed with /.close"
    ),
    "db": (
        "Db manages a named key-value store.\n"
        "Syntax: Db: ... Db.close"
    ),
    "oop": (
        "OOP library enables classes, objects,\n"
        "constructors and encapsulation."
    ),
    "con": (
        "Con defines a constructor block inside a class.\n"
        "Syntax: Con: ... con.close"
    ),
    "en": (
        "En defines an encapsulation block for private\n"
        "properties inside a class. Syntax: En: ... en.close"
    ),
    "pf": (
        "PF (Program Flow) controls execution order\n"
        "using pH and fF blocks."
    ),
    "ph": (
        "pH (Program Handler) registers execution order\n"
        "inside a PF flow. Syntax: pH: ... pH.close"
    ),
    "ff": (
        "fF (Function Flow) executes method calls in\n"
        "defined order. Syntax: fF: ... f.close"
    ),
    "check": (
        "Check provides error handling with Valid/Invalid\n"
        "branches. Syntax: Check: ... Valid: ... Invalid: ... Check.close"
    ),
    "key": (
        "Key implements a switch/case block.\n"
        "Syntax: Key.expr: ... c.cond: ... def: ... Key.close"
    ),
    "s": (
        "S declares a string variable.\n"
        "Syntax: S name or S name = \"value\""
    ),
    "i": (
        "I declares an integer variable.\n"
        "Syntax: I name or I age = 25"
    ),
    "l": (
        "L declares a list variable.\n"
        "Syntax: L name or L items = list"
    ),
    "ai": (
        "AI enables .cov:, .expo: and .Call: blocks\n"
        "for code analysis and knowledge queries."
    ),
    ".cov": (
        ".cov: runs code coverage analysis.\n"
        "Syntax: .cov: Language.\"path\" cov.close"
    ),
    ".expo": (
        ".expo: exports code to another language.\n"
        "Syntax: .expo: Language.\"path\" ex.close"
    ),
    ".call": (
        ".Call: queries the RA knowledge base.\n"
        "Syntax: .Call:\"question\" call.close"
    ),
}


def Call(query: str) -> str:
    """Answer RA-related questions from the local knowledge base."""
    q = query.strip()
    if not q:
        return "AIError:\n\n  Empty query."
    q = q.rstrip("?.!")
    q_lower = q.lower()

    # ── Direct concept match: "What is X?" ──
    m = re.search(r"\bwhat\b.*?(\S+)\s*$", q_lower)
    if m:
        concept = m.group(1)
        # Remove trailing punctuation that's not part of the name
        while concept and concept[-1] in ":.":
            concept = concept[:-1]
        if not concept:
            concept = m.group(1)
        # Map aliases
        alias_map = {
            "string": "s", "int": "i", "integer": "i",
            "list": "l", "object": "obj",
            "program": "pf", "program flow": "pf",
            "database": "db",
            "constructor": "con",
            "encapsulation": "en",
            "program handler": "ph",
            "function flow": "ff",
            "coverage": ".cov",
            "export": ".expo",
        }
        lookup = alias_map.get(concept, concept)
        if lookup in _ANSWERS:
            return _ANSWERS[lookup]
        # Try stripping leading . or @
        if lookup.startswith(".") or lookup.startswith("@"):
            stripped = lookup[1:]
            if stripped in _ANSWERS:
                return _ANSWERS[stripped]

    # ── Explain @Cls.Name: pattern ──
    m = re.search(r"@[Cc][Ll][Ss]\.([A-Za-z_]\w*)", query)
    if m:
        return f"Creates a class named {m.group(1)}."

    # ── Explain S / I / L variable patterns ──
    if re.search(r"\b(s|i|l)\b.*\b(var|type|variable)\b", q_lower) or \
       re.search(r"\b(var|type|variable)\b.*\b(s|i|l)\b", q_lower):
        parts = re.findall(r"\b(s|i|l)\b", q_lower)
        if parts:
            answers = set()
            for p in parts:
                if p in _ANSWERS:
                    answers.add(_ANSWERS[p])
            if answers:
                return "\n\n".join(answers)

    # ── Class explanation ──
    if re.search(r"\b(what|explain)\b.*\bclass\b", q_lower):
        return ("A class is a blueprint for objects, defined with\n"
                "'@Cls.ClassName:' and closed with '@.close'.")

    # ── Syntax / keywords ──
    if re.search(r"\b(syntax|keyword)\b", q_lower):
        syntax = KnowledgeBase.get_syntax()
        return f"RA keywords: {', '.join(syntax['keywords'])}"

    # ── Error help ──
    if re.search(r"\berror\b", q_lower):
        return ("Use the corrector to analyse errors:\n"
                "check variable declarations, library imports,\n"
                "and keyword casing.")

    # ── Unknown ──
    return "No knowledge available."
