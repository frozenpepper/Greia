"""La Memoria delle Meraviglie — Greia composition root.

Thin bootstrap: build collaborators (storage, audio, completion screen,
locale, canvas) and enter the Activity lifecycle. The real work lives
in :mod:`memory_app`, :mod:`memory_audio`, :mod:`memory_render` and
:mod:`memory_content`.
"""

from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    get_profile_locale,
    get_storage,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.pygame_completion import (
    CompletionContent,
    PygameCompletionScreen,
)
from greia_platform.typography import GreiaTypography

if __package__:
    from .memory_app import MemoryApp
    from .memory_audio import MemoryAudio
    from .memory_content import (
        GRID_CONFIGS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        THEMES,
    )
else:
    from memory_app import MemoryApp
    from memory_audio import MemoryAudio
    from memory_content import (
        GRID_CONFIGS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        THEMES,
    )

# Backwards-compatible re-exports for legacy tests/tools that import
# these names directly from the activity's main module.
__all__ = [
    "GRID_CONFIGS",
    "MemoryApp",
    "MemoryAudio",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "THEMES",
    "main",
]


def _localized(
    resources: LocalizedResources | None, key: str, default: str
) -> str:
    if resources is None:
        return default
    try:
        value = resources.text(key)
    except Exception:
        return default
    return value or default


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode(
            (REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE
        )
    pygame.mouse.set_visible(False)

    get_theme()
    metrics = ChildUiMetrics.for_size(*screen.get_size())
    canvas = PygameReferenceCanvas(screen)
    typography = GreiaTypography()
    sounds = MemoryAudio()

    try:
        storage = get_storage()
    except Exception:
        storage = None

    package_root = Path(__file__).resolve().parent
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    profile_lang = get_profile_locale()
    context = resolve_activity_locale(profile_lang, support)
    resources = LocalizedResources(package_root, context) if context else None
    active_locale = context.selected.language if context else "it"

    play_again_rect = pygame.Rect(
        REFERENCE_WIDTH // 2 - 120,
        REFERENCE_HEIGHT // 2 + 80,
        240,
        52,
    )
    completion = PygameCompletionScreen(
        typography,
        width=REFERENCE_WIDTH,
        height=REFERENCE_HEIGHT,
        primary_rect=play_again_rect,
    )
    completion_content = CompletionContent(
        title=_localized(resources, "victory.title", "🌟"),
        body_lines=(_localized(resources, "victory.subtitle", "★"),),
        primary_label=_localized(resources, "btn.play_again", "🔄"),
        achievement_count=3,
    )

    app = MemoryApp(
        screen=screen,
        canvas=canvas,
        metrics=metrics,
        typography=typography,
        sounds=sounds,
        resources=resources,
        active_locale=active_locale,
        storage=storage,
        completion=completion,
        completion_content=completion_content,
    )

    clock = pygame.time.Clock()
    while app._running and not activity_stop_requested():
        for event in pygame.event.get():
            app.handle_event(event)
        app._update()
        app._draw()
        # Present the frame so the first usable frame is on the display
        # BEFORE we tell the Shell the Activity is ready. MemoryApp._draw
        # already calls pygame.display.flip() for the active state; this
        # second flip is a no-op when the screen is in the same state and
        # guarantees the readiness invariant the platform checks.
        pygame.display.flip()
        if not app.ready_published:
            mark_activity_ready()
            app.ready_published = True
        clock.tick(30)
    app._persist_progress()
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
