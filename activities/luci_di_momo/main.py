"""Thin Greia composition root for Luci di Momo."""

from __future__ import annotations

from pathlib import Path
import random
import time

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .firefly_app import FireflyActivity
    from .firefly_art import FireflyArt
    from .firefly_audio import FireflyAudio
    from .firefly_model import FireflyRoundFactory, FireflySession, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .firefly_renderer import FireflyRenderer
    from .firefly_services import GreiaFireflyEvents, GreiaFireflyProgress
else:
    from firefly_app import FireflyActivity
    from firefly_art import FireflyArt
    from firefly_audio import FireflyAudio
    from firefly_model import FireflyRoundFactory, FireflySession, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from firefly_renderer import FireflyRenderer
    from firefly_services import GreiaFireflyEvents, GreiaFireflyProgress


def _resources() -> LocalizedResources:
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    context = resolve_activity_locale(get_profile_locale(), support)
    if context is None:
        context = resolve_activity_locale("it", support)
    assert context is not None
    return LocalizedResources(Path(__file__).resolve().parent, context)


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(False)

    resources = _resources()
    typography = GreiaTypography()
    canvas = PygameReferenceCanvas(screen)
    art = FireflyArt(REFERENCE_WIDTH, REFERENCE_HEIGHT)
    renderer = FireflyRenderer(art, typography, resources)
    progress = GreiaFireflyProgress()
    saved = progress.load()
    rng = random.Random()
    factory = FireflyRoundFactory(rng)
    session = FireflySession(factory.build_set(saved.level), level=saved.level, history=saved.history)
    session_id = f"{int(time.time())}-{rng.randrange(1_000_000):06d}"

    app = FireflyActivity(
        screen=screen,
        canvas=canvas,
        session=session,
        factory=factory,
        renderer=renderer,
        typography=typography,
        resources=resources,
        progress=progress,
        events=GreiaFireflyEvents(),
        audio=FireflyAudio(),
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
