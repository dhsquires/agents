"""Maintainability Index and Technical Debt Ratio (SQALE)."""

from __future__ import annotations

import math

from .config import Config
from .metrics import FileMetric


def maintainability_index(halstead_volume: float, cyclomatic: int, loc: int) -> float:
    """Visual Studio 0-100 normalised Maintainability Index.

    Raw (Oman & Hagemeister):
        MI = 171 - 5.2 ln(HV) - 0.23 CC - 16.2 ln(LOC)
    Normalised to 0-100 as Microsoft Visual Studio does.
    """
    hv = max(halstead_volume, 1.0)
    sloc = max(loc, 1)
    raw = 171 - 5.2 * math.log(hv) - 0.23 * cyclomatic - 16.2 * math.log(sloc)
    normalized = max(0.0, raw * 100.0 / 171.0)
    return round(min(normalized, 100.0), 1)


def compute_maintainability(fm: FileMetric) -> None:
    fm.maintainability_index = maintainability_index(
        fm.halstead_volume, fm.total_cyclomatic, fm.loc
    )


def resolve_afferent_coupling(files: list[FileMetric]) -> None:
    """Approximate afferent coupling (fan-in) at the module level.

    A module is the file's base name without extension; we count how many other
    analysed files import that module name. This is a heuristic but captures the
    Martin Ca/Ce instability signal for intra-repo dependencies.
    """
    import os

    module_of: dict[str, FileMetric] = {}
    for fm in files:
        mod = os.path.splitext(os.path.basename(fm.path))[0]
        module_of.setdefault(mod, fm)

    counts: dict[str, int] = {m: 0 for m in module_of}
    for fm in files:
        for imp in fm.imports:
            base = imp.split("/")[-1]
            if base in counts and module_of[base] is not fm:
                counts[base] += 1

    for mod, fm in module_of.items():
        fm.afferent_coupling = counts.get(mod, 0)


def technical_debt(files: list[FileMetric], cfg: Config) -> dict:
    """SQALE-style Technical Debt Ratio.

    Remediation cost is summed from threshold violations (in minutes) and
    compared against estimated development cost (minutes per LOC).
    """
    t = cfg.tdr
    remediation = 0.0
    total_loc = 0
    for fm in files:
        total_loc += fm.loc
        for fn in fm.functions:
            if fn.cyclomatic > cfg.cyclomatic["refactor"]:
                remediation += t["cost_high_complexity_min"]
            elif fn.cyclomatic > cfg.cyclomatic["yellow"]:
                remediation += t["cost_med_complexity_min"]
        if fm.maintainability_index < cfg.maintainability["yellow"]:
            remediation += t["cost_low_maintainability_min"]
        if fm.efferent_coupling > cfg.coupling["investigate"]:
            remediation += t["cost_high_coupling_min"]

    dev_cost = max(total_loc * t["dev_cost_min_per_loc"], 1)
    ratio = remediation / dev_cost * 100.0

    if ratio <= t["grade_a"]:
        grade = "A"
    elif ratio <= t["grade_b"]:
        grade = "B"
    elif ratio <= t["grade_c"]:
        grade = "C"
    elif ratio <= t["grade_d"]:
        grade = "D"
    else:
        grade = "E"

    return {
        "remediation_minutes": round(remediation, 1),
        "development_minutes": dev_cost,
        "ratio_percent": round(ratio, 2),
        "grade": grade,
    }
