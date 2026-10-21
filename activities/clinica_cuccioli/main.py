"""Little Vet Clinic - thin Greia composition root.

Build the collaborators (resources, storage-backed progress, events, audio,
canvas, a seeded patient queue) and enter the Activity lifecycle. The real
work lives in :mod:`clinic_app` (flow), :mod:`clinic_model` (rules),
:mod:`clinic_content` (ailments, tools, patients), :mod:`clinic_renderer` /
:mod:`clinic_art` (presentation), :mod:`clinic_controls` (shared control
kit), :mod:`clinic_layout`, :mod:`clinic_audio` and :mod:`clinic_services`.
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
    from .clinic_app import ClinicActivity
    from .clinic_audio import ClinicAudio
    from .clinic_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, SPECIES
    from .clinic_model import ClinicDay, ClinicDayFactory
    from .clinic_services import GreiaClinicEvents, GreiaClinicProgress
else:
    from clinic_app import ClinicActivity
    from clinic_audio import ClinicAudio
    from clinic_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, SPECIES
    from clinic_model import ClinicDay, ClinicDayFactory
    from clinic_services import GreiaClinicEvents, GreiaClinicProgress

__all__ = ["ClinicActivity", "build_app", "main"]


def _resources(locale: str | None = None) -> LocalizedResources:
    """Resolve the profile language from this package's declared locales."""

    return activity_resources(Path(__file__).resolve().parent, requested_locale=locale or get_profile_locale())


def build_app(screen: pygame.Surface, *, locale: str | None = None, rng: random.Random | None = None) -> ClinicActivity:
    resources = _resources(locale)
    pygame.display.set_caption(resources.text("activity.title"))
    rng = rng if rng is not None else random.Random()
    progress = GreiaClinicProgress()
    saved = progress.load()
    factory = ClinicDayFactory(rng)
    vocab = tuple(sorted({species.vocab for species in SPECIES.values() if species.vocab}))
    return ClinicActivity(
        screen=screen,
        canvas=PygameReferenceCanvas(screen, hires=True),
        day=ClinicDay(factory.build(saved.level), level=saved.level),
        factory=factory,
        typography=GreiaTypography(),
        resources=resources,
        progress=progress,
        saved=saved,
        events=GreiaClinicEvents(),
        audio=ClinicAudio(resources.context.selected.language, vocab=vocab, rng=rng),
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
