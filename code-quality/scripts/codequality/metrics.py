"""Per-function and per-file structural metrics.

Cyclomatic complexity (McCabe) and an approximation of SonarSource's Cognitive
Complexity are computed from a real AST for Python, and from a token/keyword
heuristic for every other supported language.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

from . import halstead
from .languages import DECISION_KEYWORDS, LINE_COMMENT, family


@dataclass
class FunctionMetric:
    name: str
    line: int
    cyclomatic: int = 1
    cognitive: int = 0
    length: int = 0  # source lines


@dataclass
class FileMetric:
    path: str
    language: str
    loc: int = 0            # logical lines of code (non-blank, non-comment)
    sloc: int = 0           # total physical lines
    comment_lines: int = 0
    blank_lines: int = 0
    functions: list[FunctionMetric] = field(default_factory=list)
    halstead_volume: float = 0.0
    halstead_effort: float = 0.0
    maintainability_index: float = 100.0
    efferent_coupling: int = 0
    afferent_coupling: int = 0
    imports: list[str] = field(default_factory=list)
    detected_functions: int = 0
    error: str | None = None

    @property
    def comment_ratio(self) -> float:
        if self.loc == 0:
            return 0.0
        return self.comment_lines / self.loc

    @property
    def total_cyclomatic(self) -> int:
        return sum(f.cyclomatic for f in self.functions) or 1

    @property
    def max_cyclomatic(self) -> int:
        return max((f.cyclomatic for f in self.functions), default=0)

    @property
    def max_cognitive(self) -> int:
        return max((f.cognitive for f in self.functions), default=0)

    @property
    def instability(self) -> float:
        denom = self.efferent_coupling + self.afferent_coupling
        if denom == 0:
            return 0.0
        return self.efferent_coupling / denom


# --------------------------------------------------------------------------- #
# Line counting
# --------------------------------------------------------------------------- #

def count_lines(source: str, language: str) -> tuple[int, int, int, int]:
    """Return (sloc, loc, comment_lines, blank_lines)."""
    fam = family(language)
    line_comment = LINE_COMMENT.get(fam, LINE_COMMENT["default"])
    lines = source.splitlines()
    sloc = len(lines)
    blank = comment = code = 0
    in_block = False
    in_pytriple = False
    triple_q = ""
    for raw in lines:
        line = raw.strip()
        if not line:
            blank += 1
            continue
        if in_pytriple:
            comment += 1
            if triple_q in line:
                in_pytriple = False
            continue
        if in_block:
            comment += 1
            if "*/" in line:
                in_block = False
            continue
        if language == "python" and (line.startswith('"""') or line.startswith("'''")):
            triple_q = line[:3]
            # single-line docstring?
            if not (len(line) > 5 and line.endswith(triple_q)):
                in_pytriple = True
            comment += 1
            continue
        if line.startswith(line_comment):
            comment += 1
            continue
        if language != "python" and line.startswith("/*"):
            comment += 1
            if "*/" not in line:
                in_block = True
            continue
        code += 1
    return sloc, code, comment, blank


# --------------------------------------------------------------------------- #
# Python AST analysis
# --------------------------------------------------------------------------- #

class _PyComplexity(ast.NodeVisitor):
    """Compute cyclomatic and cognitive complexity for a single function body."""

    def __init__(self) -> None:
        self.cyclomatic = 1
        self.cognitive = 0
        self._nesting = 0

    # Cyclomatic: +1 per decision point.
    def _cc(self, n: int = 1) -> None:
        self.cyclomatic += n

    def visit_If(self, node: ast.If) -> None:
        self._cc()
        self.cognitive += 1 + self._nesting
        self.visit(node.test)  # boolean ops / ternaries in the condition count
        self._nested(node.body)
        # elif / else
        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                # elif: counts as a structure but without extra nesting penalty
                self.cognitive += 1
                self.visit(node.orelse[0])
            else:
                self.cognitive += 1
                self._nested(node.orelse)

    def _loop(self, node) -> None:
        self._cc()
        self.cognitive += 1 + self._nesting
        condition = getattr(node, "test", None) or getattr(node, "iter", None)
        if condition is not None:
            self.visit(condition)
        self._nested(node.body)
        if getattr(node, "orelse", None):
            self._nested(node.orelse)

    visit_For = _loop
    visit_AsyncFor = _loop
    visit_While = _loop

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self._cc()
        self.cognitive += 1 + self._nesting
        self._nested(node.body)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # Each binary boolean operator is a decision point.
        self._cc(len(node.values) - 1)
        self.cognitive += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:  # ternary
        self._cc()
        self.cognitive += 1 + self._nesting
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self._cc(len(node.ifs))
        self.cognitive += len(node.ifs)
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        self._cc(len(node.cases))
        self.cognitive += 1 + self._nesting
        self._nested([c for c in node.cases])

    def _nested(self, body) -> None:
        self._nesting += 1
        for child in body:
            self.visit(child)
        self._nesting -= 1


def _analyze_python(source: str, fm: FileMetric) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        fm.error = f"syntax error: {exc.msg} (line {exc.lineno})"
        return

    # Imports (efferent coupling).
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                imports.add(node.module.split(".")[0])
    fm.imports = sorted(imports)
    fm.efferent_coupling = len(imports)

    func_nodes = [
        n for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    for fn in func_nodes:
        visitor = _PyComplexity()
        for stmt in fn.body:
            visitor.visit(stmt)
        end = getattr(fn, "end_lineno", fn.lineno) or fn.lineno
        fm.functions.append(FunctionMetric(
            name=fn.name,
            line=fn.lineno,
            cyclomatic=visitor.cyclomatic,
            cognitive=visitor.cognitive,
            length=end - fn.lineno + 1,
        ))


# --------------------------------------------------------------------------- #
# Generic token/keyword analysis (non-Python)
# --------------------------------------------------------------------------- #

_FUNC_PATTERNS = [
    re.compile(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\("),
    re.compile(r"\b([A-Za-z_$][\w$]*)\s*\([^;{}]*\)\s*\{"),
    re.compile(r"\b([A-Za-z_$][\w$]*)\s*[:=]\s*(?:async\s*)?\([^;{}]*\)\s*=>"),
    re.compile(r"\bfunc\s+([A-Za-z_$][\w$]*)\s*\("),
    re.compile(r"\bdef\s+([A-Za-z_$][\w$]*)"),
]

_NON_FUNCTION_WORDS = {
    "if", "for", "while", "switch", "catch", "return", "with", "do",
    "else", "function", "async", "await", "typeof", "case",
}

_IMPORT_PATTERNS = [
    re.compile(r"""import\s+.*?from\s+['"]([^'"]+)['"]"""),
    re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)"""),
    re.compile(r"""import\s+['"]([^'"]+)['"]"""),
]


def _analyze_generic(source: str, fm: FileMetric) -> None:
    from .lexer import strip_comments_and_strings

    clean = strip_comments_and_strings(source, fm.language)
    keywords = DECISION_KEYWORDS.get(family(fm.language), DECISION_KEYWORDS["c_family"])

    # File-level cyclomatic via keyword + boolean/ternary counting.
    decision_count = 0
    for kw in keywords:
        decision_count += len(re.findall(rf"\b{kw}\b", clean))
    decision_count += len(re.findall(r"&&|\|\||\?\.|\?", clean))

    # Count plausible function definitions for the summary, excluding control
    # keywords that superficially look like calls (if/for/while/switch/catch).
    names: set[tuple[str, int]] = set()
    for pat in _FUNC_PATTERNS:
        for m in pat.finditer(clean):
            name = m.group(1)
            if name in _NON_FUNCTION_WORDS:
                continue
            line = clean.count("\n", 0, m.start()) + 1
            names.add((name, line))
    fm.detected_functions = len(names)

    # Without a real parser we cannot reliably attribute complexity per
    # function for non-Python languages, so we report the file-level aggregate
    # as a single synthetic function. Install `lizard` for per-function JS/TS
    # metrics (see README). The gate still works on this file-level figure.
    fm.functions.append(FunctionMetric(
        name="<file>",
        line=1,
        cyclomatic=1 + decision_count,
        cognitive=decision_count,
        length=fm.sloc,
    ))

    # Imports (efferent coupling).
    imports: set[str] = set()
    for pat in _IMPORT_PATTERNS:
        for m in pat.finditer(clean):
            mod = m.group(1).split("/")[0]
            imports.add(mod)
    fm.imports = sorted(imports)
    fm.efferent_coupling = len(imports)


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #

def analyze_file(path: str, source: str, language: str) -> FileMetric:
    fm = FileMetric(path=path, language=language)
    fm.sloc, fm.loc, fm.comment_lines, fm.blank_lines = count_lines(source, language)

    if language == "python":
        _analyze_python(source, fm)
    else:
        _analyze_generic(source, fm)

    h = halstead.compute(source, language)
    fm.halstead_volume = round(h.volume, 2)
    fm.halstead_effort = round(h.effort, 2)
    return fm
