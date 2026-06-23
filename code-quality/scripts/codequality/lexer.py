"""A small, language-agnostic lexer.

This is intentionally approximate: it strips comments and string/char literals,
then yields word tokens (identifiers/keywords/numbers) and operator/punctuation
tokens. It is good enough for token-based cyclomatic complexity and Halstead
metrics on languages we do not parse with a real AST.
"""

from __future__ import annotations

import re
from .languages import LINE_COMMENT, family

_WORD_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*|\d+\.?\d*")
# Multi-character operators first so they are matched greedily.
_OPERATORS = [
    ">>>=", "<<=", ">>=", "===", "!==", "**=", "&&=", "||=", "??=",
    "==", "!=", "<=", ">=", "&&", "||", "??", "?.", "->", "=>", "::",
    "++", "--", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<", ">>",
    "**", "//",
    "+", "-", "*", "/", "%", "=", "<", ">", "!", "&", "|", "^", "~",
    "?", ":", ".", ",", ";", "(", ")", "[", "]", "{", "}", "@",
]
_OPERATORS_SORTED = sorted(_OPERATORS, key=len, reverse=True)


def _skip_to_newline(source: str, i: int, n: int) -> int:
    while i < n and source[i] != "\n":
        i += 1
    return i


def _consume_block_comment(source: str, i: int, n: int, out: list[str]) -> int:
    """Consume a /* ... */ comment, preserving newlines. ``i`` points after /*."""
    while i < n and not source.startswith("*/", i):
        out.append("\n" if source[i] == "\n" else " ")
        i += 1
    return i + 2


def _consume_triple_string(source: str, i: int, n: int, out: list[str]) -> int:
    """Consume a Python triple-quoted string. ``i`` points at the opening quote."""
    quote = source[i:i + 3]
    i += 3
    while i < n and not source.startswith(quote, i):
        out.append("\n" if source[i] == "\n" else " ")
        i += 1
    out.append(" ")
    return i + 3


def _consume_string(source: str, i: int, n: int, out: list[str]) -> int:
    """Consume a regular '...', "...", or `...` literal. ``i`` points at quote."""
    quote = source[i]
    i += 1
    while i < n and source[i] != quote:
        if source[i] == "\\":
            i += 2
            continue
        if source[i] == "\n":
            out.append("\n")
        i += 1
    out.append(' "" ')
    return i + 1


def strip_comments_and_strings(source: str, language: str) -> str:
    """Return source with comments and string/char literals removed."""
    line_comment = LINE_COMMENT.get(family(language), LINE_COMMENT["default"])
    is_python = language == "python"
    out: list[str] = []
    i, n = 0, len(source)
    while i < n:
        if not is_python and source.startswith("/*", i):
            i = _consume_block_comment(source, i + 2, n, out)
        elif source.startswith(line_comment, i):
            i = _skip_to_newline(source, i, n)
        elif is_python and (source.startswith('"""', i) or source.startswith("'''", i)):
            i = _consume_triple_string(source, i, n, out)
        elif source[i] in ("'", '"', "`"):
            i = _consume_string(source, i, n, out)
        else:
            out.append(source[i])
            i += 1
    return "".join(out)


def tokenize(source: str, language: str) -> tuple[list[str], list[str]]:
    """Return ``(words, operators)`` token lists with comments/strings removed."""
    clean = strip_comments_and_strings(source, language)
    words: list[str] = []
    operators: list[str] = []
    i = 0
    n = len(clean)
    while i < n:
        ch = clean[i]
        if ch.isspace():
            i += 1
            continue
        m = _WORD_RE.match(clean, i)
        if m:
            words.append(m.group(0))
            i = m.end()
            continue
        for op in _OPERATORS_SORTED:
            if clean.startswith(op, i):
                operators.append(op)
                i += len(op)
                break
        else:
            i += 1
    return words, operators
