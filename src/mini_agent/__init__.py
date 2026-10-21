"""Mini-Agent package entry.

The agent implementation lives as flat modules at the repository root
(`main.py`, `agent.py`, …). This package exposes the ``mini-agent``
console script so that ``uv run mini-agent`` matches ``python main.py``.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    """Run the root CLI (same as ``python main.py`` from the repo root)."""
    root = Path(__file__).resolve().parents[2]
    main_py = root / "main.py"
    if not main_py.is_file():
        raise SystemExit(
            "Could not find main.py next to the project root. "
            "Run from a full Mini-Agent checkout, or use: python main.py"
        )
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    runpy.run_path(str(main_py), run_name="__main__")
