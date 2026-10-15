"""Thin Greia composition root for Nanna delle Nuvolette."""

from __future__ import annotations

from pathlib import Path
import time

import pygame

from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.typography import GreiaTypography

if __package__:
    from .cloud_app import CloudActivity
    from .cloud_art import CloudArt
    from .cloud_audio import CloudAudio
    from .cloud_model import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .cloud_renderer import CloudRenderer
    from .cloud_services import GreiaCloudEvents, GreiaCloudStorage
else:
    from cloud_app import CloudActivity
    from cloud_art import CloudArt
    from cloud_audio import CloudAudio
    from cloud_model import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from cloud_renderer import CloudRenderer
    from cloud_services import GreiaCloudEvents, GreiaCloudStorage


def _locale_and_resources() -> tuple[str, LocalizedResources]:
    """Resolve the profile language from this package's declared locales."""
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
    art = CloudArt(REFERENCE_WIDTH, REFERENCE_HEIGHT)
    renderer = CloudRenderer(art, typography, resources)
    audio = CloudAudio()
    events = GreiaCloudEvents()
    storage = GreiaCloudStorage()

    app = CloudActivity(
        screen,
        renderer,
        audio,
        events,
        storage,
        night_id=f"night-{int(time.time()):06d}",
    )
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
