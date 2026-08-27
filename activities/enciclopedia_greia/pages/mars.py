"""Mars entry: rusty color, near-Earth day, ancient water, and Olympus Mons."""

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
class MarsDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    MarsDiscovery("red", "mars.red", "encyclopedia.space.mars.red", (250, 190)),
    MarsDiscovery("day", "mars.day", "encyclopedia.space.mars.day", (755, 190)),
    MarsDiscovery("water", "mars.water", "encyclopedia.space.mars.water", (250, 420)),
    MarsDiscovery("olympus", "mars.olympus", "encyclopedia.space.mars.olympus", (755, 420)),
)


class MarsPage(EncyclopediaPage):
    page_id = "space.mars"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "mars.intro"
        self._rust_age = 0.0
        self._day_age = 0.0
        self._water_age = 0.0
        self._olympus_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.mars.intro")

    def update(self, dt: float) -> None:
        self._time += dt
        self._rust_age = max(0.0, self._rust_age - dt)
        self._day_age = max(0.0, self._day_age - dt)
        self._water_age = max(0.0, self._water_age - dt)
        self._olympus_age = max(0.0, self._olympus_age - dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            hit = next(
                (i for i, rect in enumerate(self._hotspots) if rect.collidepoint(point)),
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
            self._selected = grid_step(self._selected, event.command, columns=2, count=len(DISCOVERIES))

    def _activate(self, index: int) -> None:
        discovery = DISCOVERIES[index]
        self._caption_key = discovery.caption_key
        if discovery.discovery_id == "red":
            self._rust_age = 4.0
        elif discovery.discovery_id == "day":
            self._day_age = 4.5
        elif discovery.discovery_id == "water":
            self._water_age = 4.5
        else:
            self._olympus_age = 4.5
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((30, 28, 49))
        for index in range(30):
            x = (index * 97 + 21) % 1000
            y = 76 + (index * 61) % 470
            pygame.draw.circle(surface, (226, 229, 238), (x, y), 1)
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("mars.title"),
            center=(500, 92),
            size=40,
            color=(246, 238, 220),
            role=FontRole.DISPLAY,
        )
        self._draw_mars(surface)
        self._draw_hotspots(surface)
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "leo",
            position=(925, 565),
            height=142,
            variant="default",
            fallback_color=(227, 174, 87),
        )

    def _draw_mars(self, surface: pygame.Surface) -> None:
        center = (505, 326)
        radius = 92
        base = (185, 93, 64) if self._rust_age <= 0 else (211, 104, 65)
        pygame.draw.circle(surface, base, center, radius)
        for dx, dy, rr in ((-38, -28, 16), (27, -42, 11), (43, 18, 18), (-18, 44, 13)):
            pygame.draw.circle(surface, (133, 72, 57), (center[0] + dx, center[1] + dy), rr)
            pygame.draw.circle(surface, (215, 137, 92), (center[0] + dx - 3, center[1] + dy - 3), max(3, rr - 5), 2)
        pygame.draw.arc(surface, (231, 211, 184), (450, 238, 110, 42), 0.1, 3.0, 5)
        pygame.draw.arc(surface, (231, 211, 184), (459, 371, 91, 33), 3.2, 6.0, 4)

        if self._rust_age > 0:
            for i in range(12):
                angle = i * math.tau / 12 + self._time * 0.3
                x = center[0] + int(math.cos(angle) * 72)
                y = center[1] + int(math.sin(angle) * 58)
                pygame.draw.circle(surface, (238, 139, 74), (x, y), 4)

        if self._day_age > 0:
            orbit = pygame.Rect(426, 247, 158, 158)
            pygame.draw.arc(surface, (246, 213, 92), orbit, 0.2, 5.4, 5)
            angle = self._time * 1.4
            marker = (
                center[0] + int(math.cos(angle) * 82),
                center[1] + int(math.sin(angle) * 82),
            )
            pygame.draw.circle(surface, (246, 213, 92), marker, 7)
            draw_centered_text(
                surface,
                self.context.typography,
                "24.6h",
                center=(505, 436),
                size=18,
                color=(244, 230, 194),
                role=FontRole.CONTROL,
            )

        if self._water_age > 0:
            pygame.draw.lines(surface, (84, 161, 203), False, [(450, 292), (476, 311), (465, 338), (493, 362), (523, 387)], 6)
            pygame.draw.ellipse(surface, (75, 142, 188), (520, 370, 72, 29), 4)
            pygame.draw.line(surface, (244, 226, 155), (445, 410), (589, 410), 2)

        if self._olympus_age > 0:
            ground = 444
            pygame.draw.line(surface, (227, 213, 185), (382, ground), (640, ground), 3)
            pygame.draw.polygon(surface, (143, 75, 59), [(410, ground), (490, 278), (570, ground)])
            pygame.draw.polygon(surface, (205, 123, 78), [(465, 331), (490, 278), (515, 331)])
            pygame.draw.circle(surface, (228, 215, 185), (603, ground - 36), 4)
            pygame.draw.line(surface, (228, 215, 185), (603, ground - 32), (603, ground - 10), 3)
            pygame.draw.line(surface, (228, 215, 185), (596, ground - 23), (610, ground - 23), 2)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (249, 244, 226), item.center, 37)
            pygame.draw.circle(surface, (75, 61, 55), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "red":
                pygame.draw.circle(surface, (194, 95, 63), (cx, cy), 20)
                pygame.draw.circle(surface, (235, 139, 74), (cx + 8, cy - 7), 7)
            elif item.discovery_id == "day":
                pygame.draw.circle(surface, (194, 95, 63), (cx, cy), 17)
                pygame.draw.arc(surface, (235, 194, 75), (cx - 25, cy - 25, 50, 50), 0.2, 5.0, 4)
            elif item.discovery_id == "water":
                pygame.draw.lines(surface, (74, 150, 198), False, [(cx - 21, cy - 14), (cx - 8, cy), (cx - 16, cy + 18), (cx + 19, cy + 12)], 5)
            else:
                pygame.draw.polygon(surface, (181, 93, 64), [(cx - 25, cy + 20), (cx, cy - 23), (cx + 25, cy + 20)])
                pygame.draw.circle(surface, (235, 221, 185), (cx + 24, cy + 12), 4)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (249, 244, 226), panel, border_radius=22)
        pygame.draw.rect(surface, (75, 61, 55), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (56, 49, 56))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (56, 49, 56))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
