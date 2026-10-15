"""Thin Greia composition root for L'Alfabeto di Leo (Leo's Letter Garden)."""

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
    from .alfabeto_app import AlfabetoApp
    from .alfabeto_art import AlfabetoArt
    from .alfabeto_audio import AlfabetoAudio, SpeechQueue
    from .alfabeto_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, GardenPlanner
    from .alfabeto_renderer import AlfabetoRenderer
    from .alfabeto_services import GreiaAlfabetoEvents, GreiaAlfabetoProgress
else:
    from alfabeto_app import AlfabetoApp
    from alfabeto_art import AlfabetoArt
    from alfabeto_audio import AlfabetoAudio, SpeechQueue
    from alfabeto_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, GardenPlanner
    from alfabeto_renderer import AlfabetoRenderer
    from alfabeto_services import GreiaAlfabetoEvents, GreiaAlfabetoProgress


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
    art = AlfabetoArt(REFERENCE_WIDTH, REFERENCE_HEIGHT)
    renderer = AlfabetoRenderer(art)
    progress_port = GreiaAlfabetoProgress()
    rng = random.Random()
    session_id = f"{int(time.time())}-{rng.randrange(1_000_000):06d}"
    audio = AlfabetoAudio(Path(__file__).resolve().parent, locale=locale, resources=resources)
    speech_queue = SpeechQueue(audio)

    app = AlfabetoApp(
        screen=screen,
        canvas=canvas,
        planner=GardenPlanner(rng, locale=locale),
        progress=progress_port.load(),
        progress_port=progress_port,
        events=GreiaAlfabetoEvents(),
        renderer=renderer,
        typography=typography,
        resources=resources,
        audio=audio,
        speech_queue=speech_queue,
        locale=locale,
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
