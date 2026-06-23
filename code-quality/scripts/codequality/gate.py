"""Quality gate evaluation — turns metrics into pass/warn/fail decisions."""

from __future__ import annotations

from dataclasses import dataclass

from .config import Config
from .metrics import FileMetric


@dataclass
class Finding:
    severity: str          # "error" | "warning"
    metric: str
    path: str
    detail: str
    value: float
    threshold: float


def _band(value: float, error_at: float, warn_at: float, higher_is_worse: bool,
          metric: str, path: str, detail: str) -> Finding | None:
    """Classify a value into an error/warning Finding, or None if within band."""
    if higher_is_worse:
        if value > error_at:
            return Finding("error", metric, path, detail, value, error_at)
        if value > warn_at:
            return Finding("warning", metric, path, detail, value, warn_at)
    else:
        if value < error_at:
            return Finding("error", metric, path, detail, value, error_at)
        if value < warn_at:
            return Finding("warning", metric, path, detail, value, warn_at)
    return None


def _check_function(fn, fm: FileMetric, cfg: Config) -> list[Finding]:
    g = cfg.gate
    where = f"(line {fn.line})"
    candidates = [
        _band(fn.cyclomatic, g["max_function_cyclomatic"], cfg.cyclomatic["yellow"],
              True, "cyclomatic", fm.path,
              f"{fn.name}() cyclomatic complexity {fn.cyclomatic} {where}"),
        _band(fn.cognitive, g["max_function_cognitive"], cfg.cognitive["warn"],
              True, "cognitive", fm.path,
              f"{fn.name}() cognitive complexity {fn.cognitive} {where}"),
    ]
    return [c for c in candidates if c]


def _check_file(fm: FileMetric, cfg: Config) -> list[Finding]:
    g = cfg.gate
    candidates = [
        _band(fm.maintainability_index, g["min_file_maintainability"],
              cfg.maintainability["green"], False, "maintainability", fm.path,
              f"maintainability index {fm.maintainability_index}"),
        _band(fm.efferent_coupling, g["max_file_coupling"],
              cfg.coupling["investigate"], True, "coupling", fm.path,
              f"efferent coupling {fm.efferent_coupling}"),
    ]
    return [c for c in candidates if c]


def evaluate(files: list[FileMetric], tdr: dict, cfg: Config,
             coverage: float | None = None) -> list[Finding]:
    g = cfg.gate
    findings: list[Finding] = []

    for fm in files:
        if fm.error:
            findings.append(Finding("warning", "parse", fm.path, fm.error, 0, 0))
            continue
        for fn in fm.functions:
            findings.extend(_check_function(fn, fm, cfg))
        findings.extend(_check_file(fm, cfg))

    if tdr["ratio_percent"] > g["max_tdr_percent"]:
        findings.append(Finding(
            "error", "tdr", "<codebase>",
            f"technical debt ratio {tdr['ratio_percent']}% (grade {tdr['grade']})",
            tdr["ratio_percent"], g["max_tdr_percent"]))

    if coverage is not None and g["min_coverage"] > 0 and coverage < g["min_coverage"]:
        findings.append(Finding(
            "error", "coverage", "<codebase>",
            f"test coverage {coverage}%", coverage, g["min_coverage"]))

    return findings


def gate_failed(findings: list[Finding], cfg: Config) -> bool:
    mode = cfg.gate.get("fail_on", "error")
    if mode == "never":
        return False
    if mode == "warning":
        return any(f.severity in ("error", "warning") for f in findings)
    return any(f.severity == "error" for f in findings)
