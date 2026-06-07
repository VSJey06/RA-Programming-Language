import os


def export(source_path: str, language: str) -> str:
    with open(source_path, encoding="utf-8") as f:
        source = f.read()

    if language == "Python":
        return _ra_to_python(source, source_path)
    if language == "Java":
        return _ra_to_java(source, source_path)
    raise ValueError(f"Export to {language} not yet supported")


def _ra_to_python(source: str, _path: str) -> str:
    lines = source.splitlines()
    out: list[str] = []
    indent = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            out.append("")
            continue

        converted = _translate_ra_to_python(stripped)
        if converted is None:
            continue

        is_dedent = converted == "__DEDENT__"
        if is_dedent:
            indent = max(0, indent - 1)
            continue

        if converted == "__UNDENT__":
            continue

        if converted == "__KEEP__":  # keep as-is (comments)
            out.append(stripped)
            continue

        if converted == "__BLANK__":
            continue

        indent_increment = 0
        if _is_block_opener_ra(stripped):
            indent_increment = 1

        prefix = "    " * indent
        out.append(prefix + converted)
        indent += indent_increment

    out.append("")
    return "\n".join(out)


def _ra_to_java(source: str, _path: str) -> str:
    lines = source.splitlines()
    out: list[str] = []
    indent = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            out.append("")
            continue

        converted = _translate_ra_to_java(stripped)
        if converted is None:
            continue
        if converted == "__SKIP__":
            continue

        is_closing_brace = converted == "}"
        if is_closing_brace:
            indent = max(0, indent - 1)

        prefix = "    " * indent
        out.append(prefix + converted)

        is_opening_brace = converted.rstrip().endswith("{")
        if is_opening_brace and not is_closing_brace:
            indent += 1

    out.append("")
    return "\n".join(out)


def _is_block_opener_ra(line: str) -> bool:
    return any(line.startswith(p) for p in ("! If.", "! Else", "? For.", "? While.", "M.", "@Cls."))


def _translate_ra_to_python(line: str) -> str | None:
    if line.startswith("#"):
        return "__KEEP__"

    if line in ("/", "/.close", "r.close", "f.close", "con.close",
                "en.close", "db.close", "Key.close", "Check.close",
                "pH.close", "cov.close"):
        return "__DEDENT__"

    if line == "@":
        return "__DEDENT__"
    if line == "@.close":
        return "__DEDENT__"

    if line.startswith("p "):
        expr = line[2:]
        return f"print({expr})"

    if line.startswith("R."):
        expr = line[2:]
        return f"return {expr}"

    if line.startswith("S ") and " = " in line:
        rest = line[2:]
        return rest

    if line.startswith("I ") and " = " in line:
        rest = line[2:]
        return rest

    if line.startswith("L ") and " = " in line:
        rest = line[2:]
        return rest

    if line.startswith("! If."):
        cond = line[5:].rstrip(",")
        return f"if {cond}:"

    if line.startswith("!! "):
        cond = line[3:].rstrip(",")
        return f"elif {cond}:"

    if line == "! Else":
        return "else:"

    if line.startswith("? For."):
        rest = line[6:].rstrip(",")
        var, _, r = rest.partition("=")
        start, _, end = r.partition(";")
        end_val = int(end) + 1
        return f"for {var} in range({start}, {end_val}):"

    if line.startswith("? While."):
        cond = line[8:].rstrip(",")
        return f"while {cond}:"

    if line.startswith("M.") and line.endswith(":"):
        name = line[2:-1]
        return f"def {name}():"

    if line.startswith("@Cls.") and line.endswith(":"):
        name = line[5:-1]
        return f"class {name}:"

    if line == "OOP":
        return "__BLANK__"

    if line == "PF":
        return None

    if line.startswith("AI"):
        return None

    if line.startswith(".run:") or line.startswith(".fun:"):
        return None

    if line.startswith("."):
        return None

    if line.startswith("Check:") or line.startswith("Valid:") or line.startswith("Invalid:"):
        return None

    if line.startswith("Key."):
        return None

    if line.startswith("c.") and line.endswith(":"):
        val = line[2:-1]
        return f"if key == {val}:"

    if line == "def:":
        return "else:"

    if line.startswith("Db.") or line.startswith("Db:"):
        return None

    if line.startswith("db."):
        return None

    if line.startswith("Obj."):
        return None

    if line.startswith("pH:") or line.startswith("fF:"):
        return None

    if line.startswith("Con:") or line.startswith("En:"):
        return None

    if line == "db.next":
        return "continue"

    if line == "db.break":
        return "break"

    return line


def _translate_ra_to_java(line: str) -> str | None:
    if line.startswith("#"):
        return f"// {line[1:].lstrip()}"

    if line in ("/", "/.close", "r.close", "f.close", "con.close",
                "en.close", "db.close", "Key.close", "Check.close",
                "pH.close", "cov.close", "ex.close"):
        return "}"

    if line == "@":
        return "}"
    if line == "@.close":
        return "}"

    if line == "":
        return ""

    if line.startswith("p "):
        expr = line[2:]
        return f"System.out.println({expr});"

    if line.startswith("R."):
        expr = line[2:]
        return f"return {expr};"

    if line.startswith("S ") and " = " in line:
        var, _, val = line[2:].partition(" = ")
        return f"String {var.strip()} = {val.strip()};"

    if line.startswith("I ") and " = " in line:
        var, _, val = line[2:].partition(" = ")
        return f"int {var.strip()} = {val.strip()};"

    if line.startswith("L ") and " = " in line:
        parts = line[2:].split(" = ", 1)
        return f"List {parts[0].strip()} = {parts[1].strip()};"

    if line.startswith("! If."):
        cond = line[5:].rstrip(",")
        return f"if ({cond}) {{"

    if line.startswith("!! "):
        cond = line[3:].rstrip(",")
        return f"else if ({cond}) {{"

    if line == "! Else":
        return "else {"

    if line.startswith("? For."):
        rest = line[6:].rstrip(",")
        var, _, r = rest.partition("=")
        start, _, end = r.partition(";")
        return f"for (int {var.strip()} = {start.strip()}; {var.strip()} <= {end.strip()}; {var.strip()}++) {{"

    if line.startswith("? While."):
        cond = line[8:].rstrip(",")
        return f"while ({cond}) {{"

    if line.startswith("M.") and line.endswith(":"):
        name = line[2:-1]
        return f"public void {name}() {{"

    if line.startswith("@Cls.") and line.endswith(":"):
        name = line[5:-1]
        return f"class {name} {{"

    if line in ("OOP", "PF"):
        return "__SKIP__"

    if line.startswith("AI"):
        return "__SKIP__"

    if line.startswith(".run:") or line.startswith(".fun:"):
        return "{"

    if line.startswith("."):
        return "__SKIP__"

    if line.startswith("Check:") or line.startswith("Valid:") or line.startswith("Invalid:"):
        return "{"

    if line.startswith("Check.close"):
        return "}"

    if line.startswith("Key."):
        return f"// switch ({line[4:].rstrip(':')})"

    if line.startswith("c.") and line.endswith(":"):
        val = line[2:-1]
        return f"case {val}:"

    if line == "def:":
        return "default:"

    if line.startswith("Db.") or line.startswith("Db:"):
        return "__SKIP__"

    if line.startswith("db."):
        return "__SKIP__"

    if line.startswith("Obj."):
        parts = line[4:].split(".")
        if len(parts) == 2:
            cls, var = parts
            return f"{cls} {var} = new {cls}();"
        return "__SKIP__"

    if line.startswith("pH:") or line.startswith("fF:"):
        return "__SKIP__"

    if line.startswith("Con:") or line.startswith("En:"):
        return "{"

    if line in ("con.close", "en.close"):
        return "}"

    if line == "db.next":
        return "continue;"

    if line == "db.break":
        return "break;"

    if " = " in line and not line.startswith(("S ", "I ", "L ", "@", "!", "?", "M", "R.", "p ")):
        return f"{line};"

    return line + ";"
