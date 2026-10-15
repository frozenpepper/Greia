"""Thin Greia composition root for Il Giardino dei Numeri."""

from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.localization import LocalizedResources, activity_resources
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
    resources = activity_resources(Path(__file__).resolve().parent)
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
