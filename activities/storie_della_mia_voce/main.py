"""Stories of My Voice (Story Cards) — thin Greia composition root.

Build the collaborators (resources, audio, microphone, storage-backed shelf
and progress, Creations client, canvas) and enter the Activity lifecycle. The
real work lives in :mod:`voice_app` (flow), :mod:`voice_model` (rules),
:mod:`voice_renderer` / :mod:`voice_art` (presentation), :mod:`voice_controls`
(shared control kit), :mod:`voice_layout`, :mod:`voice_audio`,
:mod:`voice_microphone`, :mod:`voice_services` and :mod:`voice_content`.
"""

from __future__ import annotations

from pathlib import Path
import random

import pygame

from greia_platform.activity_api import (
    get_audio_capture_device,
    get_creations,
    get_profile_locale,
    get_sdl_capture_device,
    get_storage,
)
from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .voice_app import StoryApp
    from .voice_audio import StoryAudio
    from .voice_content import HOST, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .voice_microphone import VoiceRecorder
    from .voice_services import StoryProgress, VoiceStorage
else:
    from voice_app import StoryApp
    from voice_audio import StoryAudio
    from voice_content import HOST, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from voice_microphone import VoiceRecorder
    from voice_services import StoryProgress, VoiceStorage

__all__ = ["StoryApp", "build_app", "main"]


def _resources(locale: str | None = None) -> LocalizedResources | None:
    try:
        return activity_resources(Path(__file__).resolve().parent, requested_locale=locale or get_profile_locale())
    except Exception:
        return None


def _microphone_available(recorder: VoiceRecorder) -> bool:
    """Ask the platform once at start-up (never per frame)."""

    try:
        if get_sdl_capture_device() is not None or get_audio_capture_device() is not None:
            return True
    except Exception:
        pass
    return recorder.available


def build_app(screen: pygame.Surface, *, locale: str | None = None, rng: random.Random | None = None) -> StoryApp:
    resources = _resources(locale)
    language = resources.context.selected.language if resources is not None else "en"
    if resources is not None:
        pygame.display.set_caption(resources.text("activity.title"))
    try:
        storage_client = get_storage()
    except Exception:
        storage_client = None
    try:
        creations = get_creations()
    except RuntimeError:
        # Standalone authoring has no trusted session broker: no sharing.
        creations = None
    recorder = VoiceRecorder()
    rng = rng if rng is not None else random.Random()
    return StoryApp(
        screen=screen,
        canvas=PygameReferenceCanvas(screen, hires=True),
        typography=GreiaTypography(),
        resources=resources,
        audio=StoryAudio(locale=language, host=HOST, rng=rng),
        recorder=recorder,
        storage=VoiceStorage.load(storage_client),
        progress=StoryProgress.load(storage_client),
        creations=creations,
        mic_available=_microphone_available(recorder),
        rng=rng,
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
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
