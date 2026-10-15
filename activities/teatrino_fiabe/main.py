"""Thin Greia composition root for Teatrino delle Fiabe (Fairy Tale Puppet Theatre)."""

from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.activity_api import get_creations, get_profile_locale, get_storage
from greia_platform.localization import LocalizationError, activity_resources

if __package__:
    from .teatrino_app import TeatrinoApp
    from .teatrino_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
else:
    from teatrino_app import TeatrinoApp
    from teatrino_content import REFERENCE_HEIGHT, REFERENCE_WIDTH


def main() -> int:
    """Run the puppet theatre through its lifecycle owner."""

    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    # The canvas presents the Greia pointer every frame (no double cursor).
    pygame.mouse.set_visible(False)
    locale = "it"
    try:
        resources = activity_resources(Path(__file__).resolve().parent, requested_locale=get_profile_locale())
        locale = resources.context.selected.language
        pygame.display.set_caption(resources.text("activity.title"))
    except (LocalizationError, OSError, ValueError, RuntimeError):
        pass
    try:
        storage = get_storage()
    except Exception:
        storage = None
    try:
        creations = get_creations()
    except RuntimeError:
        creations = None
    app = TeatrinoApp(screen, storage=storage, creations=creations, locale=locale)
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
