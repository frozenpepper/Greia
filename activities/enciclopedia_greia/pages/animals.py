"""Animals section golden master: an illustrated field table, not six cards."""

from __future__ import annotations

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import draw_authored_scene, draw_focus_patch, draw_title
    from .common import draw_presenter, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import draw_authored_scene, draw_focus_patch, draw_title
    from pages.common import draw_presenter, grid_step


ANIMALS = (
    ("lion", "animal.lion"),
    ("elephant", "animal.elephant"),
    ("octopus", "animal.octopus"),
    ("bee", "animal.bee"),
    ("penguin", "animal.penguin"),
    ("frog", "animal.frog"),
)

IMPLEMENTED_ENTRY_IDS = {
    "lion": "animals.lion",
    "elephant": "animals.elephant",
    "octopus": "animals.octopus",
    "bee": "animals.bee",
    "penguin": "animals.penguin",
    "frog": "animals.frog",
}

_TARGET_RECTS = (
    pygame.Rect(120, 202, 190, 112),
    pygame.Rect(355, 196, 190, 118),
    pygame.Rect(585, 195, 200, 120),
    pygame.Rect(155, 330, 200, 110),
    pygame.Rect(392, 330, 190, 110),
    pygame.Rect(625, 330, 200, 110),
)


class AnimalsPage(EncyclopediaPage):
    page_id = "animals"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._selected = 0
        self._hovered: int | None = None

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.animals.intro")

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            hit = next(
                (index for index, rect in enumerate(_TARGET_RECTS) if rect.collidepoint(point)),
                None,
            )
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._selected = hit
                self._open_entry(hit)
            return
        if event.kind is PageInputKind.COMMAND and event.command:
            if event.command is PageCommand.ACTIVATE:
                self._open_entry(self._selected)
                return
            self._selected = grid_step(
                self._selected,
                event.command,
                columns=3,
                count=len(ANIMALS),
            )

    def _open_entry(self, index: int) -> None:
        page_id = IMPLEMENTED_ENTRY_IDS.get(ANIMALS[index][0])
        if page_id is not None:
            self.context.host.open_page(page_id)

    def draw(self, surface: pygame.Surface) -> None:
        if not draw_authored_scene(
            surface,
            self.context.visuals,
            "encyclopedia.animals.field_table",
        ):
            surface.fill((207, 232, 221))
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("section.animals"),
            self.context.palette.ink,
        )
        for index, rect in enumerate(_TARGET_RECTS):
            draw_focus_patch(
                surface,
                rect,
                active=index == self._selected or index == self._hovered,
                radius=24,
            )
        draw_presenter(
            surface,
            self.context.visuals,
            "tito",
            position=(920, 575),
            height=190,
            variant="happy",
            fallback_color=(247, 151, 77),
        )
