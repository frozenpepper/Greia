"""My Cute Pet (Cucciolo Mio) — thin Greia composition root.

Build the collaborators (resources, audio, storage-backed pet profile,
events, canvas) and enter the Activity lifecycle. The real work lives in
:mod:`cucciolo_app` (flow), :mod:`cucciolo_model` (care-day rules),
:mod:`cucciolo_content` (pets, names, needs, cares, rooms, ladder),
:mod:`cucciolo_layout` (geometry), :mod:`cucciolo_renderer` and
:mod:`cucciolo_art` (presentation), :mod:`cucciolo_controls` (shared control
kit), :mod:`cucciolo_audio` and :mod:`cucciolo_services`.
"""

from __future__ import annotations

from pathlib import Path
import random

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .cucciolo_app import CuccioloApp
    from .cucciolo_audio import CuccioloAudio
    from .cucciolo_content import LEVELS, NAMES, REFERENCE_HEIGHT, REFERENCE_WIDTH, SPECIES
    from .cucciolo_services import GreiaPetEvents, GreiaPetProgress
else:
    from cucciolo_app import CuccioloApp
    from cucciolo_audio import CuccioloAudio
    from cucciolo_content import LEVELS, NAMES, REFERENCE_HEIGHT, REFERENCE_WIDTH, SPECIES
    from cucciolo_services import GreiaPetEvents, GreiaPetProgress

__all__ = [
    "CuccioloApp",
    "CuccioloAudio",
    "LEVELS",
    "NAMES",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SPECIES",
    "main",
]


def _resources() -> LocalizedResources | None:
    try:
        return activity_resources(Path(__file__).resolve().parent, requested_locale=get_profile_locale())
    except Exception:
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
    app = CuccioloApp(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        typography=GreiaTypography(),
        resources=resources,
        audio=CuccioloAudio(locale=locale, rng=rng),
        progress=GreiaPetProgress(),
        events=GreiaPetEvents(),
        rng=rng,
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
