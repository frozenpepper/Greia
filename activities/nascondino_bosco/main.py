"""Woodland Hide & Seek (Nascondino nel Bosco) — thin Greia composition root.

Build the collaborators (resources, audio, storage-backed progress, events,
canvas) and enter the Activity lifecycle. The real work lives in
:mod:`woodland_app` (flow), :mod:`woodland_model` (rules),
:mod:`woodland_content` (friends, props, seasons, ladder),
:mod:`woodland_layout` (geometry), :mod:`woodland_renderer` and
:mod:`woodland_art` (presentation), :mod:`woodland_controls` (shared control
kit), :mod:`woodland_audio` and :mod:`woodland_services`.
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
    from .woodland_app import WoodlandApp
    from .woodland_audio import WoodlandAudio
    from .woodland_content import FRIENDS, LEVELS, REFERENCE_HEIGHT, REFERENCE_WIDTH, SEASONS
    from .woodland_services import GreiaWoodlandEvents, GreiaWoodlandProgress
else:
    from woodland_app import WoodlandApp
    from woodland_audio import WoodlandAudio
    from woodland_content import FRIENDS, LEVELS, REFERENCE_HEIGHT, REFERENCE_WIDTH, SEASONS
    from woodland_services import GreiaWoodlandEvents, GreiaWoodlandProgress

__all__ = [
    "FRIENDS",
    "LEVELS",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SEASONS",
    "WoodlandApp",
    "WoodlandAudio",
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
    app = WoodlandApp(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        typography=GreiaTypography(),
        resources=resources,
        audio=WoodlandAudio(locale=locale, rng=rng),
        progress=GreiaWoodlandProgress(),
        events=GreiaWoodlandEvents(),
        rng=rng,
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
