"""Discover source files to analyse."""

from __future__ import annotations

import os
import subprocess

from .config import Config
from .languages import detect_language


def _is_excluded(path: str, cfg: Config) -> bool:
    parts = set(path.replace("\\", "/").split("/"))
    return any(ex in parts for ex in cfg.exclude)


def discover(paths: list[str], cfg: Config) -> list[str]:
    """Return supported source files under the given paths/files."""
    found: list[str] = []
    seen: set[str] = set()

    def add(p: str) -> None:
        norm = os.path.normpath(p)
        if norm in seen:
            return
        if _is_excluded(norm, cfg):
            return
        if detect_language(norm):
            seen.add(norm)
            found.append(norm)

    for path in paths:
        if os.path.isfile(path):
            add(path)
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in cfg.exclude]
                for name in files:
                    add(os.path.join(root, name))
    return sorted(found)


def changed_files(base_ref: str, cfg: Config) -> list[str]:
    """Files changed versus ``base_ref`` (added/copied/modified/renamed)."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{base_ref}...HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        # Fall back to a two-dot diff if the merge base form fails.
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=ACMR", base_ref],
            text=True, stderr=subprocess.DEVNULL,
        )
    files = [line.strip() for line in out.splitlines() if line.strip()]
    result = []
    for f in files:
        if os.path.isfile(f) and detect_language(f) and not _is_excluded(f, cfg):
            result.append(f)
    return sorted(result)


def staged_files(cfg: Config) -> list[str]:
    """Files staged in the git index (for pre-commit use)."""
    out = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        text=True, stderr=subprocess.DEVNULL,
    )
    files = [line.strip() for line in out.splitlines() if line.strip()]
    return sorted(
        f for f in files
        if os.path.isfile(f) and detect_language(f) and not _is_excluded(f, cfg)
    )
