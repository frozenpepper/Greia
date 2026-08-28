"""Thin composition root for the Greia Encyclopedia Activity."""

from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.activity_api import get_profile_locale, get_theme
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)

if __package__:
    from .enciclopedia_app import EncyclopediaApp
    from .enciclopedia_audio import EncyclopediaAudio
    from .enciclopedia_catalogue import build_page_registry
    from .enciclopedia_services import (
        CachedEncyclopediaTypography,
        EncyclopediaPalette,
        VisualLibrary,
    )
else:
    from enciclopedia_app import EncyclopediaApp
    from enciclopedia_audio import EncyclopediaAudio
    from enciclopedia_catalogue import build_page_registry
    from enciclopedia_services import (
        CachedEncyclopediaTypography,
        EncyclopediaPalette,
        VisualLibrary,
    )

REFERENCE_SIZE = (1024, 600)


def _localized_resources(package_root: Path) -> LocalizedResources:
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    context = resolve_activity_locale(get_profile_locale(), support)
    if context is None:
        context = resolve_activity_locale("it", support)
    assert context is not None
    return LocalizedResources(package_root, context)


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode(REFERENCE_SIZE, pygame.RESIZABLE)
    pygame.mouse.set_visible(False)

    package_root = Path(__file__).resolve().parent
    resources = _localized_resources(package_root)
    typography = CachedEncyclopediaTypography()
    visuals = VisualLibrary(package_root)
    audio = EncyclopediaAudio(resources)
    palette = EncyclopediaPalette.from_theme(get_theme())

    app = EncyclopediaApp(
        screen=screen,
        resources=resources,
        typography=typography,
        visuals=visuals,
        audio=audio,
        palette=palette,
        registry=build_page_registry(),
    )
    try:
        return app.run()
    finally:
        audio.close()
        typography.clear()
        visuals.clear()


if __name__ == "__main__":
    raise SystemExit(main())
