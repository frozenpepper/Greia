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

try:
    from orca_app import OrcaBayActivity
    from orca_audio import PygameOrcaAudio
    from orca_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, OrcaPod
    from orca_renderer import OrcaRenderer
    from orca_services import GreiaOrcaEvents, GreiaOrcaProgress
except ImportError:
    from .orca_app import OrcaBayActivity
    from .orca_audio import PygameOrcaAudio
    from .orca_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, OrcaPod
    from .orca_renderer import OrcaRenderer
    from .orca_services import GreiaOrcaEvents, GreiaOrcaProgress


def _localized_resources() -> LocalizedResources:
    support = ActivityLocaleSupport.localized(
        ("it", "en"),
        default_ui_locale="it",
    )
    context = resolve_activity_locale(get_profile_locale(), support)
    assert context is not None
    return LocalizedResources(Path(__file__).resolve().parent, context)


def main() -> int:
    """Thin composition root setting up services, adapters, and launching the Activity."""
    pygame.init()
    try:
        screen = pygame.display.get_surface()
        if screen is None:
            screen = pygame.display.set_mode(
                (REFERENCE_WIDTH, REFERENCE_HEIGHT),
                pygame.RESIZABLE,
            )
        pygame.mouse.set_visible(False)

        progress = GreiaOrcaProgress()
        pod = OrcaPod()
        pod.restore_progress(progress.load_progress())

        resources = _localized_resources()
        renderer = OrcaRenderer(GreiaTypography(), resources)
        app = OrcaBayActivity(
            screen=screen,
            canvas=PygameReferenceCanvas(screen),
            pod=pod,
            renderer=renderer,
            audio=PygameOrcaAudio(),
            progress=progress,
            events=GreiaOrcaEvents(),
        )
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
