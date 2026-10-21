"""Thin Greia composition root for Piccola Serra (Little Green Thumb).

``activity.toml`` points here. Real work lives in cohort modules: content
(plants, needs, ladder), model (pure grow/order rules + adaptive visit),
services (storage/events), layout, art, renderer, controls (shared kit),
audio and the app lifecycle.
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
    from .serra_app import SerraActivity
    from .serra_audio import SerraAudio
    from .serra_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .serra_model import Visit
    from .serra_services import GreiaSerraEvents, GreiaSerraProgress
else:
    from serra_app import SerraActivity
    from serra_audio import SerraAudio
    from serra_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from serra_model import Visit
    from serra_services import GreiaSerraEvents, GreiaSerraProgress


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
    # The platform pointer stays visible (the first release hid it).
    pygame.mouse.set_visible(True)

    resources = _resources()
    locale = resources.context.selected.language if resources is not None else "en"
    if resources is not None:
        try:
            pygame.display.set_caption(resources.text("activity.title"))
        except Exception:
            pass
    progress = GreiaSerraProgress()
    visit = Visit(progress.load(), random.Random())
    app = SerraActivity(
        screen=screen,
        canvas=PygameReferenceCanvas(screen, hires=True),
        visit=visit,
        typography=GreiaTypography(),
        resources=resources,
        audio=SerraAudio(locale),
        progress=progress,
        events=GreiaSerraEvents(),
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["SerraActivity", "SerraAudio", "Visit", "main"]
