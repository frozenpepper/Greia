"""La Torre delle Forme (Shape Tower) — thin composition root.

Build the collaborators (resources, audio, storage-backed progress, events,
canvas) and enter the Activity lifecycle. The real work lives in
:mod:`torre_app` (flow and input), :mod:`torre_model` (blocks, fitting,
sessions, ladder adaptation), :mod:`torre_content` (the build catalogue and
rungs), :mod:`torre_layout` (geometry), :mod:`torre_renderer` and
:mod:`torre_art` (presentation), :mod:`torre_controls` (shared control kit),
:mod:`torre_audio` and :mod:`torre_services`.
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
    from .torre_app import TorreActivity
    from .torre_audio import TorreAudio
    from .torre_model import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .torre_services import GreiaTorreEvents, GreiaTorreProgress
else:
    from torre_app import TorreActivity
    from torre_audio import TorreAudio
    from torre_model import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from torre_services import GreiaTorreEvents, GreiaTorreProgress

__all__ = ["TorreActivity", "TorreAudio", "REFERENCE_HEIGHT", "REFERENCE_WIDTH", "main"]


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
    app = TorreActivity(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        typography=GreiaTypography(),
        resources=resources,
        audio=TorreAudio(locale=locale, rng=rng),
        progress=GreiaTorreProgress(),
        events=GreiaTorreEvents(),
        rng=rng,
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
