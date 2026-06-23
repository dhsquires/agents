"""Language detection and per-language token definitions."""

from __future__ import annotations

import os

# Map file extension -> language id.
EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".rs": "rust",
    ".kt": "kotlin",
    ".swift": "swift",
    ".scala": "scala",
}

# Decision keywords that add to cyclomatic complexity, per language family.
# Booleans (&&, ||, and, or) and ternaries are handled separately.
DECISION_KEYWORDS: dict[str, set[str]] = {
    "c_family": {"if", "for", "while", "case", "catch"},
    "python": {"if", "elif", "for", "while", "except", "with", "assert"},
    "ruby": {"if", "elsif", "for", "while", "until", "when", "rescue"},
    "go": {"if", "for", "case", "select"},
}

# Comment syntax per language family.
LINE_COMMENT: dict[str, str] = {
    "python": "#",
    "ruby": "#",
    "default": "//",
}

BLOCK_COMMENT = ("/*", "*/")


def detect_language(path: str) -> str | None:
    _, ext = os.path.splitext(path)
    return EXTENSIONS.get(ext.lower())


def family(language: str) -> str:
    if language in ("python",):
        return "python"
    if language in ("ruby",):
        return "ruby"
    if language in ("go",):
        return "go"
    return "c_family"
