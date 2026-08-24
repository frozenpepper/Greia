"""Thin Greia composition root for Morbidi Mostriciattoli."""

from __future__ import annotations

from pathlib import Path
import random

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
from greia_platform.typography import GreiaTypography

if __package__:
    from .monster_app import MonsterActivity
    from .monster_art import MonsterArt
    from .monster_audio import MonsterAudio
    from .monster_model import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .monster_renderer import MonsterRenderer
    from .monster_services import GreiaMonsterEvents, GreiaMonsterStorage
else:
    from monster_app import MonsterActivity
    from monster_art import MonsterArt
    from monster_audio import MonsterAudio
    from monster_model import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from monster_renderer import MonsterRenderer
    from monster_services import GreiaMonsterEvents, GreiaMonsterStorage


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

    locale, resources = _locale_and_resources()
    typography = GreiaTypography()
    art = MonsterArt(REFERENCE_WIDTH, REFERENCE_HEIGHT, typography)
    renderer = MonsterRenderer(art, typography, resources)
    audio = MonsterAudio()
    events = GreiaMonsterEvents()
    storage = GreiaMonsterStorage()

    app = MonsterActivity(
        screen,
        renderer,
        audio,
        events,
        storage,
        rng=random.Random(),
    )
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
