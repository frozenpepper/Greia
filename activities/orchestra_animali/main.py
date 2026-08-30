"""Orchestra Animali — Greia composition root.

Thin bootstrap. Real work lives in :mod:`orchestra_model`,
:mod:`orchestra_content`, :mod:`orchestra_audio`,
:mod:`orchestra_renderer` and :mod:`orchestra_app`.

R7.3-migrated: trusted Home/Back chrome is platform-owned; this
Activity only preserves the renderer-neutral protected/safe viewport
geometry through the shared ``PygameReferenceCanvas`` seam.
"""

from __future__ import annotations

import pygame

if __package__:
    from .orchestra_app import OrchestraApp, build_app
    from .orchestra_audio import SoundManager
    from .orchestra_content import (
        NOTE_NAMES_EN,
        NOTE_NAMES_IT,
        RAINBOW_COLORS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
    )
    from .orchestra_model import InstrumentCard, Particle
    from .orchestra_renderer import OrchestraRenderer
else:  # pragma: no cover - runtime/script fallback
    from orchestra_app import OrchestraApp, build_app
    from orchestra_audio import SoundManager
    from orchestra_content import (
        NOTE_NAMES_EN,
        NOTE_NAMES_IT,
        RAINBOW_COLORS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
    )
    from orchestra_model import InstrumentCard, Particle
    from orchestra_renderer import OrchestraRenderer

__all__ = [
    "InstrumentCard",
    "NOTE_NAMES_EN",
    "NOTE_NAMES_IT",
    "OrchestraApp",
    "OrchestraRenderer",
    "Particle",
    "RAINBOW_COLORS",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "STORAGE_KEY",
    "SoundManager",
    "build_app",
    "main",
]


def main() -> int:
    """Thin bootstrap: build Greia context and enter :class:`OrchestraApp`."""
    _ = (
        InstrumentCard,
        Particle,
        OrchestraRenderer,
        SoundManager,
        NOTE_NAMES_IT,
        NOTE_NAMES_EN,
        RAINBOW_COLORS,
        REFERENCE_WIDTH,
        REFERENCE_HEIGHT,
        STORAGE_KEY,
    )
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(False)
    app = build_app(screen)
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
