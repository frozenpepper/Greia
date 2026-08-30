"""Acquario Magico — Greia composition root.

Thin bootstrap. The real work lives in :mod:`acquarium_app`,
:mod:`acquarium_audio`, :mod:`acquarium_assets`, :mod:`acquarium_content`,
:mod:`acquarium_model` and :mod:`acquarium_renderer`.

The Activity runs under Greia platform authority: it does not
bypass the platform lifecycle (READY/STOP), it does not pick
hardware, it does not own global reward state and it does not
draw the real Greia Home/Back chrome. The R7.3 trusted
launcher chrome owns Home input and presentation; this
Activity only preserves the renderer-neutral protected/safe
viewport geometry through the shared
``PygameReferenceCanvas``/``ChildUiMetrics`` seam.
"""

from __future__ import annotations

import time
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
from greia_platform.typography import GreiaTypography

if __package__:
    from .acquarium_app import AquariumApp, CHEST_RECT, build_app
    from .acquarium_assets import (
        AquariumAssetCache,
        _get_cached_background,
        _get_scaled_asset,
        _load_asset_surface,
    )
    from .acquarium_audio import AquariumAudio
    from .acquarium_content import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SPECIES,
        STORAGE_KEY,
        ToolIndex,
    )
    from .acquarium_model import AquariumSession
    from .acquarium_renderer import AquariumRenderer, ToolLayout
else:
    from aquarium_app import AquariumApp, CHEST_RECT, build_app
    from aquarium_assets import (
        AquariumAssetCache,
        _get_cached_background,
        _get_scaled_asset,
        _load_asset_surface,
    )
    from aquarium_audio import AquariumAudio
    from aquarium_content import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SPECIES,
        STORAGE_KEY,
        ToolIndex,
    )
    from aquarium_model import AquariumSession
    from aquarium_renderer import AquariumRenderer, ToolLayout


def _resolve_locale() -> LocalizedResources:
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    try:
        context = resolve_activity_locale(get_profile_locale(), support)
    except Exception:
        context = resolve_activity_locale("it", support)
    if context is None:
        context = resolve_activity_locale("it", support)
        if context is None:
            # ``ActivityLocaleSupport.localized`` always returns a
            # usable default; this branch only protects against a
            # future refactor that returns ``None`` for the
            # default locale as well.
            raise RuntimeError("acquario_magico: locale support is unavailable")
    return LocalizedResources(Path(__file__).resolve().parent, context)


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)
    get_theme()
    resources = _resolve_locale()
    try:
        storage = get_storage()
    except Exception:
        storage = None
    app = AquariumApp(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        metrics=ChildUiMetrics.for_size(*screen.get_size()),
        typography=GreiaTypography(),
        resources=resources,
        audio=AquariumAudio(),
        storage=storage,
    )

    # The Activity runs the platform-authority event loop in
    # main() so the ``ready_published`` invariant (READY after
    # the first presented frame, in the same launch loop) is
    # trivially satisfied: the call to ``mark_activity_ready``
    # follows the first ``pygame.display.flip()`` inside
    # ``app._draw`` in the same iteration of this loop.
    while not activity_stop_requested():
        for event in pygame.event.get():
            app.handle_event(event)
        if not app._running:
            break
        # ``_step_frame`` would re-publish READY for a frame that
        # has not been drawn yet; run a custom loop here so the
        # published frame is the frame that just presented.
        app.session.update(0.033)
        if (
            app.storage is not None
            and time.monotonic() - app.last_save_time > 10.0
        ):
            app.last_save_time = time.monotonic()
            app._autosave()
        app._draw()
        if not app.ready_published:
            mark_activity_ready()
            app.ready_published = True
        app.clock.tick(30)
    app._autosave()
    return 0


# Backwards-compatible re-exports. The historical contract tests
# (tests/test_activity_acquario_magico.py and
# tests/test_activities_phase5.py) import SPECIES, AquariumAudio,
# _get_cached_background and _get_scaled_asset directly from this
# module. Keep those names so the migration does not require
# touching every caller; the new modules own the real work.
__all__ = [
    "AquariumApp",
    "AquariumAssetCache",
    "AquariumAudio",
    "AquariumRenderer",
    "AquariumSession",
    "CHEST_RECT",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SPECIES",
    "STORAGE_KEY",
    "ToolIndex",
    "ToolLayout",
    "_get_cached_background",
    "_get_scaled_asset",
    "_load_asset_surface",
    "build_app",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
