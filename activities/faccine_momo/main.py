"""Thin Greia composition root for Momo's Happy Faces (Le Faccine di Momo)."""

from __future__ import annotations

from pathlib import Path
import random
import time

import pygame

from greia_platform.localization import activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .momo_app import MomoActivity
    from .momo_audio import MomoAudio
    from .momo_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .momo_services import GreiaMomoEvents, GreiaMomoProgress
else:
    from momo_app import MomoActivity
    from momo_audio import MomoAudio
    from momo_content import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from momo_services import GreiaMomoEvents, GreiaMomoProgress


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    package_root = Path(__file__).resolve().parent
    resources = activity_resources(package_root)
    pygame.display.set_caption(resources.text("activity.title"))
    rng = random.Random()
    app = MomoActivity(
        screen=screen,
        canvas=PygameReferenceCanvas(screen),
        typography=GreiaTypography(),
        resources=resources,
        audio=MomoAudio(
            package_root,
            locale=resources.context.selected.language,
            resources=resources,
            rng=rng,
        ),
        progress=GreiaMomoProgress(),
        events=GreiaMomoEvents(),
        rng=rng,
        session_id=f"{int(time.time())}-{rng.randrange(1_000_000):06d}",
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
