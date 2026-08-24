"""Thin Greia composition root for La Bottega delle Misure."""

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
    from .measure_app import BottegaActivity
    from .measure_art import MeasureArt
    from .measure_audio import MeasureAudio
    from .measure_model import MeasureRoundFactory, MeasureSession, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .measure_renderer import MeasureRenderer
    from .measure_services import GreiaMeasureEvents, GreiaMeasureProgress
else:
    from measure_app import BottegaActivity
    from measure_art import MeasureArt
    from measure_audio import MeasureAudio
    from measure_model import MeasureRoundFactory, MeasureSession, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from measure_renderer import MeasureRenderer
    from measure_services import GreiaMeasureEvents, GreiaMeasureProgress


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
    pygame.mouse.set_visible(True)

    resources = _resources()
    typography = GreiaTypography()
    canvas = PygameReferenceCanvas(screen)
    art = MeasureArt(REFERENCE_WIDTH, REFERENCE_HEIGHT)
    renderer = MeasureRenderer(art, typography, resources)
    progress = GreiaMeasureProgress()
    saved = progress.load()
    rng = random.Random()
    factory = MeasureRoundFactory(rng)
    session = MeasureSession(factory.build_set(saved.level), level=saved.level, history=saved.history)
    session_id = f"{int(time.time())}-{rng.randrange(1_000_000):06d}"

    package_root = Path(__file__).resolve().parent
    locale_lang = resources.context.selected.language if hasattr(resources.context, "selected") else "it"
    app = BottegaActivity(
        screen=screen,
        canvas=canvas,
        session=session,
        factory=factory,
        renderer=renderer,
        typography=typography,
        resources=resources,
        progress=progress,
        events=GreiaMeasureEvents(),
        audio=MeasureAudio(package_root, locale=locale_lang),
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
