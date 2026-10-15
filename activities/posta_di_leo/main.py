"""Thin Greia composition root for Posta di Leo."""

from __future__ import annotations

from pathlib import Path
import random
import time

import pygame

from greia_platform.activity_api import get_creations
from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .postcard_app import PostcardActivity
    from .postcard_art import PostcardArt
    from .postcard_audio import PostcardAudio
    from .postcard_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        PostcardDraft,
    )
    from .postcard_renderer import PostcardRenderer
    from .postcard_services import GreiaPostcardEvents, GreiaPostcardStorage
else:
    from postcard_app import PostcardActivity
    from postcard_art import PostcardArt
    from postcard_audio import PostcardAudio
    from postcard_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        PostcardDraft,
    )
    from postcard_renderer import PostcardRenderer
    from postcard_services import GreiaPostcardEvents, GreiaPostcardStorage


def _locale_and_resources() -> tuple[str, LocalizedResources]:
    resources = activity_resources(Path(__file__).resolve().parent)
    locale = resources.context.selected.value.split("-")[0]
    return locale, resources


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    locale, resources = _locale_and_resources()
    typography = GreiaTypography()
    canvas = PygameReferenceCanvas(screen)
    art = PostcardArt(REFERENCE_WIDTH, REFERENCE_HEIGHT, typography)
    renderer = PostcardRenderer(art, typography, resources)
    storage = GreiaPostcardStorage()
    library = storage.load()
    try:
        creations = get_creations()
    except RuntimeError:
        creations = None
    rng = random.Random()
    draft = PostcardDraft(recipient_id="leo", stamp_id="heart")
    audio = PostcardAudio()
    session_id = f"{int(time.time())}-{rng.randrange(1_000_000):06d}"

    app = PostcardActivity(
        screen=screen,
        canvas=canvas,
        draft=draft,
        library=library,
        renderer=renderer,
        typography=typography,
        resources=resources,
        storage=storage,
        events=GreiaPostcardEvents(),
        audio=audio,
        rng=rng,
        session_id=session_id,
        creations=creations,
    )
    try:
        return app.run()
    finally:
        typography.clear()
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
