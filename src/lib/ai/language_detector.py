import os

EXTENSION_MAP = {
    ".py": "Python",
    ".java": "Java",
    ".js": "JavaScript",
    ".cs": "CSharp",
    ".cpp": "CPP",
    ".php": "PHP",
    ".go": "Go",
    ".rs": "Rust",
    ".ra": "RA",
}

def detect_language(path: str, hint: str | None = None) -> str:
    if hint and hint != "Auto":
        return hint
    ext = os.path.splitext(path)[1].lower()
    return EXTENSION_MAP.get(ext, "Unknown")
