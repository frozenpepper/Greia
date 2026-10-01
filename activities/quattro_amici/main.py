"""Thin Greia composition root for Quattro Amici in Fila.

Acts strictly as the bootstrap boundary (<120 lines). Delegates all domain,
rendering, and lifecycle mechanics to sibling modules.
"""

from __future__ import annotations

import pygame

from greia_platform.activity_api import get_profile_locale

if __package__:
    from .quattro_app import build_app
else:
    from quattro_app import build_app


def main() -> int:
    """Initialize display and run Quattro Amici Activity."""
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((1024, 600), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    locale = get_profile_locale() or "it"
    app = build_app(screen, locale=locale)
    try:
        return app.run()
    finally:
        app.typography.clear()
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
