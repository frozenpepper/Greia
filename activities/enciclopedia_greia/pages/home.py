"""Home golden master: one illustrated discovery book with six spatial portals."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        announce_focus_name,
        draw_authored_scene,
        draw_discover_button,
        draw_navigation_arrows,
        draw_portal_focus,
        draw_title,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_presenter, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        announce_focus_name,
        draw_authored_scene,
        draw_discover_button,
        draw_navigation_arrows,
        draw_portal_focus,
        draw_title,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
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
# The 3x2 portal block is centered on the book as one composition; the middle
# column deliberately straddles the book spine instead of treating each page
# as an independent layout surface.
PORTAL_CENTERS = (
    (267, 225),
    (512, 225),
    (757, 225),
    (267, 415),
    (512, 415),
    (757, 415),
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

        self._focus_audio = FocusAudioTracker()
        self._selected = 0
        self._hovered: int | None = None
        self._time = 0.0
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._discover_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.home.welcome")
        self._announce_selected()

    def update(self, dt: float) -> None:
        self._time += dt

    def _announce_selected(self) -> None:
        portal = PORTALS[self._selected]
        cue = encyclopedia_focus_cue("section", portal.page_id, "name")
        self._focus_audio.announce_once(self.context.audio, cue)

    def _set_selected(self, index: int) -> None:
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def handle_input(self, event: PageInput) -> None:
        if event.kind in {PageInputKind.POINTER_MOVE, PageInputKind.POINTER_PRESS} and event.position:
            point = (int(event.position[0]), int(event.position[1]))
            # Big discover + arrows first (larger hit priority)
            if event.kind is PageInputKind.POINTER_PRESS:
                if self._discover_hit.collidepoint(point):
                    self.context.host.open_page(PORTALS[self._selected].page_id)
                    return
                if self._arrow_left_hit.collidepoint(point) and self._selected % 3 != 0:
                    previous = self._selected
                    self._set_selected(max(0, self._selected - 1))
                    if self._selected != previous:
                        pass
                    return
                if self._arrow_right_hit.collidepoint(point) and self._selected % 3 != 2:
                    self._set_selected(min(len(PORTALS) - 1, self._selected + 1))
                    return
            hit = next(
                (index for index, portal in enumerate(PORTALS) if portal.rect.collidepoint(point)),
                None,
            )
            # Announce on hover focus change for pointer move
            if event.kind is PageInputKind.POINTER_MOVE and hit is not None and hit != self._selected:
                # Hover does not change persistent selection, but announce hovered name for discoverability
                portal = PORTALS[hit]
                self._focus_audio.announce_once(
                    self.context.audio, encyclopedia_focus_cue("section", portal.page_id, "name")
                )
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self.context.host.open_page(PORTALS[hit].page_id)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            self.context.host.open_page(PORTALS[self._selected].page_id)
            return
        previous = self._selected
        self._selected = grid_step(
            self._selected,
            event.command,
            columns=3,
            count=len(PORTALS),
        )
        if self._selected != previous:
            self._announce_selected()

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
            draw_portal_focus(
                surface,
                portal.rect,
                active=index == self._selected or index == self._hovered,
                time=self._time,
            )

        # Standard navigation chrome — same grammar across encyclopedia pages.
        can_left = self._selected % 3 != 0
        can_right = self._selected % 3 != 2
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface,
            time=self._time,
            can_go_left=can_left,
            can_go_right=can_right,
        )
        self._discover_hit = draw_discover_button(
            surface,
            active=True,
            time=self._time,
            enabled=True,
        )

        # Subtle ambient shimmer on book + floating motes
        bob = int(round(math.sin(self._time * 2.0) * 4))
        sway = int(round(math.sin(self._time * 0.85) * 2))
        # Floating dust motes for depth
        for mx, my, phase in ((512, 320, 0.2), (620, 280, 1.1), (410, 360, 0.7)):
            mx2 = mx + int(math.sin(self._time * 0.7 + phase) * 6)
            my2 = my + int(math.cos(self._time * 0.9 + phase) * 3)
            pygame.draw.circle(surface, (255, 255, 255, 38), (mx2, my2), 2)
            pygame.draw.circle(surface, (255, 255, 255, 22), (mx2, my2), 4, 1)
        draw_presenter(
            surface,
            self.context.visuals,
            "leo",
            position=(880 + sway, 535 + bob),
            height=190,
            variant="happy",
        )
