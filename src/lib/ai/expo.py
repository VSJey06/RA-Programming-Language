import os

from lib.ai.exporter import export
from lib.ai.language_detector import EXTENSION_MAP


def run_expo(language: str, source_path: str) -> str:
    source_path = os.path.normpath(source_path)
    ext = _extension_for(language)
    dir_name = os.path.dirname(source_path) or "."
    base = os.path.splitext(os.path.basename(source_path))[0]
    out_path = _unique_path(dir_name, base, ext)
    code = export(source_path, language)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(code)
    return out_path


def _extension_for(language: str) -> str:
    rev = {v: k for k, v in EXTENSION_MAP.items()}
    return rev.get(language, f".{language.lower()}")


def _unique_path(directory: str, base_name: str, extension: str) -> str:
    candidate = os.path.join(directory, base_name + extension)
    if not os.path.exists(candidate):
        return candidate
    i = 1
    while True:
        candidate = os.path.join(directory, f"{base_name}_{i}{extension}")
        if not os.path.exists(candidate):
            return candidate
        i += 1
