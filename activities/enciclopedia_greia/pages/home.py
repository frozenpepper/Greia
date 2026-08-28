"""Home page golden master: an illustrated discovery book with six portals."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import draw_authored_scene, draw_focus_patch, draw_title
    from .common import draw_presenter
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import draw_authored_scene, draw_focus_patch, draw_title
    from pages.common import draw_presenter


@dataclass(frozen=True, slots=True)
class Portal:
    page_id: str
    label_key: str
    rect: pygame.Rect


PORTALS = (
    Portal("animals", "section.animals", pygame.Rect(126, 178, 158, 140)),
    Portal("space", "section.space", pygame.Rect(582, 178, 158, 142)),
    Portal("earth", "section.earth", pygame.Rect(287, 288, 132, 132)),
    Portal("body", "section.body", pygame.Rect(137, 355, 146, 124)),
    Portal("machines", "section.machines", pygame.Rect(730, 288, 150, 132)),
    Portal("history", "section.history", pygame.Rect(583, 365, 154, 120)),
)

# Visual topology is two book columns with three vertical stops. Keep semantic
# controller navigation spatially honest instead of pretending this is a card grid.
_MOVE = {
    0: {PageCommand.RIGHT: 1, PageCommand.DOWN: 2},
    1: {PageCommand.LEFT: 0, PageCommand.DOWN: 4},
    2: {PageCommand.UP: 0, PageCommand.RIGHT: 4, PageCommand.DOWN: 3},
    3: {PageCommand.UP: 2, PageCommand.RIGHT: 5},
    4: {PageCommand.UP: 1, PageCommand.LEFT: 2, PageCommand.DOWN: 5},
    5: {PageCommand.UP: 4, PageCommand.LEFT: 3},
}


class HomePage(EncyclopediaPage):
    page_id = "home"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._selected = 0
        self._hovered: int | None = None
        self._time = 0.0

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.home.welcome")

    def update(self, dt: float) -> None:
        self._time += dt

    def handle_input(self, event: PageInput) -> None:
        if event.kind in {PageInputKind.POINTER_MOVE, PageInputKind.POINTER_PRESS} and event.position:
            point = (int(event.position[0]), int(event.position[1]))
            hit = next(
                (index for index, portal in enumerate(PORTALS) if portal.rect.collidepoint(point)),
                None,
            )
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._selected = hit
                self.context.host.open_page(PORTALS[hit].page_id)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            self.context.host.open_page(PORTALS[self._selected].page_id)
            return
        self._selected = _MOVE.get(self._selected, {}).get(event.command, self._selected)

    def draw(self, surface: pygame.Surface) -> None:
        if not draw_authored_scene(
            surface,
            self.context.visuals,
            "encyclopedia.home.discovery_book",
        ):
            surface.fill((231, 240, 221))
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("home.title"),
            self.context.palette.ink,
        )
        for index, portal in enumerate(PORTALS):
            draw_focus_patch(
                surface,
                portal.rect,
                active=index == self._selected or index == self._hovered,
                radius=28,
            )

        bob = int(round(math.sin(self._time * 2.0) * 4))
        draw_presenter(
            surface,
            self.context.visuals,
            "leo",
            position=(930, 575 + bob),
            height=185,
            variant="happy",
        )
