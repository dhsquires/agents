"""Configuration and thresholds for code quality metrics.

Defaults are derived from the empirical research summarised in the project
README (SonarQube/SonarSource, Visual Studio Code Metrics, Robert C. Martin's
package metrics, and the SQALE model). Every value can be overridden via a
``code-quality.toml`` file discovered at the repo root or passed with
``--config``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from typing import Any

try:  # Python 3.11+
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - older interpreters
    tomllib = None  # type: ignore


# --- Threshold defaults -----------------------------------------------------

DEFAULTS: dict[str, Any] = {
    # Cyclomatic complexity (McCabe, 1976) — per function.
    "cyclomatic": {
        "green": 10,        # < 10 is healthy
        "yellow": 15,       # 10-15 review (SonarQube default warning)
        "refactor": 25,     # > 25 high-risk, prioritise
    },
    # Cognitive complexity (SonarSource, 2016) — per function.
    "cognitive": {
        "warn": 15,         # SonarQube default
        "refactor": 25,
    },
    # Maintainability Index (0-100 normalised formula) — per file.
    # NOTE on scale: we use the standard normalised formula
    #   MI = max(0, (171 - 5.2 ln(HV) - 0.23 CC - 16.2 ln(LOC)) * 100/171)
    # which is the one Radon implements. On this scale the established
    # interpretation (Radon) is A: >=20, B: 10-19, C: <10 — NOT the Visual
    # Studio "85/65" figures, which come from VS's per-member rollup of a
    # differently-computed Halstead volume. We therefore calibrate to the
    # formula we actually compute. See README for the full explanation.
    "maintainability": {
        "green": 20,        # >= 20 healthy (Radon grade A)
        "yellow": 10,       # 10-19 moderate (grade B); < 10 is a debt hotspot
    },
    # Coupling — efferent coupling (fan-out) per file/module.
    "coupling": {
        "investigate": 14,  # CBO/Ce > 14 correlates with higher fault risk
    },
    # Test coverage on core logic.
    "coverage": {
        "min": 80.0,
    },
    # Comment / documentation ratio (comment lines / code lines).
    "comments": {
        "min_ratio": 0.05,
    },
    # Hotspot reporting (churn x complexity).
    "hotspots": {
        "top": 20,
        "since_days": 90,
    },
    # Technical Debt Ratio (SQALE) — minutes of remediation per issue type,
    # against an estimated development cost of 30 min / LOC.
    "tdr": {
        "dev_cost_min_per_loc": 30,
        "cost_high_complexity_min": 60,    # per function over refactor threshold
        "cost_med_complexity_min": 20,     # per function over yellow threshold
        "cost_low_maintainability_min": 120,  # per file under yellow MI
        "cost_high_coupling_min": 45,      # per file over coupling threshold
        # SQALE letter grades by ratio %.
        "grade_a": 5,
        "grade_b": 10,
        "grade_c": 20,
        "grade_d": 50,
    },
    # CI/PR gate — build fails when any of these are exceeded.
    # Kept deliberately at "severe" levels so existing code is not punished;
    # tighten per project as quality improves.
    "gate": {
        "max_function_cyclomatic": 25,
        "max_function_cognitive": 30,
        "min_file_maintainability": 10,   # error below grade C
        "max_file_coupling": 30,
        "max_tdr_percent": 20.0,        # fail above SQALE grade C
        "min_coverage": 0.0,            # 0 disables the coverage gate by default
        "fail_on": "error",            # "error" | "warning" | "never"
    },
}


@dataclass
class Config:
    cyclomatic: dict = field(default_factory=lambda: dict(DEFAULTS["cyclomatic"]))
    cognitive: dict = field(default_factory=lambda: dict(DEFAULTS["cognitive"]))
    maintainability: dict = field(default_factory=lambda: dict(DEFAULTS["maintainability"]))
    coupling: dict = field(default_factory=lambda: dict(DEFAULTS["coupling"]))
    coverage: dict = field(default_factory=lambda: dict(DEFAULTS["coverage"]))
    comments: dict = field(default_factory=lambda: dict(DEFAULTS["comments"]))
    hotspots: dict = field(default_factory=lambda: dict(DEFAULTS["hotspots"]))
    tdr: dict = field(default_factory=lambda: dict(DEFAULTS["tdr"]))
    gate: dict = field(default_factory=lambda: dict(DEFAULTS["gate"]))
    exclude: list = field(default_factory=lambda: [
        ".git", "node_modules", "venv", ".venv", "dist", "build",
        "__pycache__", ".mypy_cache", ".pytest_cache", "vendor",
        "site-packages", ".next", "coverage", "target",
    ])

    def to_dict(self) -> dict:
        return asdict(self)


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def find_config_file(start: str = ".") -> str | None:
    """Walk up from ``start`` looking for a code-quality config file."""
    names = ["code-quality.toml", ".code-quality.toml"]
    current = os.path.abspath(start)
    while True:
        for name in names:
            candidate = os.path.join(current, name)
            if os.path.isfile(candidate):
                return candidate
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def load_config(path: str | None = None) -> Config:
    """Load configuration, merging any TOML overrides onto the defaults."""
    cfg = Config()
    if path is None:
        path = find_config_file()
    if not path:
        return cfg
    if tomllib is None:
        return cfg
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, ValueError):
        return cfg
    # Allow an optional [tool.code-quality] table in addition to top level.
    section = data.get("tool", {}).get("code-quality", data)
    merged = _deep_merge(cfg.to_dict(), section)
    return Config(**{k: merged[k] for k in cfg.to_dict().keys() if k in merged})
