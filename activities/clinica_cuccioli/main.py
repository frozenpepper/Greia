from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

from clinic_app import ClinicActivity
from clinic_audio import PygameClinicAudio
from clinic_model import ClinicSession
from clinic_renderer import ClinicRenderer, REFERENCE_HEIGHT, REFERENCE_WIDTH
from clinic_services import GreiaClinicEvents, GreiaClinicProgress


def _localized_resources() -> LocalizedResources:
    support = ActivityLocaleSupport.localized(
        ("it", "en"),
        default_ui_locale="it",
    )
    context = resolve_activity_locale(get_profile_locale(), support)
    assert context is not None
    return LocalizedResources(Path(__file__).resolve().parent, context)


def main() -> int:
    """Compose the Activity from domain, presentation and Greia service owners."""

    pygame.init()
    try:
        screen = pygame.display.get_surface()
        if screen is None:
            screen = pygame.display.set_mode(
                (REFERENCE_WIDTH, REFERENCE_HEIGHT),
                pygame.RESIZABLE,
            )
        pygame.mouse.set_visible(False)

        progress = GreiaClinicProgress()
        session = ClinicSession(total_stars=progress.load_stars())
        resources = _localized_resources()
        renderer = ClinicRenderer(GreiaTypography(), resources)
        app = ClinicActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            session=session,
            renderer=renderer,
            audio=PygameClinicAudio(),
            progress=progress,
            events=GreiaClinicEvents(),
        )
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
