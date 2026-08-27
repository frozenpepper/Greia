"""Rainbow entry: viewing geometry, droplet optics, color separation, circular bow."""

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
class RainbowDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    RainbowDiscovery("position", "rainbow.position", "encyclopedia.earth.rainbow.position", (250, 190)),
    RainbowDiscovery("droplet", "rainbow.droplet", "encyclopedia.earth.rainbow.droplet", (755, 190)),
    RainbowDiscovery("colors", "rainbow.colors", "encyclopedia.earth.rainbow.colors", (250, 420)),
    RainbowDiscovery("circle", "rainbow.circle", "encyclopedia.earth.rainbow.circle", (755, 420)),
)

_COLORS = (
    (221, 76, 84),
    (237, 137, 62),
    (244, 204, 69),
    (83, 168, 92),
    (72, 136, 204),
    (133, 103, 187),
)


class RainbowPage(EncyclopediaPage):
    page_id = "earth.rainbow"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "rainbow.intro"
        self._alignment_step = 0
        self._droplet_age = 0.0
        self._colors_age = 0.0
        self._circle_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )

    @property
    def _aligned(self) -> bool:
        return self._alignment_step == 2

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.earth.rainbow.intro")

    def update(self, dt: float) -> None:
        self._time += dt
        self._droplet_age = max(0.0, self._droplet_age - dt)
        self._colors_age = max(0.0, self._colors_age - dt)
        self._circle_age = max(0.0, self._circle_age - dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
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
        if discovery.discovery_id == "position":
            self._alignment_step = (self._alignment_step + 1) % 3
        elif discovery.discovery_id == "droplet":
            self._droplet_age = 5.0
        elif discovery.discovery_id == "colors":
            self._colors_age = 5.0
        else:
            self._circle_age = 5.0
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((176, 221, 240))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("rainbow.title"),
            center=(500, 92),
            size=40,
            color=(58, 63, 68),
            role=FontRole.DISPLAY,
        )
        self._draw_rainbow_scene(surface)
        self._draw_hotspots(surface)
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "tito",
            position=(925, 565),
            height=145,
            variant="surprised",
            fallback_color=(247, 151, 77),
        )

    def _draw_rainbow_scene(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (104, 173, 91), (0, 405, 1024, 195))
        viewer = (505, 390)
        pygame.draw.circle(surface, (238, 198, 151), (viewer[0], viewer[1] - 33), 12)
        pygame.draw.line(surface, (74, 70, 68), (viewer[0], viewer[1] - 20), (viewer[0], viewer[1] + 16), 5)
        pygame.draw.line(surface, (74, 70, 68), (viewer[0], viewer[1] - 4), (viewer[0] - 15, viewer[1] + 6), 4)
        pygame.draw.line(surface, (74, 70, 68), (viewer[0], viewer[1] - 4), (viewer[0] + 15, viewer[1] + 6), 4)
        for index in range(18):
            x = 420 + (index * 37) % 180
            y = 188 + (index * 53) % 115
            pygame.draw.line(surface, (78, 151, 201), (x, y), (x - 4, y + 13), 3)

        sun_positions = ((370, 310), (650, 260), (505, 475))
        sun = sun_positions[self._alignment_step]
        pygame.draw.circle(surface, (251, 210, 66), sun, 27)
        for index in range(8):
            angle = index * math.tau / 8
            pygame.draw.line(
                surface,
                (251, 210, 66),
                (sun[0] + int(math.cos(angle) * 34), sun[1] + int(math.sin(angle) * 34)),
                (sun[0] + int(math.cos(angle) * 46), sun[1] + int(math.sin(angle) * 46)),
                3,
            )

        if self._aligned:
            for y in range(435, 285, -22):
                pygame.draw.line(surface, (246, 203, 73), (505, y), (505, y - 12), 3)
            for index, color in enumerate(_COLORS):
                inset = index * 7
                pygame.draw.arc(
                    surface,
                    color,
                    (350 + inset, 190 + inset, 310 - inset * 2, 245 - inset * 2),
                    0,
                    math.pi,
                    6,
                )

        if self._droplet_age > 0:
            center = (505, 285)
            pygame.draw.circle(surface, (221, 241, 247), center, 72)
            pygame.draw.circle(surface, (91, 163, 204), center, 72, 3)
            pygame.draw.line(surface, (248, 235, 182), (382, 255), (458, 276), 5)
            pygame.draw.line(surface, (248, 235, 182), (458, 276), (543, 326), 5)
            pygame.draw.line(surface, (248, 235, 182), (543, 326), (565, 253), 5)
            pygame.draw.line(surface, (248, 235, 182), (565, 253), (632, 228), 5)
            pygame.draw.circle(surface, (245, 214, 80), (458, 276), 6)
            pygame.draw.circle(surface, (245, 214, 80), (543, 326), 6)

        if self._colors_age > 0:
            start = (446, 333)
            pygame.draw.line(surface, (245, 241, 216), (376, 333), start, 7)
            for index, color in enumerate(_COLORS):
                pygame.draw.line(surface, color, start, (628, 290 + index * 16), 5)

        if self._circle_age > 0:
            main_center = (505, 292)
            for index, color in enumerate(_COLORS):
                radius = 105 - index * 8
                pygame.draw.circle(surface, color, main_center, radius, 5)
            # Ground masks the lower half in the ordinary ground-level view.
            pygame.draw.rect(surface, (104, 173, 91), (355, 292, 300, 135))
            pygame.draw.line(surface, (75, 110, 78), (355, 292), (655, 292), 3)
            # A separate elevated-view inset explicitly shows the full circle.
            inset_center = (682, 330)
            pygame.draw.circle(surface, (231, 241, 244), inset_center, 47)
            for index, color in enumerate(_COLORS):
                radius = 41 - index * 5
                pygame.draw.circle(surface, color, inset_center, radius, 3)
            pygame.draw.circle(surface, (90, 119, 153), inset_center, 47, 2)
            pygame.draw.line(surface, (90, 119, 153), (653, 371), (711, 289), 2)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (255, 249, 232), item.center, 37)
            pygame.draw.circle(surface, (72, 66, 59), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "position":
                pygame.draw.circle(surface, (248, 204, 65), (cx - 17, cy + 9), 9)
                pygame.draw.circle(surface, (235, 198, 151), (cx + 1, cy + 8), 6)
                for off in (-8, 7, 22):
                    pygame.draw.line(surface, (81, 151, 199), (cx + 12 + off, cy - 18), (cx + 8 + off, cy - 5), 3)
            elif item.discovery_id == "droplet":
                pygame.draw.circle(surface, (211, 237, 246), (cx, cy), 22)
                pygame.draw.line(surface, (245, 221, 112), (cx - 27, cy - 9), (cx + 19, cy + 13), 4)
            elif item.discovery_id == "colors":
                for off, color in enumerate(_COLORS):
                    pygame.draw.line(surface, color, (cx - 25, cy - 15 + off * 6), (cx + 24, cy - 15 + off * 6), 4)
            else:
                for off, color in enumerate(_COLORS):
                    pygame.draw.arc(
                        surface,
                        color,
                        (cx - 26 + off * 2, cy - 24 + off * 2, 52 - off * 4, 48 - off * 4),
                        0,
                        math.tau,
                        3,
                    )
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (255, 249, 232), panel, border_radius=22)
        pygame.draw.rect(surface, (72, 66, 59), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (54, 53, 53))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (54, 53, 53))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
