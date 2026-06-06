"""Tests for RA PF (Program Flow) library.

Covers:
  - Tokenizer: PF, pH, pH.close, fF tokens
  - Parser: PF activation, pH block, fF block
  - Parser: Auto-close at EOF
  - Parser: Stray close markers
  - Parser: .run/.fun rejection in pH/fF
  - Parser: Malformed items in pH/fF
  - Runtime: PF activation
  - Runtime: pH without PF → error
  - Runtime: fF without PF → error
  - Runtime: pH without fF → error
  - Runtime: fF without pH → error
  - Runtime: Full PF execution flow
  - AST dump
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lexer.tokenizer import tokenize
from parser.parser import Parser, ParseError
from parser.ra_ast import PFNode, ProgramHandlerNode, FunctionFlowNode, dump
from runtime.runtime import Runtime
from runtime.runtime import RuntimeError as RAError

PASS = 0
FAIL = 0


def ok(label: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        print(f"  PASS: {label}")
        PASS += 1
    else:
        msg = f"  FAIL: {label}"
        if detail:
            msg += f"  ({detail})"
        print(msg)
        FAIL += 1


# ── Tokenizer tests ───────────────────────────────────────────────────────

def test_token_pf() -> None:
    names = [t.type.name for t in tokenize("PF\n")]
    ok("PF is PF token", names[0] == "PF")


def test_token_ph() -> None:
    names = [t.type.name for t in tokenize("pH:\n")]
    ok("pH: is PH COLON", names[:2] == ["PH", "COLON"])


def test_token_ph_close() -> None:
    names = [t.type.name for t in tokenize("pH.close\n")]
    ok("pH.close is PH_CLOSE", names[0] == "PH_CLOSE")


def test_token_ff() -> None:
    names = [t.type.name for t in tokenize("fF:\n")]
    ok("fF: is FF COLON", names[:2] == ["FF", "COLON"])


def test_token_ff_close() -> None:
    """f.close is reused as FUN_CLOSE."""
    names = [t.type.name for t in tokenize("f.close\n")]
    ok("f.close is FUN_CLOSE", names[0] == "FUN_CLOSE")


# ── Parser tests ──────────────────────────────────────────────────────────

def test_parse_pf() -> None:
    prog = Parser(tokenize("PF\n")).parse()
    ok("PF parses", isinstance(prog.body[0], PFNode))


def test_parse_ph() -> None:
    src = "pH:\n@Cls.User\nObj.User.Ken\nM.Login\npH.close\n"
    prog = Parser(tokenize(src)).parse()
    n = prog.body[0]
    ok("pH parses", isinstance(n, ProgramHandlerNode))
    ok("pH has 3 items", len(n.body) == 3)


def test_parse_ph_auto_close() -> None:
    prog = Parser(tokenize("pH:\n@Cls.User\n")).parse()
    ok("pH auto close", prog.body[0].auto_close)


def test_parse_ff() -> None:
    src = "fF:\nUser.Login\nUser.Profile\nf.close\n"
    prog = Parser(tokenize(src)).parse()
    n = prog.body[0]
    ok("fF parses", isinstance(n, FunctionFlowNode))
    ok("fF has 2 calls", len(n.body) == 2)


def test_parse_ff_auto_close() -> None:
    prog = Parser(tokenize("fF:\nUser.Login\n")).parse()
    ok("fF auto close", prog.body[0].auto_close)


def test_stray_ph_close() -> None:
    try:
        Parser(tokenize("pH.close\n")).parse()
        ok("Stray pH.close raises ParseError", False)
    except ParseError:
        ok("Stray pH.close raises ParseError", True)


def test_dot_run_rejected_in_ph() -> None:
    try:
        Parser(tokenize("PF\npH:\n.run:\n  p 1\nr.close\npH.close\n")).parse()
        ok(".run rejected in pH", False)
    except ParseError:
        ok(".run rejected in pH", True)


def test_dot_run_rejected_in_ff() -> None:
    try:
        Parser(tokenize("PF\nfF:\n.run:\n  p 1\nr.close\nf.close\n")).parse()
        ok(".run rejected in fF", False)
    except ParseError:
        ok(".run rejected in fF", True)


def test_dot_fun_rejected_in_ph() -> None:
    try:
        Parser(tokenize("PF\npH:\n.fun:\n  p 1\nf.close\npH.close\n")).parse()
        ok(".fun rejected in pH", False)
    except ParseError:
        ok(".fun rejected in pH", True)


def test_dot_fun_rejected_in_ff() -> None:
    try:
        Parser(tokenize("PF\nfF:\n.fun:\n  p 1\nf.close\nf.close\n")).parse()
        ok(".fun rejected in fF", False)
    except ParseError:
        ok(".fun rejected in fF", True)


def test_ph_bad_item() -> None:
    try:
        Parser(tokenize("pH:\nI x = 1\npH.close\n")).parse()
        ok("Bad pH item raises ParseError", False)
    except ParseError:
        ok("Bad pH item raises ParseError", True)


def test_ff_bad_item() -> None:
    try:
        Parser(tokenize("fF:\nI x = 1\nf.close\n")).parse()
        ok("Bad fF item raises ParseError", False)
    except ParseError:
        ok("Bad fF item raises ParseError", True)


# ── Runtime tests ─────────────────────────────────────────────────────────

def test_runtime_pf_activates() -> None:
    rt = Runtime()
    rt.execute(Parser(tokenize("PF\n")).parse())
    ok("PF activates", rt._pf_engine.active)


def test_ph_without_pf() -> None:
    rt = Runtime()
    try:
        rt.execute(Parser(tokenize("pH:\n@Cls.User\npH.close\n")).parse())
        ok("pH without PF raises error", False)
    except RAError as e:
        ok("pH without PF raises error", "PF library not activated" in str(e))


def test_ff_without_pf() -> None:
    rt = Runtime()
    try:
        rt.execute(Parser(tokenize("fF:\nUser.Login\nf.close\n")).parse())
        ok("fF without PF raises error", False)
    except RAError as e:
        ok("fF without PF raises error", "PF library not activated" in str(e))


def test_ph_without_ff() -> None:
    rt = Runtime()
    try:
        rt.execute(Parser(tokenize(
            "PF\npH:\n@Cls.User\npH.close\n",
        )).parse())
        ok("pH without fF raises error", False)
    except RAError as e:
        ok("pH without fF raises error", "pH requires fF" in str(e))


def test_ff_without_ph() -> None:
    rt = Runtime()
    try:
        rt.execute(Parser(tokenize(
            "PF\nfF:\nUser.Login\nf.close\n",
        )).parse())
        ok("fF without pH raises error", False)
    except RAError as e:
        ok("fF without pH raises error", "fF requires pH" in str(e))


def test_full_pf_flow() -> None:
    src = """
PF

@Cls.User:
    M.Login:
        p."Login"
    /.close
    M.Profile:
        p."Profile"
    /.close
@.close

Obj.User.Ken

pH:
    @Cls.User
    Obj.User.Ken
    M.Login
    M.Profile
pH.close

fF:
    User.Login
    User.Profile
f.close
"""
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    out = buf.getvalue().strip()
    ok("Full PF flow outputs Login and Profile",
       out == "Login\nProfile" or out == "Login Profile")


# ── Mode B: explicit binding tests ────────────────────────────────────────

def test_parse_ff_with_target() -> None:
    """fF.M.Login: parses as FunctionFlowNode with target 'M.Login'."""
    src = "fF.M.Login:\nUser.Validate\nUser.Login\nf.close\n"
    prog = Parser(tokenize(src)).parse()
    n = prog.body[0]
    ok("fF.M.Login: parses", isinstance(n, FunctionFlowNode))
    ok("fF target is M.Login", n.target == "M.Login")
    ok("fF body has 2 calls", len(n.body) == 2)


def test_parse_ff_target_obj() -> None:
    """fF.Obj.User.Admin: parses with target 'Obj.User.Admin'."""
    src = "fF.Obj.User.Admin:\nUser.Login\nf.close\n"
    prog = Parser(tokenize(src)).parse()
    n = prog.body[0]
    ok("fF.Obj.User.Admin: parses", isinstance(n, FunctionFlowNode))
    ok("target is Obj.User.Admin", n.target == "Obj.User.Admin")


def test_parse_ff_target_cls() -> None:
    """fF.@Cls.User: parses with target '@Cls.User'."""
    src = "fF.@Cls.User:\nUser.Login\nf.close\n"
    prog = Parser(tokenize(src)).parse()
    n = prog.body[0]
    ok("fF.@Cls.User: parses", isinstance(n, FunctionFlowNode))
    ok("target is @Cls.User", n.target == "@Cls.User")


def test_parse_ff_no_target_is_none() -> None:
    """Plain fF: has target=None."""
    src = "fF:\nUser.Login\nf.close\n"
    prog = Parser(tokenize(src)).parse()
    n = prog.body[0]
    ok("plain fF target is None", n.target is None)


def test_ast_dump_pf() -> None:
    src = "PF\npH:\n@Cls.User\npH.close\nfF:\nUser.Login\nf.close\n"
    out = dump(Parser(tokenize(src)).parse())
    ok("AST dump has PFNode", "PFNode" in out)
    ok("AST dump has ProgramHandlerNode", "ProgramHandlerNode" in out)
    ok("AST dump has FunctionFlowNode", "FunctionFlowNode" in out)


# ── Mode B: runtime tests ─────────────────────────────────────────────────

def test_mode_b_single_flow() -> None:
    """1 pH → 1 fF with explicit M.Login binding."""
    src = """
PF

@Cls.User:
    M.Login:
        p."Login"
    /.close
@.close

Obj.User.u

pH:
    @Cls.User
    Obj.User.u
    M.Login
pH.close

fF.M.Login:
    User.Login
f.close
"""
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    out = buf.getvalue().strip()
    ok("Mode B single flow outputs Login",
       out == "Login")


def test_mode_b_multi_flow() -> None:
    """1 pH → 2 fF with explicit M.Login and M.Profile bindings."""
    src = """
PF

@Cls.User:
    M.Login:
        p."Login"
    /.close
    M.Profile:
        p."Profile"
    /.close
@.close

Obj.User.u

pH:
    @Cls.User
    Obj.User.u
    M.Login
    M.Profile
pH.close

fF.M.Login:
    User.Login
f.close

fF.M.Profile:
    User.Profile
f.close
"""
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    out = buf.getvalue().strip()
    ok("Mode B multi flow outputs Login and Profile in order",
       out == "Login\nProfile" or out == "Login Profile")


def test_mode_b_invalid_target() -> None:
    """fF.M.Unknown: raises error when target not in pH."""
    src = """
PF

pH:
    M.Login
pH.close

fF.M.Unknown:
    User.Login
f.close
"""
    rt = Runtime()
    try:
        rt.execute(Parser(tokenize(src)).parse())
        ok("Invalid target raises error", False)
    except RAError as e:
        ok("Invalid target raises error",
           "PF flow target 'M.Unknown' not found" in str(e))


# ── Check / Key integration inside fF ─────────────────────────────────────

def test_check_inside_ff() -> None:
    """Check block inside fF executes correctly."""
    src = """
PF

@Cls.User:
    M.Login:
        p."Login"
    /.close
@.close

Obj.User.u

pH:
    @Cls.User
    Obj.User.u
    M.Login
pH.close

fF:
    Check:
        User.Login
    Valid:
        User.Login
    Check.close
f.close
"""
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    out = buf.getvalue().strip()
    # Check body runs without error → Valid runs → User.Login runs again
    ok("Check inside fF outputs Login twice",
       out.count("Login") == 2)


def test_check_inside_ff_bound() -> None:
    """Check block inside bound fF works."""
    src = """
PF

@Cls.User:
    M.Login:
        p."Login"
    /.close
@.close

Obj.User.u

pH:
    @Cls.User
    Obj.User.u
    M.Login
pH.close

fF.M.Login:
    Check:
        User.Login
    Check.close
f.close
"""
    import io
    buf = io.StringIO()
    sys.stdout = buf
    Runtime().execute(Parser(tokenize(src)).parse())
    sys.stdout = sys.__stdout__
    out = buf.getvalue().strip()
    ok("Check inside bound fF outputs Login",
       out == "Login")


# ── Run all ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("------------------------------------------------------------")
    print("PF (Program Flow) library tests")
    print("------------------------------------------------------------")
    test_token_pf()
    test_token_ph()
    test_token_ph_close()
    test_token_ff()
    test_token_ff_close()
    test_parse_pf()
    test_parse_ph()
    test_parse_ph_auto_close()
    test_parse_ff()
    test_parse_ff_auto_close()
    test_stray_ph_close()
    test_dot_run_rejected_in_ph()
    test_dot_run_rejected_in_ff()
    test_dot_fun_rejected_in_ph()
    test_dot_fun_rejected_in_ff()
    test_ph_bad_item()
    test_ff_bad_item()
    test_runtime_pf_activates()
    test_ph_without_pf()
    test_ff_without_pf()
    test_ph_without_ff()
    test_ff_without_ph()
    test_full_pf_flow()
    test_parse_ff_with_target()
    test_parse_ff_target_obj()
    test_parse_ff_target_cls()
    test_parse_ff_no_target_is_none()
    test_ast_dump_pf()
    test_mode_b_single_flow()
    test_mode_b_multi_flow()
    test_mode_b_invalid_target()
    test_check_inside_ff()
    test_check_inside_ff_bound()

    print("------------------------------------------------------------")
    print(f"Total: {PASS} passed, {FAIL} failed")
    print("------------------------------------------------------------")
    sys.exit(1 if FAIL else 0)
