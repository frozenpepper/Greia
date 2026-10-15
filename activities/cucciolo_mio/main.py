"""Thin bootstrap for Cucciolo Mio.

Composition root only; domain, rendering and lifecycle live in siblings.
Re-exports historical symbols for compatibility.
"""

from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.activity_api import get_profile_locale, get_storage, get_theme
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .cucciolo_app import CuccioloApp, SoundManager
    from .cucciolo_content import (
        ACCENT_BLUE,
        DARK_TEXT,
        GOLD,
        NIGHT_FLOOR,
        NIGHT_WALL,
        PASTEL_PINK,
        PINK,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ROOM_FLOOR,
        ROOM_WALL,
        STORAGE_KEY,
        WHITE,
    )
    from .cucciolo_model import Particle, PetEntity
    from .cucciolo_renderer import CuccioloRenderer
else:
    from cucciolo_app import CuccioloApp, SoundManager  # type: ignore[import-not-found,no-redef]
    from cucciolo_content import (  # type: ignore[import-not-found,no-redef]
        ACCENT_BLUE,
        DARK_TEXT,
        GOLD,
        NIGHT_FLOOR,
        NIGHT_WALL,
        PASTEL_PINK,
        PINK,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ROOM_FLOOR,
        ROOM_WALL,
        STORAGE_KEY,
        WHITE,
    )
    from cucciolo_model import Particle, PetEntity  # type: ignore[import-not-found,no-redef]
    from cucciolo_renderer import CuccioloRenderer  # type: ignore[import-not-found,no-redef]

__all__ = [
    "REFERENCE_WIDTH",
    "REFERENCE_HEIGHT",
    "STORAGE_KEY",
    "ROOM_WALL",
    "ROOM_FLOOR",
    "NIGHT_WALL",
    "NIGHT_FLOOR",
    "WHITE",
    "DARK_TEXT",
    "GOLD",
    "PINK",
    "PASTEL_PINK",
    "ACCENT_BLUE",
    "SoundManager",
    "Particle",
    "PetEntity",
    "CuccioloRenderer",
    "CuccioloApp",
    "main",
]


def _localized_resources() -> LocalizedResources | None:
    package_root = Path(__file__).parent
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    profile_lang = get_profile_locale()
    context = resolve_activity_locale(profile_lang, support)
    if context is None:
        return None
    return LocalizedResources(package_root, context)


def main() -> int:
    """Compose platform services and enter the Activity lifecycle."""

    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    try:
        theme = get_theme()
        metrics = ChildUiMetrics.for_size(*screen.get_size())
        canvas = PygameReferenceCanvas(screen)
        typography = GreiaTypography()
        try:
            storage = get_storage()
        except Exception:
            storage = None

        resources = _localized_resources()

        app = CuccioloApp(
            screen=screen,
            canvas=canvas,
            metrics=metrics,
            typography=typography,
            theme=theme,
            storage=storage,
            resources=resources,
        )
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
