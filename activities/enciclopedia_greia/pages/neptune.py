"""Neptune entry: distance, long year, supersonic winds, blue ice-giant structure."""

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
class NeptuneDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    NeptuneDiscovery("distance", "neptune.distance", "encyclopedia.space.neptune.distance", (250, 190)),
    NeptuneDiscovery("year", "neptune.year", "encyclopedia.space.neptune.year", (755, 190)),
    NeptuneDiscovery("winds", "neptune.winds", "encyclopedia.space.neptune.winds", (250, 420)),
    NeptuneDiscovery("blue", "neptune.blue", "encyclopedia.space.neptune.blue", (755, 420)),
)


class NeptunePage(EncyclopediaPage):
    page_id = "space.neptune"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "neptune.intro"
        self._distance_age = 0.0
        self._year_age = 0.0
        self._wind_age = 0.0
        self._rings_visible = False
        self._hotspots = tuple(pygame.Rect(cx - 43, cy - 43, 86, 86) for cx, cy in (d.center for d in DISCOVERIES))

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.neptune.intro")

    def update(self, dt: float) -> None:
        self._time += dt
        self._distance_age = max(0.0, self._distance_age - dt)
        self._year_age = max(0.0, self._year_age - dt)
        self._wind_age = max(0.0, self._wind_age - dt)

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
        if discovery.discovery_id == "distance":
            self._distance_age = 5.0
        elif discovery.discovery_id == "year":
            self._year_age = 5.0
        elif discovery.discovery_id == "winds":
            self._wind_age = 4.5
        else:
            self._rings_visible = not self._rings_visible
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((17, 24, 53))
        for i in range(33):
            pygame.draw.circle(surface, (226, 232, 243), ((i * 107 + 11) % 1000, 77 + (i * 51) % 470), 1)
        draw_centered_text(surface, self.context.typography, self.context.resources.text("neptune.title"), center=(500, 92), size=40, color=(244, 241, 222), role=FontRole.DISPLAY)
        self._draw_neptune(surface)
        self._draw_hotspots(surface)
        self._draw_caption(surface)
        draw_presenter(surface, self.context.visuals, "leo", position=(925, 565), height=142, variant="default", fallback_color=(227, 174, 87))

    def _draw_neptune(self, surface: pygame.Surface) -> None:
        center = (505, 326)
        radius = 90
        if self._rings_visible:
            for inset in (0, 7):
                pygame.draw.ellipse(surface, (113, 125, 149), (center[0] - 132 + inset, center[1] - 33 + inset // 2, 264 - inset * 2, 66 - inset), 2)
        pygame.draw.circle(surface, (75, 112, 194), center, radius)
        pygame.draw.circle(surface, (45, 67, 122), center, radius, 3)
        for yoff in (-47, -19, 14, 46):
            wave = int(math.sin(self._time * 0.45 + yoff) * 7)
            pygame.draw.arc(surface, (110, 148, 218), (center[0] - 80 + wave, center[1] + yoff - 9, 160, 22), 0.15, 3.0, 4)

        if self._wind_age > 0:
            speed = 155
            for i in range(10):
                y = 255 + i * 17
                x = 395 + int((self._time * speed + i * 47) % 220)
                pygame.draw.line(surface, (188, 220, 246), (x - 26, y), (x + 16, y - 4), 4)
            pygame.draw.ellipse(surface, (58, 77, 139), (530, 340, 70, 34))
            pygame.draw.ellipse(surface, (133, 169, 221), (539, 347, 51, 20), 3)

        if self._distance_age > 0:
            sun = (362, 326)
            pygame.draw.circle(surface, (250, 204, 68), sun, 19)
            for step in range(1, 7):
                x = sun[0] + step * 35
                alpha_color = (245 - step * 15, 213 - step * 12, 103)
                pygame.draw.circle(surface, alpha_color, (x, 326), max(2, 8 - step))
            draw_centered_text(surface, self.context.typography, "≈4h", center=(505, 446), size=18, color=(237, 228, 194), role=FontRole.CONTROL)

        if self._year_age > 0:
            orbit = pygame.Rect(392, 245, 226, 164)
            pygame.draw.circle(surface, (250, 204, 68), (505, 327), 19)
            pygame.draw.ellipse(surface, (75, 84, 117), orbit, 2)
            phase = self._time * 0.34
            pos = (orbit.centerx + int(math.cos(phase) * orbit.width / 2), orbit.centery + int(math.sin(phase) * orbit.height / 2))
            pygame.draw.circle(surface, (75, 112, 194), pos, 12)
            draw_centered_text(surface, self.context.typography, "165y / 16h", center=(505, 450), size=18, color=(237, 228, 194), role=FontRole.CONTROL)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (248, 245, 228), item.center, 37)
            pygame.draw.circle(surface, (66, 60, 60), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "distance":
                pygame.draw.circle(surface, (249, 202, 67), (cx - 19, cy), 8)
                pygame.draw.circle(surface, (75, 112, 194), (cx + 22, cy), 9)
                pygame.draw.line(surface, (178, 184, 194), (cx - 8, cy), (cx + 10, cy), 3)
            elif item.discovery_id == "year":
                pygame.draw.ellipse(surface, (115, 124, 153), (cx - 27, cy - 18, 54, 36), 3)
                pygame.draw.circle(surface, (75, 112, 194), (cx + 24, cy), 7)
            elif item.discovery_id == "winds":
                for off in (-11, 0, 11):
                    pygame.draw.line(surface, (96, 145, 211), (cx - 24, cy + off), (cx + 22, cy + off - 5), 4)
            else:
                pygame.draw.circle(surface, (75, 112, 194), (cx, cy), 20)
                pygame.draw.ellipse(surface, (119, 130, 151), (cx - 28, cy - 9, 56, 18), 3)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (248, 245, 228), panel, border_radius=22)
        pygame.draw.rect(surface, (66, 60, 60), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (54, 49, 58))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (54, 49, 58))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
