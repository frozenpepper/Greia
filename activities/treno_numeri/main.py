"""Thin Greia composition root for Treno Numeri (Number Express).

``activity.toml`` points here. Real work lives in cohort modules: content
(catalogue + geometry), model (pure rules), services (storage/events), art,
renderer, controls, audio and the app lifecycle.
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
    from .treno_app import TrenoApp
    from .treno_audio import TrainAudio
    from .treno_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .treno_model import Journey, StationFactory
    from .treno_services import GreiaTrainEvents, GreiaTrainProgress
else:
    from treno_app import TrenoApp
    from treno_audio import TrainAudio
    from treno_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from treno_model import Journey, StationFactory
    from treno_services import GreiaTrainEvents, GreiaTrainProgress


def _resources() -> LocalizedResources:
    return activity_resources(Path(__file__).resolve().parent, requested_locale=get_profile_locale())


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    resources = _resources()
    typography = GreiaTypography()
    canvas = PygameReferenceCanvas(screen)
    rng = random.Random()
    progress = GreiaTrainProgress()
    journey = Journey(StationFactory(rng), progress.load())
    app = TrenoApp(
        screen=screen,
        canvas=canvas,
        journey=journey,
        typography=typography,
        resources=resources,
        audio=TrainAudio(locale=resources.context.selected.language, resources=resources),
        progress=progress,
        events=GreiaTrainEvents(),
        rng=rng,
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
