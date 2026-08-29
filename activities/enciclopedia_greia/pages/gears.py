"""Gears golden master: authored workshop board with semantic mechanism overlays."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        TOKEN_SHAPE_WORKSHOP_TAG,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_title,
    )
    from .common import draw_presenter, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        TOKEN_SHAPE_WORKSHOP_TAG,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_title,
    )
    from pages.common import draw_presenter, grid_step


@dataclass(frozen=True, slots=True)
class GearDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    GearDiscovery("teeth", "gears.teeth", "encyclopedia.machines.gears.teeth", (235, 195)),
    GearDiscovery(
        "direction",
        "gears.direction",
        "encyclopedia.machines.gears.direction",
        (775, 195),
    ),
    GearDiscovery("ratio", "gears.ratio", "encyclopedia.machines.gears.ratio", (235, 405)),
    GearDiscovery("rack", "gears.rack", "encyclopedia.machines.gears.rack", (775, 405)),
)


class GearTrainModel:
    """Own the finite interaction state shown over the authored mechanism board."""

    def __init__(self) -> None:
        self.driver_angle = 0.0
        self.direction = 1.0
        self.speed = 0.85
        self.teeth_age = 0.0
        self.direction_age = 0.0
        self.ratio_age = 0.0
        self.rack_age = 0.0

    def update(self, dt: float) -> None:
        self.driver_angle += dt * self.speed * self.direction
        self.teeth_age = max(0.0, self.teeth_age - dt)
        self.direction_age = max(0.0, self.direction_age - dt)
        self.ratio_age = max(0.0, self.ratio_age - dt)
        self.rack_age = max(0.0, self.rack_age - dt)

    def show_teeth(self) -> None:
        self.teeth_age = 3.2

    def reverse(self) -> None:
        self.direction *= -1.0
        self.direction_age = 3.2

    def show_ratio(self) -> None:
        self.ratio_age = 4.0

    def show_rack(self) -> None:
        self.rack_age = 4.0


class GearsPage(EncyclopediaPage):
    page_id = "machines.gears"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._model = GearTrainModel()
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "gears.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 50, cy - 50, 100, 100)
            for cx, cy in (item.center for item in DISCOVERIES)
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.machines.gears.intro")

    def update(self, dt: float) -> None:
        self._model.update(dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            hit = next(
                (index for index, rect in enumerate(self._hotspots) if rect.collidepoint(point)),
                None,
            )
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._selected = hit
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            self._activate(self._selected)
        else:
            self._selected = grid_step(
                self._selected,
                event.command,
                columns=2,
                count=len(DISCOVERIES),
            )

    def _activate(self, index: int) -> None:
        item = DISCOVERIES[index]
        self._caption_key = item.caption_key
        if item.discovery_id == "teeth":
            self._model.show_teeth()
        elif item.discovery_id == "direction":
            self._model.reverse()
        elif item.discovery_id == "ratio":
            self._model.show_ratio()
        else:
            self._model.show_rack()
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        if not draw_authored_scene(
            surface,
            self.context.visuals,
            "encyclopedia.machines.gears.workbench",
        ):
            surface.fill((239, 231, 205))
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("gears.title"),
            self.context.palette.ink,
        )
        self._draw_reveals(surface)
        for index, item in enumerate(DISCOVERIES):
            draw_discovery_token(
                surface,
                item.center,
                selected=index == self._selected,
                hovered=index == self._hovered,
                recently_activated=self._recent(item.discovery_id),
                icon=lambda target, center, item=item: self._draw_icon(
                    target,
                    center,
                    item.discovery_id,
                ),
                token_shape=TOKEN_SHAPE_WORKSHOP_TAG,
            )
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
        )
        draw_presenter(
            surface,
            self.context.visuals,
            "dani",
            position=(880, 575),
            height=190,
            variant="happy",
            fallback_color=(101, 171, 211),
        )

    def _recent(self, discovery_id: str) -> bool:
        ages = {
            "teeth": self._model.teeth_age,
            "direction": self._model.direction_age,
            "ratio": self._model.ratio_age,
            "rack": self._model.rack_age,
        }
        return ages[discovery_id] > 0

    def _draw_reveals(self, surface: pygame.Surface) -> None:
        if self._model.teeth_age > 0:
            # The authored train has exactly two mesh boundaries. Keep the
            # teaching highlight tied to those real tooth-contact points.
            contact_points = ((450, 318), (550, 318))
            for point in contact_points:
                pygame.draw.circle(surface, (255, 228, 91), point, 20, 6)
                pygame.draw.circle(surface, (255, 170, 60), point, 8, 3)
            for index, point in enumerate(contact_points):
                ax, ay = point
                ax -= 6
                ay -= 28
                if index % 2 == 0:
                    ax2, ay2 = ax + 12, ay
                else:
                    ax2, ay2 = ax - 12, ay
                pygame.draw.line(surface, (255, 170, 60), (ax, ay), (ax2, ay2), 4)
                if index % 2 == 0:
                    pygame.draw.polygon(
                        surface,
                        (255, 170, 60),
                        [(ax2, ay2), (ax2 - 7, ay2 - 5), (ax2 - 7, ay2 + 5)],
                    )
                else:
                    pygame.draw.polygon(
                        surface,
                        (255, 170, 60),
                        [(ax2, ay2), (ax2 + 7, ay2 - 5), (ax2 + 7, ay2 + 5)],
                    )

        if self._model.direction_age > 0:
            specs = (
                ((385, 318), 72, self._model.direction),
                ((500, 318), 58, -self._model.direction),
                ((592, 318), 47, self._model.direction),
            )
            for center, radius, _direction in specs:
                rect = pygame.Rect(
                    center[0] - radius,
                    center[1] - radius,
                    radius * 2,
                    radius * 2,
                )
                pygame.draw.arc(surface, (255, 221, 89), rect, 0.3, 1.9, 5)

        if self._model.ratio_age > 0:
            for x, count in ((385, 2), (500, 3), (592, 4)):
                for index in range(count):
                    pygame.draw.rect(
                        surface,
                        (255, 218, 80),
                        (x - 30 + index * 18, 205, 11, 20),
                        border_radius=4,
                    )

        if self._model.rack_age > 0:
            offset = int(math.sin(self._model.driver_angle * 2.2) * 28)
            pygame.draw.line(
                surface,
                (255, 220, 86),
                (690 + offset, 410),
                (815 + offset, 410),
                6,
            )
            pygame.draw.polygon(
                surface,
                (255, 220, 86),
                [
                    (815 + offset, 410),
                    (799 + offset, 399),
                    (799 + offset, 421),
                ],
            )

    @staticmethod
    def _draw_icon(
        surface: pygame.Surface,
        center: tuple[int, int],
        discovery_id: str,
    ) -> None:
        cx, cy = center
        if discovery_id == "teeth":
            for offset in (-15, 0, 15):
                pygame.draw.rect(
                    surface,
                    (83, 145, 181),
                    (cx + offset - 6, cy - 20, 12, 40),
                    border_radius=3,
                )
        elif discovery_id == "direction":
            pygame.draw.arc(
                surface,
                (231, 157, 71),
                (cx - 23, cy - 23, 46, 46),
                0.2,
                math.pi * 1.6,
                6,
            )
        elif discovery_id == "ratio":
            pygame.draw.circle(surface, (83, 145, 181), (cx - 13, cy), 18)
            pygame.draw.circle(surface, (231, 157, 71), (cx + 19, cy), 10)
        else:
            pygame.draw.circle(surface, (155, 117, 183), (cx - 11, cy - 6), 13, 5)
            pygame.draw.rect(surface, (102, 84, 67), (cx, cy + 4, 27, 8))
