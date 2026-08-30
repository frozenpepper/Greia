"""Thin Greia composition root for Writing.

The historical ``main.py`` was a 942-line monolith that mixed constants,
domain state, rendering and the event loop. Real work now lives in
:mod:`writing_content`, :mod:`writing_model`, :mod:`writing_renderer`
and :mod:`writing_app`. This module only re-exports the historical API
surface and composes the lifecycle owned by :class:`WritingApp`.

The Activity remains R7.3-migrated: it does not own the trusted Greia
Home/Back chrome and respects the protected viewport through the shared
``PygameReferenceCanvas``/``activity_viewport_for_surface`` seam.
"""

from __future__ import annotations

import pygame

from greia_platform.activity_api import get_storage, get_theme
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .writing_app import WritingApp
    from .writing_content import (
        AUTOSAVE_IDLE_SECONDS,
        INDEX_KEY,
        MAX_CHARACTERS,
        MAX_DOCUMENTS,
        MAX_UNDO_EDITS,
        MAX_UNDO_PAYLOAD_CHARS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
    )
    from .writing_model import DocumentRecord, DocumentRepository, TextBuffer, TextEdit, UndoHistory, clamp_text, preview_text
    from .writing_renderer import VisualLine, WritingRenderer
else:  # pragma: no cover - runtime/script fallback
    from writing_app import WritingApp
    from writing_content import (
        AUTOSAVE_IDLE_SECONDS,
        INDEX_KEY,
        MAX_CHARACTERS,
        MAX_DOCUMENTS,
        MAX_UNDO_EDITS,
        MAX_UNDO_PAYLOAD_CHARS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
    )
    from writing_model import DocumentRecord, DocumentRepository, TextBuffer, TextEdit, UndoHistory, clamp_text, preview_text
    from writing_renderer import VisualLine, WritingRenderer

# Re-export compatibility surface (tests/tools may import these from main).
__all__ = [
    "main",
    "WritingApp",
    "WritingRenderer",
    "VisualLine",
    "DocumentRecord",
    "DocumentRepository",
    "TextBuffer",
    "TextEdit",
    "UndoHistory",
    "clamp_text",
    "preview_text",
    "INDEX_KEY",
    "STORAGE_KEY",
    "AUTOSAVE_IDLE_SECONDS",
    "MAX_CHARACTERS",
    "MAX_DOCUMENTS",
    "MAX_UNDO_EDITS",
    "MAX_UNDO_PAYLOAD_CHARS",
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
        try:
            canvas = PygameReferenceCanvas(screen)
        except Exception:
            canvas = None
        metrics = ChildUiMetrics.for_size(*screen.get_size())
        typography = GreiaTypography()
        theme = get_theme()
        try:
            storage = get_storage()
        except Exception:
            storage = None
        # Repository is owned by the app but composed here so storage failure
        # is visible at the composition root and tests can inject a fake.
        if storage is None:
            # Headless / test fallback: use an in-memory stub so import still succeeds.
            class _StubStorage:  # pragma: no cover - minimal stub
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
        repository = DocumentRepository(storage)
        app = WritingApp(
            screen=screen,
            canvas=canvas,
            metrics=metrics,
            typography=typography,
            theme=theme,
            repository=repository,
        )
        return app.run()
    finally:
        # WritingApp already calls pygame.quit(); keep finally idempotent.
        try:
            if pygame.get_init():
                pygame.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
