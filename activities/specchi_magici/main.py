"""Thin Greia composition root for Specchi Magici."""

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
    from .mirror_app import MirrorActivity
    from .mirror_art import MirrorArt
    from .mirror_audio import MirrorAudio
    from .mirror_model import MirrorRoundFactory, MirrorSession, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .mirror_renderer import MirrorRenderer
    from .mirror_services import GreiaMirrorEvents, GreiaMirrorProgress
else:
    from mirror_app import MirrorActivity
    from mirror_art import MirrorArt
    from mirror_audio import MirrorAudio
    from mirror_model import MirrorRoundFactory, MirrorSession, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from mirror_renderer import MirrorRenderer
    from mirror_services import GreiaMirrorEvents, GreiaMirrorProgress


def _locale_and_resources() -> tuple[str, LocalizedResources]:
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    context = resolve_activity_locale(get_profile_locale(), support)
    if context is None:
        context = resolve_activity_locale("it", support)
    assert context is not None
    locale = context.selected.value.split("-")[0]
    return locale, LocalizedResources(Path(__file__).resolve().parent, context)


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    locale, resources = _locale_and_resources()
    typography = GreiaTypography()
    canvas = PygameReferenceCanvas(screen)
    art = MirrorArt(REFERENCE_WIDTH, REFERENCE_HEIGHT)
    renderer = MirrorRenderer(art, typography, resources)
    progress = GreiaMirrorProgress()
    saved = progress.load()
    rng = random.Random()
    factory = MirrorRoundFactory(rng)
    session = MirrorSession(factory.build_set(saved.level), level=saved.level, history=saved.history)
    session_id = f"{int(time.time())}-{rng.randrange(1_000_000):06d}"
    audio = MirrorAudio(Path(__file__).resolve().parent, locale=locale, resources=resources)

    app = MirrorActivity(
        screen=screen,
        canvas=canvas,
        session=session,
        factory=factory,
        renderer=renderer,
        typography=typography,
        resources=resources,
        progress=progress,
        events=GreiaMirrorEvents(),
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
