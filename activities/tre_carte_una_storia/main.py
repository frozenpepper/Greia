"""Thin Greia composition root for Tre Carte Una Storia."""

from __future__ import annotations

from pathlib import Path
import random
import time

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .story_cards_app import StoryActivity
    from .story_cards_art import StoryArt
    from .story_cards_audio import StoryAudio
    from .story_cards_content import STORY_SEEDS
    from .story_cards_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        create_shuffled_round,
    )
    from .story_cards_renderer import StoryRenderer
    from .story_cards_services import GreiaStoryEvents, GreiaStoryStorage
else:
    from story_cards_app import StoryActivity
    from story_cards_art import StoryArt
    from story_cards_audio import StoryAudio
    from story_cards_content import STORY_SEEDS
    from story_cards_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        create_shuffled_round,
    )
    from story_cards_renderer import StoryRenderer
    from story_cards_services import GreiaStoryEvents, GreiaStoryStorage


def _locale_and_resources() -> tuple[str, LocalizedResources]:
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    context = resolve_activity_locale(get_profile_locale(), support)
    if context is None:
        context = resolve_activity_locale("it", support)
    assert context is not None
    locale = context.selected.value.split("-")[0]
    return locale, LocalizedResources(Path(__file__).resolve().parent, context)


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(False)

    locale, resources = _locale_and_resources()
    typography = GreiaTypography()
    canvas = PygameReferenceCanvas(screen)
    art = StoryArt(REFERENCE_WIDTH, REFERENCE_HEIGHT, typography)
    renderer = StoryRenderer(art, typography, resources)
    storage = GreiaStoryStorage()
    library = storage.load()
    rng = random.Random()
    round_state = create_shuffled_round(STORY_SEEDS[0], rng)
    audio = StoryAudio()
    session_id = f"{int(time.time())}-{rng.randrange(1_000_000):06d}"

    app = StoryActivity(
        screen=screen,
        canvas=canvas,
        round_state=round_state,
        library=library,
        renderer=renderer,
        typography=typography,
        resources=resources,
        storage=storage,
        events=GreiaStoryEvents(),
        audio=audio,
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
