"""Colline Allegre (Bumpy Hills) — thin composition root.

Build the collaborators (resources, audio, storage-backed progress, events,
canvas) and enter the Activity lifecycle. The real work lives in
:mod:`colline_app` (flow, timing and input), :mod:`colline_model` (terrain,
fixed-step physics, courses and the ladder), :mod:`colline_content` (the five
courses and constants), :mod:`colline_input` (game-profile pedals),
:mod:`colline_layout` (geometry), :mod:`colline_renderer` and
:mod:`colline_art` (presentation), :mod:`colline_controls` (shared control
kit), :mod:`colline_audio` and :mod:`colline_services`.
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
    from .colline_app import CollineActivity
    from .colline_audio import CollineAudio
    from .colline_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .colline_services import GreiaCollineEvents, GreiaCollineProgress
else:
    from colline_app import CollineActivity
    from colline_audio import CollineAudio
    from colline_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from colline_services import GreiaCollineEvents, GreiaCollineProgress

__all__ = ["CollineActivity", "CollineAudio", "REFERENCE_HEIGHT", "REFERENCE_WIDTH", "main"]


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
    app = CollineActivity(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        typography=GreiaTypography(),
        resources=resources,
        audio=CollineAudio(locale=locale, rng=rng),
        progress=GreiaCollineProgress(),
        events=GreiaCollineEvents(),
        rng=rng,
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
