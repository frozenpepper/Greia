"""Venus entry: Earth-size comparison, greenhouse heat, clouds and reverse spin."""

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
class VenusDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    VenusDiscovery("compare", "venus.compare", "encyclopedia.space.venus.compare", (250, 190)),
    VenusDiscovery("heat", "venus.heat", "encyclopedia.space.venus.heat", (755, 190)),
    VenusDiscovery("clouds", "venus.clouds", "encyclopedia.space.venus.clouds", (250, 420)),
    VenusDiscovery("rotation", "venus.rotation", "encyclopedia.space.venus.rotation", (755, 420)),
)


class VenusPage(EncyclopediaPage):
    page_id = "space.venus"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "venus.intro"
        self._compare_age = 0.0
        self._heat_age = 0.0
        self._clouds_hidden = False
        self._rotation_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.venus.intro")

    def update(self, dt: float) -> None:
        self._time += dt
        self._compare_age = max(0.0, self._compare_age - dt)
        self._heat_age = max(0.0, self._heat_age - dt)
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
        if discovery.discovery_id == "compare":
            self._compare_age = 4.0
        elif discovery.discovery_id == "heat":
            self._heat_age = 4.0
        elif discovery.discovery_id == "clouds":
            self._clouds_hidden = not self._clouds_hidden
        else:
            self._rotation_age = 4.0
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((27, 30, 58))
        for index in range(32):
            x = (index * 89 + 17) % 1000
            y = 78 + (index * 57) % 470
            pygame.draw.circle(surface, (228, 231, 242), (x, y), 1)
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("venus.title"),
            center=(500, 92),
            size=40,
            color=(246, 239, 215),
            role=FontRole.DISPLAY,
        )
        self._draw_venus(surface)
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

    def _draw_venus(self, surface: pygame.Surface) -> None:
        center = (505, 326)
        radius = 96

        # Rocky base exists in both modes; the opaque cloud layer normally hides it.
        pygame.draw.circle(surface, (168, 104, 66), center, radius)
        for dx, dy, width, height in (
            (-42, -24, 54, 21),
            (18, -42, 46, 18),
            (-15, 24, 63, 22),
            (40, 36, 30, 15),
        ):
            pygame.draw.ellipse(
                surface,
                (130, 82, 62),
                (center[0] + dx, center[1] + dy, width, height),
                3,
            )
        pygame.draw.polygon(
            surface,
            (119, 73, 59),
            [(470, 355), (490, 305), (510, 355)],
        )
        pygame.draw.polygon(
            surface,
            (119, 73, 59),
            [(532, 365), (551, 318), (570, 365)],
        )

        if not self._clouds_hidden:
            pygame.draw.circle(surface, (222, 185, 103), center, radius)
            for index in range(8):
                y = center[1] - 65 + index * 19
                wave = int(math.sin(self._time * 0.45 + index) * 8)
                pygame.draw.arc(
                    surface,
                    (242, 218, 154),
                    (center[0] - 82 + wave, y - 8, 164, 30),
                    0.05,
                    3.05,
                    5,
                )

        if self._heat_age > 0:
            for ring in range(4):
                pygame.draw.circle(
                    surface,
                    (236, 103, 55),
                    center,
                    radius + 12 + ring * 11,
                    3,
                )
            # A few inward-turning arrows communicate trapped heat without a
            # particle system or claiming a literal atmospheric path.
            for angle in (0.3, 1.9, 3.5, 5.1):
                start = (
                    center[0] + int(math.cos(angle) * 145),
                    center[1] + int(math.sin(angle) * 145),
                )
                end = (
                    center[0] + int(math.cos(angle) * 112),
                    center[1] + int(math.sin(angle) * 112),
                )
                pygame.draw.line(surface, (247, 171, 70), start, end, 5)

        if self._compare_age > 0:
            earth = (631, 364)
            pygame.draw.circle(surface, (72, 145, 215), earth, 31)
            pygame.draw.arc(surface, (91, 181, 105), (611, 345, 39, 31), 0.1, 3.0, 6)
            pygame.draw.line(surface, (247, 226, 150), (470, 432), (643, 432), 4)
            pygame.draw.line(surface, (247, 226, 150), (470, 424), (470, 440), 4)
            pygame.draw.line(surface, (247, 226, 150), (643, 424), (643, 440), 4)

        if self._rotation_age > 0:
            rect = pygame.Rect(center[0] - 127, center[1] - 127, 254, 254)
            # Arc deliberately runs opposite the direction used by the generic
            # clockwise indicator on other pages.
            start = 0.15 + self._time * 0.08
            pygame.draw.arc(surface, (250, 220, 104), rect, start, start + 4.8, 6)
            angle = start
            tip = (
                center[0] + int(math.cos(angle) * 126),
                center[1] + int(math.sin(angle) * 126),
            )
            tangent = angle - math.pi / 2
            points = [
                tip,
                (
                    tip[0] - int(math.cos(tangent + 0.55) * 18),
                    tip[1] - int(math.sin(tangent + 0.55) * 18),
                ),
                (
                    tip[0] - int(math.cos(tangent - 0.55) * 18),
                    tip[1] - int(math.sin(tangent - 0.55) * 18),
                ),
            ]
            pygame.draw.polygon(surface, (250, 220, 104), points)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (249, 244, 224), item.center, 37)
            pygame.draw.circle(surface, (74, 62, 57), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "compare":
                pygame.draw.circle(surface, (219, 181, 101), (cx - 13, cy), 18)
                pygame.draw.circle(surface, (72, 145, 215), (cx + 18, cy + 4), 17)
            elif item.discovery_id == "heat":
                pygame.draw.circle(surface, (219, 181, 101), (cx, cy), 17)
                for ring in (22, 28):
                    pygame.draw.arc(surface, (232, 99, 51), (cx - ring, cy - ring, ring * 2, ring * 2), 0.3, 2.6, 3)
            elif item.discovery_id == "clouds":
                pygame.draw.circle(surface, (169, 104, 66), (cx, cy + 4), 20)
                pygame.draw.arc(surface, (232, 210, 155), (cx - 25, cy - 17, 50, 24), 0.1, 3.0, 6)
            else:
                pygame.draw.arc(surface, (219, 181, 101), (cx - 23, cy - 23, 46, 46), 0.2, 4.9, 5)
                pygame.draw.polygon(surface, (219, 181, 101), [(cx - 20, cy - 8), (cx - 29, cy + 2), (cx - 13, cy + 3)])
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (249, 244, 224), panel, border_radius=22)
        pygame.draw.rect(surface, (74, 62, 57), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (56, 50, 58))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (56, 50, 58))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
