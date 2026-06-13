"""RA Terminal REPL — GUI with Code Area | Assist Area split."""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import ttk

_src = os.path.join(os.path.dirname(__file__), "..")
if _src not in sys.path:
    sys.path.insert(0, os.path.abspath(_src))

from lexer.tokenizer import TokenizeError, tokenize
from parser.parser import ParseError, Parser
from runtime.runtime import Runtime, RuntimeError as RAError
from display.banner import get_banner_plain
from display.syntax_library import render_all as render_syntax_all
from display.syntax_library import render_category_by_name
from display.exit import should_exit
from corrector.corrector import Corrector
from lib.ai.assist import MentorEngine as Assist
from lib.ai.assist import Suggestor

_INDENT = "    "

_BANNER_TEXT: str = ""
_BANNER_SEP = "─" * 55


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


class RATerminal(tk.Tk):
    """RA Terminal REPL — split Code Area | Assist Area GUI."""

    def __init__(self):
        super().__init__()
        self.title("RA Terminal")
        self.geometry("900x650")
        self.minsize(700, 450)

        global _BANNER_TEXT
        _BANNER_TEXT = get_banner_plain()

        self._runtime = Runtime()
        self._corrector = Corrector()
        self._suggestor = Suggestor()
        self._buffer: list[str] = []
        self._closer_stack: list[str] = []
        self._hl_after_id: str | None = None

        Assist.ensure_loaded()

        self._build_banner()
        self._build_split()
        self._build_output_bar()

        self._code_area.bind("<KeyRelease>", self._on_code_change)
        self._code_area.bind("<Return>", self._on_enter)
        self.bind_all("<Control-d>", lambda e: self._run_code())
        self.bind_all("<Control-l>", lambda e: self._clear_screen())
        self._code_area.focus_set()

        self._update_assist()

    # ── Top banner ──────────────────────────────────────────────

    def _build_banner(self) -> None:
        frame = tk.Frame(self, bg="#1e1e2e", bd=0)
        frame.pack(fill=tk.X, padx=0, pady=0)

        banner_text = tk.Text(
            frame, wrap=tk.WORD,
            bg="#1e1e2e", fg="#89b4fa",
            font=("Consolas", 10),
            height=8, bd=0,
            highlightthickness=0,
            state=tk.DISABLED,
            relief=tk.FLAT,
        )
        banner_text.pack(fill=tk.X, padx=12, pady=(8, 0))

        banner_text.config(state=tk.NORMAL)
        banner_text.insert(tk.END, f"{_BANNER_TEXT}\n")
        banner_text.insert(tk.END, f"{_BANNER_SEP}\n")
        banner_text.insert(tk.END, "Commands:\n")
        banner_text.insert(tk.END, "  syntax - Open Syntax Library\n")
        banner_text.insert(tk.END, "  exit   - Exit RA Terminal\n")
        banner_text.insert(tk.END, "  clear  - Clear code area and output\n")
        banner_text.insert(tk.END, "  reset  - Reboot RA runtime\n")
        banner_text.insert(tk.END, f"{_BANNER_SEP}")
        banner_text.config(state=tk.DISABLED)

    # ── Split: Code Area | Assist Area ──────────────────────────

    def _build_split(self) -> None:
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#2d2d44",
                               sashrelief=tk.RAISED, sashwidth=2)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 0))

        self._code_frame = ttk.LabelFrame(paned, text="Code Area")
        self._code_area = tk.Text(
            self._code_frame, wrap=tk.WORD,
            bg="#1e1e2e", fg="#cdd6f4",
            insertbackground="#cdd6f4",
            font=("Consolas", 11),
            relief=tk.SUNKEN, bd=1,
            undo=True,
            tabs=("1c", "2c", "3c", "4c", "5c"),
        )
        self._code_area.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        scroll_c = ttk.Scrollbar(self._code_area, command=self._code_area.yview)
        scroll_c.pack(side=tk.RIGHT, fill=tk.Y)
        self._code_area.config(yscrollcommand=scroll_c.set)
        paned.add(self._code_frame, width=550, stretch="always")

        self._assist_frame = ttk.LabelFrame(paned, text="Assist Area")
        self._assist_text = tk.Text(
            self._assist_frame, wrap=tk.WORD,
            bg="#1e1e2e", fg="#a6adc8",
            font=("Consolas", 10),
            relief=tk.SUNKEN, bd=1,
            state=tk.DISABLED,
        )
        self._assist_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        scroll_a = ttk.Scrollbar(self._assist_text, command=self._assist_text.yview)
        scroll_a.pack(side=tk.RIGHT, fill=tk.Y)
        self._assist_text.config(yscrollcommand=scroll_a.set)

        self._assist_text.tag_config("heading", foreground="#a6e3a1",
                                     font=("Consolas", 10, "bold"))
        self._assist_text.tag_config("suggestion", foreground="#89b4fa")
        self._assist_text.tag_config("hint", foreground="#6c7086")

        paned.add(self._assist_frame, width=280, stretch="never")

    # ── Bottom output bar ───────────────────────────────────────

    def _build_output_bar(self) -> None:
        bar_frame = tk.Frame(self, bg="#1e1e2e", bd=1, relief=tk.SUNKEN)
        bar_frame.pack(fill=tk.X, padx=8, pady=(2, 6))

        self._run_btn = tk.Button(
            bar_frame, text="Run (Ctrl+D)",
            bg="#313244", fg="#cdd6f4",
            activebackground="#45475a",
            font=("Consolas", 9),
            relief=tk.RAISED, bd=1,
            command=self._run_code,
        )
        self._run_btn.pack(side=tk.LEFT, padx=(4, 8), pady=2)

        self._output_var = tk.StringVar()
        self._output_label = tk.Label(
            bar_frame, textvariable=self._output_var,
            bg="#1e1e2e", fg="#cdd6f4",
            font=("Consolas", 10),
            anchor=tk.W,
        )
        self._output_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4, pady=2)

    # ── Assist Area updates ─────────────────────────────────────

    def _update_assist(self) -> None:
        code = self._code_area.get("1.0", tk.END).strip()
        assist = self._assist_text
        assist.config(state=tk.NORMAL)
        assist.delete("1.0", tk.END)

        if not code:
            assist.insert(tk.END, "  Start typing code above\n", "hint")
        else:
            try:
                idx = self._code_area.index(tk.INSERT)
                line_num = int(idx.split(".")[0])
                current_line = self._code_area.get(f"{line_num}.0", f"{line_num}.end").strip()
            except tk.TclError:
                current_line = ""

            if current_line:
                assist_msg = Assist.assist_line(current_line)
                if assist_msg:
                    assist.insert(tk.END, "Check:\n", "heading")
                    for l in assist_msg.split("\n"):
                        ls = l.strip()
                        if ls:
                            assist.insert(tk.END, f"  {ls}\n", "hint")
                    assist.insert(tk.END, "\n")

                next_suggestion = Assist.suggest_next(current_line)
                if next_suggestion:
                    assist.insert(tk.END, "Suggestion:\n", "heading")
                    formatted = self._format_suggestion(next_suggestion)
                    for sline in formatted.split("\n"):
                        if sline.strip() or sline == "":
                            assist.insert(tk.END, f"  {sline}\n", "suggestion")

        assist.config(state=tk.DISABLED)

    def _format_suggestion(self, text: str) -> str:
        try:
            from display.formatter import format_source
            return format_source(text).rstrip()
        except ImportError:
            return text

    # ── Code Area events ────────────────────────────────────────

    def _on_code_change(self, event: tk.Event | None = None) -> None:
        if self._hl_after_id:
            self.after_cancel(self._hl_after_id)
        self._hl_after_id = self.after(200, self._update_assist)

    def _on_enter(self, event: tk.Event | None = None) -> str:
        self._code_area.insert(tk.INSERT, "\n")
        return "break"

    # ── Run code ────────────────────────────────────────────────

    def _run_code(self) -> None:
        source = self._code_area.get("1.0", tk.END).strip()
        if not source:
            return

        lines = source.split("\n")
        first_line = lines[0].strip() if lines else ""

        if first_line == "exit":
            self.destroy()
            return

        if first_line == "clear":
            self._clear_screen()
            return

        if first_line == "reset":
            self._runtime = Runtime()
            self._set_output("Runtime reset")
            self._buffer.clear()
            self._closer_stack.clear()
            return

        if first_line in ("help", "syntax"):
            self._code_area.delete("1.0", tk.END)
            self._code_area.insert("1.0", render_syntax_all())
            self._set_output("Syntax Library — full reference")
            return

        if first_line.startswith("syntax "):
            cat = first_line[7:].strip()
            rendered = render_category_by_name(cat)
            if rendered:
                self._code_area.delete("1.0", tk.END)
                self._code_area.insert("1.0", rendered)
                self._set_output(f"Syntax Library: {cat}")
            else:
                self._set_output(f"Unknown category: {cat!r}", is_error=True)
            return

        import io
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
            Assist.learn_pattern(source, valid=True)
        except (ParseError, RAError, SyntaxError, TokenizeError) as exc:
            msg = str(exc)
            correction = None
            try:
                correction = self._corrector.translator.translate_exception(exc, source, self._runtime)
            except Exception:
                pass
            if correction:
                self._set_output(f"Error: {correction}", is_error=True)
            else:
                etype = "Syntax" if isinstance(exc, (ParseError, TokenizeError)) else "Runtime"
                self._set_output(f"{etype}Error: {msg}", is_error=True)
        finally:
            sys.stdout = old_stdout

        self._update_assist()

    # ── Output ──────────────────────────────────────────────────

    def _set_output(self, text: str, is_error: bool = False) -> None:
        self._output_var.set(text)
        fg = "#f38ba8" if is_error else "#cdd6f4"
        self._output_label.config(fg=fg)

    def _clear_screen(self) -> None:
        self._code_area.delete("1.0", tk.END)
        self._set_output("")
        self._output_var.set("")
        self._buffer.clear()
        self._closer_stack.clear()
        self._update_assist()


def launch() -> int:
    """Launch the RA Terminal GUI (used by main.py)."""
    app = RATerminal()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(launch())
