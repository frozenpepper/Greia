"""Thin Greia composition root for Festa delle Rime."""

from __future__ import annotations

from pathlib import Path
import random
import time

import pygame

from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .rhyme_app import RhymeActivity
    from .rhyme_art import RhymeArt
    from .rhyme_audio import RhymeAudio, SpeechQueue
    from .rhyme_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, RhymeRoundFactory, RhymeSession
    from .rhyme_renderer import RhymeRenderer
    from .rhyme_services import GreiaRhymeEvents, GreiaRhymeProgress
else:
    from rhyme_app import RhymeActivity
    from rhyme_art import RhymeArt
    from rhyme_audio import RhymeAudio, SpeechQueue
    from rhyme_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, RhymeRoundFactory, RhymeSession
    from rhyme_renderer import RhymeRenderer
    from rhyme_services import GreiaRhymeEvents, GreiaRhymeProgress


def _locale_and_resources() -> tuple[str, LocalizedResources]:
    resources = activity_resources(Path(__file__).resolve().parent)
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
    art = RhymeArt(REFERENCE_WIDTH, REFERENCE_HEIGHT, typography)
    renderer = RhymeRenderer(art, typography, resources)
    progress = GreiaRhymeProgress()
    saved = progress.load()
    rng = random.Random()
    factory = RhymeRoundFactory(rng, locale=locale)
    session = RhymeSession(factory.build_set(saved.level), level=saved.level, history=saved.history)
    session_id = f"{int(time.time())}-{rng.randrange(1_000_000):06d}"

    audio = RhymeAudio(Path(__file__).resolve().parent, locale=locale, resources=resources)
    speech_queue = SpeechQueue(audio)

    app = RhymeActivity(
        screen=screen,
        canvas=canvas,
        session=session,
        factory=factory,
        renderer=renderer,
        typography=typography,
        resources=resources,
        progress=progress,
        events=GreiaRhymeEvents(),
        audio=audio,
        speech_queue=speech_queue,
        rng=rng,
        session_id=session_id,
    )
    try:
        return app.run()
    finally:
        typography.clear()
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
