"""Thin Greia composition root for La Bottega delle Misure (The Measurement Workshop).

``activity.toml`` points here. Real work lives in cohort modules: content
(scene geometry), model (pure rules), services (storage/events), art,
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
    from .measure_app import BottegaActivity
    from .measure_audio import MeasureAudio
    from .measure_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .measure_model import Delivery, TaskFactory
    from .measure_services import GreiaMeasureEvents, GreiaMeasureProgress
else:
    from measure_app import BottegaActivity
    from measure_audio import MeasureAudio
    from measure_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from measure_model import Delivery, TaskFactory
    from measure_services import GreiaMeasureEvents, GreiaMeasureProgress


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
    canvas = PygameReferenceCanvas(screen, hires=True)
    rng = random.Random()
    progress = GreiaMeasureProgress()
    delivery = Delivery(TaskFactory(rng), progress.load())
    app = BottegaActivity(
        screen=screen,
        canvas=canvas,
        delivery=delivery,
        typography=typography,
        resources=resources,
        audio=MeasureAudio(resources, rng=rng),
        progress=progress,
        events=GreiaMeasureEvents(),
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
