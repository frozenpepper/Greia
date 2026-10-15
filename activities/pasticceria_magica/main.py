from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.activity_api import get_profile_locale, get_storage
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .pasticceria_app import PasticceriaApp, SoundManager
    from .pasticceria_content import (
        BAKERY_COUNTER,
        BAKERY_WALL,
        CAKE_SLOTS,
        COUNTER_TOP,
        DARK_TEXT,
        GOLD,
        PASTEL_PINK,
        PINK,
        PLATE_COLOR,
        PLATE_RIM,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SHELF_COLOR,
        STORAGE_KEY,
        TOPPINGS,
        WHITE,
    )
    from .pasticceria_model import PasticceriaModel
    from .pasticceria_renderer import Particle, PasticceriaRenderer
else:
    from pasticceria_app import PasticceriaApp, SoundManager
    from pasticceria_content import (
        BAKERY_COUNTER,
        BAKERY_WALL,
        CAKE_SLOTS,
        COUNTER_TOP,
        DARK_TEXT,
        GOLD,
        PASTEL_PINK,
        PINK,
        PLATE_COLOR,
        PLATE_RIM,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SHELF_COLOR,
        STORAGE_KEY,
        TOPPINGS,
        WHITE,
    )
    from pasticceria_model import PasticceriaModel
    from pasticceria_renderer import Particle, PasticceriaRenderer

# Re-export compatibility surface (tests/tools may import these from main).
__all__ = [
    "main",
    "PasticceriaApp",
    "PasticceriaModel",
    "PasticceriaRenderer",
    "SoundManager",
    "Particle",
    "REFERENCE_WIDTH",
    "REFERENCE_HEIGHT",
    "STORAGE_KEY",
    "BAKERY_WALL",
    "BAKERY_COUNTER",
    "COUNTER_TOP",
    "PLATE_COLOR",
    "PLATE_RIM",
    "SHELF_COLOR",
    "WHITE",
    "DARK_TEXT",
    "GOLD",
    "PINK",
    "PASTEL_PINK",
    "TOPPINGS",
    "CAKE_SLOTS",
]


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    # Compatibility alias: real guard lives in pasticceria_app.
    if __package__:
        from .pasticceria_app import _is_safe_point as _real
    else:
        from pasticceria_app import _is_safe_point as _real
    return _real(surface, position)


def main() -> int:
    """Thin composition root: build Greia context, model, renderer and run the app."""
    pygame.init()
    try:
        screen = pygame.display.get_surface()
        if screen is None:
            # Fullscreen path when launched by Greia; windowed fallback for simulator/dev.
            try:
                screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            except pygame.error:
                screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
        pygame.mouse.set_visible(False)

        metrics = ChildUiMetrics.for_size(*screen.get_size())
        canvas = PygameReferenceCanvas(screen)
        typography = GreiaTypography()

        # Localization
        package_root = Path(__file__).resolve().parent
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        profile_lang = get_profile_locale()
        context = resolve_activity_locale(profile_lang, support)
        resources = LocalizedResources(package_root, context) if context else None

        # Domain model with persisted progress.
        model = PasticceriaModel()
        try:
            storage = get_storage()
            saved = storage.kv_get(STORAGE_KEY, {})
            model.load_saved(saved)
        except Exception:
            pass

        renderer = PasticceriaRenderer(typography, resources)
        app = PasticceriaApp(
            screen=screen,
            canvas=canvas,
            metrics=metrics,
            typography=typography,
            model=model,
            renderer=renderer,
            resources=resources,
        )
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
