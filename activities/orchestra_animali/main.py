"""Orchestra Animali (the Animal Band) — thin Greia composition root.

Real work lives in :mod:`orchestra_model` (echo rules, stage ladder, saved
progress), :mod:`orchestra_audio` (band sounds, approved cast speech, backing
playback), :mod:`orchestra_playalong` (My Creations backing track),
:mod:`orchestra_art` / :mod:`orchestra_renderer` (presentation),
:mod:`orchestra_controls` (shared control kit) and :mod:`orchestra_app`.

Trusted Home/Back chrome is platform-owned; the Activity draws into the
shared ``PygameReferenceCanvas`` and keeps the platform pointer visible.
"""

from __future__ import annotations

from pathlib import Path
import random
import time

import pygame

from greia_platform.activity_api import get_creations, get_profile_locale
from greia_platform.localization import LocalizationError, LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .orchestra_app import OrchestraApp
    from .orchestra_audio import BandAudio
    from .orchestra_backing import BackingTrackRepository
    from .orchestra_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .orchestra_playalong import PlayAlong
    from .orchestra_services import GreiaOrchestraEvents, GreiaOrchestraProgress
else:  # pragma: no cover - runtime/script fallback
    from orchestra_app import OrchestraApp
    from orchestra_audio import BandAudio
    from orchestra_backing import BackingTrackRepository
    from orchestra_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from orchestra_playalong import PlayAlong
    from orchestra_services import GreiaOrchestraEvents, GreiaOrchestraProgress

PACKAGE_ROOT = Path(__file__).resolve().parent


def _resources() -> LocalizedResources | None:
    try:
        return activity_resources(PACKAGE_ROOT, requested_locale=get_profile_locale())
    except (LocalizationError, OSError):
        return None


def build_app(screen: pygame.Surface, *, clock=time.monotonic) -> OrchestraApp:
    """Compose the Activity from Greia services (also used by tools/tests)."""

    resources = _resources()
    locale = resources.context.selected.language if resources is not None else "en"
    progress = GreiaOrchestraProgress.from_platform()
    try:
        creations = get_creations()
    except RuntimeError:
        creations = None
    storage = progress.storage
    playalong = PlayAlong(
        creations=creations,
        store=BackingTrackRepository(storage) if storage is not None else None,
    )
    rng = random.Random()
    return OrchestraApp(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        typography=GreiaTypography(),
        resources=resources,
        audio=BandAudio(locale=locale, rng=rng),
        progress=progress,
        events=GreiaOrchestraEvents(),
        playalong=playalong,
        rng=rng,
        session_id=f"{int(time.time())}-{rng.randrange(1_000_000):06d}",
        clock=clock,
    )


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)
    app = build_app(screen)
    try:
        return app.run()
    finally:
        try:
            if pygame.get_init():
                pygame.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
