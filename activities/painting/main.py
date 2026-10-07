"""Thin Greia composition root for Painting.

The historical ``main.py`` was an 845-line monolith that mixed constants,
domain state, rendering and the event loop. Real work now lives in
:mod:`painting_content`, :mod:`painting_model`, :mod:`painting_renderer`
and :mod:`painting_app`. This module only re-exports the historical API
surface and composes the lifecycle owned by :class:`PaintingApp`.

The Activity remains R7.3-migrated: it does not own the trusted Greia
Home/Back chrome and respects the protected viewport through the shared
``ChildUiMetrics`` / ``activity_viewport_for_surface`` seam.
"""

from __future__ import annotations

import pygame

from greia_platform.activity_api import get_creations, get_storage, get_theme
from greia_platform.activity_ui import ChildUiMetrics

if __package__:
    from .painting_app import PaintingApp
    from .painting_content import (
        AUTOSAVE_IDLE_SECONDS,
        BRUSH_SIZES,
        COLORS,
        INDEX_KEY,
        MAX_PAINTINGS,
        MAX_STROKE_POINTS,
        MAX_UNDO_STROKES,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
    )
    from .painting_model import PaintingRecord, PaintingRepository, Stroke, StrokeHistory
    from .painting_renderer import PaintingRenderer, _decode_png, _encode_png
else:  # pragma: no cover - runtime/script fallback
    from painting_app import PaintingApp
    from painting_content import (
        AUTOSAVE_IDLE_SECONDS,
        BRUSH_SIZES,
        COLORS,
        INDEX_KEY,
        MAX_PAINTINGS,
        MAX_STROKE_POINTS,
        MAX_UNDO_STROKES,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
    )
    from painting_model import PaintingRecord, PaintingRepository, Stroke, StrokeHistory
    from painting_renderer import PaintingRenderer, _decode_png, _encode_png

# Re-export compatibility surface (tests/tools may import these from main).
__all__ = [
    "main",
    "PaintingApp",
    "PaintingRenderer",
    "PaintingRecord",
    "PaintingRepository",
    "Stroke",
    "StrokeHistory",
    "_encode_png",
    "_decode_png",
    "INDEX_KEY",
    "STORAGE_KEY",
    "AUTOSAVE_IDLE_SECONDS",
    "MAX_PAINTINGS",
    "MAX_UNDO_STROKES",
    "MAX_STROKE_POINTS",
    "COLORS",
    "BRUSH_SIZES",
    "REFERENCE_WIDTH",
    "REFERENCE_HEIGHT",
]


def main() -> int:
    """Thin composition root: build Greia context and run the app."""
    pygame.init()
    try:
        screen = pygame.display.get_surface()
        if screen is None:
            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        metrics = ChildUiMetrics.for_size(*screen.get_size())
        theme = get_theme()
        try:
            storage = get_storage()
        except Exception:
            storage = None
        if storage is None:
            # Headless / test fallback: minimal stub so import still succeeds
            class _StubStorage:  # pragma: no cover
                def kv_get(self, k, d=None):
                    return d

                def kv_set(self, k, v):
                    pass

                def file_write_atomic(self, n, p):
                    pass

                def file_read(self, n):
                    raise RuntimeError("no storage")

                def file_delete(self, n):
                    return False

            storage = _StubStorage()  # type: ignore[assignment]
        repository = PaintingRepository(storage)
        try:
            creations = get_creations()
        except RuntimeError:
            # Standalone authoring has no trusted session broker, so sharing
            # is absent instead of falling back to a globally writable path.
            creations = None
        app = PaintingApp(
            screen=screen,
            metrics=metrics,
            theme=theme,
            repository=repository,
            creations=creations,
        )
        return app.run()
    finally:
        try:
            if pygame.get_init():
                pygame.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
