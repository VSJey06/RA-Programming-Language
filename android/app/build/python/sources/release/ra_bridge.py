import sys
import io
from pathlib import Path
from contextlib import redirect_stdout

from lexer.tokenizer import tokenize
from parser.parser import Parser, ParseError
from runtime.runtime import Runtime, RuntimeError as RAError
from runtime.db_engine import DatabaseEngine
from parser.ra_ast import dump

_runtime = Runtime()

def init(data_dir: str) -> None:
    global _runtime
    path = Path(data_dir)
    path.mkdir(parents=True, exist_ok=True)
    bundled = Path(__file__).resolve().parent / "data"
    if bundled.is_dir() and not any(path.iterdir()):
        for f in bundled.glob("*.json"):
            import shutil
            shutil.copy2(f, path / f.name)
    _runtime = Runtime(data_dir=str(path))

def exec(cmd: str) -> str:
    global _runtime
    cmd = cmd.strip()
    if not cmd:
        return ""

    diag = io.StringIO()
    diag.write(f"Raw Input: {cmd}\n")

    try:
        tokens = tokenize(cmd)
        diag.write(f"Tokens: {[(t.kind.name, t.value) for t in tokens]}\n")

        parser = Parser(tokens)
        program = parser.parse()
        diag.write(f"AST Nodes:\n")
        for stmt in program.body:
            diag.write(f"  {dump(stmt)}\n")

        buf = io.StringIO()
        with redirect_stdout(buf):
            _runtime.execute(program)
        output = buf.getvalue()

        if output.rstrip("\n"):
            return output.rstrip("\n")
        return diag.getvalue().rstrip("\n")

    except ParseError as e:
        return f"ParseError: {e}"
    except RAError as e:
        return f"RuntimeError: {e}"
    except Exception as e:
        return f"Error: {e}"

def reset():
    global _runtime
    _runtime = Runtime()
