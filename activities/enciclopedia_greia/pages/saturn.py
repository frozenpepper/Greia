"""Saturn final-entry pilot: size, gas, separate ring particles and tilt."""

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
class SaturnDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    SaturnDiscovery("place", "saturn.place", "encyclopedia.space.saturn.place", (275, 205)),
    SaturnDiscovery("gas", "saturn.gas", "encyclopedia.space.saturn.gas", (735, 205)),
    SaturnDiscovery("rings", "saturn.rings", "encyclopedia.space.saturn.rings", (275, 410)),
    SaturnDiscovery("tilt", "saturn.tilt", "encyclopedia.space.saturn.tilt", (735, 410)),
)

_RING_HEIGHTS = (34, 70, 105, 70)


class SaturnPage(EncyclopediaPage):
    page_id = "space.saturn"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "saturn.intro"
        self._tilt_state = 1
        self._rings_age = 0.0
        self._place_age = 0.0
        self._gas_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.saturn.intro")

    def update(self, dt: float) -> None:
        self._time += dt
        self._rings_age = max(0.0, self._rings_age - dt)
        self._place_age = max(0.0, self._place_age - dt)
        self._gas_age = max(0.0, self._gas_age - dt)

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
        if discovery.discovery_id == "place":
            self._place_age = 3.2
        elif discovery.discovery_id == "gas":
            self._gas_age = 3.2
        elif discovery.discovery_id == "rings":
            self._rings_age = 3.2
        elif discovery.discovery_id == "tilt":
            self._tilt_state = (self._tilt_state + 1) % len(_RING_HEIGHTS)
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((22, 26, 59))
        for i in range(42):
            x = (41 + i * 79) % 1014
            y = 75 + ((17 + i * 53) % 480)
            pygame.draw.circle(surface, (226, 230, 244), (x, y), 1 + i % 2)

        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("saturn.title"),
            center=(505, 94),
            size=40,
            color=(250, 240, 205),
            role=FontRole.DISPLAY,
        )
        self._draw_saturn(surface)
        self._draw_hotspots(surface)
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "leo",
            position=(930, 565),
            height=142,
            variant="surprised",
        )

    def _draw_saturn(self, surface: pygame.Surface) -> None:
        cx, cy = 505, 315
        ring_h = _RING_HEIGHTS[self._tilt_state]
        outer = pygame.Rect(cx - 180, cy - ring_h // 2, 360, ring_h)
        inner = pygame.Rect(cx - 145, cy - max(8, ring_h // 2 - 9), 290, max(16, ring_h - 18))
        pygame.draw.ellipse(surface, (210, 187, 125), outer, 13)
        pygame.draw.ellipse(surface, (239, 219, 165), inner, 6)

        pygame.draw.circle(surface, (219, 183, 118), (cx, cy), 82)
        for offset, color in (
            (-48, (231, 205, 153)),
            (-25, (199, 157, 100)),
            (0, (236, 208, 153)),
            (28, (196, 151, 94)),
            (50, (229, 197, 141)),
        ):
            shift = int(math.sin(self._time * (1.8 if self._gas_age > 0 else 0.5) + offset) * (5 if self._gas_age > 0 else 1))
            pygame.draw.line(
                surface,
                color,
                (cx - 64 + shift, cy + offset),
                (cx + 64 + shift, cy + offset),
                8,
            )
        # Re-outline the limb after bands so Saturn remains a clear sphere.
        pygame.draw.circle(surface, (128, 103, 77), (cx, cy), 82, 3)

        if self._rings_age > 0:
            # Show that a ring is a population of individual orbiting pieces,
            # not one solid plate. Positions are deterministic and bounded.
            for i in range(34):
                angle = self._time * (0.35 + (i % 5) * 0.025) + i * 0.67
                rx = 120 + (i % 6) * 10
                ry = max(12, ring_h * (0.34 + (i % 4) * 0.035))
                x = cx + int(math.cos(angle) * rx)
                y = cy + int(math.sin(angle) * ry)
                pygame.draw.circle(surface, (245, 232, 197), (x, y), 2 + i % 3)

        if self._place_age > 0:
            # Deliberately schematic scale comparison: Earth shown beside Saturn
            # with a clear size contrast, not an exact orbital-scale diagram.
            pygame.draw.circle(surface, (78, 146, 211), (620, 300), 18)
            pygame.draw.ellipse(surface, (83, 176, 104), (610, 291, 18, 10))
            for i in range(6):
                pygame.draw.circle(surface, (247, 205, 70), (365 + i * 18, 190), max(3, 8 - i))
            pygame.draw.circle(surface, (219, 183, 118), (485, 190), 12)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (248, 243, 224), item.center, 37)
            pygame.draw.circle(surface, (86, 83, 96), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "place":
                pygame.draw.circle(surface, (249, 205, 64), (cx - 18, cy), 10)
                for i in range(5):
                    pygame.draw.circle(surface, (103, 141, 200), (cx - 2 + i * 10, cy), 3 + i // 2)
            elif item.discovery_id == "gas":
                for dy in (-14, 0, 14):
                    pygame.draw.arc(surface, (192, 149, 91), (cx - 22, cy + dy - 6, 44, 12), 0, math.pi, 4)
            elif item.discovery_id == "rings":
                pygame.draw.ellipse(surface, (205, 176, 112), (cx - 26, cy - 12, 52, 24), 6)
                for dx in (-20, -8, 8, 20):
                    pygame.draw.circle(surface, (92, 87, 82), (cx + dx, cy), 3)
            else:
                pygame.draw.ellipse(surface, (205, 176, 112), (cx - 26, cy - 8, 52, 16), 5)
                pygame.draw.line(surface, (92, 87, 82), (cx, cy - 23), (cx, cy + 23), 3)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (248, 243, 224), panel, border_radius=22)
        pygame.draw.rect(surface, (86, 83, 96), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (52, 49, 61))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (52, 49, 61))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
