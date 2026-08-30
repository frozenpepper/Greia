"""Foresta Parole — thin composition root.

The historical ``main.py`` was a 663-line monolith that mixed constants,
domain progression, rendering and the event loop. Real work now lives in
:mod:`foresta_content`, :mod:`foresta_model`, :mod:`foresta_renderer`
and :mod:`foresta_app`. This module only re-exports the historical API
surface and composes the lifecycle owned by :class:`ForestaApp`.

The Activity remains R7.3-migrated: it does not own the trusted Greia
Home/Back chrome and respects the protected viewport through the shared
``PygameReferenceCanvas``/``activity_viewport_for_surface`` seam.
"""

from __future__ import annotations

import pygame

if __package__:
    from .foresta_app import ForestaApp, SoundManager
    from .foresta_content import (
        BRANCH_BROWN,
        CANOPY_DARK,
        CANOPY_LIGHT,
        CARD_BG,
        CARD_BORDER,
        DARK_TEXT,
        FOREST_SKY_BOTTOM,
        FOREST_SKY_TOP,
        GOLD,
        LEAF_GREEN,
        LEAF_LIGHT,
        ORB_COLORS,
        PHONICS_DATA,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
        WHITE,
    )
    from .foresta_model import ForestaModel
    from .foresta_renderer import ForestaRenderer, LetterOrb, OwlCompanion, Particle
else:
    from foresta_app import ForestaApp, SoundManager  # type: ignore[no-redef]
    from foresta_content import (  # type: ignore[no-redef]
        BRANCH_BROWN,
        CANOPY_DARK,
        CANOPY_LIGHT,
        CARD_BG,
        CARD_BORDER,
        DARK_TEXT,
        FOREST_SKY_BOTTOM,
        FOREST_SKY_TOP,
        GOLD,
        LEAF_GREEN,
        LEAF_LIGHT,
        ORB_COLORS,
        PHONICS_DATA,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
        WHITE,
    )
    from foresta_model import ForestaModel  # type: ignore[no-redef]
    from foresta_renderer import ForestaRenderer, LetterOrb, OwlCompanion, Particle  # type: ignore[no-redef]

# Backwards-compatible re-exports. Historical contract tests
# (tests/test_activity_foresta_parole.py) import PHONICS_DATA,
# SoundManager, OwlCompanion, LetterOrb and Particle directly from
# this module. Keep those names so the migration does not require
# touching every caller; the new modules own the real work.
__all__ = [
    "BRANCH_BROWN",
    "CANOPY_DARK",
    "CANOPY_LIGHT",
    "CARD_BG",
    "CARD_BORDER",
    "DARK_TEXT",
    "FOREST_SKY_BOTTOM",
    "FOREST_SKY_TOP",
    "ForestaApp",
    "ForestaModel",
    "ForestaRenderer",
    "GOLD",
    "LEAF_GREEN",
    "LEAF_LIGHT",
    "LetterOrb",
    "ORB_COLORS",
    "OwlCompanion",
    "PHONICS_DATA",
    "Particle",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "STORAGE_KEY",
    "SoundManager",
    "WHITE",
    "main",
]


def main() -> int:
    """Compose the Activity and enter its lifecycle."""

    # Keep a tiny reference to the historical constants so this bootstrap
    # remains the documented export surface for tests/tools.
    _ = (
        BRANCH_BROWN,
        CANOPY_DARK,
        CANOPY_LIGHT,
        CARD_BG,
        CARD_BORDER,
        DARK_TEXT,
        FOREST_SKY_BOTTOM,
        FOREST_SKY_TOP,
        GOLD,
        LEAF_GREEN,
        LEAF_LIGHT,
        ORB_COLORS,
        PHONICS_DATA,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
        ForestaModel,
        ForestaRenderer,
        LetterOrb,
        OwlCompanion,
        Particle,
        SoundManager,
    )
    app = ForestaApp()
    try:
        return app.run()
    finally:
        try:
            pygame.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
