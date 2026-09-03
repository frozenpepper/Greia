"""Thin Greia composition root for Il Grande Albero delle Stagioni."""

from __future__ import annotations

from pathlib import Path
import sys

import pygame

try:
    from greia_platform.activity_api import get_profile_locale
    from greia_platform.localization import ActivityLocaleSupport, resolve_activity_locale
except ImportError:
    # Standalone dev fallback
    get_profile_locale = lambda: "it"
    ActivityLocaleSupport = None
    resolve_activity_locale = None

if __package__:
    from .tree_app import TreeActivity
    from .tree_audio import TreeAudio
    from .tree_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, TreeModel
    from .tree_renderer import TreeRenderer
else:
    from tree_app import TreeActivity
    from tree_audio import TreeAudio
    from tree_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, TreeModel
    from tree_renderer import TreeRenderer


def _resolve_locale() -> str:
    default_loc = "it"
    if ActivityLocaleSupport is not None and resolve_activity_locale is not None:
        try:
            support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
            context = resolve_activity_locale(get_profile_locale(), support)
            if context is not None:
                return context.selected.value.split("-")[0]
        except Exception:
            pass
    return default_loc


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Il Grande Albero delle Stagioni")
    pygame.mouse.set_visible(True)

    package_root = Path(__file__).resolve().parent
    locale = _resolve_locale()

    model = TreeModel()
    audio = TreeAudio(package_root, locale=locale)
    renderer = TreeRenderer()

    app = TreeActivity(
        screen=screen,
        renderer=renderer,
        audio=audio,
        model=model,
    )
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
