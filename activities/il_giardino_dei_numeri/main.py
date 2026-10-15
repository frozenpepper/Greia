"""Thin Greia composition root for Il Giardino dei Numeri."""

from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .giardino_app import GiardinoApp
    from .giardino_audio import GiardinoAudio
    from .giardino_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, GardenModel
    from .giardino_renderer import GiardinoRenderer
    from .giardino_services import GiardinoServices
else:
    from giardino_app import GiardinoApp
    from giardino_audio import GiardinoAudio
    from giardino_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, GardenModel
    from giardino_renderer import GiardinoRenderer
    from giardino_services import GiardinoServices


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

    canvas = PygameReferenceCanvas(screen)
    typography = GreiaTypography()
    locale, resources = _locale_and_resources()
    audio = GiardinoAudio(locale=locale, resources=resources)
    services = GiardinoServices()
    renderer = GiardinoRenderer(canvas, typography, resources)
    model = GardenModel()

    app = GiardinoApp(
        screen=screen,
        canvas=canvas,
        renderer=renderer,
        audio=audio,
        services=services,
        resources=resources,
        typography=typography,
        model=model,
    )
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
