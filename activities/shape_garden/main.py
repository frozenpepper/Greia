"""Thin Greia composition root for Shape Garden.

The historical ``main.py`` was a 432-line monolith that mixed constants,
domain state, rendering and the event loop. Real work now lives in
:mod:`garden_content`, :mod:`garden_model`, :mod:`garden_renderer`
and :mod:`garden_app`. This module only re-exports the historical API
surface and composes the lifecycle owned by :class:`GardenApp`.

The Activity remains R7.3-migrated: it does not own the trusted Greia
Home/Back chrome and respects the protected viewport through the shared
``PygameReferenceCanvas`` / ``activity_viewport_for_surface`` seam.
"""

from __future__ import annotations

import pygame

from greia_platform.activity_api import get_creations, get_storage

if __package__:
    from .garden_app import GardenApp
    from .garden_content import (
        COLORS,
        LEAF_COLOR,
        MAX_PARTICLES,
        MAX_SHAPES,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SOIL_TOP,
        STEM_COLOR,
        STORAGE_KEY,
    )
    from .garden_model import GardenModel, Particle, PlacedShape
    from .garden_project_repository import GardenProjectRepository
    from .garden_renderer import GardenRenderer, draw_shape, draw_soil_bed, draw_sprout_stem
else:  # pragma: no cover - runtime/script fallback
    from garden_app import GardenApp
    from garden_content import (
        COLORS,
        LEAF_COLOR,
        MAX_PARTICLES,
        MAX_SHAPES,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SOIL_TOP,
        STEM_COLOR,
        STORAGE_KEY,
    )
    from garden_model import GardenModel, Particle, PlacedShape
    from garden_project_repository import GardenProjectRepository
    from garden_renderer import GardenRenderer, draw_shape, draw_soil_bed, draw_sprout_stem

# Re-export compatibility surface (tests/tools may import these from main).
__all__ = [
    "COLORS",
    "GardenApp",
    "GardenModel",
    "GardenRenderer",
    "LEAF_COLOR",
    "MAX_PARTICLES",
    "MAX_SHAPES",
    "Particle",
    "PlacedShape",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SOIL_TOP",
    "STEM_COLOR",
    "STORAGE_KEY",
    "draw_shape",
    "draw_soil_bed",
    "draw_sprout_stem",
    "main",
]


def main() -> int:
    """Thin composition root: build Greia context and run the app."""
    # Keep a tiny reference to the historical constants so this bootstrap
    # remains the documented export surface for tests/tools.
    _ = (
        COLORS,
        REFERENCE_WIDTH,
        REFERENCE_HEIGHT,
        SOIL_TOP,
        STEM_COLOR,
        LEAF_COLOR,
        STORAGE_KEY,
        PlacedShape,
        Particle,
        GardenModel,
        GardenRenderer,
    )
    try:
        repository = GardenProjectRepository(get_storage())
    except RuntimeError:
        repository = None
    try:
        creations = get_creations()
    except RuntimeError:
        creations = None
    app = GardenApp(repository=repository, creations=creations)
    try:
        return app.run()
    finally:
        try:
            if pygame.get_init():
                pygame.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
