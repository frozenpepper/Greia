"""Thin Greia composition root for Il Bosco dei Numeri di Tito (Tito's Number Forest)."""

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
    from .bosco_app import BoscoApp
    from .bosco_art import BoscoArt
    from .bosco_audio import BoscoAudio, SpeechQueue
    from .bosco_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, WalkPlanner
    from .bosco_renderer import BoscoRenderer
    from .bosco_services import GreiaBoscoEvents, GreiaBoscoProgress
else:
    from bosco_app import BoscoApp
    from bosco_art import BoscoArt
    from bosco_audio import BoscoAudio, SpeechQueue
    from bosco_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, WalkPlanner
    from bosco_renderer import BoscoRenderer
    from bosco_services import GreiaBoscoEvents, GreiaBoscoProgress


def _locale_and_resources() -> tuple[str, LocalizedResources]:
    resources = activity_resources(Path(__file__).resolve().parent, requested_locale=get_profile_locale())
    return resources.context.selected.language, resources


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    locale, resources = _locale_and_resources()
    typography = GreiaTypography()
    canvas = PygameReferenceCanvas(screen)
    art = BoscoArt(REFERENCE_WIDTH, REFERENCE_HEIGHT)
    renderer = BoscoRenderer(art)
    progress_port = GreiaBoscoProgress()
    rng = random.Random()
    session_id = f"{int(time.time())}-{rng.randrange(1_000_000):06d}"
    audio = BoscoAudio(Path(__file__).resolve().parent, locale=locale, resources=resources)
    speech_queue = SpeechQueue(audio)

    app = BoscoApp(
        screen=screen,
        canvas=canvas,
        planner=WalkPlanner(rng),
        progress=progress_port.load(),
        progress_port=progress_port,
        events=GreiaBoscoEvents(),
        renderer=renderer,
        typography=typography,
        resources=resources,
        audio=audio,
        speech_queue=speech_queue,
        rng=rng,
        session_id=session_id,
    )
    try:
        return app.run()
    finally:
        speech_queue.clear()
        app.kit.clear()
        art.clear()
        typography.clear()
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
