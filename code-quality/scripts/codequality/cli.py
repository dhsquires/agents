"""Command-line interface for the code-quality metrics engine.

Usage examples
--------------
  # Analyse the whole repo, print a terminal report
  python -m codequality analyze .

  # Analyse only files changed vs origin/main, fail the build on violations
  python -m codequality analyze --changed-only --base origin/main --gate .

  # Pre-commit: analyse staged files only
  python -m codequality analyze --staged --gate .

  # Emit a Markdown report for a PR comment
  python -m codequality analyze --format md --output report.md .

  # Behavioural git-history report
  python -m codequality hotspots .
"""

from __future__ import annotations

import argparse
import os
import sys

from . import __version__, hotspots as hs_mod
from .config import load_config
from .coverage import read_coverage
from .discovery import changed_files, discover, staged_files
from .gate import evaluate, gate_failed
from .maintainability import compute_maintainability, resolve_afferent_coupling, technical_debt
from .metrics import analyze_file
from .report import build_json, build_markdown, build_text


def _read(path: str) -> str | None:
    for enc in ("utf-8", "latin-1"):
        try:
            with open(path, encoding=enc) as fh:
                return fh.read()
        except (OSError, UnicodeDecodeError):
            continue
    return None


def _collect_files(args, cfg) -> list[str]:
    if args.staged:
        return staged_files(cfg)
    if args.changed_only:
        return changed_files(args.base, cfg)
    return discover(args.paths or ["."], cfg)


def _analyze(paths: list[str], language_filter=None):
    from .languages import detect_language

    results = []
    for path in paths:
        lang = detect_language(path)
        if lang is None:
            continue
        source = _read(path)
        if source is None:
            continue
        fm = analyze_file(path, source, lang)
        compute_maintainability(fm)
        results.append(fm)
    return results


def cmd_analyze(args) -> int:
    cfg = load_config(args.config)
    files = _collect_files(args, cfg)
    if not files:
        print("No supported source files found to analyse.", file=sys.stderr)
        # Not an error: nothing changed is a passing state.
        if args.format == "md" and args.output:
            with open(args.output, "w") as fh:
                fh.write("## 📊 Code Quality Report\n\n_No analysable files in scope._\n")
        return 0

    file_metrics = _analyze(files)
    resolve_afferent_coupling(file_metrics)
    tdr = technical_debt(file_metrics, cfg)

    coverage = read_coverage(args.coverage_file) if args.coverage_file else None

    extras: dict = {}
    if args.behavioral:
        complexity_map = {fm.path: fm.total_cyclomatic for fm in file_metrics}
        extras["hotspots"] = hs_mod.hotspots(complexity_map, cfg)
        extras["change_coupling"] = hs_mod.change_coupling(
            cfg.hotspots["since_days"], cfg)

    findings = evaluate(file_metrics, tdr, cfg, coverage)

    title = "Code Quality Report"
    if args.changed_only:
        title = "Code Quality Report — changed files"
    elif args.staged:
        title = "Code Quality Report — staged files"

    if args.format == "json":
        rendered = build_json(file_metrics, tdr, findings, extras)
    elif args.format == "md":
        rendered = build_markdown(file_metrics, tdr, findings, cfg, extras, title)
    else:
        rendered = build_text(file_metrics, tdr, findings, cfg,
                              color=not args.no_color and sys.stdout.isatty())

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as fh:
            fh.write(rendered + "\n")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(rendered)

    if args.gate and gate_failed(findings, cfg):
        n = sum(1 for f in findings if f.severity == "error")
        print(f"\nQuality gate FAILED: {n} error-level violation(s).",
              file=sys.stderr)
        return 1
    return 0


def cmd_hotspots(args) -> int:
    cfg = load_config(args.config)
    files = discover(args.paths or ["."], cfg)
    file_metrics = _analyze(files)
    complexity_map = {fm.path: fm.total_cyclomatic for fm in file_metrics}

    spots = hs_mod.hotspots(complexity_map, cfg)
    coupling = hs_mod.change_coupling(cfg.hotspots["since_days"], cfg)
    knowledge = hs_mod.knowledge_map(cfg.hotspots["since_days"], cfg)

    if args.format == "json":
        import json
        print(json.dumps({
            "hotspots": spots,
            "change_coupling": coupling,
            "knowledge_map": knowledge,
        }, indent=2))
        return 0

    print(f"🔥 Hotspots (churn × complexity, last {cfg.hotspots['since_days']} days)")
    print("-" * 60)
    if not spots:
        print("  (no git history or no qualifying files)")
    for r in spots:
        print(f"  {r['score']:6}  {r['commits']:3} commits  cc={r['complexity']:4}  {r['path']}")

    print("\n🔗 Change coupling (logical dependencies)")
    print("-" * 60)
    for r in coupling[:15]:
        print(f"  {r['coupling']:.0%}  ({r['shared_commits']}x)  {r['file_a']}  <->  {r['file_b']}")

    print("\n🚌 Bus-factor risks (single-author files)")
    print("-" * 60)
    risky = [k for k in knowledge if k["bus_factor_risk"]][:15]
    for r in risky:
        print(f"  {r['main_author']:20}  owns 100%  {r['path']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="codequality",
        description="Code maintainability & complexity metrics.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyze", help="compute static metrics & quality gate")
    a.add_argument("paths", nargs="*", help="files or directories (default: .)")
    a.add_argument("--config", help="path to code-quality.toml")
    a.add_argument("--changed-only", action="store_true",
                   help="only files changed vs --base")
    a.add_argument("--base", default="origin/main",
                   help="base ref for --changed-only (default: origin/main)")
    a.add_argument("--staged", action="store_true",
                   help="only files staged in git index (pre-commit)")
    a.add_argument("--gate", action="store_true",
                   help="exit non-zero when thresholds are violated")
    a.add_argument("--format", choices=["text", "md", "json"], default="text")
    a.add_argument("--output", help="write report to a file instead of stdout")
    a.add_argument("--coverage-file", help="coverage report (xml/json/lcov)")
    a.add_argument("--behavioral", action="store_true",
                   help="include git-history hotspots & change coupling")
    a.add_argument("--no-color", action="store_true")
    a.set_defaults(func=cmd_analyze)

    h = sub.add_parser("hotspots", help="git-history behavioural metrics")
    h.add_argument("paths", nargs="*")
    h.add_argument("--config")
    h.add_argument("--format", choices=["text", "json"], default="text")
    h.set_defaults(func=cmd_hotspots)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
