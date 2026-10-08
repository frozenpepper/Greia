"""Greia composition root for My Time (source-only pre-audio candidate)."""
from __future__ import annotations

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import ActivityLocaleSupport, resolve_activity_locale

if __package__:
    from .time_app import TimeActivity
else:
    from time_app import TimeActivity


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((1024, 600), pygame.RESIZABLE)
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    context = resolve_activity_locale(get_profile_locale(), support)
    locale = context.selected.value.split("-")[0] if context is not None else "it"
    return TimeActivity(screen, locale).run()


if __name__ == "__main__":
    raise SystemExit(main())
