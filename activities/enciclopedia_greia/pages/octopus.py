"""Octopus final-entry pilot: arms, camouflage, ink and three hearts."""

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
class OctopusDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


# Tuple order is deliberately the same as the visible 2×2 grid so Greia's
# semantic directional navigation matches what the child sees.
DISCOVERIES = (
    OctopusDiscovery("camouflage", "octopus.camouflage", "encyclopedia.animals.octopus.camouflage", (300, 215)),
    OctopusDiscovery("ink", "octopus.ink", "encyclopedia.animals.octopus.ink", (735, 230)),
    OctopusDiscovery("arms", "octopus.arms", "encyclopedia.animals.octopus.arms", (265, 405)),
    OctopusDiscovery("hearts", "octopus.hearts", "encyclopedia.animals.octopus.hearts", (740, 405)),
)

_BODY_COLORS = (
    (183, 103, 173),
    (98, 155, 150),
    (192, 127, 75),
    (113, 116, 155),
)


class OctopusPage(EncyclopediaPage):
    page_id = "animals.octopus"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._camouflage_state = 0
        self._ink_age = 0.0
        self._sucker_age = 0.0
        self._heart_age = 0.0
        self._caption_key = "octopus.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 44, cy - 44, 88, 88)
            for cx, cy in (item.center for item in DISCOVERIES)
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.animals.octopus.intro")

    def update(self, dt: float) -> None:
        self._time += dt
        self._ink_age = max(0.0, self._ink_age - dt)
        self._sucker_age = max(0.0, self._sucker_age - dt)
        self._heart_age = max(0.0, self._heart_age - dt)

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
        if discovery.discovery_id == "arms":
            self._sucker_age = 3.0
        elif discovery.discovery_id == "camouflage":
            self._camouflage_state = (self._camouflage_state + 1) % len(_BODY_COLORS)
        elif discovery.discovery_id == "ink":
            self._ink_age = 2.6
        elif discovery.discovery_id == "hearts":
            self._heart_age = 3.0
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((77, 156, 184))
        pygame.draw.rect(surface, (46, 116, 145), (0, 470, 1024, 130))
        pygame.draw.ellipse(surface, (198, 177, 130), (-40, 505, 1110, 150))
        for x in (95, 155, 850, 905):
            sway = int(math.sin(self._time * 1.4 + x) * 7)
            pygame.draw.line(surface, (74, 139, 89), (x, 550), (x + sway, 360), 12)

        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("octopus.title"),
            center=(500, 100),
            size=40,
            color=(255, 250, 236),
            role=FontRole.DISPLAY,
        )

        self._draw_octopus(surface)
        self._draw_discovery_hotspots(surface)
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "tito",
            position=(925, 565),
            height=142,
            variant="happy",
            fallback_color=(247, 151, 77),
        )

    def _draw_octopus(self, surface: pygame.Surface) -> None:
        color = _BODY_COLORS[self._camouflage_state]
        center = (505, 310)
        arm_paths = (
            ((475, 340), (440, 380), (400, 415), (350, 430)),
            ((485, 345), (465, 395), (445, 440), (420, 475)),
            ((495, 346), (490, 405), (485, 455), (470, 500)),
            ((505, 348), (515, 405), (525, 455), (535, 500)),
            ((515, 346), (545, 395), (570, 440), (595, 475)),
            ((525, 340), (570, 380), (610, 415), (660, 430)),
            ((485, 335), (420, 350), (365, 345), (320, 325)),
            ((520, 335), (585, 350), (645, 345), (695, 320)),
        )
        for path in arm_paths:
            pygame.draw.lines(surface, color, False, path, 22)
            for point in (path[1], path[2], path[3]):
                pygame.draw.circle(surface, color, point, 11)
        pygame.draw.ellipse(surface, color, (445, 215, 120, 145))
        pygame.draw.circle(surface, (248, 238, 215), (482, 270), 14)
        pygame.draw.circle(surface, (248, 238, 215), (528, 270), 14)
        pygame.draw.circle(surface, (49, 44, 52), (484, 272), 6)
        pygame.draw.circle(surface, (49, 44, 52), (526, 272), 6)

        if self._sucker_age > 0:
            for arm in arm_paths[:6]:
                for x, y in arm[1:]:
                    pygame.draw.circle(surface, (248, 224, 201), (x, y + 7), 5, 2)
        if self._heart_age > 0:
            for dx, dy in ((-26, 0), (0, -16), (26, 0)):
                self._draw_heart(surface, (center[0] + dx, center[1] + dy), 10)
        if self._ink_age > 0:
            progress = 1.0 - self._ink_age / 2.6
            for i in range(18):
                angle = i * 0.72 + self._time * 0.35
                radius = 12 + int(progress * (35 + (i % 5) * 8))
                x = 650 + int(math.cos(angle) * radius)
                y = 330 + int(math.sin(angle) * radius * 0.65)
                size = 8 + (i % 4) * 3
                pygame.draw.circle(surface, (35, 38, 55), (x, y), size)

    def _draw_discovery_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            active = index == self._selected
            hover = index == self._hovered
            pygame.draw.circle(surface, (255, 250, 236), item.center, 38)
            pygame.draw.circle(surface, (54, 72, 82), item.center, 38, 3)
            if item.discovery_id == "arms":
                pygame.draw.line(
                    surface,
                    (183, 103, 173),
                    (item.center[0] - 20, item.center[1] + 15),
                    (item.center[0] + 20, item.center[1] - 15),
                    10,
                )
                for n in range(4):
                    pygame.draw.circle(
                        surface,
                        (227, 170, 204),
                        (item.center[0] - 14 + n * 10, item.center[1] + 5 - n * 7),
                        4,
                    )
            elif item.discovery_id == "camouflage":
                for n, swatch in enumerate(_BODY_COLORS):
                    pygame.draw.circle(
                        surface,
                        swatch,
                        (
                            item.center[0] - 16 + (n % 2) * 32,
                            item.center[1] - 16 + (n // 2) * 32,
                        ),
                        10,
                    )
            elif item.discovery_id == "ink":
                for dx, dy, radius in (
                    (0, 0, 14),
                    (-13, 8, 9),
                    (14, 9, 10),
                    (6, -12, 8),
                ):
                    pygame.draw.circle(
                        surface,
                        (35, 38, 55),
                        (item.center[0] + dx, item.center[1] + dy),
                        radius,
                    )
            else:
                for dx, dy in ((-14, 6), (0, -8), (14, 6)):
                    self._draw_heart(
                        surface,
                        (item.center[0] + dx, item.center[1] + dy),
                        7,
                    )
            focus_ring(surface, rect, active or hover)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (255, 250, 236), panel, border_radius=22)
        pygame.draw.rect(surface, (54, 72, 82), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(
            text,
            FontRole.BODY,
            18,
            (54, 57, 61),
        )
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(
                text,
                FontRole.BODY,
                15,
                (54, 57, 61),
            )
        surface.blit(rendered, rendered.get_rect(center=panel.center))

    @staticmethod
    def _draw_heart(
        surface: pygame.Surface,
        center: tuple[int, int],
        size: int,
    ) -> None:
        cx, cy = center
        color = (206, 69, 84)
        pygame.draw.circle(surface, color, (cx - size // 2, cy), size // 2 + 1)
        pygame.draw.circle(surface, color, (cx + size // 2, cy), size // 2 + 1)
        pygame.draw.polygon(
            surface,
            color,
            [(cx - size, cy), (cx + size, cy), (cx, cy + size * 2)],
        )
