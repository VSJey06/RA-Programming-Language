import os

from lib.ai.converter import convert
from lib.ai.language_detector import detect_language


def run_cov(language: str, source_path: str) -> str:
    source_path = os.path.normpath(source_path)
    detected = detect_language(source_path, language)
    ra_code = convert(source_path, language)
    dir_name = os.path.dirname(source_path) or "."
    base = os.path.splitext(os.path.basename(source_path))[0]
    out_path = _unique_path(dir_name, base, ".ra")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(ra_code)
    return out_path


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
