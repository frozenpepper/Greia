"""Jupiter entry: scale, fast day, giant storm, and gas-giant structure."""

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
class JupiterDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    JupiterDiscovery("scale", "jupiter.scale", "encyclopedia.space.jupiter.scale", (250, 190)),
    JupiterDiscovery("day", "jupiter.day", "encyclopedia.space.jupiter.day", (755, 190)),
    JupiterDiscovery("storm", "jupiter.storm", "encyclopedia.space.jupiter.storm", (250, 420)),
    JupiterDiscovery("gas", "jupiter.gas", "encyclopedia.space.jupiter.gas", (755, 420)),
)


class JupiterPage(EncyclopediaPage):
    page_id = "space.jupiter"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "jupiter.intro"
        self._scale_age = 0.0
        self._day_age = 0.0
        self._storm_age = 0.0
        self._gas_age = 0.0
        self._hotspots = tuple(pygame.Rect(cx - 43, cy - 43, 86, 86) for cx, cy in (d.center for d in DISCOVERIES))

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.jupiter.intro")

    def update(self, dt: float) -> None:
        self._time += dt
        self._scale_age = max(0.0, self._scale_age - dt)
        self._day_age = max(0.0, self._day_age - dt)
        self._storm_age = max(0.0, self._storm_age - dt)
        self._gas_age = max(0.0, self._gas_age - dt)

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
        if discovery.discovery_id == "scale":
            self._scale_age = 4.0
        elif discovery.discovery_id == "day":
            self._day_age = 4.0
        elif discovery.discovery_id == "storm":
            self._storm_age = 4.5
        else:
            self._gas_age = 4.0
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((24, 27, 50))
        for i in range(31):
            pygame.draw.circle(surface, (226, 230, 239), ((i * 91 + 17) % 1000, 78 + (i * 53) % 468), 1)
        draw_centered_text(surface, self.context.typography, self.context.resources.text("jupiter.title"), center=(500, 92), size=40, color=(246, 239, 220), role=FontRole.DISPLAY)
        self._draw_jupiter(surface)
        self._draw_hotspots(surface)
        self._draw_caption(surface)
        draw_presenter(surface, self.context.visuals, "leo", position=(925, 565), height=142, variant="surprised", fallback_color=(227, 174, 87))

    def _draw_jupiter(self, surface: pygame.Surface) -> None:
        center = (505, 326)
        radius = 100
        pygame.draw.circle(surface, (205, 169, 127), center, radius)
        clip = surface.get_clip()
        surface.set_clip(pygame.Rect(center[0] - radius, center[1] - radius, radius * 2, radius * 2))
        bands = ((-70, 24, (237, 220, 190)), (-42, 26, (174, 118, 83)), (-11, 24, (239, 225, 196)), (19, 29, (181, 124, 88)), (54, 22, (233, 214, 181)))
        offset = int(math.sin(self._time * (1.7 if self._day_age > 0 else 0.35)) * 9)
        for yoff, height, color in bands:
            pygame.draw.rect(surface, color, (center[0] - 112 + offset, center[1] + yoff, 224, height))
        surface.set_clip(clip)
        pygame.draw.circle(surface, (90, 66, 55), center, radius, 3)

        storm_center = (544, 358)
        storm_w = 62 + (8 if self._storm_age > 0 else 0)
        pygame.draw.ellipse(surface, (173, 82, 63), (storm_center[0] - storm_w // 2, storm_center[1] - 17, storm_w, 34))
        if self._storm_age > 0:
            for ring in range(3):
                pygame.draw.ellipse(surface, (230, 139, 96), (storm_center[0] - 43 - ring * 6, storm_center[1] - 22 - ring * 3, 86 + ring * 12, 44 + ring * 6), 3)

        if self._scale_age > 0:
            for row in range(2):
                for col in range(6):
                    pygame.draw.circle(surface, (73, 145, 214), (404 + col * 27, 442 + row * 22), 8)
            draw_centered_text(surface, self.context.typography, "≈11×", center=(505, 475), size=18, color=(245, 229, 177), role=FontRole.CONTROL)

        if self._gas_age > 0:
            for ring, color in ((78, (224, 198, 157)), (58, (196, 151, 110)), (38, (160, 113, 91))):
                pygame.draw.circle(surface, color, center, ring, 5)
            pygame.draw.line(surface, (246, 220, 143), (605, 280), (650, 248), 4)
            pygame.draw.line(surface, (246, 220, 143), (605, 372), (650, 404), 4)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (249, 244, 226), item.center, 37)
            pygame.draw.circle(surface, (73, 60, 55), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "scale":
                pygame.draw.circle(surface, (205, 169, 127), (cx - 10, cy), 21)
                pygame.draw.circle(surface, (73, 145, 214), (cx + 20, cy + 8), 7)
            elif item.discovery_id == "day":
                pygame.draw.arc(surface, (214, 176, 93), (cx - 24, cy - 24, 48, 48), 0.1, 5.2, 5)
                pygame.draw.polygon(surface, (214, 176, 93), [(cx + 21, cy - 9), (cx + 29, cy + 3), (cx + 13, cy + 4)])
            elif item.discovery_id == "storm":
                pygame.draw.ellipse(surface, (178, 83, 64), (cx - 25, cy - 13, 50, 26))
                pygame.draw.ellipse(surface, (228, 144, 101), (cx - 18, cy - 9, 36, 18), 3)
            else:
                for r in (21, 14, 7):
                    pygame.draw.circle(surface, (205, 169 - r, 115), (cx, cy), r, 3)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (249, 244, 226), panel, border_radius=22)
        pygame.draw.rect(surface, (73, 60, 55), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (55, 49, 56))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (55, 49, 56))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
