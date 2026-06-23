"""Tests for the code-quality metrics engine.

Run with:  python -m pytest tests/   (or)   python tests/test_metrics.py
No third-party dependencies required; falls back to a tiny runner when pytest
is absent.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from codequality.metrics import analyze_file, count_lines
from codequality.maintainability import maintainability_index, technical_debt, compute_maintainability
from codequality.halstead import compute as halstead_compute
from codequality.config import Config
from codequality.gate import evaluate, gate_failed
from codequality.lexer import strip_comments_and_strings


PY_SAMPLE = '''
"""Module docstring."""
import os
import sys

def simple(x):
    return x + 1

def branchy(items):
    total = 0
    for it in items:            # +1 for
        if it > 0 and it < 10:  # +1 if, +1 and
            total += it
        elif it == 0:           # +1 elif
            total -= 1
        else:
            try:
                total += risky() # in try
            except ValueError:   # +1 except
                total = 0
    return total
'''


def test_cyclomatic_python():
    fm = analyze_file("sample.py", PY_SAMPLE, "python")
    funcs = {f.name: f for f in fm.functions}
    assert funcs["simple"].cyclomatic == 1, funcs["simple"].cyclomatic
    # for(+1) if(+1) and(+1) elif(+1) except(+1) -> base 1 + 5 = 6
    assert funcs["branchy"].cyclomatic == 6, funcs["branchy"].cyclomatic


def test_cognitive_python_nesting():
    fm = analyze_file("sample.py", PY_SAMPLE, "python")
    funcs = {f.name: f for f in fm.functions}
    # branchy is more cognitively complex than simple
    assert funcs["branchy"].cognitive > funcs["simple"].cognitive
    assert funcs["simple"].cognitive == 0


def test_imports_efferent_coupling():
    fm = analyze_file("sample.py", PY_SAMPLE, "python")
    assert set(fm.imports) == {"os", "sys"}
    assert fm.efferent_coupling == 2


def test_line_counts():
    src = "# comment\n\ncode = 1\n'''\nblock\n'''\nmore = 2\n"
    sloc, loc, comments, blank = count_lines(src, "python")
    assert blank == 1
    assert loc == 2          # code = 1 ; more = 2
    assert comments >= 3     # # comment + triple-quote block


def test_maintainability_index_monotonic():
    # Higher volume / complexity / LOC -> lower MI.
    high = maintainability_index(100, 1, 10)
    low = maintainability_index(10000, 40, 500)
    assert high > low
    assert 0 <= low <= 100 and 0 <= high <= 100


def test_halstead_volume_positive():
    h = halstead_compute("a = b + c * d\n", "python")
    assert h.volume > 0
    assert h.vocabulary > 0


def test_strip_comments_removes_noise():
    js = 'const x = "// not a comment"; // real comment\n/* block */ y = 1;'
    clean = strip_comments_and_strings(js, "javascript")
    assert "real comment" not in clean
    assert "not a comment" not in clean
    assert "y = 1" in clean


def test_javascript_generic_complexity():
    js = '''
function f(a, b) {
  if (a && b) { return 1; }
  for (let i = 0; i < a; i++) { while (b) { b--; } }
  return a ? b : 0;
}
'''
    fm = analyze_file("f.js", js, "javascript")
    assert fm.functions, "expected at least one function bucket"
    # if + && + for + while + ternary -> clearly > 1
    assert fm.functions[0].cyclomatic >= 5, fm.functions[0].cyclomatic


def test_gate_flags_complex_function():
    src = "def f(x):\n" + "".join(
        f"    if x == {i}: return {i}\n" for i in range(40)
    )
    fm = analyze_file("big.py", src, "python")
    compute_maintainability(fm)
    cfg = Config()
    tdr = technical_debt([fm], cfg)
    findings = evaluate([fm], tdr, cfg)
    assert any(f.metric == "cyclomatic" and f.severity == "error" for f in findings)
    assert gate_failed(findings, cfg)


def test_technical_debt_grades():
    cfg = Config()
    clean = analyze_file("clean.py", "def f():\n    return 1\n", "python")
    compute_maintainability(clean)
    tdr = technical_debt([clean], cfg)
    assert tdr["grade"] == "A"


def _run():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL  {t.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  ERROR {t.__name__}: {exc!r}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run())
