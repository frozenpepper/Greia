#!/usr/bin/env python3
"""Repository entry point for the Greia Activity Simulator."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from greia_simulator.app import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
