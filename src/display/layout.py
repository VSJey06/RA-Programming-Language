"""RA Terminal Layout Engine — Code Area | Assist Area | Syntax Library split."""

from __future__ import annotations

import io
import os
import sys

from textual.app import App, ComposeResult, SystemCommand
from textual.widgets import Header, Input, TextArea, Static
from textual.containers import Horizontal, Vertical

_src = os.path.join(os.path.dirname(__file__), "..")
if _src not in sys.path:
    sys.path.insert(0, os.path.abspath(_src))

from lexer.tokenizer import TokenizeError, tokenize
from parser.parser import ParseError, Parser
from runtime.runtime import Runtime, RuntimeError as RAError
from display.banner import get_banner
from display.syntax_library import render_all as render_syntax_all
from display.syntax_library import render_category_by_name
from display.exit import should_exit
from corrector.corrector import Corrector
from lib.ai.assist import MentorEngine as Assist
from lib.ai.assist import Suggestor


CSS = """
Screen {
    layout: vertical;
}
#code-panel {
    width: 2fr;
    height: 1fr;
    min-width: 30;
}
#assist-panel {
    width: 1fr;
    height: 1fr;
    min-width: 16;
}
#syntax-panel {
    width: 1fr;
    height: 1fr;
    min-width: 18;
}
#syntax-panel.hidden {
    display: none;
}
#code-area {
    height: 1fr;
    overflow-y: auto;
    padding: 0 1;
}
#assist-area {
    height: 1fr;
}
#syntax-content {
    height: 1fr;
    overflow-y: auto;
    padding: 0 1;
}
#output-area {
    height: 1;
    background: $surface;
    color: $text;
    padding: 0 1;
}
#prompt {
    dock: bottom;
    margin: 0 0 1 0;
}
.panel-header {
    background: $primary-background;
    color: $primary;
    text-style: bold;
    padding: 0 1;
}
"""


def _is_block_opener(line: str) -> str | None:
    s = line.strip()
    if s.startswith("Db") and s.endswith(":"):
        return "db.close"
    if s.startswith(".run:"):
        return "r.close"
    if s.startswith(".fun:"):
        return "f.close"
    if s.startswith("@Cls.") and s.endswith(":"):
        return "@.close"
    if s.startswith("M.") and s.endswith(":"):
        return "/.close"
    if s.startswith("? For"):
        return "#"
    if s.startswith("? While"):
        return "#"
    if s.startswith("! If"):
        return "#"
    if s.startswith("pH:"):
        return "pH.close"
    if s.startswith("fF:") or (s.startswith("fF") and "." in s and s.endswith(":")):
        return "f.close"
    if s.startswith("Check") and s.endswith(":"):
        return "Check.close"
    if s.startswith("Key") and s.endswith(":"):
        return "Key.close"
    if s.startswith("Con") and s.endswith(":"):
        return "Con.close"
    if s.startswith("En") and s.endswith(":"):
        return "En.close"
    return None


class RALayoutApp(App):
    """RA Terminal TUI with Code Area | Assist Area | Syntax Library split."""

    CSS = CSS

    def __init__(self):
        super().__init__()
        self.title = "RA"
        self._banner = get_banner()
        self._syntax_visible = False
        self._runtime = Runtime()
        self._corrector = Corrector()
        self._suggestor = Suggestor()
        self._buffer: list[str] = []
        self._closer_stack: list[str] = []

        Assist.ensure_loaded()

    def get_system_commands(self, screen):
        for cmd in super().get_system_commands(screen):
            if cmd.title == "Keys":
                yield SystemCommand(
                    "Syntax Library",
                    "Browse the syntax library",
                    self.action_open_syntax_library,
                )
            else:
                yield cmd

    def action_open_syntax_library(self) -> None:
        self._toggle_syntax_library()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal():
            with Vertical(id="code-panel"):
                yield Static("Code Area", classes="panel-header")
                yield Static(id="code-area")
            with Vertical(id="assist-panel"):
                yield Static("Assist Area", classes="panel-header")
                yield TextArea(id="assist-area", read_only=True,
                               show_line_numbers=False)
            with Vertical(id="syntax-panel", classes="hidden"):
                yield Static("Syntax Library", classes="panel-header")
                yield Static(id="syntax-content")
        yield Static(id="output-area")
        yield Input(id="prompt", placeholder="RA > ")

    def on_mount(self) -> None:
        code_w = self.query_one("#code-area", Static)
        code_w.update(self._banner)
        self.query_one("#prompt").focus()
        self._update_assist("")

    # ── Input events ──────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        line = event.value
        self.query_one("#prompt").clear()
        self._process_line(line)

    def on_input_changed(self, event: Input.Changed) -> None:
        self._update_assist(event.value)

    # ── Line processing ───────────────────────────────────────

    def _process_line(self, line: str) -> None:
        stripped = line.strip()
        if not stripped:
            return

        if not self._closer_stack:
            if should_exit(stripped):
                self.exit()
                return
            if stripped in ("help", "syntax"):
                self._ensure_syntax_visible()
                self._show_syntax_library()
                return
            if stripped.startswith("syntax "):
                cat = stripped[7:].strip()
                self._ensure_syntax_visible()
                self._show_syntax_library(cat)
                return
            if stripped == "clear":
                self._clear_screen()
                return
            if stripped == "reset":
                self._runtime = Runtime()
                self._set_output("Runtime reset")
                return

            assist_msg = Assist.assist_line(stripped)
            if assist_msg:
                self._set_output(assist_msg)

            if not self._corrector.validate(line, self._runtime):
                return

            expected = _is_block_opener(stripped)
            if expected is not None:
                self._closer_stack.append(expected)
                self._buffer.append(line)
                self._update_code_area()
                next_suggestion = Assist.suggest_next(stripped)
                if next_suggestion:
                    self._set_output(assist_msg or next_suggestion)
                return

        self._buffer.append(line)

        if self._closer_stack:
            if stripped == self._closer_stack[-1]:
                self._closer_stack.pop()
                if not self._closer_stack:
                    self._execute_buffer()
            else:
                expected = _is_block_opener(stripped)
                if expected is not None:
                    self._closer_stack.append(expected)
            self._update_code_area()
        else:
            self._execute_line(line)

    def _execute_buffer(self) -> None:
        source = "\n".join(self._buffer)
        self._run_source(source)
        self._buffer.clear()
        self._update_code_area()
        Assist.learn_pattern(source, valid=True)

    def _execute_line(self, line: str) -> None:
        self._run_source(line)
        Assist.learn_pattern(line, valid=True)

    def _run_source(self, source: str) -> None:
        old_stdout = sys.stdout
        captured = io.StringIO()
        sys.stdout = captured
        try:
            tokens = tokenize(source)
            ast = Parser(tokens).parse()
            self._runtime.execute(ast)
            output = captured.getvalue()
            if output:
                self._set_output(output.rstrip())
            else:
                self._set_output("(executed successfully)")
        except (ParseError, RAError, SyntaxError, TokenizeError) as exc:
            msg = str(exc)
            correction = None
            try:
                correction = self._corrector.translator.translate_exception(
                    exc, source, self._runtime)
            except Exception:
                pass
            if correction:
                self._set_output(f"Error: {correction}", is_error=True)
            else:
                etype = ("Syntax" if isinstance(exc, (ParseError, TokenizeError))
                         else "Runtime")
                self._set_output(f"{etype}Error: {msg}", is_error=True)
        finally:
            sys.stdout = old_stdout

    # ── UI updates ────────────────────────────────────────────

    def _update_code_area(self) -> None:
        code_w = self.query_one("#code-area", Static)
        text = "\n".join(self._buffer) if self._buffer else ""
        code_w.update(text)

    def _update_assist(self, line: str) -> None:
        stripped = line.strip()
        assist_w = self.query_one("#assist-area", TextArea)
        lines: list[str] = []

        if stripped:
            assist_msg = Assist.assist_line(stripped)
            if assist_msg:
                lines.append("Check:")
                for l in assist_msg.split("\n"):
                    ls = l.strip()
                    if ls:
                        lines.append(f"  {ls}")
                lines.append("")

            next_suggestion = Assist.suggest_next(stripped)
            if next_suggestion:
                lines.append("Suggestion:")
                for sline in next_suggestion.split("\n"):
                    s = sline.strip()
                    if s:
                        lines.append(f"  {s}")
        else:
            lines.append("  Start typing code in the prompt")

        assist_w.load_text("\n".join(lines) if lines else "")

    def _set_output(self, text: str, is_error: bool = False) -> None:
        out_w = self.query_one("#output-area", Static)
        out_w.update(text)

    def _clear_screen(self) -> None:
        self._buffer.clear()
        self._closer_stack.clear()
        self._update_code_area()
        self._set_output("")

    # ── Syntax Library panel ──────────────────────────────────

    def _ensure_syntax_visible(self) -> None:
        panel = self.query_one("#syntax-panel")
        panel.remove_class("hidden")
        self._syntax_visible = True

    def _toggle_syntax_library(self) -> None:
        panel = self.query_one("#syntax-panel")
        if self._syntax_visible:
            panel.add_class("hidden")
            self._syntax_visible = False
        else:
            panel.remove_class("hidden")
            self._syntax_visible = True
            self._show_syntax_library()

    def _show_syntax_library(self, category: str = "") -> None:
        sc = self.query_one("#syntax-content", Static)
        if category:
            rendered = render_category_by_name(category)
            if rendered:
                sc.update(rendered)
                self._set_output(f"Syntax Library: {category}")
            else:
                sc.update(f"Unknown category: {category!r}")
                self._set_output(f"Unknown category: {category!r}", is_error=True)
        else:
            sc.update(render_syntax_all())
            self._set_output("Syntax Library — full reference")


def launch() -> int:
    app = RALayoutApp()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(launch())
