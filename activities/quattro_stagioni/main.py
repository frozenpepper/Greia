"""Thin Greia composition root for Il Grande Albero delle Stagioni."""

from __future__ import annotations

from pathlib import Path

import pygame

from greia_platform.localization import activity_resources

if __package__:
    from .tree_app import TreeActivity
    from .tree_audio import TreeAudio
    from .tree_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, TreeModel
    from .tree_renderer import TreeRenderer
else:
    from tree_app import TreeActivity
    from tree_audio import TreeAudio
    from tree_model import REFERENCE_HEIGHT, REFERENCE_WIDTH, TreeModel
    from tree_renderer import TreeRenderer


def main() -> int:
    pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.RESIZABLE)
    pygame.mouse.set_visible(True)

    package_root = Path(__file__).resolve().parent
    resources = activity_resources(package_root)
    locale = resources.context.selected.language
    pygame.display.set_caption(resources.text("activity.title"))

    model = TreeModel()
    audio = TreeAudio(package_root, locale=locale, resources=resources)
    renderer = TreeRenderer(resources=resources)

    app = TreeActivity(
        screen=screen,
        renderer=renderer,
        audio=audio,
        model=model,
    )
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
