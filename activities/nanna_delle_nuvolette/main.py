"""Cloud Bedtime (Nanna delle Nuvolette) — thin composition root.

Build the collaborators (resources, audio, storage-backed progress, events,
canvas) and enter the Activity lifecycle. The real work lives in
:mod:`cloud_app` (flow and input), :mod:`cloud_model` (rules),
:mod:`cloud_content` (colours, quilts, the night ladder), :mod:`cloud_layout`
(geometry), :mod:`cloud_renderer` and :mod:`cloud_art` (presentation),
:mod:`cloud_controls` (shared control kit), :mod:`cloud_audio` and
:mod:`cloud_services`.
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
    from .cloud_app import CloudActivity
    from .cloud_audio import CloudAudio
    from .cloud_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .cloud_services import GreiaBedtimeProgress, GreiaCloudEvents
else:
    from cloud_app import CloudActivity
    from cloud_audio import CloudAudio
    from cloud_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from cloud_services import GreiaBedtimeProgress, GreiaCloudEvents

__all__ = ["CloudActivity", "CloudAudio", "REFERENCE_HEIGHT", "REFERENCE_WIDTH", "main"]


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
    app = CloudActivity(
        screen=screen,
        canvas=PygameReferenceCanvas(screen, hires=True),
        typography=GreiaTypography(),
        resources=resources,
        audio=CloudAudio(locale=locale, rng=rng),
        progress=GreiaBedtimeProgress(),
        events=GreiaCloudEvents(),
        rng=rng,
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
