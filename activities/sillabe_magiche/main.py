from __future__ import annotations

"""Thin composition root for Sillabe Magiche — Greia bootstrap + re-exports."""

from pathlib import Path

import pygame

from greia_platform.activity_api import get_profile_locale, get_storage, get_theme
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .sillabe_app import SillabeApp
    from .sillabe_audio import SoundManager
    from .sillabe_content import (
        CONSONANTS_IT,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
        VOWELS_IT,
        WORDS_DATA_EN,
        WORDS_DATA_IT,
    )
    from .sillabe_renderer import FloatingOrb, LeoCompanion, Particle, SyllableCard, WordTile
else:
    from sillabe_app import SillabeApp
    from sillabe_audio import SoundManager
    from sillabe_content import (
        CONSONANTS_IT,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STORAGE_KEY,
        VOWELS_IT,
        WORDS_DATA_EN,
        WORDS_DATA_IT,
    )
    from sillabe_renderer import FloatingOrb, LeoCompanion, Particle, SyllableCard, WordTile

# Re-export historical symbols for tests / tools importing from main.
__all__ = [
    "main",
    "REFERENCE_WIDTH",
    "REFERENCE_HEIGHT",
    "STORAGE_KEY",
    "CONSONANTS_IT",
    "VOWELS_IT",
    "WORDS_DATA_IT",
    "WORDS_DATA_EN",
    "LeoCompanion",
    "SyllableCard",
    "FloatingOrb",
    "WordTile",
    "Particle",
    "SoundManager",
    "SillabeApp",
]


def main() -> int:
    """Compose Greia context and delegate to the lifecycle owner."""

    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    theme = get_theme()
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    canvas = PygameReferenceCanvas(screen)
    typography = GreiaTypography()

    try:
        storage = get_storage()
    except Exception:
        storage = None

    package_root = Path(__file__).parent
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    profile_lang = get_profile_locale()
    context = resolve_activity_locale(profile_lang, support)
    resources = LocalizedResources(package_root, context) if context else None
    active_locale = context.selected.language if context else "it"

    app = SillabeApp(
        screen=screen,
        canvas=canvas,
        metrics=metrics,
        typography=typography,
        resources=resources,
        active_locale=active_locale,
        theme=theme,
        storage=storage,
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
