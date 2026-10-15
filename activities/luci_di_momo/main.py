"""Thin Greia composition root for Luci di Momo."""

from __future__ import annotations

from pathlib import Path
import random
import time

import pygame

from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .firefly_app import FireflyActivity
    from .firefly_audio import FireflyAudio
    from .firefly_model import FireflyRoundFactory, FireflySession, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .firefly_services import GreiaFireflyEvents, GreiaFireflyProgress
else:
    from firefly_app import FireflyActivity
    from firefly_audio import FireflyAudio
    from firefly_model import FireflyRoundFactory, FireflySession, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from firefly_services import GreiaFireflyEvents, GreiaFireflyProgress


def _locale_and_resources() -> tuple[str, LocalizedResources]:
    resources = activity_resources(Path(__file__).resolve().parent)
    return resources.context.selected.language, resources


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    locale, resources = _locale_and_resources()
    typography = GreiaTypography()
    canvas = PygameReferenceCanvas(screen)
    progress = GreiaFireflyProgress()
    saved = progress.load()
    rng = random.Random()
    factory = FireflyRoundFactory(rng)
    session = FireflySession(factory.build_set(saved.level), level=saved.level, history=saved.history)
    session_id = f"{int(time.time())}-{rng.randrange(1_000_000):06d}"
    audio = FireflyAudio(Path(__file__).resolve().parent, locale=locale, resources=resources, rng=rng)

    app = FireflyActivity(
        screen=screen,
        canvas=canvas,
        session=session,
        factory=factory,
        typography=typography,
        resources=resources,
        progress=progress,
        events=GreiaFireflyEvents(),
        audio=audio,
        rng=rng,
        session_id=session_id,
    )
    try:
        return app.run()
    finally:
        typography.clear()
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
