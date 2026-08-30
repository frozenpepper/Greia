"""Piccola Serra — thin composition root.

This module is the Greia entrypoint (``activity.toml`` points here). Real
work lives in cohort modules: content, model, renderer and app. This file
only re-exports historical symbols for back-compat and composes the
SerraApp lifecycle.
"""

from __future__ import annotations

import pygame

if __package__:
    from .serra_app import GreenhouseAudio, SerraApp
    from .serra_content import PLANTS, REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY
    from .serra_model import SerraModel
    from .serra_renderer import SerraRenderer
else:
    from serra_app import GreenhouseAudio, SerraApp
    from serra_content import PLANTS, REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY
    from serra_model import SerraModel
    from serra_renderer import SerraRenderer

__all__ = [
    "PLANTS",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "STORAGE_KEY",
    "GreenhouseAudio",
    "SerraModel",
    "SerraRenderer",
    "SerraApp",
    "main",
]


def main() -> int:
    """Compose the Activity and enter its lifecycle."""

    # Keep a tiny reference to the historical constants so this bootstrap
    # remains the documented export surface for tests/tools.
    _ = (PLANTS, REFERENCE_WIDTH, REFERENCE_HEIGHT, STORAGE_KEY, GreenhouseAudio, SerraModel, SerraRenderer)
    app = SerraApp()
    try:
        return app.run()
    finally:
        try:
            pygame.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
