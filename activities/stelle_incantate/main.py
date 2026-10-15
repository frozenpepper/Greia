"""Thin Greia composition root for Stelle Incantate."""

from __future__ import annotations

from pathlib import Path
import time

import pygame

from greia_platform.localization import LocalizedResources, activity_resources
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
    return activity_resources(Path(__file__).resolve().parent)


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
