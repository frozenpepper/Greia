"""Thin Greia composition root for Mondo Contrari."""

from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)

if __package__:
    from .contrari_app import ContrariActivity
    from .contrari_audio import ContrariAudio
    from .contrari_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ContrariModel,
    )
    from .contrari_renderer import ContrariRenderer
else:
    from contrari_app import ContrariActivity
    from contrari_audio import ContrariAudio
    from contrari_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ContrariModel,
    )
    from contrari_renderer import ContrariRenderer


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    package_root = Path(__file__).resolve().parent
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    context = resolve_activity_locale(get_profile_locale(), support)
    assert context is not None
    resources = LocalizedResources(package_root, context)
    pygame.display.set_caption(resources.text("activity.title"))

    model = ContrariModel()
    audio = ContrariAudio(package_root, locale=context.selected.language)
    renderer = ContrariRenderer(
        locale=context.selected.language,
        resources=resources,
    )

    app = ContrariActivity(
        screen=screen,
        renderer=renderer,
        audio=audio,
        model=model,
    )
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
