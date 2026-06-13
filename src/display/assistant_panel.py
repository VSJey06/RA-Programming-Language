"""RA Assistant Panel — read-only suggestion panel widget."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from lib.ai.assist import MentorEngine as Assist


class AssistPanel(ttk.Frame):
    """Read-only panel showing RA assistant suggestions."""

    def __init__(self, parent: tk.Widget, on_insert: Callable[[str], None] | None = None,
                 **kwargs):
        super().__init__(parent, **kwargs)
        self._on_insert = on_insert

        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        self._assist_frame = ttk.Frame(self._notebook)
        self._notebook.add(self._assist_frame, text="Assist")

        self._assist_text = tk.Text(
            self._assist_frame, wrap=tk.WORD,
            bg="#1e1e2e", fg="#cdd6f4",
            insertbackground="#cdd6f4",
            font=("Consolas", 10),
            state=tk.DISABLED,
            relief=tk.SUNKEN, bd=1,
        )
        self._assist_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self._assist_text.tag_config("suggestion", foreground="#89b4fa")
        self._assist_text.tag_config("heading", foreground="#a6e3a1", font=("Consolas", 10, "bold"))
        self._assist_text.tag_config("hint", foreground="#6c7086")

        self._docs_frame = ttk.Frame(self._notebook)
        self._notebook.add(self._docs_frame, text="Docs")

        self._docs_text = tk.Text(
            self._docs_frame, wrap=tk.WORD,
            bg="#1e1e2e", fg="#cdd6f4",
            font=("Consolas", 10),
            state=tk.DISABLED,
            relief=tk.SUNKEN, bd=1,
        )
        self._docs_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self._errors_frame = ttk.Frame(self._notebook)
        self._notebook.add(self._errors_frame, text="Errors")

        self._errors_text = tk.Text(
            self._errors_frame, wrap=tk.WORD,
            bg="#1e1e2e", fg="#cdd6f4",
            font=("Consolas", 10),
            state=tk.DISABLED,
            relief=tk.SUNKEN, bd=1,
        )
        self._errors_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    def _set_text(self, widget: tk.Text, content: str) -> None:
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.config(state=tk.DISABLED)

    def update_suggestions(self, line: str, errors: str = "") -> None:
        widget = self._assist_text
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)

        widget.insert(tk.END, "Suggestions\n", "heading")
        widget.insert(tk.END, "\n")

        stripped = line.strip()
        if stripped:
            assist_msg = Assist.assist_line(stripped)
            if assist_msg:
                lines = assist_msg.split("\n")
                for l in lines:
                    l_stripped = l.strip()
                    if l_stripped:
                        widget.insert(tk.END, f"  {l_stripped}\n", "hint")
                widget.insert(tk.END, "\n")

            next_suggestion = Assist.suggest_next(stripped)
            if next_suggestion:
                widget.insert(tk.END, "Next lines:\n", "heading")
                for sline in next_suggestion.split("\n"):
                    s = sline.strip()
                    if s:
                        widget.insert(tk.END, f"  {s}\n", "suggestion")
        else:
            widget.insert(tk.END, "  Start typing code above\n", "hint")

        widget.config(state=tk.DISABLED)

    def show_errors(self, message: str) -> None:
        self._set_text(self._errors_text, message)
        self._notebook.select(self._errors_frame)

    def show_docs(self, content: str) -> None:
        self._set_text(self._docs_text, content)
