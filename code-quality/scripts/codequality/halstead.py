"""Halstead complexity measures (Halstead, 1977).

Computed from token counts:
    n1 = unique operators        N1 = total operators
    n2 = unique operands         N2 = total operands
    vocabulary  n  = n1 + n2
    length      N  = N1 + N2
    volume      V  = N * log2(n)
    difficulty  D  = (n1 / 2) * (N2 / n2)
    effort      E  = D * V

Volume feeds directly into the Maintainability Index.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .lexer import tokenize


@dataclass
class Halstead:
    n1: int = 0
    n2: int = 0
    N1: int = 0
    N2: int = 0

    @property
    def vocabulary(self) -> int:
        return self.n1 + self.n2

    @property
    def length(self) -> int:
        return self.N1 + self.N2

    @property
    def volume(self) -> float:
        n = self.vocabulary
        if n <= 0:
            return 0.0
        return self.length * math.log2(n)

    @property
    def difficulty(self) -> float:
        if self.n2 == 0:
            return 0.0
        return (self.n1 / 2) * (self.N2 / self.n2)

    @property
    def effort(self) -> float:
        return self.difficulty * self.volume

    def as_dict(self) -> dict:
        return {
            "volume": round(self.volume, 2),
            "difficulty": round(self.difficulty, 2),
            "effort": round(self.effort, 2),
            "vocabulary": self.vocabulary,
            "length": self.length,
        }


# Words that are operators rather than operands (control/keywords).
_KEYWORD_OPERATORS = {
    "if", "else", "elif", "for", "while", "do", "switch", "case", "default",
    "return", "break", "continue", "try", "catch", "except", "finally",
    "throw", "raise", "new", "delete", "in", "is", "and", "or", "not",
    "with", "yield", "await", "async", "def", "class", "function", "import",
    "from", "export", "const", "let", "var", "public", "private", "protected",
    "static", "void", "typeof", "instanceof", "as", "of", "pass", "lambda",
}


def compute(source: str, language: str) -> Halstead:
    words, ops = tokenize(source, language)
    operand_words = [w for w in words if w not in _KEYWORD_OPERATORS]
    operator_words = [w for w in words if w in _KEYWORD_OPERATORS]

    all_operators = ops + operator_words
    h = Halstead()
    h.N1 = len(all_operators)
    h.N2 = len(operand_words)
    h.n1 = len(set(all_operators))
    h.n2 = len(set(operand_words))
    return h
