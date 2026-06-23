"""Render analysis results as Markdown, JSON, or terminal text."""

from __future__ import annotations

import json

from .config import Config
from .gate import Finding
from .metrics import FileMetric


def _mi_badge(mi: float, cfg: Config) -> str:
    if mi >= cfg.maintainability["green"]:
        return "🟢"
    if mi >= cfg.maintainability["yellow"]:
        return "🟡"
    return "🔴"


def _cc_badge(cc: int, cfg: Config) -> str:
    if cc <= cfg.cyclomatic["green"]:
        return "🟢"
    if cc <= cfg.cyclomatic["yellow"]:
        return "🟡"
    if cc <= cfg.cyclomatic["refactor"]:
        return "🟠"
    return "🔴"


def build_json(files: list[FileMetric], tdr: dict, findings: list[Finding],
               extras: dict) -> str:
    payload = {
        "summary": _summary(files, tdr),
        "technical_debt": tdr,
        "files": [
            {
                "path": fm.path,
                "language": fm.language,
                "loc": fm.loc,
                "sloc": fm.sloc,
                "comment_ratio": round(fm.comment_ratio, 3),
                "maintainability_index": fm.maintainability_index,
                "halstead_volume": fm.halstead_volume,
                "halstead_effort": fm.halstead_effort,
                "total_cyclomatic": fm.total_cyclomatic,
                "max_cyclomatic": fm.max_cyclomatic,
                "max_cognitive": fm.max_cognitive,
                "efferent_coupling": fm.efferent_coupling,
                "afferent_coupling": fm.afferent_coupling,
                "instability": round(fm.instability, 2),
                "error": fm.error,
                "functions": [
                    {
                        "name": fn.name, "line": fn.line,
                        "cyclomatic": fn.cyclomatic,
                        "cognitive": fn.cognitive,
                        "length": fn.length,
                    }
                    for fn in fm.functions
                ],
            }
            for fm in files
        ],
        "findings": [vars(f) for f in findings],
        **extras,
    }
    return json.dumps(payload, indent=2)


def _summary(files: list[FileMetric], tdr: dict) -> dict:
    n = len(files) or 1
    return {
        "files": len(files),
        "total_loc": sum(f.loc for f in files),
        "functions": sum(len(f.functions) for f in files),
        "avg_maintainability": round(sum(f.maintainability_index for f in files) / n, 1),
        "max_cyclomatic": max((f.max_cyclomatic for f in files), default=0),
        "max_cognitive": max((f.max_cognitive for f in files), default=0),
        "tdr_percent": tdr["ratio_percent"],
        "tdr_grade": tdr["grade"],
    }


def build_markdown(files: list[FileMetric], tdr: dict, findings: list[Finding],
                   cfg: Config, extras: dict, title: str = "Code Quality Report") -> str:
    s = _summary(files, tdr)
    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    verdict = "❌ **FAILED**" if errors else ("⚠️ **PASSED with warnings**" if warnings else "✅ **PASSED**")

    out: list[str] = []
    out.append(f"## 📊 {title}")
    out.append("")
    out.append(f"**Gate:** {verdict}  ·  {len(errors)} error(s), {len(warnings)} warning(s)")
    out.append("")
    out.append("| Metric | Value |")
    out.append("|---|---|")
    out.append(f"| Files analysed | {s['files']} |")
    out.append(f"| Lines of code | {s['total_loc']} |")
    out.append(f"| Functions | {s['functions']} |")
    out.append(f"| Avg. Maintainability Index | {s['avg_maintainability']} {_mi_badge(s['avg_maintainability'], cfg)} |")
    out.append(f"| Max Cyclomatic Complexity | {s['max_cyclomatic']} {_cc_badge(s['max_cyclomatic'], cfg)} |")
    out.append(f"| Max Cognitive Complexity | {s['max_cognitive']} |")
    out.append(f"| Technical Debt Ratio (SQALE) | {s['tdr_percent']}% — grade **{s['tdr_grade']}** |")
    out.append("")

    if errors or warnings:
        out.append("### Findings")
        out.append("")
        out.append("| Severity | Metric | Location | Detail |")
        out.append("|---|---|---|---|")
        for f in errors + warnings:
            icon = "🔴" if f.severity == "error" else "🟡"
            out.append(f"| {icon} {f.severity} | {f.metric} | `{f.path}` | {f.detail} |")
        out.append("")

    # Worst files by maintainability.
    ranked = sorted(files, key=lambda f: f.maintainability_index)[:10]
    if ranked:
        out.append("<details><summary>Lowest maintainability files</summary>")
        out.append("")
        out.append("| File | MI | Max CC | Max Cog | Ce | Instability | LOC |")
        out.append("|---|---|---|---|---|---|---|")
        for fm in ranked:
            out.append(
                f"| `{fm.path}` | {fm.maintainability_index} {_mi_badge(fm.maintainability_index, cfg)} "
                f"| {fm.max_cyclomatic} | {fm.max_cognitive} | {fm.efferent_coupling} "
                f"| {round(fm.instability, 2)} | {fm.loc} |"
            )
        out.append("")
        out.append("</details>")
        out.append("")

    hs = extras.get("hotspots")
    if hs:
        out.append("<details><summary>🔥 Hotspots (churn × complexity)</summary>")
        out.append("")
        out.append("| File | Commits | Complexity | Score |")
        out.append("|---|---|---|---|")
        for r in hs:
            out.append(f"| `{r['path']}` | {r['commits']} | {r['complexity']} | {r['score']} |")
        out.append("")
        out.append("</details>")
        out.append("")

    cc = extras.get("change_coupling")
    if cc:
        out.append("<details><summary>🔗 Change coupling (files that change together)</summary>")
        out.append("")
        out.append("| File A | File B | Shared commits | Coupling |")
        out.append("|---|---|---|---|")
        for r in cc:
            out.append(f"| `{r['file_a']}` | `{r['file_b']}` | {r['shared_commits']} | {r['coupling']} |")
        out.append("")
        out.append("</details>")
        out.append("")

    out.append("<sub>Generated by the <code>code-quality</code> Claude plugin. "
               "Thresholds follow SonarQube / Visual Studio / SQALE research defaults — "
               "tune them in <code>code-quality.toml</code>.</sub>")
    return "\n".join(out)


_RESET = "\033[0m"
_COLORS = {"error": "\033[31m", "warning": "\033[33m", "ok": "\033[32m"}


def build_text(files: list[FileMetric], tdr: dict, findings: list[Finding],
               cfg: Config, color: bool = True) -> str:
    def c(text: str, kind: str) -> str:
        if not color:
            return text
        return f"{_COLORS.get(kind, '')}{text}{_RESET}"

    s = _summary(files, tdr)
    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    lines = []
    lines.append("Code Quality Report")
    lines.append("=" * 60)
    lines.append(f"Files: {s['files']}   LOC: {s['total_loc']}   Functions: {s['functions']}")
    lines.append(f"Avg Maintainability Index: {s['avg_maintainability']}")
    lines.append(f"Max Cyclomatic: {s['max_cyclomatic']}   Max Cognitive: {s['max_cognitive']}")
    lines.append(f"Technical Debt Ratio: {s['tdr_percent']}%  (grade {s['tdr_grade']})")
    lines.append("")
    if not findings:
        lines.append(c("✓ No threshold violations.", "ok"))
    for f in errors + warnings:
        lines.append(c(f"[{f.severity.upper():7}] {f.metric:14} {f.path}: {f.detail}", f.severity))
    lines.append("")
    verdict = c("FAILED", "error") if errors else (c("PASSED (warnings)", "warning") if warnings else c("PASSED", "ok"))
    lines.append(f"Gate: {verdict}  ({len(errors)} errors, {len(warnings)} warnings)")
    return "\n".join(lines)
