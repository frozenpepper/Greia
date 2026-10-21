"""Thin Greia composition root for Il Labirinto Magico (Tito's hedge maze).

``activity.toml`` points here. Real work lives in cohort modules: model (pure
maze rules + adaptive visit), services (storage/events), layout, art,
renderer, controls (shared kit HUD), audio and the app lifecycle.
"""

from __future__ import annotations

from pathlib import Path
import random

import pygame

from greia_platform.activity_api import get_profile_locale
from greia_platform.localization import LocalizedResources, activity_resources
from greia_platform.pygame_canvas import PygameReferenceCanvas
from greia_platform.typography import GreiaTypography

if __package__:
    from .maze_app import LabyrinthActivity
    from .maze_audio import LabyrinthAudio, MazeAudio
    from .maze_layout import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .maze_model import LEVELS, MazeGenerator, MazeLayout, Visit
    from .maze_services import GreiaLabyrinthEvents, GreiaLabyrinthProgress
else:
    from maze_app import LabyrinthActivity
    from maze_audio import LabyrinthAudio, MazeAudio
    from maze_layout import REFERENCE_HEIGHT, REFERENCE_WIDTH
    from maze_model import LEVELS, MazeGenerator, MazeLayout, Visit
    from maze_services import GreiaLabyrinthEvents, GreiaLabyrinthProgress


def _resources() -> LocalizedResources:
    return activity_resources(Path(__file__).resolve().parent, requested_locale=get_profile_locale())


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    resources = _resources()
    rng = random.Random()
    progress = GreiaLabyrinthProgress()
    visit = Visit(MazeGenerator(rng), progress.load())
    app = LabyrinthActivity(
        screen=screen,
        canvas=PygameReferenceCanvas(screen, hires=True),
        visit=visit,
        typography=GreiaTypography(),
        resources=resources,
        audio=LabyrinthAudio(resources.context.selected.language, rng=rng),
        progress=progress,
        events=GreiaLabyrinthEvents(),
    )
    try:
        return app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["LEVELS", "LabyrinthActivity", "LabyrinthAudio", "MazeAudio", "MazeGenerator", "MazeLayout", "Visit", "main"]
