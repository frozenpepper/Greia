"""Wonder Match (La Memoria delle Meraviglie) — thin Greia composition root.

Build the collaborators (resources, audio, storage-backed progress, events,
canvas) and enter the Activity lifecycle. The real work lives in
:mod:`memory_app` (flow), :mod:`memory_model` (rules), :mod:`memory_render`
and :mod:`memory_art` (presentation), :mod:`memory_controls` (shared control
kit), :mod:`memory_audio`, :mod:`memory_services` and :mod:`memory_content`.
"""

from __future__ import annotations

from pathlib import Path
import random

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .memory_app import MemoryApp
    from .memory_audio import MemoryAudio
    from .memory_content import ALBUMS, LEVELS, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .memory_services import GreiaMemoryEvents, GreiaMemoryProgress
else:
    from memory_app import MemoryApp
    from memory_audio import MemoryAudio
    from memory_content import ALBUMS, LEVELS, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from memory_services import GreiaMemoryEvents, GreiaMemoryProgress

__all__ = [
    "ALBUMS",
    "LEVELS",
    "MemoryApp",
    "MemoryAudio",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "main",
]


def _resources() -> LocalizedResources | None:
    try:
        return activity_resources(Path(__file__).resolve().parent, requested_locale=get_profile_locale())
    except Exception:
        return None


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    resources = _resources()
    locale = resources.context.selected.language if resources is not None else "en"
    rng = random.Random()
    app = MemoryApp(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        typography=GreiaTypography(),
        resources=resources,
        audio=MemoryAudio(resources, locale=locale, rng=rng),
        progress=GreiaMemoryProgress(),
        events=GreiaMemoryEvents(),
        rng=rng,
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
