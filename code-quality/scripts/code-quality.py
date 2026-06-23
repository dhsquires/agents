#!/usr/bin/env python3
"""Convenience entry point so the tool can be run as a single file:

    python scripts/code-quality.py analyze --gate .

It simply ensures the package directory is importable, then delegates to the
``codequality`` package CLI. Requires only the Python 3.9+ standard library.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from codequality.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
