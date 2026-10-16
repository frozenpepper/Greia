"""Fluffy Monsters — thin Greia composition root.

Build the collaborators (resources, sounds, storage-backed gallery and draft,
Creations client, canvas) and enter the Activity lifecycle. The real work lives
in :mod:`monster_app` (flow), :mod:`monster_model` (rules),
:mod:`monster_art` (part compositor), :mod:`monster_renderer` (presentation),
:mod:`monster_controls` (shared control kit), :mod:`monster_layout`,
:mod:`monster_audio`, :mod:`monster_services` and :mod:`monster_content`.
"""

from __future__ import annotations

from pathlib import Path
import random

import pygame

from greia_platform.activity_api import get_creations, get_profile_locale
from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .monster_app import MonsterActivity
    from .monster_audio import MonsterAudio
    from .monster_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .monster_services import GreiaMonsterEvents, GreiaMonsterStorage
else:
    from monster_app import MonsterActivity
    from monster_audio import MonsterAudio
    from monster_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from monster_services import GreiaMonsterEvents, GreiaMonsterStorage

__all__ = ["MonsterActivity", "build_app", "main"]


def _resources(locale: str | None = None) -> LocalizedResources | None:
    try:
        return activity_resources(Path(__file__).resolve().parent, requested_locale=locale or get_profile_locale())
    except Exception:
        return None


def build_app(screen: pygame.Surface, *, locale: str | None = None, rng: random.Random | None = None) -> MonsterActivity:
    resources = _resources(locale)
    language = resources.context.selected.language if resources is not None else "en"
    if resources is not None:
        pygame.display.set_caption(resources.text("activity.title"))
    storage = GreiaMonsterStorage()
    try:
        creations = get_creations()
    except RuntimeError:
        # Standalone authoring has no trusted session broker: no sharing.
        creations = None
    return MonsterActivity(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        typography=GreiaTypography(),
        resources=resources,
        storage=storage,
        events=GreiaMonsterEvents(),
        audio=MonsterAudio(locale=language),
        rng=rng if rng is not None else random.Random(),
        creations=creations,
        draft=storage.load_draft(),
    )


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)
    app = build_app(screen)
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
