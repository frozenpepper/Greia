"""Acquario Magico — Greia composition root.

Thin bootstrap. The real work lives in :mod:`acquarium_app`,
:mod:`acquarium_audio`, :mod:`acquarium_assets`, :mod:`acquarium_cast`,
:mod:`acquarium_content`, :mod:`acquarium_controls`, :mod:`acquarium_missions`,
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

from pathlib import Path

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    get_storage,
    get_theme,
    mark_activity_ready,
)
from greia_platform.frame_governor import FrameGovernor, FrameKind
from greia_platform.localization import LocalizedResources, activity_resources

if __package__:
    from .acquarium_app import build_app
    from .acquarium_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
else:
    from acquarium_app import build_app
    from acquarium_content import REFERENCE_HEIGHT, REFERENCE_WIDTH


def _resolve_locale() -> LocalizedResources:
    """Resolve the profile language from this package's declared locales."""
    return activity_resources(Path(__file__).resolve().parent)


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
    app = build_app(screen, resources, storage=storage)

    # READY is published only after the first frame has actually been presented.
    # The tank simulates at a fixed 30 Hz step; swimming is ambient, so it is
    # presented at a reduced rate once the child has been idle.
    frames = FrameGovernor(redraw_on_input=True)
    while not activity_stop_requested():
        for event in frames.events():
            app.handle_event(event)
        if not app._running:
            break
        app.advance(0.033)
        frame = frames.frame(ambient=True)
        if frame is FrameKind.FULL:
            app._draw()
            if not app.ready_published:
                mark_activity_ready()
                app.ready_published = True
        elif frame is FrameKind.POINTER:
            app.canvas.present_pointer()
        frames.wait(polling=True)  # keep the fixed simulation cadence
    app._autosave()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
