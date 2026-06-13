"""Syntax Library — single source of truth for all RA syntax documentation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SyntaxEntry:
    """A single syntax item."""
    name: str
    description: str = ""
    syntax: str = ""
    examples: list[str] = field(default_factory=list)


@dataclass
class SyntaxCategory:
    """A category of syntax features."""
    name: str
    description: str = ""
    entries: list[SyntaxEntry] = field(default_factory=list)


LIBRARY: list[SyntaxCategory] = [

    SyntaxCategory(
        name="Variables",
        description="Variable declarations with type inference and defaults",
        entries=[
            SyntaxEntry("Integer", "Integer variable (default 0)",
                        "I name\nI name = <int>",
                        ["I age", "I count = 42"]),
            SyntaxEntry("String", "String variable (default empty)",
                        "S name\nS name = <string>",
                        ["S name = \"Ken\""]),
            SyntaxEntry("List", "List variable (default empty)",
                        "L name\nL name = <list>",
                        ["L items", "L items = [1, 2, 3]"]),
            SyntaxEntry("Boolean", "Boolean variable (default False)",
                        "B name\nB name = True/False",
                        ["B ok", "B done = True"]),
            SyntaxEntry("Float", "Float variable (default 0.0)",
                        "F name\nF name = <float>",
                        ["F pi = 3.14"]),
            SyntaxEntry("Reassignment", "Change value of existing variable",
                        "name = <expr>",
                        ["x = 10", "name = \"Alice\""]),
            SyntaxEntry("Defaults", "Variables auto-initialize to zero values",
                        "",
                        ["I age  -> 0", "S name -> \"\"", "B ok   -> False"]),
        ],
    ),

    SyntaxCategory(
        name="Print",
        description="Output values to the terminal",
        entries=[
            SyntaxEntry("Print with newline", "Print expression followed by newline",
                        "p expression",
                        ["p \"Hello\"", "p x + 1"]),
            SyntaxEntry("Print without newline", "Print expression without trailing newline",
                        "pl expression",
                        ["pl \"Size = \"", "pl Users.size"]),
            SyntaxEntry("Dot syntax", "Optional dot separator (syntactic sugar)",
                        "p.expression\npl.expression",
                        ["p.x", "pl.items"]),
        ],
    ),

    SyntaxCategory(
        name="PAC System",
        description="Package-based container system — built-in runtime packages",
        entries=[
            SyntaxEntry("Available packages", "Built-in container types",
                        "Stack\nQueue\nDequeue",
                        ["Stack.Users", "Queue.Tasks", "Dequeue.Grid"]),
            SyntaxEntry("Container creation", "Create a named container instance",
                        "Stack.Name\nQueue.Name\nDequeue.Name",
                        ["Stack.Users", "Queue.Tasks", "Dequeue.Grid"]),
        ],
    ),

    SyntaxCategory(
        name="Stack (LIFO)",
        description="Last-In-First-Out data structure",
        entries=[
            SyntaxEntry("Creation", "Create a new stack",
                        "Stack.Name", ["Stack.Users"]),
            SyntaxEntry("Push", "Push value onto stack",
                        "Name.push:value", ["Users.push:10"]),
            SyntaxEntry("Pop", "Pop top value (removes it)",
                        "Name.pop", ["x = Users.pop"]),
            SyntaxEntry("Peek", "Peek top value (keeps it)",
                        "Name.peek", ["y = Users.peek"]),
            SyntaxEntry("Size", "Total slot count",
                        "Name.size", ["Users.size"]),
            SyntaxEntry("Count", "Filled slot count",
                        "Name.count", ["Users.count"]),
            SyntaxEntry("Space", "Empty slot count",
                        "Name.space", ["Users.space"]),
            SyntaxEntry("Empty check", "True if stack is empty",
                        "Name.empty", ["Users.empty"]),
            SyntaxEntry("Space operations", "Fill specific empty slots",
                        "Name.space.first:value\nName.space.last:value\nName.space.sFirst:value\nName.space.bLast:value\nName.space.insert:value",
                        ["Users.space.first:99"]),
        ],
    ),

    SyntaxCategory(
        name="Queue (FIFO)",
        description="First-In-First-Out data structure",
        entries=[
            SyntaxEntry("Creation", "Create a new queue",
                        "Queue.Name", ["Queue.Users"]),
            SyntaxEntry("Push", "Enqueue at rear",
                        "Name.push:value", ["Users.push:10"]),
            SyntaxEntry("Pop", "Dequeue from front",
                        "Name.pop", ["x = Users.pop"]),
            SyntaxEntry("Peek", "Peek front (keeps it)",
                        "Name.peek", ["y = Users.peek"]),
            SyntaxEntry("Size", "Number of elements",
                        "Name.size", ["Users.size"]),
            SyntaxEntry("Count", "Number of elements",
                        "Name.count", ["Users.count"]),
            SyntaxEntry("Empty check", "True if queue is empty",
                        "Name.empty", ["Users.empty"]),
        ],
    ),

    SyntaxCategory(
        name="Dequeue (2D Grid)",
        description="Two-dimensional grid container with dynamic rows and fixed columns (default 4)",
        entries=[
            SyntaxEntry("Creation", "Create a new dequeue grid",
                        "Dequeue.Name", ["Dequeue.Grid"]),
            SyntaxEntry("Insert", "Insert value into first empty cell",
                        "Name.insert:value", ["Grid.insert:10"]),
            SyntaxEntry("Remove", "Replace cell with EMPTY",
                        "Name.remove.X,Y", ["Grid.remove.1,2"]),
            SyntaxEntry("Get", "Read cell value (1-indexed)",
                        "Name.get.X,Y", ["Grid.get.1,1"]),
            SyntaxEntry("Find", "Search for a value, returns \"X,Y\" or \"- -\"",
                        "Name.find:value", ["Grid.find:20"]),
            SyntaxEntry("Exists", "Check if value exists in grid",
                        "Name.exists:value", ["Grid.exists:20"]),
            SyntaxEntry("Rows", "Number of rows",
                        "Name.rows", ["Grid.rows"]),
            SyntaxEntry("Colms", "Column count (max width)",
                        "Name.colms", ["Grid.colms"]),
            SyntaxEntry("Row", "Get row N as space-separated string",
                        "Name.row.N", ["Grid.row.1"]),
            SyntaxEntry("Column", "Get column N as space-separated string",
                        "Name.colm.N", ["Grid.colm.1"]),
            SyntaxEntry("Size", "Total cell count",
                        "Name.size", ["Grid.size"]),
            SyntaxEntry("Count", "Non-empty cell count",
                        "Name.count", ["Grid.count"]),
            SyntaxEntry("Space", "Empty cell count (EMPTY or NV)",
                        "Name.space", ["Grid.space"]),
            SyntaxEntry("Empty check", "True if grid is empty",
                        "Name.empty", ["Grid.empty"]),
            SyntaxEntry("Clear", "Destructive clear of all cells",
                        "Name.clear", ["Grid.clear"]),
            SyntaxEntry("Diagonal", "8 directional rays (1-indexed)",
                        "Name.diagonal.x\nName.diagonal.y\nName.diagonal.-x\nName.diagonal.-y\nName.diagonal.x-y\nName.diagonal.y-x\nName.diagonal.-x-y\nName.diagonal.-y-x",
                        ["Grid.diagonal.x", "Grid.diagonal.x-y"]),
            SyntaxEntry("Space operations", "Fill specific empty cells",
                        "Name.space.first:value\nName.space.last:value\nName.space.sFirst:value\nName.space.bLast:value\nName.space.X,Y:value",
                        ["Grid.space.first:99"]),
        ],
    ),

    SyntaxCategory(
        name="Special Values",
        description="Built-in singleton sentinels for container slots",
        entries=[
            SyntaxEntry("EMPTY", "Intentionally emptied slot (user-removed)",
                        "EMPTY", ["Grid.remove.1,1", "x == EMPTY"]),
            SyntaxEntry("NV", "System-created unfilled cell (Dequeue only)",
                        "NV", ["Grid.space returns NV count"]),
        ],
    ),

    SyntaxCategory(
        name="Methods",
        description="Define and execute reusable procedures",
        entries=[
            SyntaxEntry("Define method", "Create a method block",
                        "M.Name:\n  ...\n/.close",
                        ["M.test:\n  p \"HI\"\n/.close"]),
            SyntaxEntry("Execute method", "Run a method (global or object)",
                        "Name.run\nObj.Method.run",
                        ["test.run", "Person.say.run"]),
        ],
    ),

    SyntaxCategory(
        name="Classes",
        description="Object-oriented class definitions",
        entries=[
            SyntaxEntry("Define class", "Create a class block",
                        "@Cls.Name:\n  ...\n@.close",
                        ["@Cls.Person:", "@.close"]),
        ],
    ),

    SyntaxCategory(
        name="Objects",
        description="Object instantiation from classes",
        entries=[
            SyntaxEntry("Create object", "Instantiate a class",
                        "Obj.Class.Name",
                        ["Obj.Person.Ken"]),
        ],
    ),

    SyntaxCategory(
        name="OOP Library",
        description="OOP activation and advanced object features",
        entries=[
            SyntaxEntry("Activate OOP", "Enable OOP library features",
                        "OOP", ["OOP"]),
            SyntaxEntry("Constructor", "Object initialization block",
                        "Con:\n  ...\nCon.close",
                        ["Con:\n  p.\"Created\"\nCon.close"]),
            SyntaxEntry("Encapsulation", "Private member block",
                        "En:\n  ...\nEn.close",
                        ["En:\n  S password=\"1234\"\nEn.close"]),
        ],
    ),

    SyntaxCategory(
        name="Database",
        description="Named in-memory databases with persistence",
        entries=[
            SyntaxEntry("Create database", "Define a named database",
                        "Db.Name:\n  ...\nDb.close", ["Db.Users:", "Db.close"]),
            SyntaxEntry("Save", "Persist database to disk",
                        "Db.Name.save", ["Db.Users.save"]),
            SyntaxEntry("Load", "Load database from disk",
                        "Db.Name.load", ["Db.Users.load"]),
        ],
    ),

    SyntaxCategory(
        name="Check / Exception Handling",
        description="Try-Except pattern for RA",
        entries=[
            SyntaxEntry("Define check block",
                        "Check:\n  ...\nValid:\n  ...\nInvalid:\n  ...\nCheck.close",
                        "",
                        ["Check:\n  p.UnknownVariable\nValid:\n  p.\"Success\"\nInvalid:\n  p.\"Failed\"\nCheck.close"]),
        ],
    ),

    SyntaxCategory(
        name="Key / Switch",
        description="Multi-branch conditional matching",
        entries=[
            SyntaxEntry("Key on variable",
                        "Key.variable:\n  c.value:\n    ...\n  def:\n    ...\nKey.close",
                        "",
                        ["Key.age:\n  c.18:\n    p.\"Adult\"\n  def:\n    p.\"Unknown\"\nKey.close"]),
            SyntaxEntry("Key on object property",
                        "Key.Obj.prop:\n  c.\"value\":\n    ...\n  def:\n    ...\nKey.close",
                        "",
                        ["Key.Admin.role:\n  c.\"Admin\":\n    p.\"Admin\"\n  def:\n    p.\"Guest\"\nKey.close"]),
        ],
    ),

    SyntaxCategory(
        name="Loops",
        description="For and While iteration blocks",
        entries=[
            SyntaxEntry("For loop", "Iterate over a range",
                        "? For.var=start;end,\n  ...\n#",
                        ["? For.i=0;10,\n  p i\n#"]),
            SyntaxEntry("While loop", "Loop while condition is true",
                        "? While.condition,\n  ...\n#",
                        ["? While.x < 10,\n  p x\n#"]),
        ],
    ),

    SyntaxCategory(
        name="Conditions",
        description="If / ElseIf / Else branching blocks",
        entries=[
            SyntaxEntry("If", "Conditional execution",
                        "! If.condition,\n  ...\n#", ["! If.x > 5,\n  p \"Big\"\n#"]),
            SyntaxEntry("Else If", "Additional condition",
                        "!! condition,\n  ...\n#", ["!! x > 10,\n  p \"Even bigger\"\n#"]),
            SyntaxEntry("Else", "Fallback branch",
                        "! Else\n  ...\n#", ["! Else\n  p \"Small\"\n#"]),
        ],
    ),

    SyntaxCategory(
        name="Blocks",
        description="Reusable code blocks (.run:, .fun:)",
        entries=[
            SyntaxEntry("Run block", "Execute-once block",
                        ".run:\n  ...\nr.close", [""]),
            SyntaxEntry("Function block", "Reusable function block",
                        ".fun:\n  ...\nf.close", [""]),
        ],
    ),

    SyntaxCategory(
        name="PF Framework",
        description="Program Framework — blueprint + execution flows",
        entries=[
            SyntaxEntry("Activate PF", "Enable PF framework",
                        "PF", ["PF"]),
            SyntaxEntry("Program handler", "Blueprint defining program structure",
                        "pH:\n  M.Name\n  M.Name\npH.close",
                        ["pH:\n  M.Login\n  M.Dashboard\npH.close"]),
            SyntaxEntry("Single function flow", "Execute a single flow",
                        "fF:\n  Module.Func\nf.close",
                        ["fF:\n  User.Login\nf.close"]),
            SyntaxEntry("Multiple function flows", "Named flows",
                        "fF.M.Name:\n  Module.Func\nf.close",
                        ["fF.M.Login:\n  User.Login\nf.close"]),
            SyntaxEntry("PF + Check", "Flow with exception handling",
                        "fF.M.Name:\n  Check:\n    ...\n  Valid:\n    ...\n  Invalid:\n    ...\n  Check.close\nf.close",
                        [""]),
            SyntaxEntry("PF + Key", "Flow with switch",
                        "fF.M.Name:\n  Key.prop:\n    c.val:\n      ...\n    def:\n      ...\n  Key.close\nf.close",
                        [""]),
        ],
    ),

    SyntaxCategory(
        name="AI Library",
        description="AI-powered code conversion and generation",
        entries=[
            SyntaxEntry("Activate AI", "Enable AI library features",
                        "AI", ["AI"]),
            SyntaxEntry(".cov:", "Convert source from another language to RA",
                        ".cov:Language.\"path\"\ncov.close", [""]),
            SyntaxEntry(".expo:", "Export RA source to another language",
                        ".expo:Language.\"path\"\nex.close", [""]),
            SyntaxEntry(".Call:", "Query built-in knowledge base",
                        ".Call:\"question\"\ncall.close", [""]),
            SyntaxEntry(".Gen:", "Generate RA code from natural language",
                        ".Gen:\"description\"\ngen.close", [""]),
        ],
    ),

    SyntaxCategory(
        name="REPL Commands",
        description="Runtime commands available in the terminal prompt",
        entries=[
            SyntaxEntry("Syntax Library", "Open this documentation",
                        "syntax", [""]),
            SyntaxEntry("Clear", "Clear the code area and output",
                        "clear", [""]),
            SyntaxEntry("Reset", "Reboot the RA runtime (clear all state)",
                        "reset", [""]),
            SyntaxEntry("Exit", "Exit RA",
                        "exit", [""]),
        ],
    ),

    # ── Future categories (placeholders for upcoming features) ──

    SyntaxCategory(
        name="Future — DSA",
        description="Coming: advanced data structures",
        entries=[
            SyntaxEntry("Tree", "Binary tree operations", "", []),
            SyntaxEntry("Graph", "Graph traversal algorithms", "", []),
            SyntaxEntry("Hash Table", "Key-value hash map", "", []),
        ],
    ),
]


def get_category(name: str) -> SyntaxCategory | None:
    """Look up a category by name (case-insensitive)."""
    for cat in LIBRARY:
        if cat.name.lower() == name.lower():
            return cat
    return None


def render_category(cat: SyntaxCategory) -> str:
    """Render a single category as formatted text."""
    lines: list[str] = []
    lines.append(f"## {cat.name}")
    if cat.description:
        lines.append(f"\n{cat.description}\n")
    for entry in cat.entries:
        lines.append(f"\n### {entry.name}")
        if entry.description:
            lines.append(f"\n{entry.description}")
        if entry.syntax:
            lines.append(f"\nSyntax:\n{entry.syntax}")
        if entry.examples:
            ex_lines = []
            for ex in entry.examples:
                if ex.strip():
                    ex_lines.append(f"  {ex}")
            if ex_lines:
                lines.append(f"\nExamples:\n" + "\n".join(ex_lines))
    return "\n".join(lines)


def render_all() -> str:
    """Render the complete syntax library as formatted text."""
    lines: list[str] = []
    lines.append("# RA Syntax Library")
    lines.append("")
    lines.append("Available categories:")
    for cat in LIBRARY:
        lines.append(f"  {cat.name}  — {cat.description}" if cat.description else f"  {cat.name}")
    lines.append("")
    lines.append("Type `syntax <category>` to view a specific category.")
    lines.append("Example: `syntax Dequeue`")
    lines.append("")
    lines.append("─" * 50)
    lines.append("")
    for cat in LIBRARY:
        lines.append(render_category(cat))
        lines.append("")
        lines.append("─" * 50)
        lines.append("")
    return "\n".join(lines)


def render_category_by_name(name: str) -> str | None:
    """Render a single category by name. Returns None if not found."""
    cat = get_category(name)
    if cat is None:
        return None
    return render_category(cat)
