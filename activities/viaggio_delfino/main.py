"""Composition root for Il Viaggio del Delfino (org.greia.viaggio-delfino)."""

from __future__ import annotations

try:
    from delfino_app import DelfinoJourneyApp
except ImportError:
    from .delfino_app import DelfinoJourneyApp


def main() -> int:
    app = DelfinoJourneyApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
