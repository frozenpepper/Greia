"""Thin Greia composition root for Stelle Incantate (Enchanted Stars).

``activity.toml`` points here. Real work lives in cohort modules: content
(figure catalogue + geometry), model (pure rules), services (storage/events),
art, renderer, controls, audio and the app lifecycle.
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
    from .sky_app import SkyActivity
    from .sky_audio import SkyAudio
    from .sky_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .sky_model import Night, RoundFactory
    from .sky_services import GreiaSkyEvents, GreiaSkyProgress
else:
    from sky_app import SkyActivity
    from sky_audio import SkyAudio
    from sky_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from sky_model import Night, RoundFactory
    from sky_services import GreiaSkyEvents, GreiaSkyProgress


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
    canvas = PygameReferenceCanvas(screen)
    progress = GreiaSkyProgress()
    night = Night(RoundFactory(random.Random()), progress.load())
    app = SkyActivity(
        screen=screen,
        canvas=canvas,
        night=night,
        typography=typography,
        resources=resources,
        audio=SkyAudio(locale=resources.context.selected.language, resources=resources),
        progress=progress,
        events=GreiaSkyEvents(),
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
