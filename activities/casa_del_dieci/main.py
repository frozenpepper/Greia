"""Thin Greia composition root for La Casa del Dieci."""

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
    from .ten_house_app import TenHouseActivity
    from .ten_house_art import TenHouseArt
    from .ten_house_audio import TenHouseAudio
    from .ten_house_model import TenHouseRoundFactory, TenHouseSession, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .ten_house_renderer import TenHouseRenderer
    from .ten_house_services import GreiaTenHouseEvents, GreiaTenHouseProgress
else:
    from ten_house_app import TenHouseActivity
    from ten_house_art import TenHouseArt
    from ten_house_audio import TenHouseAudio
    from ten_house_model import TenHouseRoundFactory, TenHouseSession, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from ten_house_renderer import TenHouseRenderer
    from ten_house_services import GreiaTenHouseEvents, GreiaTenHouseProgress


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
    art = TenHouseArt(REFERENCE_WIDTH, REFERENCE_HEIGHT)
    renderer = TenHouseRenderer(art, typography, resources)
    progress = GreiaTenHouseProgress()
    saved = progress.load()
    rng = random.Random()
    factory = TenHouseRoundFactory(rng)
    session = TenHouseSession(factory.build_set(saved.level), level=saved.level, history=saved.history)
    session_id = f"{int(time.time())}-{rng.randrange(1_000_000):06d}"

    package_root = Path(__file__).resolve().parent
    locale_lang = resources.context.selected.language if hasattr(resources.context, "selected") else "it"
    app = TenHouseActivity(
        screen=screen,
        canvas=canvas,
        session=session,
        factory=factory,
        renderer=renderer,
        typography=typography,
        resources=resources,
        progress=progress,
        events=GreiaTenHouseEvents(),
        audio=TenHouseAudio(package_root, locale=locale_lang),
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
