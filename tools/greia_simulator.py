#!/usr/bin/env python3
"""Repository entry point for the Greia Activity Simulator.

The executable shim intentionally shares the basename ``greia_simulator`` with
the real package under ``src/greia_simulator``. Normal execution removes the
tools directory from ``sys.path`` before importing the package. Test harnesses
and developer tooling can still temporarily place ``tools/`` first, however,
which makes Python import this file as the top-level ``greia_simulator`` module.
In that case expose the real package directory as this module's package search
path so submodule imports remain correct instead of failing with
"'greia_simulator' is not a package".
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
PACKAGE_ROOT = SOURCE / "greia_simulator"
TOOLS = str(Path(__file__).resolve().parent)

while TOOLS in sys.path:
    sys.path.remove(TOOLS)
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

if __name__ == "greia_simulator":
    # Defensive compatibility for import-path shadowing. This keeps the CLI
    # shim thin while allowing Python to resolve greia_simulator.<submodule>
    # from the actual package if tools/ happened to win the initial lookup.
    __path__ = [str(PACKAGE_ROOT)]  # type: ignore[name-defined]
    __package__ = "greia_simulator"

from greia_simulator.app import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
