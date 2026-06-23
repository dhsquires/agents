"""Read total line coverage from common report formats (best-effort)."""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET


def read_coverage(path: str) -> float | None:
    """Return overall line coverage as a percentage, or None if unreadable."""
    if not path or not os.path.isfile(path):
        return None
    try:
        if path.endswith(".xml"):
            return _read_cobertura(path)
        if path.endswith(".json"):
            return _read_json(path)
        if path.endswith(".info") or "lcov" in os.path.basename(path):
            return _read_lcov(path)
    except (OSError, ValueError, ET.ParseError):
        return None
    return None


def _read_cobertura(path: str) -> float | None:
    root = ET.parse(path).getroot()
    rate = root.get("line-rate")
    if rate is not None:
        return round(float(rate) * 100, 2)
    return None


def _read_json(path: str) -> float | None:
    import json
    with open(path) as fh:
        data = json.load(fh)
    # coverage.py json format
    pct = data.get("totals", {}).get("percent_covered")
    if pct is not None:
        return round(float(pct), 2)
    # istanbul/nyc summary format
    total = data.get("total", {}).get("lines", {}).get("pct")
    if total is not None:
        return round(float(total), 2)
    return None


def _read_lcov(path: str) -> float | None:
    found = hit = 0
    with open(path) as fh:
        for line in fh:
            if line.startswith("LF:"):
                found += int(line[3:])
            elif line.startswith("LH:"):
                hit += int(line[3:])
    if found == 0:
        return None
    return round(hit / found * 100, 2)
