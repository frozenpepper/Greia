"""Thin Greia composition root for Mondo Contrari (Flash's Opposite Game)."""

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
    from .contrari_app import ContrariActivity
    from .contrari_audio import ContrariAudio
    from .contrari_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, ContrariRoundFactory, ContrariSession
    from .contrari_services import GreiaContrariEvents, GreiaContrariProgress
else:
    from contrari_app import ContrariActivity
    from contrari_audio import ContrariAudio
    from contrari_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, ContrariRoundFactory, ContrariSession
    from contrari_services import GreiaContrariEvents, GreiaContrariProgress


def _resources() -> LocalizedResources:
    return activity_resources(Path(__file__).resolve().parent, requested_locale=get_profile_locale())


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    resources = _resources()
    pygame.display.set_caption(resources.text("activity.title"))
    typography = GreiaTypography()
    canvas = PygameReferenceCanvas(screen, hires=True)
    progress = GreiaContrariProgress()
    saved = progress.load()
    rng = random.Random()
    factory = ContrariRoundFactory(rng)
    session = ContrariSession(factory.build_visit(saved.level), level=saved.level, history=saved.history)
    app = ContrariActivity(
        screen=screen,
        canvas=canvas,
        session=session,
        factory=factory,
        typography=typography,
        resources=resources,
        progress=progress,
        events=GreiaContrariEvents(),
        audio=ContrariAudio(
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
