"""Greia composition root for My Time (source-only pre-audio candidate)."""
from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale

if __package__:
    from .time_app import TimeActivity
    from .time_renderer import WORD_KEYS
else:
    from time_app import TimeActivity
    from time_renderer import WORD_KEYS


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((1024, 600), pygame.RESIZABLE)
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    context = resolve_activity_locale(get_profile_locale(), support)
    if context is None:
        context = resolve_activity_locale("it", support)
    assert context is not None
    locale = context.selected.value.split("-")[0]
    resources = LocalizedResources(Path(__file__).resolve().parent, context)
    words = {key: resources.text(key) for key in WORD_KEYS}
    return TimeActivity(screen, locale, words).run()


if __name__ == "__main__":
    raise SystemExit(main())
