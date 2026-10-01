from __future__ import annotations

"""Clean thin composition root for La Torre delle Forme."""

from pathlib import Path
import random
import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import ActivityLocaleSupport, LocalizedResources, resolve_activity_locale
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .torre_app import TorreApp
    from .torre_audio import TorreAudio
    from .torre_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .torre_model import TorreModel
    from .torre_renderer import TorreRenderer
else:
    from torre_app import TorreApp
    from torre_audio import TorreAudio
    from torre_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from torre_model import TorreModel
    from torre_renderer import TorreRenderer


def _load_resources() -> LocalizedResources:
    support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
    context = resolve_activity_locale(get_profile_locale(), support)
    if context is None:
        context = resolve_activity_locale("it", support)
    assert context is not None
    return LocalizedResources(Path(__file__).resolve().parent, context)


def main() -> int:
    """Compose Greia platform services and run Torre delle Forme."""
    pygame.init()
    try:
        screen = pygame.display.get_surface()
        if screen is None:
            screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
        pygame.mouse.set_visible(True)

        resources = _load_resources()
        typography = GreiaTypography()
        canvas = PygameReferenceCanvas(screen)
        renderer = TorreRenderer(typography, resources)
        audio = TorreAudio()
        rng = random.Random()
        model = TorreModel(rng=rng)

        app = TorreApp(
            screen=screen,
            canvas=canvas,
            typography=typography,
            resources=resources,
            model=model,
            renderer=renderer,
            audio=audio,
            rng=rng,
        )
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
