"""Thin Greia composition root for My Greia (``workshop_settings``).

My Greia is the child's own space: a live miniature of their Home and big
picture choices (friend avatar, room and sparkle colours, Home pictures,
big/small letters). Every choice saves immediately through the trusted
customization services. Work lives in ``workshop_app`` (lifecycle/input),
``workshop_model`` (pure state), ``workshop_services`` (platform port),
``workshop_controls`` (shared control kit), ``workshop_preview`` (Home
miniature), ``workshop_art`` (bounded pictures), ``workshop_audio`` and
``workshop_renderer``. Removable-media wallpaper import is not part of the
child flow; the platform capability remains for a parent-reviewed route.
"""

from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

# Support both Greia runtime/script and repository/package contexts. When
# loaded via importlib.spec_from_file_location (tests) __package__ is falsy;
# set it to the canonical package so relative imports succeed. For direct
# script execution bare imports remain the fallback.
if not __package__:
    __package__ = "activities.workshop_settings"  # type: ignore[assignment]

try:
    from .workshop_app import MyGreiaApp
    from .workshop_audio import MyGreiaAudio
    from .workshop_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .workshop_services import GreiaCustomization
except ImportError:
    from workshop_app import MyGreiaApp  # type: ignore[no-redef]
    from workshop_audio import MyGreiaAudio  # type: ignore[no-redef]
    from workshop_content import REFERENCE_HEIGHT, REFERENCE_WIDTH  # type: ignore[no-redef]
    from workshop_services import GreiaCustomization  # type: ignore[no-redef]

# Historical name kept for tools/tests that import it from ``main``.
MyGreiaSettings = MyGreiaApp

__all__ = ["main", "MyGreiaApp", "MyGreiaSettings"]


def _resources() -> LocalizedResources:
    return activity_resources(Path(__file__).resolve().parent, requested_locale=get_profile_locale())


def main() -> int:
    pygame.init()
    try:
        screen = pygame.display.get_surface()
        if screen is None:
            screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
        # The Greia pointer is drawn by the canvas on every presented frame.
        pygame.mouse.set_visible(False)
        resources = _resources()
        typography = GreiaTypography()
        app = MyGreiaApp(
            screen=screen,
            canvas=PygameReferenceCanvas(screen, hires=True),
            typography=typography,
            resources=resources,
            services=GreiaCustomization(),
            audio=MyGreiaAudio(resources),
        )
        return app.run()
    finally:
        try:
            if pygame.get_init():
                pygame.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
