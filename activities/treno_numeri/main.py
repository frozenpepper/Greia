"""Treno Numeri — thin composition root.

This module is the Greia entrypoint (``activity.toml`` points here). Real
work lives in cohort modules: content, model, renderer and app. This file
only re-exports historical symbols for back-compat and composes the
TrenoApp lifecycle.
"""

from __future__ import annotations

import pygame

if __package__:
    from .treno_app import TrenoApp
    from .treno_audio import TrainAudio
    from .treno_content import FRUITS, ITEMS, REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY
    from .treno_model import TrainModel
    from .treno_renderer import TrenoRenderer
else:
    from treno_app import TrenoApp
    from treno_audio import TrainAudio
    from treno_content import FRUITS, ITEMS, REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY
    from treno_model import TrainModel
    from treno_renderer import TrenoRenderer

__all__ = [
    "FRUITS",
    "ITEMS",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "STORAGE_KEY",
    "TrainAudio",
    "TrainModel",
    "TrenoApp",
    "TrenoRenderer",
    "main",
]


def main() -> int:
    """Compose the Activity and enter its lifecycle."""

    # Keep a tiny reference to the historical constants so this bootstrap
    # remains the documented export surface for tests/tools.
    _ = (FRUITS, ITEMS, REFERENCE_WIDTH, REFERENCE_HEIGHT, STORAGE_KEY, TrainAudio, TrainModel, TrenoRenderer)
    app = TrenoApp()
    try:
        return app.run()
    finally:
        try:
            pygame.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
