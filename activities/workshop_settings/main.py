"""Thin Greia composition root for workshop_settings.

The historical ``main.py`` was a 707-line monolith that mixed constants,
domain state, rendering and the event loop. Real work now lives in
:mod:`workshop_content`, :mod:`workshop_model`, :mod:`workshop_renderer`
and :mod:`workshop_app`. This module only re-exports the historical API
surface and composes the lifecycle owned by :class:`WorkshopApp`.

The surface remains parent-only (not a child Activity), R7.3-migrated:
it does not own trusted Greia Home/Back chrome and respects the
protected viewport through the shared ``ActivityViewport`` seam.
"""

from __future__ import annotations

import pygame

from greia_platform.activity_api import get_theme

# Support both Greia runtime/script and repository/package contexts
# without importing forbidden modules. When loaded via
# importlib.spec_from_file_location (tests) __package__ is falsy; we
# set it to the canonical package so relative imports succeed. For
# direct script execution ``python main.py`` bare imports remain the
# fallback because sys.path[0] is the Activity directory itself.
if not __package__:
    __package__ = "activities.workshop_settings"  # type: ignore[assignment]

try:
    from .workshop_app import WorkshopApp
    from .workshop_content import (
        MAX_THUMBNAIL_CACHE,
        MAX_THUMBNAIL_PIXELS,
        MODE_ICONS,
        MODES,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SCAN_INTERVAL_SECONDS,
    )
    from .workshop_model import WorkshopModel
    from .workshop_renderer import HitTarget, WorkshopRenderer, _mix, settings_safe_ui_rect
except ImportError:
    from workshop_app import WorkshopApp  # type: ignore[no-redef]
    from workshop_content import (  # type: ignore[no-redef]
        MAX_THUMBNAIL_CACHE,
        MAX_THUMBNAIL_PIXELS,
        MODE_ICONS,
        MODES,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SCAN_INTERVAL_SECONDS,
    )
    from workshop_model import WorkshopModel  # type: ignore[no-redef]
    from workshop_renderer import HitTarget, WorkshopRenderer, _mix, settings_safe_ui_rect  # type: ignore[no-redef]

# Re-export compatibility surface (tests/tools may import these from main).
MyGreiaSettings = WorkshopApp

__all__ = [
    "main",
    "MyGreiaSettings",
    "WorkshopApp",
    "WorkshopModel",
    "WorkshopRenderer",
    "HitTarget",
    "settings_safe_ui_rect",
    "_mix",
    "SCAN_INTERVAL_SECONDS",
    "MAX_THUMBNAIL_CACHE",
    "MAX_THUMBNAIL_PIXELS",
    "MODES",
    "MODE_ICONS",
    "REFERENCE_WIDTH",
    "REFERENCE_HEIGHT",
]


def main() -> int:
    """Thin composition root: build Greia context and run the app."""
    pygame.init()
    try:
        screen = pygame.display.get_surface()
        if screen is None:
            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
        # Warm theme cache so first frame has correct colors.
        try:
            get_theme()
        except Exception:
            pass
        app = WorkshopApp(screen)
        return app.run()
    finally:
        try:
            if pygame.get_init():
                pygame.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
