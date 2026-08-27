"""Gears final-entry pilot: meshing, direction, ratio and rack motion."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from .common import draw_centered_text, draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class GearDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


@dataclass(frozen=True, slots=True)
class GearSpec:
    center: tuple[int, int]
    teeth: int
    radius: int
    color: tuple[int, int, int]


DISCOVERIES = (
    GearDiscovery("teeth", "gears.teeth", "encyclopedia.machines.gears.teeth", (255, 190)),
    GearDiscovery("direction", "gears.direction", "encyclopedia.machines.gears.direction", (755, 190)),
    GearDiscovery("ratio", "gears.ratio", "encyclopedia.machines.gears.ratio", (255, 420)),
    GearDiscovery("rack", "gears.rack", "encyclopedia.machines.gears.rack", (755, 420)),
)

# Radii, center distances and tooth counts deliberately share one coherent
# schematic pitch: adjacent pitch circles touch and larger gears have more teeth.
GEARS = (
    GearSpec((395, 330), 28, 74, (83, 145, 181)),
    GearSpec((521, 330), 20, 52, (231, 157, 71)),
    GearSpec((611, 330), 14, 38, (119, 177, 102)),
)
_PINION = GearSpec((680, 330), 12, 31, (155, 117, 183))
_RACK_BASE_X = 645
_RACK_Y = 369


class GearTrainModel:
    """Own idealized gear relationships; rendering consumes derived motion."""

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

    def angles(self) -> tuple[float, float, float]:
        first = self.driver_angle
        second = -first * GEARS[0].teeth / GEARS[1].teeth
        third = -second * GEARS[1].teeth / GEARS[2].teeth
        return first, second, third

    @property
    def pinion_angle(self) -> float:
        third = self.angles()[2]
        return -third * GEARS[2].teeth / _PINION.teeth

    @property
    def rack_offset(self) -> int:
        # Bounded oscillation makes rotary-to-linear conversion visible without
        # allowing the teaching rack to wander off-screen.
        return int(math.sin(self.pinion_angle) * 34)

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
            pygame.Rect(cx - 43, cy - 43, 86, 86)
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
            return
        self._selected = grid_step(
            self._selected,
            event.command,
            columns=2,
            count=len(DISCOVERIES),
        )

    def _activate(self, index: int) -> None:
        discovery = DISCOVERIES[index]
        self._caption_key = discovery.caption_key
        if discovery.discovery_id == "teeth":
            self._model.show_teeth()
        elif discovery.discovery_id == "direction":
            self._model.reverse()
        elif discovery.discovery_id == "ratio":
            self._model.show_ratio()
        else:
            self._model.show_rack()
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((239, 231, 205))
        pygame.draw.rect(surface, (175, 125, 78), (0, 470, 1024, 130))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("gears.title"),
            center=(500, 92),
            size=40,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )
        self._draw_train(surface)
        self._draw_hotspots(surface)
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "dani",
            position=(925, 565),
            height=142,
            variant="happy",
            fallback_color=(101, 171, 211),
        )

    def _draw_train(self, surface: pygame.Surface) -> None:
        angles = self._model.angles()
        for spec, angle in zip(GEARS, angles):
            self._draw_gear(surface, spec, angle)
        self._draw_gear(surface, _PINION, self._model.pinion_angle)

        if self._model.teeth_age > 0:
            for point in ((469, 330), (573, 330), (649, 330)):
                pygame.draw.circle(surface, (255, 233, 102), point, 15, 5)

        if self._model.direction_age > 0:
            for spec, angle in (*tuple(zip(GEARS, angles)), (_PINION, self._model.pinion_angle)):
                self._draw_direction_arrow(
                    surface,
                    spec.center,
                    spec.radius + 14,
                    angle,
                    self._model.direction,
                )

        if self._model.ratio_age > 0:
            speeds = (
                abs(self._model.speed),
                abs(self._model.speed * GEARS[0].teeth / GEARS[1].teeth),
                abs(self._model.speed * GEARS[0].teeth / GEARS[2].teeth),
            )
            maximum = max(speeds)
            for spec, speed in zip(GEARS, speeds):
                bars = max(1, int(round(4 * speed / maximum)))
                for index in range(bars):
                    x = spec.center[0] - 25 + index * 16
                    pygame.draw.rect(
                        surface,
                        (246, 202, 72),
                        (x, spec.center[1] - spec.radius - 30, 10, 18),
                        border_radius=4,
                    )

        rack_x = _RACK_BASE_X + (
            self._model.rack_offset if self._model.rack_age > 0 else 0
        )
        pygame.draw.rect(
            surface,
            (102, 84, 67),
            (rack_x, _RACK_Y, 135, 15),
            border_radius=4,
        )
        for index in range(10):
            pygame.draw.rect(
                surface,
                (102, 84, 67),
                (rack_x + index * 14, _RACK_Y - 8, 8, 10),
            )
        if self._model.rack_age > 0:
            arrow_y = _RACK_Y + 28
            pygame.draw.line(
                surface,
                (246, 202, 72),
                (rack_x - 25, arrow_y),
                (rack_x + 155, arrow_y),
                5,
            )
            positive = self._model.rack_offset >= 0
            tip_x = rack_x + 155 if positive else rack_x - 25
            sign = 1 if positive else -1
            pygame.draw.polygon(
                surface,
                (246, 202, 72),
                [
                    (tip_x, arrow_y),
                    (tip_x - 14 * sign, arrow_y - 10),
                    (tip_x - 14 * sign, arrow_y + 10),
                ],
            )

    @staticmethod
    def _draw_gear(surface: pygame.Surface, spec: GearSpec, angle: float) -> None:
        cx, cy = spec.center
        points: list[tuple[int, int]] = []
        tooth_depth = max(8, spec.radius // 6)
        for index in range(spec.teeth * 2):
            theta = angle + index * math.pi / spec.teeth
            radius = spec.radius if index % 2 == 0 else spec.radius - tooth_depth
            points.append(
                (
                    cx + int(math.cos(theta) * radius),
                    cy + int(math.sin(theta) * radius),
                )
            )
        pygame.draw.polygon(surface, spec.color, points)
        hub = max(10, spec.radius // 3)
        pygame.draw.circle(surface, (239, 231, 205), spec.center, hub)
        pygame.draw.circle(surface, (91, 80, 66), spec.center, hub, 4)

    @staticmethod
    def _draw_direction_arrow(
        surface: pygame.Surface,
        center: tuple[int, int],
        radius: int,
        angle: float,
        direction: float,
    ) -> None:
        cx, cy = center
        start = angle
        end = angle + direction * 1.6
        rect = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2)
        if direction > 0:
            pygame.draw.arc(surface, (245, 211, 79), rect, start, end, 5)
        else:
            pygame.draw.arc(surface, (245, 211, 79), rect, end, start, 5)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (255, 249, 229), item.center, 37)
            pygame.draw.circle(surface, (78, 65, 56), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "teeth":
                for offset in (-15, 0, 15):
                    pygame.draw.rect(
                        surface,
                        (83, 145, 181),
                        (cx + offset - 6, cy - 20, 12, 40),
                        border_radius=3,
                    )
            elif item.discovery_id == "direction":
                pygame.draw.arc(
                    surface,
                    (231, 157, 71),
                    (cx - 23, cy - 23, 46, 46),
                    0.2,
                    math.pi * 1.6,
                    6,
                )
                pygame.draw.polygon(
                    surface,
                    (231, 157, 71),
                    [(cx - 18, cy - 13), (cx - 27, cy - 2), (cx - 11, cy - 2)],
                )
            elif item.discovery_id == "ratio":
                pygame.draw.circle(surface, (83, 145, 181), (cx - 13, cy), 18)
                pygame.draw.circle(surface, (231, 157, 71), (cx + 19, cy), 10)
            else:
                pygame.draw.circle(surface, (155, 117, 183), (cx - 11, cy - 6), 13, 5)
                pygame.draw.rect(surface, (102, 84, 67), (cx, cy + 4, 27, 8))
                for offset in range(0, 26, 8):
                    pygame.draw.rect(
                        surface,
                        (102, 84, 67),
                        (cx + offset, cy - 2, 5, 8),
                    )
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (255, 249, 229), panel, border_radius=22)
        pygame.draw.rect(surface, (78, 65, 56), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(
            text,
            FontRole.BODY,
            18,
            (58, 50, 45),
        )
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(
                text,
                FontRole.BODY,
                15,
                (58, 50, 45),
            )
        surface.blit(rendered, rendered.get_rect(center=panel.center))
