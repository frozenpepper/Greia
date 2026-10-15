"""Thin Greia composition root for Shape Garden.

Real work lives in :mod:`garden_content` (pure data), :mod:`garden_model`
(the composition editor), :mod:`garden_project_model` /
:mod:`garden_project_repository` (save format, library and v1 migration),
:mod:`garden_art` (shared-library shapes and backdrops),
:mod:`garden_renderer`, :mod:`garden_controls` (shared control kit),
:mod:`garden_input` (controller virtual pointer), :mod:`garden_audio` and
:mod:`garden_app` (lifecycle). This module only builds the Greia services
and runs :class:`GardenApp`.

The Activity does not own the trusted Greia Home/Back chrome and keeps its
controls outside the protected region through the shared
``PygameReferenceCanvas`` / ``ControlLayout`` seam.
"""

from __future__ import annotations

import pygame

from greia_platform.activity_api import get_creations, get_profile_locale, get_storage

if __package__:
    from .garden_app import GardenApp
    from .garden_content import MAX_GARDENS, MAX_SHAPES, REFERENCE_HEIGHT, REFERENCE_WIDTH, SHAPE_KINDS, STORAGE_KEY
    from .garden_model import GardenEditor, GardenState, PlacedShape
    from .garden_project_repository import GardenProjectRepository
else:  # pragma: no cover - runtime/script fallback
    from garden_app import GardenApp
    from garden_content import MAX_GARDENS, MAX_SHAPES, REFERENCE_HEIGHT, REFERENCE_WIDTH, SHAPE_KINDS, STORAGE_KEY
    from garden_model import GardenEditor, GardenState, PlacedShape
    from garden_project_repository import GardenProjectRepository

__all__ = [
    "GardenApp",
    "GardenEditor",
    "GardenState",
    "MAX_GARDENS",
    "MAX_SHAPES",
    "PlacedShape",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SHAPE_KINDS",
    "STORAGE_KEY",
    "main",
]


def main() -> int:
    """Build the Greia context (storage, Creations, locale) and run the app."""
    try:
        repository = GardenProjectRepository(get_storage())
    except RuntimeError:
        repository = None
    try:
        creations = get_creations()
    except RuntimeError:
        # Standalone authoring has no trusted broker: sharing is simply absent.
        creations = None
    try:
        locale = get_profile_locale() or "en"
    except Exception:  # noqa: BLE001 - speech falls back to English
        locale = "en"
    app = GardenApp(repository=repository, creations=creations, locale=str(locale).split("-")[0])
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
