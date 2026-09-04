"""Animals golden master: six selectable subjects inside one illustrated habitat world."""

from __future__ import annotations

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        ambient_sway,
        announce_focus_name,
        encyclopedia_focus_cue,
        draw_authored_scene,
        draw_discover_button,
        draw_focus_patch,
        draw_navigation_arrows,
        draw_title,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_presenter, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        ambient_sway,
        announce_focus_name,
        encyclopedia_focus_cue,
        draw_authored_scene,
        draw_discover_button,
        draw_focus_patch,
        draw_navigation_arrows,
        draw_title,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
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

# Centers are mirrored in the authored SVG as data-target/data-center metadata.
# One geometry therefore owns pointer focus, controller topology, and the
# illustrated subject location instead of letting those drift independently.
ANIMAL_CENTERS = (
    (190, 260),
    (430, 260),
    (670, 260),
    (190, 410),
    (430, 410),
    (670, 410),
)
_TARGET_RECTS = tuple(
    pygame.Rect(center[0] - 95, center[1] - 60, 190, 120)
    for center in ANIMAL_CENTERS
)


class AnimalsPage(EncyclopediaPage):
    page_id = "animals"

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
        self.context.audio.play("encyclopedia.animals.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        name, _ = ANIMALS[self._selected]
        self._focus_audio.announce_once(self.context.audio, encyclopedia_focus_cue("animals", name, "name"))

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(ANIMALS) - 1, index))
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def update(self, dt: float) -> None:
        self._time += dt

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            if event.kind is PageInputKind.POINTER_PRESS:
                if self._discover_hit.collidepoint(point):
                    self._open_entry(self._selected)
                    return
                if self._arrow_left_hit.collidepoint(point):
                    # Move left within grid
                    prev = self._selected
                    self._set_selected(max(0, self._selected - 1))
                    if self._selected != prev:
                        pass
                    return
                if self._arrow_right_hit.collidepoint(point):
                    self._set_selected(min(len(ANIMALS) - 1, self._selected + 1))
                    return
            hit = next(
                (index for index, rect in enumerate(_TARGET_RECTS) if rect.collidepoint(point)),
                None,
            )
            if event.kind is PageInputKind.POINTER_MOVE and hit is not None and hit != self._selected:
                name, _ = ANIMALS[hit]
                self._focus_audio.announce_once(self.context.audio, encyclopedia_focus_cue("animals", name, "name"))
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._open_entry(hit)
            return
        if event.kind is PageInputKind.COMMAND and event.command:
            if event.command is PageCommand.ACTIVATE:
                self._open_entry(self._selected)
                return
            prev = self._selected
            self._selected = grid_step(
                self._selected,
                event.command,
                columns=3,
                count=len(ANIMALS),
            )
            if self._selected != prev:
                self._announce_selected()

    def _open_entry(self, index: int) -> None:
        page_id = IMPLEMENTED_ENTRY_IDS.get(ANIMALS[index][0])
        if page_id is not None:
            self.context.host.open_page(page_id)

    def draw(self, surface: pygame.Surface) -> None:
        authored = draw_authored_scene(
            surface,
            self.context.visuals,
            "encyclopedia.animals.field_table",
        )
        if not authored:
            surface.fill((207, 232, 221))
        else:
            # Ambient: very gentle grass sway at bottom edge — low-cost, non-obscuring
            for gx, phase in ((140, 0.2), (360, 1.1), (580, 0.7), (800, 1.8)):
                sway = ambient_sway(self._time, phase=phase, amplitude=3)
                pygame.draw.line(
                    surface,
                    (135, 165, 110),
                    (gx + sway, 515),
                    (gx + sway // 2, 495),
                    3,
                )
                pygame.draw.circle(surface, (145, 175, 120), (gx + sway // 2, 492), 5)
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
                time=self._time,
            )
        # Standard navigation chrome — same grammar across encyclopedia pages.
        can_left = self._selected % 3 != 0 or self._selected > 0
        can_right = self._selected % 3 != 2 and self._selected < len(ANIMALS) - 1
        # For grid, allow linear left/right navigation consistently
        can_left = self._selected > 0
        can_right = self._selected < len(ANIMALS) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        self._discover_hit = draw_discover_button(
            surface, active=True, time=self._time, enabled=True
        )
        sway = ambient_sway(self._time, phase=0.4, amplitude=2)
        draw_presenter(
            surface,
            self.context.visuals,
            "tito",
            position=(905 + sway, 560),
            height=170,
            variant="happy",
            fallback_color=(247, 151, 77),
        )
