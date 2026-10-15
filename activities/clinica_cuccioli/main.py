from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

try:
    from clinic_app import ClinicActivity
    from clinic_audio import PygameClinicAudio
    from clinic_model import ClinicSession
    from clinic_renderer import ClinicRenderer, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from clinic_services import GreiaClinicEvents, GreiaClinicProgress
except ImportError:
    from .clinic_app import ClinicActivity
    from .clinic_audio import PygameClinicAudio
    from .clinic_model import ClinicSession
    from .clinic_renderer import ClinicRenderer, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .clinic_services import GreiaClinicEvents, GreiaClinicProgress

PATIENTS: list[dict[str, object]] = [
    {"id": "dog", "color": (217, 119, 6), "ear_color": (180, 83, 9), "muzzle": (254, 243, 199)},
    {"id": "cat", "color": (251, 146, 60), "ear_color": (244, 114, 182), "muzzle": (255, 255, 255)},
    {"id": "bunny", "color": (248, 250, 252), "ear_color": (244, 114, 182), "muzzle": (255, 255, 255)},
    {"id": "bear", "color": (146, 64, 14), "ear_color": (120, 53, 15), "muzzle": (254, 215, 170)},
]

TOOLS: list[dict[str, object]] = [
    {"id": "stethoscope", "color": (59, 130, 246)},
    {"id": "bath", "color": (14, 165, 233)},
    {"id": "bandaid", "color": (236, 72, 153)},
    {"id": "food", "color": (234, 179, 8)},
    {"id": "cuddle", "color": (239, 68, 68)},
]

VetAudio = PygameClinicAudio


def _localized_resources() -> LocalizedResources:
    """Resolve the profile language from this package's declared locales."""
    return activity_resources(Path(__file__).resolve().parent)


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
