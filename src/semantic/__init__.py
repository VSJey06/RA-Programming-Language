"""Semantic analysis layer for the RA language.

Collects structural information from the AST into a Symbol Table
without modifying any runtime behaviour.
"""

from semantic.symbol import (
    Symbol,
    ClassSymbol,
    MethodSymbol,
    VariableSymbol,
    ObjectSymbol,
    DatabaseSymbol,
)
from semantic.scope import (
    Scope,
    GlobalScope,
    ClassScope,
    MethodScope,
    DatabaseScope,
)
from semantic.symbol_table import SymbolTable
from semantic.symbol_builder import SymbolBuilder

__all__ = [
    "Symbol", "ClassSymbol", "MethodSymbol", "VariableSymbol",
    "ObjectSymbol", "DatabaseSymbol",
    "Scope", "GlobalScope", "ClassScope", "MethodScope", "DatabaseScope",
    "SymbolTable", "SymbolBuilder",
]
