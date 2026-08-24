"""Composition root for Il Volo del Draghetto (org.greia.volo-draghetto)."""

from __future__ import annotations

from pathlib import Path
import sys

_ACTIVITY_DIR = Path(__file__).resolve().parent
if str(_ACTIVITY_DIR) not in sys.path:
    sys.path.insert(0, str(_ACTIVITY_DIR))

try:
    from dragon_app import DragonFlightApp
except ImportError:
    from .dragon_app import DragonFlightApp


def main() -> int:
    app = DragonFlightApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
