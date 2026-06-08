from __future__ import annotations

import json
import re
import time
from pathlib import Path

_RA_LIB = Path(__file__).parent / "ra_lib"


def _load_json(name: str) -> dict:
    path = _RA_LIB / name
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_json(name: str, data: dict) -> None:
    path = _RA_LIB / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class MentorEngine:
    _cache: dict[str, dict] = {}
    _loaded = False

    # ── public API ──────────────────────────────────────────────

    @classmethod
    def reload(cls) -> None:
        for name in ("syntax", "errors", "patterns", "methods",
                     "classes", "workflow", "suggestions",
                     "user_patterns", "memory"):
            cls._cache[name] = _load_json(f"{name}.json")
        cls._loaded = True

    @classmethod
    def ensure_loaded(cls) -> None:
        if not cls._loaded:
            cls.reload()

    # ── entry point for single-line REPL assist ────────────────

    @classmethod
    def assist_line(cls, line: str) -> str | None:
        """Check *line* before execution and return a suggestion or None."""
        cls.ensure_loaded()
        stripped = line.strip()
        if not stripped:
            return None

        # 1. case fix
        suggestion = cls._check_case(stripped)
        if suggestion:
            return suggestion

        # 2. library requirement
        suggestion = cls._check_library(stripped)
        if suggestion:
            return suggestion

        # 3. missing colon
        suggestion = cls._check_missing_colon(stripped)
        if suggestion:
            return suggestion

        return None

    @classmethod
    def suggest_next(cls, line: str) -> str | None:
        """Predict the next line(s) after *line* in REPL context."""
        cls.ensure_loaded()
        stripped = line.strip()
        if not stripped:
            return None

        # 4. @Cls.Name: → suggest fields + method
        m = re.match(r"@Cls\.([A-Za-z_]\w*)\s*:$", stripped)
        if m:
            return cls._suggest_class_body(m.group(1))

        # 3. M.Name: → suggest method body
        m = re.match(r"M\.([A-Za-z_]\w*)\s*:$", stripped)
        if m:
            return cls._suggest_method_body(m.group(1))

        # Db: → suggest Check / Key / close
        if stripped == "Db:":
            return cls._fmt("next_prediction", lines="Check:\nKey:\nDb.close")

        # Check: → suggest body / Valid / Invalid
        if stripped == "Check:":
            return cls._fmt("next_prediction", lines="<body>\nValid:\n<valid>\nInvalid:\n<invalid>\nCheck.close")

        # Key: → suggest case structure
        if stripped.startswith("Key.") and stripped.endswith(":"):
            return cls._fmt("next_prediction", lines="c.{case}:\n<body>\ndef:\n<default>\nKey.close")

        # (after class) → method suggestion
        if stripped == "@.close":
            return None  # class is done

        # empty line after method body
        if stripped == "/.close":
            return None

        return None

    @classmethod
    def suggest_method(cls, context: str = "") -> list[dict]:
        """Return known method templates."""
        cls.ensure_loaded()
        methods = cls._cache.get("methods", {})
        return methods.get("common_methods", [])

    @classmethod
    def suggest_field(cls, class_name: str = "") -> list[dict]:
        """Return suggested fields for *class_name* or all common fields."""
        cls.ensure_loaded()
        classes = cls._cache.get("classes", {})
        if class_name:
            return classes.get("field_suggestions", {}).get(class_name, [])
        patterns = cls._cache.get("patterns", {})
        common = patterns.get("common_fields", {})
        result = []
        for typ, names in common.items():
            for n in names:
                result.append({"type": typ, "name": n})
        return result

    @classmethod
    def explain_code(cls, code: str) -> str:
        """Return plain‑English explanation of *code*."""
        from .analyzer import Analyzer
        return Analyzer.explain(code)

    @classmethod
    def learn_pattern(cls, code: str, valid: bool) -> None:
        """Store a successfully executed pattern for future predictions."""
        cls.ensure_loaded()
        memory = cls._cache.setdefault("memory", {})
        memory["total_executions"] = memory.get("total_executions", 0) + 1
        patterns = cls._cache.setdefault("user_patterns", {})
        patterns.setdefault("patterns", [])

        if not valid:
            return

        # extract structural fingerprint
        fingerprint = cls._fingerprint(code)
        if fingerprint:
            patterns["patterns"].append({
                "code": code,
                "fingerprint": fingerprint,
                "ts": time.time(),
                "success": True,
            })

        # update field / method preferences
        cls._update_preferences(code)

        _save_json("memory.json", memory)
        _save_json("user_patterns.json", patterns)

    # ── internal helpers ────────────────────────────────────────

    @classmethod
    def _check_case(cls, stripped: str) -> str | None:
        errors = cls._cache.get("errors", {})
        for entry in errors.get("case_sensitive_keywords", []):
            wrong = entry["wrong"]
            correct = entry["correct"]
            if stripped.startswith(wrong) and not stripped.startswith(correct):
                suggestion = correct + stripped[len(wrong):]
                return cls._fmt("invalid_keyword", suggestion=suggestion)
        return None

    @classmethod
    def _check_missing_colon(cls, stripped: str) -> str | None:
        errors = cls._cache.get("errors", {})
        patterns = errors.get("missing_colon", {})
        for pat in patterns.get("patterns", []):
            if not stripped.startswith(pat):
                continue
            if stripped.rstrip().endswith(":"):
                continue
            # Don't flag "pH:content" — a colon already follows the keyword
            after_keyword = stripped[len(pat):]
            if after_keyword.startswith(":"):
                continue
            return cls._fmt("missing_colon", suggestion=stripped + ":")
        return None

    @classmethod
    def _check_unexpected_close(cls, stripped: str) -> str | None:
        errors = cls._cache.get("errors", {})
        mapping = errors.get("unexpected_close", {})
        # case-insensitive lookup
        for key, val in mapping.items():
            if stripped.lower() == key.lower():
                return cls._fmt("missing_closure",
                                block=val,
                                expected=f"{stripped} after closing {val}")
        return None

    @classmethod
    def _check_library(cls, stripped: str) -> str | None:
        errors = cls._cache.get("errors", {})
        reqs = errors.get("library_requirements", {})
        for keyword, lib in reqs.items():
            if stripped.startswith(keyword):
                return cls._fmt("invalid_keyword",
                                suggestion=f"Add '{lib}' before using '{keyword}'")
        return None

    @classmethod
    def _suggest_class_body(cls, name: str) -> str:
        classes = cls._cache.get("classes", {})
        fields = classes.get("field_suggestions", {}).get(name, ["S name", "I age"])
        methods = classes.get("method_suggestions", {}).get(name, ["M.method:"])

        if not methods:
            methods = ["M.{name}:".format(name=name.lower())]

        field_str = "\n    ".join(fields)
        method_str = "\n    ".join(methods)

        return cls._fmt("next_prediction",
                        lines=f"{field_str}\n    {method_str}\n    /.close\n@.close")

    @classmethod
    def _suggest_method_body(cls, name: str) -> str:
        methods = cls._cache.get("methods", {})
        for m in methods.get("common_methods", []):
            if m["name"].lower() == name.lower():
                body = "\n        ".join(m["body"])
                return cls._fmt("next_prediction",
                                lines=f"    {body}\n/.close")
        return cls._fmt("next_prediction",
                        lines='    p "' + name + '"\n/.close')

    @classmethod
    def _fmt(cls, key: str, **kwargs) -> str:
        templates = cls._cache.get("suggestions", {}).get("templates", {})
        tmpl = templates.get(key, {})
        msg = tmpl.get("message", "Assist:")
        fmt = tmpl.get("format", "")
        for k, v in kwargs.items():
            msg = msg.replace("{" + k + "}", v)
            fmt = fmt.replace("{" + k + "}", v)
        return f"{msg}\n{fmt}"

    @classmethod
    def _fingerprint(cls, code: str) -> str | None:
        """Return a structural fingerprint of the code."""
        lines = [l.strip() for l in code.split("\n") if l.strip()]
        if not lines:
            return None
        sig = []
        for l in lines:
            if re.match(r"@Cls\.\w+\s*:", l):
                sig.append("CLASS_START")
            elif re.match(r"M\.\w+\s*:", l):
                sig.append("METHOD_START")
            elif l == "/.close":
                sig.append("METHOD_END")
            elif l == "@.close":
                sig.append("CLASS_END")
            elif l == "Db.close":
                sig.append("DB_END")
            elif re.match(r"(S|I|L)\s+\w", l):
                sig.append("VAR_DECL")
            elif l.startswith("Db:"):
                sig.append("DB_START")
            elif re.match(r"! (If|ElseIf|Else)", l):
                sig.append("COND")
            elif re.match(r"\? (For|While)", l):
                sig.append("LOOP")
            else:
                sig.append("OTHER")
        return " | ".join(sig)

    @classmethod
    def _update_preferences(cls, code: str) -> None:
        patterns = cls._cache.get("user_patterns", {})
        for m in re.finditer(r"^\s*(S|I|L)\s+(\w+)", code, re.MULTILINE):
            typ, name = m.group(1), m.group(2)
            field_prefs = patterns.setdefault("learned_fields", {})
            prefs = field_prefs.setdefault(name, {})
            prefs[typ] = prefs.get(typ, 0) + 1

        for m in re.finditer(r"M\.(\w+)\s*:", code):
            name = m.group(1).lower()
            method_prefs = patterns.setdefault("learned_methods", {})
            method_prefs[name] = method_prefs.get(name, 0) + 1


# ═══════════════════════════════════════════════════════════════════
# Suggestor — ghost-text suggestion engine
# ═══════════════════════════════════════════════════════════════════

class Suggestor:
    """Context-aware multi-step suggestion engine for ghost-text autocomplete.

    Usage
    -----
    >>> suggestor = Suggestor()
    >>> suggestor.feed("@Cls.Person:")       # called after each submitted line
    >>> suggestor.suggest("")                # → "S name"
    >>> suggestor.accept_ghost("")           # → "S name"
    >>> suggestor.suggest("S name")          # → None (exact match → advances)
    >>> suggestor.suggest("")                # → "I age"
    """

    def __init__(self):
        self._steps: list[str] = []
        self._step_idx = 0

    # ── public API ────────────────────────────────────────────────

    def reset(self) -> None:
        self._steps = []
        self._step_idx = 0

    def feed(self, line: str) -> None:
        """Notify the suggestor that *line* was submitted (pressed Enter)."""
        MentorEngine.ensure_loaded()
        stripped = line.strip()
        if not stripped:
            self._steps = []
            self._step_idx = 0
            return

        # 1. If the line matches the current step, just advance.
        if self._step_idx < len(self._steps):
            if self._steps[self._step_idx] == stripped:
                self._step_idx += 1
                return

        # 2. If this line is a known block opener, compute a new step sequence.
        seq = self._compute_seq(stripped)
        if seq is not None:
            self._steps = seq
            self._step_idx = 0
            return

    def suggest(self, line: str) -> str | None:
        """Return ghost text for the current *line* being typed."""
        if self._step_idx >= len(self._steps):
            return None
        target = self._steps[self._step_idx]

        if not line:
            return target
        if target.startswith(line):
            return target[len(line):]
        # exact match → ghost is empty (caller should call feed instead)
        return None

    def accept_ghost(self, line: str) -> str:
        """Accept the full ghost text, advance step, return completed line."""
        ghost = self.suggest(line)
        if ghost is None:
            return line
        self._step_idx += 1
        return line + ghost

    def accept_token(self, line: str) -> str:
        """Accept just the next token of the ghost text."""
        ghost = self.suggest(line)
        if not ghost:
            return line
        trimmed = ghost.lstrip()
        sp = trimmed.find(" ")
        token = trimmed[:sp] if sp != -1 else trimmed
        lead = len(ghost) - len(trimmed)
        return line + ghost[:lead] + token

    # ── internal ──────────────────────────────────────────────────

    def _compute_seq(self, line: str) -> list[str] | None:
        """Return a list of predicted next lines for a block opener, or None."""
        m = re.match(r"@Cls\.([A-Za-z_]\w*)\s*:$", line)
        if m:
            return self._class_body(m.group(1))

        if line == "Db:":
            return ["Check:", "Key:", "Db.close"]

        if line == "Check:":
            return ["<body>", "Valid:", "<valid>", "Invalid:", "<invalid>", "Check.close"]

        m = re.match(r"Key\.(.+)\s*:$", line)
        if m:
            return ["c.{case}:".format(case="<case>"), "<body>", "def:", "<default>", "Key.close"]

        m = re.match(r"M\.([A-Za-z_]\w*)\s*:$", line)
        if m:
            return self._method_body(m.group(1))

        if line == ".run:":
            return ["<command>", "r.close"]
        if line == ".fun:":
            return ["<body>", "f.close"]

        return None

    def _class_body(self, name: str) -> list[str]:
        classes = MentorEngine._cache.get("classes", {})
        fields = classes.get("field_suggestions", {}).get(name, ["S name", "I age"])
        methods = classes.get("method_suggestions", {}).get(name, ["M.method:"])
        result = list(fields)
        result.extend(methods)
        result.append("/.close")
        result.append("@.close")
        return result

    def _method_body(self, name: str) -> list[str]:
        methods_data = MentorEngine._cache.get("methods", {})
        for m in methods_data.get("common_methods", []):
            if m["name"].lower() == name.lower():
                return list(m["body"]) + ["/.close"]
        return ['    p "' + name + '"', "/.close"]


# Module-level convenience alias
Mentor = MentorEngine
