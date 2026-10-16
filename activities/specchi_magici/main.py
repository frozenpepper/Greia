"""Specchi Magici (Magic Mirrors) — thin composition root.

Build the collaborators (resources, audio, storage-backed progress, events,
canvas) and enter the Activity lifecycle. The real work lives in
:mod:`mirror_app` (flow and input), :mod:`mirror_model` (reflections, mosaics,
ladder), :mod:`mirror_layout` (geometry), :mod:`mirror_renderer` and
:mod:`mirror_art` (presentation), :mod:`mirror_controls` (shared control
kit), :mod:`mirror_audio` and :mod:`mirror_services`.
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
    from .mirror_app import MirrorActivity
    from .mirror_audio import MirrorAudio
    from .mirror_model import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .mirror_services import GreiaMirrorEvents, GreiaMirrorProgress
else:
    from mirror_app import MirrorActivity
    from mirror_audio import MirrorAudio
    from mirror_model import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from mirror_services import GreiaMirrorEvents, GreiaMirrorProgress

__all__ = ["MirrorActivity", "MirrorAudio", "REFERENCE_HEIGHT", "REFERENCE_WIDTH", "main"]


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
    if resources is not None:
        try:
            pygame.display.set_caption(resources.text("activity.title"))
        except Exception:
            pass
    rng = random.Random()
    app = MirrorActivity(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        typography=GreiaTypography(),
        resources=resources,
        audio=MirrorAudio(locale=locale, resources=resources, rng=rng),
        progress=GreiaMirrorProgress(),
        events=GreiaMirrorEvents(),
        rng=rng,
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
