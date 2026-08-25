"""Thin Greia composition root for Stelle Incantate."""

from __future__ import annotations

from pathlib import Path
import time

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.typography import GreiaTypography

if __package__:
    from .sky_app import SkyActivity
    from .sky_audio import SkyAudio
    from .sky_renderer import REFERENCE_HEIGHT, REFERENCE_WIDTH, SkyRenderer
    from .sky_services import GreiaSkyEvents, GreiaSkyStorage
else:
    from sky_app import SkyActivity
    from sky_audio import SkyAudio
    from sky_renderer import REFERENCE_HEIGHT, REFERENCE_WIDTH, SkyRenderer
    from sky_services import GreiaSkyEvents, GreiaSkyStorage


def _locale_and_resources() -> LocalizedResources:
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
        screen = pygame.display.set_mode(
            (REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE
        )
    pygame.mouse.set_visible(True)

    resources = _locale_and_resources()
    typography = GreiaTypography()
    renderer = SkyRenderer(typography, resources)
    audio = SkyAudio()
    events = GreiaSkyEvents()
    storage = GreiaSkyStorage()

    app = SkyActivity(
        screen,
        renderer,
        audio,
        events,
        storage,
        resources,
        session_id=f"sky-{int(time.time()):06d}",
    )
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
