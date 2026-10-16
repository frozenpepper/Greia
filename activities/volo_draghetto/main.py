"""Thin Greia composition root for Il Volo del Draghetto (org.greia.volo-draghetto)."""

from __future__ import annotations

from pathlib import Path
import random
import time

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .dragon_app import DragonFlightActivity
    from .dragon_audio import DragonAudio
    from .dragon_model import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .dragon_services import GreiaFlightEvents, GreiaFlightProgress
else:
    from dragon_app import DragonFlightActivity
    from dragon_audio import DragonAudio
    from dragon_model import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from dragon_services import GreiaFlightEvents, GreiaFlightProgress


def _resources() -> LocalizedResources:
    return activity_resources(Path(__file__).resolve().parent, requested_locale=get_profile_locale())


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    resources = _resources()
    rng = random.Random()
    app = DragonFlightActivity(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        typography=GreiaTypography(),
        resources=resources,
        progress=GreiaFlightProgress(),
        events=GreiaFlightEvents(),
        audio=DragonAudio(resources.context.selected.language, rng=rng),
        rng=rng,
        session_id=f"{int(time.time())}-{rng.randrange(1_000_000):06d}",
    )
    try:
        return app.run_loop()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
