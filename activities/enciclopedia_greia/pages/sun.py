"""Sun entry: star/plasma, scale, fusion and differential rotation."""

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
class SunDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    SunDiscovery("plasma", "sun.plasma", "encyclopedia.space.sun.plasma", (250, 190)),
    SunDiscovery("scale", "sun.scale", "encyclopedia.space.sun.scale", (755, 190)),
    SunDiscovery("fusion", "sun.fusion", "encyclopedia.space.sun.fusion", (250, 420)),
    SunDiscovery("rotation", "sun.rotation", "encyclopedia.space.sun.rotation", (755, 420)),
)


class SunPage(EncyclopediaPage):
    page_id = "space.sun"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "sun.intro"
        self._plasma_age = 0.0
        self._scale_age = 0.0
        self._fusion_age = 0.0
        self._rotation_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.sun.intro")

    def update(self, dt: float) -> None:
        self._time += dt
        self._plasma_age = max(0.0, self._plasma_age - dt)
        self._scale_age = max(0.0, self._scale_age - dt)
        self._fusion_age = max(0.0, self._fusion_age - dt)
        self._rotation_age = max(0.0, self._rotation_age - dt)

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
        if discovery.discovery_id == "plasma":
            self._plasma_age = 4.0
        elif discovery.discovery_id == "scale":
            self._scale_age = 4.0
        elif discovery.discovery_id == "fusion":
            self._fusion_age = 4.0
        else:
            self._rotation_age = 4.0
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((18, 25, 57))
        for index in range(34):
            x = (index * 97 + 23) % 1000
            y = 80 + (index * 53) % 470
            pygame.draw.circle(surface, (229, 235, 246), (x, y), 1)
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("sun.title"),
            center=(500, 92),
            size=40,
            color=(248, 240, 207),
            role=FontRole.DISPLAY,
        )
        self._draw_sun(surface)
        self._draw_hotspots(surface)
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "leo",
            position=(925, 565),
            height=142,
            variant="surprised",
            fallback_color=(227, 174, 87),
        )

    def _draw_sun(self, surface: pygame.Surface) -> None:
        center = (505, 326)
        radius = 112
        pulse = int(4 * math.sin(self._time * 2.0))
        pygame.draw.circle(surface, (231, 116, 37), center, radius + 13 + pulse, 4)
        pygame.draw.circle(surface, (248, 169, 48), center, radius)
        pygame.draw.circle(surface, (255, 206, 76), center, radius - 22)

        for index in range(12):
            angle = self._time * 0.22 + index * math.tau / 12
            inner = 62 + (index % 3) * 9
            start = (
                center[0] + int(math.cos(angle) * inner),
                center[1] + int(math.sin(angle) * inner),
            )
            end = (
                center[0] + int(math.cos(angle + 0.42) * (inner + 24)),
                center[1] + int(math.sin(angle + 0.42) * (inner + 24)),
            )
            pygame.draw.line(surface, (255, 231, 120), start, end, 4)

        if self._plasma_age > 0:
            pygame.draw.circle(surface, (255, 242, 156), center, radius - 8, 5)
            for index in range(6):
                angle = self._time * 0.8 + index * math.tau / 6
                x = center[0] + int(math.cos(angle) * 83)
                y = center[1] + int(math.sin(angle) * 83)
                pygame.draw.circle(surface, (255, 239, 141), (x, y), 8, 3)

        if self._fusion_age > 0:
            pygame.draw.circle(surface, (255, 249, 205), center, 29)
            for ring in range(4):
                phase = (self._time * 36 + ring * 26) % 94
                pygame.draw.circle(
                    surface,
                    (255, 232, 126),
                    center,
                    32 + int(phase),
                    2,
                )

        if self._rotation_age > 0:
            equator_angle = self._time * 1.45
            polar_angle = self._time * 0.78
            pygame.draw.ellipse(surface, (186, 91, 35), (395, 305, 220, 42), 2)
            pygame.draw.ellipse(surface, (186, 91, 35), (470, 214, 70, 220), 2)
            eq = (
                center[0] + int(math.cos(equator_angle) * 106),
                center[1] + int(math.sin(equator_angle) * 18),
            )
            pole = (
                center[0] + int(math.cos(polar_angle) * 30),
                center[1] + int(math.sin(polar_angle) * 104),
            )
            pygame.draw.circle(surface, (91, 70, 55), eq, 8)
            pygame.draw.circle(surface, (91, 70, 55), pole, 8)

        if self._scale_age > 0:
            earth_center = (630, 368)
            pygame.draw.circle(surface, (73, 146, 214), earth_center, 8)
            pygame.draw.arc(surface, (94, 182, 110), (624, 361, 11, 11), 0.2, 2.8, 3)
            badge = pygame.Rect(614, 391, 72, 38)
            pygame.draw.rect(surface, (250, 244, 218), badge, border_radius=14)
            draw_centered_text(
                surface,
                self.context.typography,
                "≈100×",
                center=badge.center,
                size=19,
                color=(52, 47, 63),
                role=FontRole.CONTROL,
            )

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (250, 244, 218), item.center, 37)
            pygame.draw.circle(surface, (73, 61, 57), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "plasma":
                pygame.draw.circle(surface, (247, 167, 49), (cx, cy), 19)
                pygame.draw.arc(surface, (230, 102, 36), (cx - 22, cy - 15, 44, 30), 0.2, 2.9, 4)
            elif item.discovery_id == "scale":
                pygame.draw.circle(surface, (247, 167, 49), (cx - 11, cy), 18)
                pygame.draw.circle(surface, (73, 146, 214), (cx + 21, cy + 7), 6)
            elif item.discovery_id == "fusion":
                pygame.draw.circle(surface, (255, 218, 81), (cx, cy), 19)
                pygame.draw.circle(surface, (255, 247, 194), (cx, cy), 8)
            else:
                pygame.draw.arc(surface, (231, 127, 45), (cx - 23, cy - 23, 46, 46), 0.2, 5.0, 5)
                pygame.draw.circle(surface, (73, 61, 57), (cx + 19, cy - 10), 4)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (250, 244, 218), panel, border_radius=22)
        pygame.draw.rect(surface, (73, 61, 57), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (55, 49, 59))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (55, 49, 59))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
