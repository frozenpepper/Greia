"""Thin Greia composition root for La Foresta delle Parole (The Word Forest).

The round, the falling letters and the basket live in :mod:`foresta_model`;
art in :mod:`foresta_art`; drawing in :mod:`foresta_renderer`; kit controls in
:mod:`foresta_controls`; speech in :mod:`foresta_audio`; storage/events in
:mod:`foresta_services`; the lifecycle in :class:`foresta_app.ForestaApp`.
"""

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
    from .foresta_app import ForestaApp
    from .foresta_art import ForestArt
    from .foresta_audio import ForestAudio, SpeechQueue
    from .foresta_content import PHONICS_DATA, REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY
    from .foresta_model import RoundPlanner
    from .foresta_renderer import ForestRenderer
    from .foresta_services import GreiaForestEvents, GreiaForestProgress
else:
    from foresta_app import ForestaApp
    from foresta_art import ForestArt
    from foresta_audio import ForestAudio, SpeechQueue
    from foresta_content import PHONICS_DATA, REFERENCE_HEIGHT, REFERENCE_WIDTH, STORAGE_KEY
    from foresta_model import RoundPlanner
    from foresta_renderer import ForestRenderer
    from foresta_services import GreiaForestEvents, GreiaForestProgress

__all__ = ["ForestaApp", "PHONICS_DATA", "STORAGE_KEY", "build_app", "main"]


def _locale_and_resources() -> tuple[str, LocalizedResources]:
    resources = activity_resources(Path(__file__).resolve().parent, requested_locale=get_profile_locale())
    return resources.context.selected.language, resources


def build_app(screen: pygame.Surface, *, rng: random.Random | None = None) -> ForestaApp:
    """Compose the Activity on ``screen`` (also used by tests and tools)."""

    locale, resources = _locale_and_resources()
    rng = rng if rng is not None else random.Random()
    typography = GreiaTypography()
    canvas = PygameReferenceCanvas(screen)
    art = ForestArt(REFERENCE_WIDTH, REFERENCE_HEIGHT, typography)
    audio = ForestAudio(Path(__file__).resolve().parent, locale=locale, resources=resources)
    progress_port = GreiaForestProgress()
    return ForestaApp(
        screen=screen,
        canvas=canvas,
        planner=RoundPlanner(rng, language=locale),
        progress=progress_port.load(),
        progress_port=progress_port,
        events=GreiaForestEvents(),
        renderer=ForestRenderer(art),
        typography=typography,
        resources=resources,
        audio=audio,
        speech_queue=SpeechQueue(audio),
        locale=locale,
        rng=rng,
        session_id=f"{int(time.time())}-{rng.randrange(1_000_000):06d}",
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
        app.speech_queue.clear()
        app.kit.clear()
        app.renderer.art.clear()
        app.typography.clear()
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
