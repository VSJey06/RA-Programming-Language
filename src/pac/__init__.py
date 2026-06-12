"""PackageRegistry — discovers and loads PAC packages for the RA compiler.

Packages live under ``src/pac/*`` and are scanned at startup.
Each package directory must contain a ``version.json`` manifest.
"""
from __future__ import annotations

import importlib
import os
import json
from typing import Any


_PAC_DIR = os.path.abspath(os.path.dirname(__file__))


class PackageInfo:
    """Metadata for a single discovered package.

    Attributes
    ----------
    name        : str  — display name (e.g. ``"DSA Library for RA"``).
    module_name : str  — Python dotted path (e.g. ``"pac.dsa"``).
    commands    : dict[str, type] — command-name → class mapping.
    symbols     : dict[str, "PackageSymbol"] — resolved symbol name → PackageSymbol.
    """

    __slots__ = ("name", "module_name", "commands", "symbols")

    def __init__(self, name: str, module_name: str) -> None:
        self.name = name
        self.module_name = module_name
        self.commands: dict[str, type] = {}
        self.symbols: dict[str, Any] = {}

    def __repr__(self) -> str:
        return f"PackageInfo({self.name!r}, commands={list(self.commands)})"


class PackageRegistry:
    """Singleton registry that discovers and exposes PAC packages.

    Usage
    -----
        PackageRegistry.discover()           # one-time scan
        info = PackageRegistry.get("Stack")  # → PackageInfo
        sym  = PackageRegistry.symbols()     # → dict[str, PackageSymbol]
    """

    _packages: dict[str, PackageInfo] = {}        # command-name → PackageInfo
    _symbols: dict[str, "PackageSymbol"] = {}     # name → PackageSymbol (for SymbolTable)

    # ── Discovery ─────────────────────────────────────────────────

    @classmethod
    def discover(cls) -> None:
        """Scan ``src/pac/*`` and load every package found."""
        cls._packages = {}
        cls._symbols = {}
        if not os.path.isdir(_PAC_DIR):
            return
        for entry in sorted(os.listdir(_PAC_DIR)):
            pkg_dir = os.path.join(_PAC_DIR, entry)
            if not os.path.isdir(pkg_dir) or entry.startswith("_"):
                continue
            manifest = os.path.join(pkg_dir, "version.json")
            if not os.path.isfile(manifest):
                continue
            try:
                cls._load_package(entry, manifest)
            except Exception as exc:
                import warnings
                warnings.warn(f"Failed to load PAC package '{entry}': {exc}")

    @classmethod
    def _load_package(cls, dir_name: str, manifest_path: str) -> None:
        with open(manifest_path, encoding="utf-8") as f:
            meta = json.load(f)
        display_name = meta.get("name", dir_name)
        module_name = f"pac.{dir_name}"
        try:
            mod = importlib.import_module(module_name)
        except Exception as exc:
            raise ImportError(f"Cannot import {module_name}: {exc}") from exc

        info = PackageInfo(name=display_name, module_name=module_name)

        # Discover command classes
        descriptions = meta.get("descriptions", {})
        for attr_name in dir(mod):
            obj = getattr(mod, attr_name, None)
            if isinstance(obj, type) and hasattr(obj, "call") and callable(obj.call):
                cmd_name = cls._command_name(attr_name, meta)
                info.commands[cmd_name] = obj
                from semantic.symbol import PackageSymbol
                details = descriptions.get(attr_name, "")
                sym = PackageSymbol(
                    name=cmd_name,
                    target_class=obj,
                    description=details,
                )
                # Populate members from the class's call() op names
                sym.members = cls._discover_members(obj)
                info.symbols[cmd_name] = sym
                cls._symbols[cmd_name] = sym

        cls._packages[dir_name] = info

    @staticmethod
    def _discover_members(cls_obj: type) -> dict[str, str]:
        """Extract operation names from a class's ``call()`` method body.

        Falls back to documenting that the class uses dynamic dispatch.
        """
        import inspect
        members: dict[str, str] = {}
        try:
            source = inspect.getsource(cls_obj.call)
            # Match op name strings inside call(), e.g. ``"new"``, ``"push"``
            import re
            for m in re.finditer(r'"(\w+)"', source):
                op = m.group(1)
                if op not in members:
                    members[op] = f"call '{op}' on {cls_obj.__name__}"
        except Exception:
            members["..."] = f"Operations on {cls_obj.__name__}"
        return members

    @staticmethod
    def _command_name(attr_name: str, meta: dict) -> str:
        """Map a Python class name to its RA command name.

        ``StackOps`` → ``"Stack"``, ``SortingAlgos`` → ``"Sort"`` etc.
        Override via ``version.json`` ``"aliases"`` map if present.
        """
        aliases = meta.get("aliases", {})
        if attr_name in aliases:
            return aliases[attr_name]
        # Strip trailing "Ops", "Algos", "Commands" etc.
        for suffix in ("Ops", "Algos", "Commands", "Library"):
            if attr_name.endswith(suffix):
                return attr_name[: -len(suffix)]
        return attr_name

    # ── Query ─────────────────────────────────────────────────────

    @classmethod
    def get(cls, name: str) -> PackageInfo | None:
        """Return ``PackageInfo`` for a command name (e.g. ``"Stack"``)."""
        for info in cls._packages.values():
            if name in info.commands:
                return info
        return None

    @classmethod
    def has(cls, name: str) -> bool:
        """Return ``True`` if *name* is a known package command."""
        return name in cls._symbols

    @classmethod
    def symbols(cls) -> dict[str, "PackageSymbol"]:
        """Return all discovered ``PackageSymbol`` objects (name → symbol)."""
        return dict(cls._symbols)

    @classmethod
    def register_symbols(cls, table: Any) -> None:
        """Inject all package symbols into *table*'s global scope.

        Call this once per ``SymbolTable`` instance after creation.
        """
        for sym in cls._symbols.values():
            table.global_scope.define(sym)

    @classmethod
    def packages(cls) -> dict[str, PackageInfo]:
        return dict(cls._packages)
