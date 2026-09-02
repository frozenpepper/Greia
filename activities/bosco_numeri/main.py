"""Il Bosco dei Numeri di Tito — Greia composition root."""

from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.activity_api import get_profile_locale, get_storage
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .bosco_app import BoscoApp
    from .bosco_audio import BoscoAudio
    from .bosco_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
else:
    from bosco_app import BoscoApp
    from bosco_audio import BoscoAudio
    from bosco_content import REFERENCE_HEIGHT, REFERENCE_WIDTH


def _resolve_locale() -> LocalizedResources:
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    try:
        context = resolve_activity_locale(get_profile_locale(), support)
    except Exception:
        context = resolve_activity_locale("it", support)
    if context is None:
        context = resolve_activity_locale("it", support)
        if context is None:
            raise RuntimeError("bosco_numeri: locale support is unavailable")
    return LocalizedResources(Path(__file__).resolve().parent, context)


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode(
            (REFERENCE_WIDTH, REFERENCE_HEIGHT),
            pygame.RESIZABLE,
        )
    pygame.mouse.set_visible(True)

    resources = _resolve_locale()
    try:
        storage = get_storage()
    except Exception:
        storage = None

    audio = BoscoAudio(Path(__file__).resolve().parent, resources)
    canvas = PygameReferenceCanvas(screen)
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    typography = GreiaTypography()

    app = BoscoApp(
        screen=screen,
        canvas=canvas,
        metrics=metrics,
        typography=typography,
        resources=resources,
        audio=audio,
        storage=storage,
    )
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
