"""Thin Greia composition root for Il Giardino dei Numeri."""

from __future__ import annotations

from pathlib import Path
import random

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .giardino_app import GiardinoApp
    from .giardino_audio import GiardinoAudio
    from .giardino_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, GardenSession, RoundFactory
    from .giardino_services import GreiaGardenEvents, GreiaGardenProgress
else:
    from giardino_app import GiardinoApp
    from giardino_audio import GiardinoAudio
    from giardino_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, GardenSession, RoundFactory
    from giardino_services import GreiaGardenEvents, GreiaGardenProgress


def _resources() -> LocalizedResources:
    return activity_resources(Path(__file__).resolve().parent, requested_locale=get_profile_locale())


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    resources = _resources()
    typography = GreiaTypography()
    canvas = PygameReferenceCanvas(screen, hires=True)
    rng = random.Random()
    progress = GreiaGardenProgress()
    session = GardenSession(RoundFactory(rng), progress.load())
    app = GiardinoApp(
        screen=screen,
        canvas=canvas,
        session=session,
        typography=typography,
        resources=resources,
        audio=GiardinoAudio(locale=resources.context.selected.language, resources=resources),
        progress=progress,
        events=GreiaGardenEvents(),
        rng=rng,
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
