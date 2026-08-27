"""Uranus entry: sideways axis, long seasons, methane color, and faint rings."""

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
class UranusDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    UranusDiscovery("tilt", "uranus.tilt", "encyclopedia.space.uranus.tilt", (250, 190)),
    UranusDiscovery("seasons", "uranus.seasons", "encyclopedia.space.uranus.seasons", (755, 190)),
    UranusDiscovery("color", "uranus.color", "encyclopedia.space.uranus.color", (250, 420)),
    UranusDiscovery("rings", "uranus.rings", "encyclopedia.space.uranus.rings", (755, 420)),
)


class UranusPage(EncyclopediaPage):
    page_id = "space.uranus"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "uranus.intro"
        self._tilt_age = 0.0
        self._season_age = 0.0
        self._color_age = 0.0
        self._rings_visible = False
        self._hotspots = tuple(pygame.Rect(cx - 43, cy - 43, 86, 86) for cx, cy in (d.center for d in DISCOVERIES))

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.uranus.intro")

    def update(self, dt: float) -> None:
        self._time += dt
        self._tilt_age = max(0.0, self._tilt_age - dt)
        self._season_age = max(0.0, self._season_age - dt)
        self._color_age = max(0.0, self._color_age - dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {PageInputKind.POINTER_MOVE, PageInputKind.POINTER_PRESS}:
            point = (int(event.position[0]), int(event.position[1]))
            hit = next((i for i, rect in enumerate(self._hotspots) if rect.collidepoint(point)), None)
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
        if discovery.discovery_id == "tilt":
            self._tilt_age = 4.5
        elif discovery.discovery_id == "seasons":
            self._season_age = 5.0
        elif discovery.discovery_id == "color":
            self._color_age = 4.0
        else:
            self._rings_visible = not self._rings_visible
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((21, 27, 53))
        for i in range(31):
            pygame.draw.circle(surface, (226, 232, 242), ((i * 103 + 15) % 1000, 78 + (i * 49) % 468), 1)
        draw_centered_text(surface, self.context.typography, self.context.resources.text("uranus.title"), center=(500, 92), size=40, color=(243, 240, 220), role=FontRole.DISPLAY)
        self._draw_uranus(surface)
        self._draw_hotspots(surface)
        self._draw_caption(surface)
        draw_presenter(surface, self.context.visuals, "leo", position=(925, 565), height=142, variant="surprised", fallback_color=(227, 174, 87))

    def _draw_uranus(self, surface: pygame.Surface) -> None:
        center = (505, 326)
        radius = 88
        planet_color = (144, 207, 211) if self._color_age <= 0 else (119, 199, 207)

        ring_rect = pygame.Rect(center[0] - 132, center[1] - 44, 264, 88)
        if self._rings_visible:
            for inset in (0, 8, 16):
                pygame.draw.ellipse(surface, (151, 160, 160), ring_rect.inflate(-inset * 2, -inset), 2)

        pygame.draw.circle(surface, planet_color, center, radius)
        pygame.draw.circle(surface, (82, 116, 123), center, radius, 3)

        axis_angle = math.radians(82)
        if self._tilt_age > 0:
            wobble = math.sin(self._time * 1.8) * 0.08
            axis_angle += wobble
        dx = int(math.cos(axis_angle) * 126)
        dy = int(math.sin(axis_angle) * 126)
        pygame.draw.line(surface, (247, 219, 97), (center[0] - dx, center[1] - dy), (center[0] + dx, center[1] + dy), 5)
        pygame.draw.circle(surface, (247, 219, 97), (center[0] + dx, center[1] + dy), 6)
        if self._tilt_age > 0:
            pygame.draw.arc(surface, (247, 219, 97), pygame.Rect(center[0] - 115, center[1] - 115, 230, 230), 0.5, 5.1, 4)

        if self._season_age > 0:
            sun = (360, 326)
            orbit = pygame.Rect(390, 238, 250, 176)
            pygame.draw.circle(surface, (250, 203, 69), sun, 22)
            pygame.draw.ellipse(surface, (71, 80, 112), orbit, 2)
            angle = self._time * 0.55
            pos = (orbit.centerx + int(math.cos(angle) * orbit.width / 2), orbit.centery + int(math.sin(angle) * orbit.height / 2))
            pygame.draw.circle(surface, planet_color, pos, 17)
            pole = (pos[0] + int(math.cos(angle) * 19), pos[1] + int(math.sin(angle) * 19))
            pygame.draw.circle(surface, (251, 224, 112), pole, 5)
            draw_centered_text(surface, self.context.typography, "84y", center=(505, 453), size=18, color=(240, 229, 190), role=FontRole.CONTROL)

        if self._color_age > 0:
            for offset in (-36, -12, 12, 36):
                pygame.draw.arc(surface, (180, 232, 228), (center[0] - 82, center[1] + offset - 9, 164, 18), 0.1, 3.0, 3)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (248, 245, 228), item.center, 37)
            pygame.draw.circle(surface, (68, 61, 58), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "tilt":
                pygame.draw.circle(surface, (144, 207, 211), (cx, cy), 18)
                pygame.draw.line(surface, (230, 194, 70), (cx - 22, cy + 18), (cx + 22, cy - 18), 5)
            elif item.discovery_id == "seasons":
                pygame.draw.circle(surface, (250, 203, 69), (cx - 14, cy), 9)
                pygame.draw.ellipse(surface, (127, 135, 158), (cx - 26, cy - 19, 52, 38), 3)
                pygame.draw.circle(surface, (144, 207, 211), (cx + 22, cy), 7)
            elif item.discovery_id == "color":
                pygame.draw.circle(surface, (119, 199, 207), (cx, cy), 21)
                pygame.draw.arc(surface, (204, 239, 234), (cx - 22, cy - 9, 44, 18), 0.2, 3.0, 4)
            else:
                pygame.draw.ellipse(surface, (144, 207, 211), (cx - 16, cy - 16, 32, 32))
                pygame.draw.ellipse(surface, (123, 130, 133), (cx - 29, cy - 11, 58, 22), 3)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (248, 245, 228), panel, border_radius=22)
        pygame.draw.rect(surface, (68, 61, 58), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (54, 49, 58))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (54, 49, 58))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
