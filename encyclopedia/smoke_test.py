"""Provider-free smoke checks for the encyclopedia foundation.

Run from repository root while E0 is still outside Activity discovery:

    PYTHONPATH=. python3 encyclopedia/smoke_test.py
"""

from __future__ import annotations

from engine.navigation import PageRegistry
from pages.catalogue import validate_catalogue


def main() -> int:
    validate_catalogue()
    registry = PageRegistry()
    if registry.page_ids():
        raise AssertionError("foundation registry should start empty before E1")
    print("Greia Encyclopedia E0 foundation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
