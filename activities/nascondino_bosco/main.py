"""Entrypoint and compatibility composition root for Nascondino nel Bosco."""

from __future__ import annotations

from pathlib import Path
from typing import Final

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)

try:
    from woodland_app import WoodlandApp
    from woodland_audio import WoodlandAudio
    from woodland_model import (
        ALL_ANIMALS,
        GROUNDED_SPOTS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )
except ImportError:
    from .woodland_app import WoodlandApp
    from .woodland_audio import WoodlandAudio
    from .woodland_model import (
        ALL_ANIMALS,
        GROUNDED_SPOTS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )

# Backward-compatibility exports for test suites and existing consumers
SEASONS: Final[list[str]] = ["spring", "summer", "autumn"]
ANIMALS: Final[list[dict[str, object]]] = [
    {
        "id": a.id,
        "color": a.primary_color,
        "belly": a.secondary_color,
        "cue": a.clue_kind,
    }
    for a in ALL_ANIMALS
]
SPOTS: Final[list[dict[str, object]]] = [
    {
        "id": s.spot_id,
        "x": s.cx,
        "y": s.cy,
        "w": s.width,
        "h": s.height,
        "kind": s.kind,
    }
    for s in GROUNDED_SPOTS
]


def _localized_resources() -> LocalizedResources:
    support = ActivityLocaleSupport.localized(
        ("it", "en"),
        default_ui_locale="it",
    )
    context = resolve_activity_locale(get_profile_locale(), support)
    if context is None:
        context = resolve_activity_locale("it", support)
    assert context is not None
    return LocalizedResources(Path(__file__).resolve().parent, context)


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode(
            (REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE
        )
    pygame.mouse.set_visible(False)

    resources = _localized_resources()
    app = WoodlandApp(screen, resources)
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
