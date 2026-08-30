"""Science & Machines section: five semantic objects on an authored workbench."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        announce_focus_name,
        encyclopedia_focus_cue,
        draw_authored_scene,
        draw_discover_button,
        draw_focus_patch,
        draw_navigation_arrows,
        draw_title,
    )
    from .common import draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        announce_focus_name,
        encyclopedia_focus_cue,
        draw_authored_scene,
        draw_discover_button,
        draw_focus_patch,
        draw_navigation_arrows,
        draw_title,
    )
    from pages.common import draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class MachineTarget:
    target_id: str
    page_id: str
    center: tuple[int, int]
    size: tuple[int, int]


# E3 replaces tiny icon bubbles with real workshop objects. Pointer/focus bounds
# therefore follow the visible object footprints while the semantic centers
# remain exactly aligned with SVG data-target/data-center metadata.
MACHINE_TARGETS = (
    MachineTarget("gears", "machines.gears", (225, 220), (190, 120)),
    MachineTarget("magnet", "machines.magnet", (500, 190), (160, 130)),
    MachineTarget("bicycle", "machines.bicycle", (775, 220), (190, 130)),
    MachineTarget("airplane", "machines.airplane", (335, 415), (180, 120)),
    MachineTarget("bridge", "machines.bridge", (665, 415), (190, 140)),
)


class MachinesPage(EncyclopediaPage):
    page_id = "machines"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._target_rects = tuple(
            pygame.Rect(
                target.center[0] - target.size[0] // 2,
                target.center[1] - target.size[1] // 2,
                target.size[0],
                target.size[1],
            )
            for target in MACHINE_TARGETS
        )
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._discover_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.machines.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        target = MACHINE_TARGETS[self._selected]
        announce_focus_name(self.context.audio, encyclopedia_focus_cue("machines", target.target_id, "name"))

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(MACHINE_TARGETS) - 1, index))
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
                    self._open_selected()
                    return
                if self._arrow_left_hit.collidepoint(point):
                    self._set_selected(self._selected - 1)
                    return
                if self._arrow_right_hit.collidepoint(point):
                    self._set_selected(self._selected + 1)
                    return
            hit = next(
                (i for i, rect in enumerate(self._target_rects) if rect.collidepoint(point)),
                None,
            )
            if event.kind is PageInputKind.POINTER_MOVE and hit is not None and hit != self._selected:
                announce_focus_name(
                    self.context.audio, encyclopedia_focus_cue("machines", MACHINE_TARGETS[hit].target_id, "name")
                )
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._open_selected()
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            self._open_selected()
        else:
            prev = self._selected
            self._selected = grid_step(
                self._selected,
                event.command,
                columns=3,
                count=len(MACHINE_TARGETS),
            )
            if self._selected != prev:
                self._announce_selected()

    def _open_selected(self) -> None:
        self.context.host.open_page(MACHINE_TARGETS[self._selected].page_id)

    def draw(self, surface: pygame.Surface) -> None:
        authored = draw_authored_scene(
            surface,
            self.context.visuals,
            "encyclopedia.machines.gallery.workbench",
        )
        if not authored:
            self._draw_fallback_scene(surface)

        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("section.machines"),
            (245, 235, 208) if authored else self.context.palette.ink,
        )
        for index, rect in enumerate(self._target_rects):
            active = index == self._selected or index == self._hovered
            if authored:
                draw_focus_patch(surface, rect, active=active, radius=16, time=self._time)
            else:
                focus_ring(surface, rect, active)
        can_left = self._selected > 0
        can_right = self._selected < len(MACHINE_TARGETS) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        self._discover_hit = draw_discover_button(
            surface, active=True, time=self._time, enabled=True
        )

        draw_presenter(
            surface,
            self.context.visuals,
            "dani",
            position=(910, 565),
            height=150,
            variant="happy",
            fallback_color=(101, 171, 211),
        )

    def _draw_fallback_scene(self, surface: pygame.Surface) -> None:
        """Retain the proven workshop while the authored PNG is absent."""

        surface.fill((239, 231, 205))
        pygame.draw.rect(surface, (178, 125, 77), (0, 455, 1024, 145))
        pygame.draw.rect(surface, (215, 190, 142), (105, 130, 790, 330), border_radius=30)
        pygame.draw.rect(surface, (112, 82, 62), (105, 130, 790, 330), 4, border_radius=30)
        self._draw_workshop_hints(surface)
        self._draw_targets(surface)

    def _draw_workshop_hints(self, surface: pygame.Surface) -> None:
        self._gear(surface, (180, 310), 42, 10, self._time, (83, 145, 181))
        self._gear(surface, (250, 310), 29, 8, -self._time * 1.4, (231, 157, 71))

        pygame.draw.rect(surface, (209, 77, 79), (445, 292, 34, 68), border_radius=8)
        pygame.draw.rect(surface, (85, 126, 190), (479, 292, 34, 68), border_radius=8)
        pygame.draw.arc(surface, (103, 128, 181), (424, 272, 110, 109), 0.2, math.pi - 0.2, 2)

        pygame.draw.circle(surface, (75, 77, 77), (700, 320), 50, 5)
        pygame.draw.circle(surface, (75, 77, 77), (810, 320), 50, 5)
        pygame.draw.line(surface, (76, 135, 181), (700, 320), (752, 266), 5)
        pygame.draw.line(surface, (76, 135, 181), (752, 266), (810, 320), 5)
        pygame.draw.line(surface, (76, 135, 181), (700, 320), (770, 320), 5)

        pygame.draw.ellipse(surface, (235, 236, 229), (265, 360, 130, 25))
        pygame.draw.polygon(surface, (204, 212, 211), [(325, 371), (290, 410), (340, 379)])

        pygame.draw.line(surface, (91, 80, 66), (570, 400), (745, 400), 10)
        pygame.draw.line(surface, (91, 80, 66), (590, 400), (630, 345), 7)
        pygame.draw.line(surface, (91, 80, 66), (725, 400), (685, 345), 7)
        pygame.draw.line(surface, (91, 80, 66), (630, 345), (685, 345), 7)

    def _draw_targets(self, surface: pygame.Surface) -> None:
        for index, (target, rect) in enumerate(zip(MACHINE_TARGETS, self._target_rects)):
            pygame.draw.circle(surface, (253, 247, 225), target.center, 37)
            pygame.draw.circle(surface, (91, 80, 66), target.center, 37, 3)
            self._draw_target_icon(surface, target)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    @staticmethod
    def _draw_target_icon(surface: pygame.Surface, target: MachineTarget) -> None:
        cx, cy = target.center
        if target.target_id == "gears":
            pygame.draw.circle(surface, (83, 145, 181), (cx - 13, cy), 18, 5)
            pygame.draw.circle(surface, (231, 157, 71), (cx + 17, cy + 4), 12, 4)
        elif target.target_id == "magnet":
            pygame.draw.rect(surface, (209, 77, 79), (cx - 27, cy - 11, 27, 22), border_radius=5)
            pygame.draw.rect(surface, (85, 126, 190), (cx, cy - 11, 27, 22), border_radius=5)
        elif target.target_id == "bicycle":
            pygame.draw.circle(surface, (72, 74, 75), (cx - 20, cy + 8), 15, 3)
            pygame.draw.circle(surface, (72, 74, 75), (cx + 20, cy + 8), 15, 3)
            pygame.draw.line(surface, (76, 135, 181), (cx - 20, cy + 8), (cx, cy - 15), 4)
            pygame.draw.line(surface, (76, 135, 181), (cx, cy - 15), (cx + 20, cy + 8), 4)
        elif target.target_id == "airplane":
            pygame.draw.ellipse(surface, (220, 224, 221), (cx - 30, cy - 8, 60, 16))
            pygame.draw.polygon(surface, (196, 205, 205), [(cx, cy), (cx - 21, cy + 22), (cx + 9, cy + 4)])
        else:
            pygame.draw.line(surface, (91, 137, 173), (cx - 29, cy + 18), (cx + 29, cy + 18), 5)
            pygame.draw.line(surface, (91, 137, 173), (cx - 24, cy + 17), (cx, cy - 20), 5)
            pygame.draw.line(surface, (91, 137, 173), (cx, cy - 20), (cx + 24, cy + 17), 5)

    @staticmethod
    def _gear(
        surface: pygame.Surface,
        center: tuple[int, int],
        radius: int,
        teeth: int,
        angle: float,
        color: tuple[int, int, int],
    ) -> None:
        cx, cy = center
        points: list[tuple[int, int]] = []
        for index in range(teeth * 2):
            theta = angle + index * math.pi / teeth
            r = radius if index % 2 == 0 else radius - 9
            points.append((cx + int(math.cos(theta) * r), cy + int(math.sin(theta) * r)))
        pygame.draw.polygon(surface, color, points)
        pygame.draw.circle(surface, (239, 231, 205), center, max(8, radius // 3))
