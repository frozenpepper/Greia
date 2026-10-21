"""Thin Greia composition root for La Discesa della Biglia (Tito's Marble Run).

``activity.toml`` points here. Real work lives in cohort modules: content
(authored boards), engine (fixed-step physics), model (board state, hints,
visit), services (storage/events), layout, art, renderer, controls (shared
kit), audio and the app lifecycle.
"""

from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .ramp_app import MarbleRunActivity
    from .ramp_audio import RampAudio
    from .ramp_layout import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .ramp_model import Visit
    from .ramp_services import GreiaRampEvents, GreiaRampProgress
else:
    from ramp_app import MarbleRunActivity
    from ramp_audio import RampAudio
    from ramp_layout import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from ramp_model import Visit
    from ramp_services import GreiaRampEvents, GreiaRampProgress


def _resources() -> LocalizedResources:
    return activity_resources(Path(__file__).resolve().parent, requested_locale=get_profile_locale())


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    resources = _resources()
    pygame.display.set_caption(resources.text("activity.title"))
    progress = GreiaRampProgress()
    app = MarbleRunActivity(
        screen=screen,
        canvas=PygameReferenceCanvas(screen, hires=True),
        visit=Visit(progress.load()),
        typography=GreiaTypography(),
        resources=resources,
        audio=RampAudio(resources.context.selected.language),
        progress=progress,
        events=GreiaRampEvents(),
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["MarbleRunActivity", "RampAudio", "Visit", "main"]
