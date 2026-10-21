"""Magic Bakery (Pasticceria Magica) - thin Greia composition root.

Build the collaborators (resources, audio, storage-backed progress, events,
the My Creations picture adapter, canvas) and enter the Activity lifecycle.
The real work lives in :mod:`pasticceria_app` (flow), :mod:`pasticceria_model`
(orders, cakes, rounds, ladder), :mod:`pasticceria_content` (toppings, cast,
ladder data), :mod:`pasticceria_layout` (geometry), :mod:`pasticceria_renderer`
and :mod:`pasticceria_art` (presentation), :mod:`pasticceria_controls`
(shared control kit), :mod:`pasticceria_audio` and :mod:`pasticceria_services`.
"""

from __future__ import annotations

from pathlib import Path
import random

import pygame

from greia_platform.activity_api import get_creations, get_profile_locale, get_storage
from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .pasticceria_app import PasticceriaApp
    from .pasticceria_audio import BakeryAudio
    from .pasticceria_content import LEVELS, REFERENCE_HEIGHT, REFERENCE_WIDTH, TOPPINGS
    from .pasticceria_services import GreiaBakeryEvents, GreiaBakeryPictures, GreiaBakeryProgress
else:
    from pasticceria_app import PasticceriaApp
    from pasticceria_audio import BakeryAudio
    from pasticceria_content import LEVELS, REFERENCE_HEIGHT, REFERENCE_WIDTH, TOPPINGS
    from pasticceria_services import GreiaBakeryEvents, GreiaBakeryPictures, GreiaBakeryProgress

__all__ = [
    "BakeryAudio",
    "LEVELS",
    "PasticceriaApp",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "TOPPINGS",
    "main",
]


def _resources() -> LocalizedResources | None:
    try:
        return activity_resources(Path(__file__).resolve().parent, requested_locale=get_profile_locale())
    except Exception:
        return None


def _storage():
    try:
        return get_storage()
    except Exception:
        return None


def _creations():
    try:
        return get_creations()
    except Exception:
        # Standalone authoring has no trusted session broker, so saving to My
        # Creations is absent instead of falling back to a writable path.
        return None


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    resources = _resources()
    locale = resources.context.selected.language if resources is not None else "en"
    rng = random.Random()
    storage = _storage()
    app = PasticceriaApp(
        screen=screen,
        canvas=PygameReferenceCanvas(screen, hires=True),
        typography=GreiaTypography(),
        resources=resources,
        audio=BakeryAudio(locale=locale, rng=rng),
        progress=GreiaBakeryProgress(storage),
        events=GreiaBakeryEvents(),
        pictures=GreiaBakeryPictures(storage, _creations()),
        rng=rng,
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
