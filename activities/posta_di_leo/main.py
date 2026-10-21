"""Leo's Post — thin Greia composition root.

Build the collaborators (resources, sounds, storage-backed postbox and draft,
Creations client, canvas) and enter the Activity lifecycle. The real work
lives in :mod:`postcard_app` (flow), :mod:`postcard_model` (rules),
:mod:`postcard_renderer` / :mod:`postcard_art` (presentation),
:mod:`postcard_controls` (shared control kit), :mod:`postcard_layout`,
:mod:`postcard_audio`, :mod:`postcard_services` and :mod:`postcard_content`.
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
    from .postcard_app import PostcardActivity
    from .postcard_audio import PostcardAudio
    from .postcard_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .postcard_services import GreiaPostcardEvents, GreiaPostcardStorage
else:
    from postcard_app import PostcardActivity
    from postcard_audio import PostcardAudio
    from postcard_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from postcard_services import GreiaPostcardEvents, GreiaPostcardStorage

__all__ = ["PostcardActivity", "build_app", "main"]


def _resources(locale: str | None = None) -> LocalizedResources | None:
    try:
        return activity_resources(Path(__file__).resolve().parent, requested_locale=locale or get_profile_locale())
    except Exception:
        return None


def build_app(screen: pygame.Surface, *, locale: str | None = None, rng: random.Random | None = None) -> PostcardActivity:
    resources = _resources(locale)
    language = resources.context.selected.language if resources is not None else "en"
    if resources is not None:
        pygame.display.set_caption(resources.text("activity.title"))
    storage = GreiaPostcardStorage()
    try:
        creations = get_creations()
    except RuntimeError:
        # Standalone authoring has no trusted session broker: no sharing.
        creations = None
    restored = storage.load_draft()
    draft, picture = restored if restored is not None else (None, None)
    return PostcardActivity(
        screen=screen,
        canvas=PygameReferenceCanvas(screen, hires=True),
        typography=GreiaTypography(),
        resources=resources,
        storage=storage,
        events=GreiaPostcardEvents(),
        audio=PostcardAudio(locale=language),
        rng=rng if rng is not None else random.Random(),
        creations=creations,
        draft=draft,
        draft_picture=picture,
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
