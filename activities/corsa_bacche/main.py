"""Thin Greia composition root for La Corsa delle Bacche (Momo's berry chase).

``activity.toml`` points here. Real work lives in cohort modules: content
(authored gardens + ladder), model (pure garden rules + adaptive visit),
services (storage/events), layout, art, renderer, controls (shared kit HUD),
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
    from .corsa_app import CorsaActivity
    from .corsa_audio import CorsaAudio
    from .corsa_layout import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .corsa_model import Visit
    from .corsa_services import GreiaCorsaEvents, GreiaCorsaProgress
else:
    from corsa_app import CorsaActivity
    from corsa_audio import CorsaAudio
    from corsa_layout import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from corsa_model import Visit
    from corsa_services import GreiaCorsaEvents, GreiaCorsaProgress


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
    if resources is not None:
        try:
            pygame.display.set_caption(resources.text("activity.title"))
        except Exception:
            pass
    progress = GreiaCorsaProgress()
    visit = Visit(progress.load(), random.Random())
    app = CorsaActivity(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        visit=visit,
        typography=GreiaTypography(),
        resources=resources,
        audio=CorsaAudio(locale),
        progress=progress,
        events=GreiaCorsaEvents(),
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["CorsaActivity", "CorsaAudio", "Visit", "main"]
