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
    from .acquarium_app import AquariumApp
    from .acquarium_audio import AquariumAudio
    from .acquarium_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
else:
    from acquarium_app import AquariumApp
    from acquarium_audio import AquariumAudio
    from acquarium_content import REFERENCE_HEIGHT, REFERENCE_WIDTH


def _resolve_locale() -> LocalizedResources:
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    try:
        context = resolve_activity_locale(get_profile_locale(), support)
    except Exception:
        context = resolve_activity_locale("it", support)
    if context is None:
        context = resolve_activity_locale("it", support)
        if context is None:
            raise RuntimeError("acquario_magico: locale support is unavailable")
    return LocalizedResources(Path(__file__).resolve().parent, context)


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode(
            (REFERENCE_WIDTH, REFERENCE_HEIGHT),
            pygame.RESIZABLE,
        )
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

    # READY is published only after the first frame has actually been presented.
    while not activity_stop_requested():
        for event in pygame.event.get():
            app.handle_event(event)
        if not app._running:
            break
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


if __name__ == "__main__":
    raise SystemExit(main())
