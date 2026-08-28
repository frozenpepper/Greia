"""Home golden master: one illustrated discovery book with six spatial portals."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import draw_authored_scene, draw_focus_patch, draw_title
    from .common import draw_presenter, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import draw_authored_scene, draw_focus_patch, draw_title
    from pages.common import draw_presenter, grid_step


@dataclass(frozen=True, slots=True)
class Portal:
    page_id: str
    label_key: str
    rect: pygame.Rect


PORTAL_IDS = ("animals", "space", "earth", "body", "machines", "history")
PORTAL_LABEL_KEYS = (
    "section.animals",
    "section.space",
    "section.earth",
    "section.body",
    "section.machines",
    "section.history",
)
# These centers are also authored into the SVG master as data-center metadata.
# Keeping the semantic geometry explicit prevents illustrated portals from
# drifting away from the regions a child can actually activate.
PORTAL_CENTERS = (
    (192, 225),
    (437, 225),
    (682, 225),
    (192, 415),
    (437, 415),
    (682, 415),
)
_PORTAL_SIZE = (176, 140)


def _portal_rect(center: tuple[int, int]) -> pygame.Rect:
    rect = pygame.Rect(0, 0, *_PORTAL_SIZE)
    rect.center = center
    return rect


PORTALS = tuple(
    Portal(page_id, label_key, _portal_rect(center))
    for page_id, label_key, center in zip(PORTAL_IDS, PORTAL_LABEL_KEYS, PORTAL_CENTERS)
)


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
        self._selected = grid_step(
            self._selected,
            event.command,
            columns=3,
            count=len(PORTALS),
        )

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
