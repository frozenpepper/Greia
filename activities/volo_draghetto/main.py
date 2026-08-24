"""Composition root for Il Volo del Draghetto (org.greia.volo-draghetto)."""

from __future__ import annotations

try:
    from dragon_app import DragonFlightApp
except ImportError:
    from .dragon_app import DragonFlightApp


def main() -> int:
    app = DragonFlightApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
