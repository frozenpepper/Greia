"""Thin Greia composition root for La Casa del Dieci."""

from __future__ import annotations

from pathlib import Path
import random
import time

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .ten_house_app import TenHouseActivity
    from .ten_house_audio import TenHouseAudio
    from .ten_house_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, TenHouseRoundFactory, TenHouseSession
    from .ten_house_services import GreiaTenHouseEvents, GreiaTenHouseProgress
else:
    from ten_house_app import TenHouseActivity
    from ten_house_audio import TenHouseAudio
    from ten_house_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, TenHouseRoundFactory, TenHouseSession
    from ten_house_services import GreiaTenHouseEvents, GreiaTenHouseProgress


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
    progress = GreiaTenHouseProgress()
    saved = progress.load()
    rng = random.Random()
    factory = TenHouseRoundFactory(rng)
    session = TenHouseSession(factory.build_set(saved.level), level=saved.level, history=saved.history)
    app = TenHouseActivity(
        screen=screen,
        canvas=canvas,
        session=session,
        factory=factory,
        typography=typography,
        resources=resources,
        progress=progress,
        events=GreiaTenHouseEvents(),
        audio=TenHouseAudio(
            Path(__file__).resolve().parent,
            locale=resources.context.selected.language,
            resources=resources,
            rng=rng,
        ),
        rng=rng,
        session_id=f"{int(time.time())}-{rng.randrange(1_000_000):06d}",
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
