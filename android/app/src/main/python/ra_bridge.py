import sys
import io
import traceback
from contextlib import redirect_stdout

from lexer.tokenizer import tokenize
from parser.parser import ParseError, Parser
from runtime.runtime import Runtime, RuntimeError as RAError

_runtime = Runtime()

def exec(cmd: str) -> str:
    global _runtime
    cmd = cmd.strip()
    if not cmd:
        return ""
    if cmd.lower() == "help":
        return _help_text()
    if cmd.lower() == "clear":
        return "\n" * 50
    if cmd.lower() == "reset":
        _runtime = Runtime()
        return "Runtime reset."
    if cmd.lower() in ("exit", "quit"):
        return ""
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            tokens = tokenize(cmd)
            parser = Parser(tokens)
            program = parser.parse()
            _runtime.execute(program)
    except ParseError as e:
        return f"ParseError: {e}"
    except RAError as e:
        return f"RuntimeError: {e}"
    except Exception as e:
        return f"Error: {e}"
    output = buf.getvalue()
    return output.rstrip("\n")

def _help_text() -> str:
    return """RA Language v1.0.3
S var = "text"    - String variable
I var = 123       - Integer variable
p expr            - Print expression
! If.cond, ... #  - If statement
? For.var=s;e,    - For loop
? While.cond,     - While loop
@Cls.Name: ... @  - Class definition
Obj.Class.Var     - Object instantiation
help              - Show this help
clear             - Clear screen
reset             - Reset runtime"""

def reset():
    global _runtime
    _runtime = Runtime()
