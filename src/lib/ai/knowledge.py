import json
from pathlib import Path

class KnowledgeBase:
    _syntax = None
    _libraries = None
    _errors = None

    @classmethod
    def reload(cls):
        base = Path(__file__).parent
        with open(base / 'syntax.json', 'r') as f:
            cls._syntax = json.load(f)
        with open(base / 'libraries.json', 'r') as f:
            cls._libraries = json.load(f)
        with open(base / 'errors.json', 'r') as f:
            cls._errors = json.load(f)

    @classmethod
    def get_syntax(cls):
        if cls._syntax is None:
            cls.reload()
        return cls._syntax

    @classmethod
    def get_libraries(cls):
        if cls._libraries is None:
            cls.reload()
        return cls._libraries

    @classmethod
    def get_errors(cls):
        if cls._errors is None:
            cls.reload()
        return cls._errors