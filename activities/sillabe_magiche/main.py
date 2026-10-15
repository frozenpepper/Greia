"""Thin Greia composition root for Magic Syllables — Leo's Syllable Train."""

from __future__ import annotations

from pathlib import Path
import random
import time

import pygame

from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .sillabe_app import SillabeActivity
    from .sillabe_art import SillabeArt
    from .sillabe_audio import SillabeAudio, SpeechQueue, recorded_clip_checker
    from .sillabe_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .sillabe_model import TrainRoundFactory, TrainSession
    from .sillabe_renderer import SillabeRenderer
    from .sillabe_services import GreiaTrainEvents, GreiaTrainProgress, TrainProgress
else:
    from sillabe_app import SillabeActivity
    from sillabe_art import SillabeArt
    from sillabe_audio import SillabeAudio, SpeechQueue, recorded_clip_checker
    from sillabe_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from sillabe_model import TrainRoundFactory, TrainSession
    from sillabe_renderer import SillabeRenderer
    from sillabe_services import GreiaTrainEvents, GreiaTrainProgress, TrainProgress

PACKAGE_ROOT = Path(__file__).resolve().parent


def _locale_and_resources() -> tuple[str, LocalizedResources]:
    resources = activity_resources(PACKAGE_ROOT)
    return resources.context.selected.language, resources


class _NoStorage:
    """Fallback when Greia Storage is unavailable: progress simply is not kept."""

    def kv_get(self, key, default=None):
        return default

    def kv_set(self, key, value) -> None:
        return None


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    locale, resources = _locale_and_resources()
    typography = GreiaTypography()
    canvas = PygameReferenceCanvas(screen)
    art = SillabeArt(REFERENCE_WIDTH, REFERENCE_HEIGHT, typography)
    renderer = SillabeRenderer(art)
    try:
        progress = GreiaTrainProgress()
    except Exception:
        progress = GreiaTrainProgress(_NoStorage())
    saved: TrainProgress = progress.load()
    rng = random.Random()
    factory = TrainRoundFactory(rng, locale=locale, clip_exists=recorded_clip_checker(PACKAGE_ROOT, locale))
    session = TrainSession(factory.build_set(saved.level), level=saved.level, history=saved.history)
    session_id = f"{int(time.time())}-{rng.randrange(1_000_000):06d}"

    audio = SillabeAudio(PACKAGE_ROOT, locale=locale, resources=resources)
    speech_queue = SpeechQueue(audio)

    app = SillabeActivity(
        screen=screen,
        canvas=canvas,
        session=session,
        factory=factory,
        renderer=renderer,
        typography=typography,
        resources=resources,
        locale=locale,
        progress=progress,
        events=GreiaTrainEvents(),
        audio=audio,
        speech_queue=speech_queue,
        rng=rng,
        session_id=session_id,
    )
    try:
        return app.run()
    finally:
        speech_queue.clear()
        audio.clear()
        app.kit.clear()
        art.clear()
        typography.clear()
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
