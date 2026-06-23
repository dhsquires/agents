"""Behavioural metrics from git history: hotspots, change coupling, knowledge.

A *hotspot* is a file that is both complex and frequently changed — the
intersection where technical debt extracts the highest cost (Tornhill /
CodeScene). We also surface temporal (change) coupling and a simple bus-factor
estimate from commit authorship.
"""

from __future__ import annotations

import subprocess
from collections import Counter, defaultdict
from itertools import combinations

from .config import Config
from .languages import detect_language


def _git(args: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git"] + args, text=True, stderr=subprocess.DEVNULL
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _supported(path: str, cfg: Config) -> bool:
    if detect_language(path) is None:
        return False
    parts = set(path.split("/"))
    return not any(ex in parts for ex in cfg.exclude)


def churn_by_file(since_days: int, cfg: Config) -> dict[str, int]:
    """Number of commits touching each (supported) file in the window."""
    out = _git([
        "log", f"--since={since_days} days ago", "--name-only",
        "--pretty=format:%H",
    ])
    counts: Counter[str] = Counter()
    for line in out.splitlines():
        line = line.strip()
        if not line or len(line) == 40 and all(c in "0123456789abcdef" for c in line):
            continue
        if _supported(line, cfg):
            counts[line] += 1
    return dict(counts)


def hotspots(file_complexity: dict[str, int], cfg: Config) -> list[dict]:
    """Rank files by churn x complexity.

    ``file_complexity`` maps path -> a complexity score (e.g. total cyclomatic).
    """
    churn = churn_by_file(cfg.hotspots["since_days"], cfg)
    rows = []
    for path, commits in churn.items():
        complexity = file_complexity.get(path, 0)
        if complexity == 0:
            continue
        rows.append({
            "path": path,
            "commits": commits,
            "complexity": complexity,
            "score": commits * complexity,
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[: cfg.hotspots["top"]]


def change_coupling(since_days: int, cfg: Config, min_shared: int = 3,
                    threshold: float = 0.3) -> list[dict]:
    """Pairs of files that change together in > ``threshold`` of their commits."""
    out = _git([
        "log", f"--since={since_days} days ago", "--name-only",
        "--pretty=format:%H",
    ])
    commits: list[list[str]] = []
    current: list[str] = []
    for line in out.splitlines():
        line = line.strip()
        is_sha = len(line) == 40 and all(c in "0123456789abcdef" for c in line)
        if is_sha or not line:
            if current:
                commits.append(current)
                current = []
            continue
        if _supported(line, cfg):
            current.append(line)
    if current:
        commits.append(current)

    file_commits: Counter[str] = Counter()
    pair_commits: Counter[tuple[str, str]] = Counter()
    for files in commits:
        uniq = sorted(set(files))
        for f in uniq:
            file_commits[f] += 1
        for a, b in combinations(uniq, 2):
            pair_commits[(a, b)] += 1

    rows = []
    for (a, b), shared in pair_commits.items():
        if shared < min_shared:
            continue
        degree = shared / min(file_commits[a], file_commits[b])
        if degree >= threshold:
            rows.append({
                "file_a": a, "file_b": b,
                "shared_commits": shared,
                "coupling": round(degree, 2),
            })
    rows.sort(key=lambda r: r["coupling"], reverse=True)
    return rows[:50]


def knowledge_map(since_days: int, cfg: Config) -> list[dict]:
    """Per-file authorship; flags bus-factor=1 files (single dominant author)."""
    out = _git([
        "log", f"--since={since_days} days ago", "--name-only",
        "--pretty=format:%H|%an",
    ])
    author = ""
    file_authors: dict[str, Counter[str]] = defaultdict(Counter)
    for line in out.splitlines():
        line = line.rstrip()
        if "|" in line and len(line.split("|", 1)[0]) == 40:
            author = line.split("|", 1)[1]
            continue
        line = line.strip()
        if line and _supported(line, cfg):
            file_authors[line][author] += 1

    rows = []
    for path, authors in file_authors.items():
        total = sum(authors.values())
        top_author, top = authors.most_common(1)[0]
        rows.append({
            "path": path,
            "authors": len(authors),
            "main_author": top_author,
            "ownership": round(top / total, 2) if total else 0.0,
            "bus_factor_risk": len(authors) == 1,
        })
    rows.sort(key=lambda r: (r["bus_factor_risk"], r["ownership"]), reverse=True)
    return rows
