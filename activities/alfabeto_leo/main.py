"""Thin Greia composition root for L'Alfabeto di Leo."""

from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .alfabeto_app import AlfabetoApp
    from .alfabeto_audio import AlfabetoAudio
    from .alfabeto_model import AlfabetoModel, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .alfabeto_renderer import AlfabetoRenderer
    from .alfabeto_services import AlfabetoServices
else:
    from alfabeto_app import AlfabetoApp
    from alfabeto_audio import AlfabetoAudio
    from alfabeto_model import AlfabetoModel, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from alfabeto_renderer import AlfabetoRenderer
    from alfabeto_services import AlfabetoServices


def _locale_and_resources() -> tuple[str, LocalizedResources]:
    resources = activity_resources(
        Path(__file__).resolve().parent, requested_locale=get_profile_locale()
    )
    return resources.context.selected.language, resources


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    canvas = PygameReferenceCanvas(screen)
    typography = GreiaTypography()
    locale, resources = _locale_and_resources()
    audio = AlfabetoAudio(locale=locale, resources=resources)
    services = AlfabetoServices()
    renderer = AlfabetoRenderer(canvas, typography, resources)
    model = AlfabetoModel(locale=locale)

    app = AlfabetoApp(
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
