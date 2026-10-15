"""Thin Greia composition root for Le Faccine di Momo."""

from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.localization import activity_resources

if __package__:
    from .momo_app import MomoActivity
    from .momo_audio import MomoAudio
    from .momo_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, MomoModel
    from .momo_renderer import MomoRenderer
    from .momo_services import GreiaMomoEvents
else:
    from momo_app import MomoActivity
    from momo_audio import MomoAudio
    from momo_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, MomoModel
    from momo_renderer import MomoRenderer
    from momo_services import GreiaMomoEvents


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    package_root = Path(__file__).resolve().parent
    resources = activity_resources(package_root)
    locale = resources.context.selected.language
    pygame.display.set_caption(resources.text("activity.title"))

    model = MomoModel()
    audio = MomoAudio(package_root, locale=locale, resources=resources)
    renderer = MomoRenderer(resources=resources)

    app = MomoActivity(
        screen=screen,
        renderer=renderer,
        audio=audio,
        model=model,
        events=GreiaMomoEvents(),
    )
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
