"""Lion entry: mane, pride, roar communication and strong forelegs."""

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
class LionDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    LionDiscovery("mane", "lion.mane", "encyclopedia.animals.lion.mane", (260, 205)),
    LionDiscovery("pride", "lion.pride", "encyclopedia.animals.lion.pride", (745, 205)),
    LionDiscovery("roar", "lion.roar", "encyclopedia.animals.lion.roar", (260, 410)),
    LionDiscovery("forelegs", "lion.forelegs", "encyclopedia.animals.lion.forelegs", (745, 410)),
)

_MANE_COLORS = ((136, 82, 46), (102, 67, 46), (78, 55, 44))
_MANE_RADII = (58, 66, 72)


class LionPage(EncyclopediaPage):
    """Own the lion exhibit's small bounded presentation state."""

    page_id = "animals.lion"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._mane_state = 0
        self._pride_age = 0.0
        self._roar_age = 0.0
        self._foreleg_age = 0.0
        self._caption_key = "lion.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.animals.lion.intro")

    def update(self, dt: float) -> None:
        self._time += dt
        self._pride_age = max(0.0, self._pride_age - dt)
        self._roar_age = max(0.0, self._roar_age - dt)
        self._foreleg_age = max(0.0, self._foreleg_age - dt)

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
        if discovery.discovery_id == "mane":
            self._mane_state = (self._mane_state + 1) % len(_MANE_COLORS)
        elif discovery.discovery_id == "pride":
            self._pride_age = 4.0
        elif discovery.discovery_id == "roar":
            self._roar_age = 3.0
        else:
            self._foreleg_age = 3.5
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((232, 211, 144))
        pygame.draw.rect(surface, (165, 181, 100), (0, 430, 1024, 170))
        pygame.draw.circle(surface, (250, 214, 96), (865, 125), 42)
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("lion.title"),
            center=(500, 92),
            size=40,
            color=self.context.palette.ink,
            role=FontRole.DISPLAY,
        )
        self._draw_lion(surface)
        self._draw_hotspots(surface)
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

    def _draw_lion(self, surface: pygame.Surface) -> None:
        cx, cy = 505, 315
        body_color = (222, 157, 72)
        mane_color = _MANE_COLORS[self._mane_state]
        mane_radius = _MANE_RADII[self._mane_state]

        pygame.draw.ellipse(surface, body_color, (438, 324, 145, 92))
        pygame.draw.circle(surface, mane_color, (cx, cy - 36), mane_radius)
        pygame.draw.circle(surface, body_color, (cx, cy - 36), 43)
        pygame.draw.polygon(surface, body_color, [(476, 252), (487, 224), (499, 255)])
        pygame.draw.polygon(surface, body_color, [(511, 255), (524, 224), (535, 252)])
        pygame.draw.circle(surface, (57, 47, 39), (492, cy - 43), 4)
        pygame.draw.circle(surface, (57, 47, 39), (518, cy - 43), 4)
        pygame.draw.ellipse(surface, (244, 199, 113), (486, cy - 28, 38, 25))
        pygame.draw.circle(surface, (57, 47, 39), (505, cy - 25), 5)

        foreleg_width = 20 + (7 if self._foreleg_age > 0 else 0)
        for x in (465, 548):
            pygame.draw.line(surface, body_color, (x, 377), (x - 3, 454), foreleg_width)
            paw_radius = 17 + (6 if self._foreleg_age > 0 else 0)
            pygame.draw.ellipse(surface, body_color, (x - paw_radius, 441, paw_radius * 2, 24))

        pygame.draw.line(surface, body_color, (570, 350), (622, 330), 13)
        pygame.draw.circle(surface, mane_color, (628, 327), 10)

        if self._pride_age > 0:
            for index, x in enumerate((380, 420, 630)):
                scale = 22 if index != 1 else 18
                pygame.draw.ellipse(surface, (205, 145, 72), (x - scale, 390, scale * 2, 30))
                pygame.draw.circle(surface, (205, 145, 72), (x + scale - 3, 392), 12)

        if self._roar_age > 0:
            progress = 1.0 - self._roar_age / 3.0
            mouth = (526, 300)
            for index in range(4):
                radius = 18 + index * 18 + int(progress * 18)
                rect = pygame.Rect(
                    mouth[0] - radius,
                    mouth[1] - radius,
                    radius * 2,
                    radius * 2,
                )
                pygame.draw.arc(surface, (245, 225, 124), rect, -0.55, 0.55, 4)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (255, 248, 222), item.center, 37)
            pygame.draw.circle(surface, (82, 65, 50), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "mane":
                pygame.draw.circle(surface, _MANE_COLORS[1], (cx, cy), 23)
                pygame.draw.circle(surface, (222, 157, 72), (cx, cy), 13)
            elif item.discovery_id == "pride":
                for dx, dy in ((-18, 7), (0, -7), (18, 7)):
                    pygame.draw.circle(surface, (205, 145, 72), (cx + dx, cy + dy), 10)
            elif item.discovery_id == "roar":
                for radius in (10, 20, 30):
                    pygame.draw.arc(surface, (191, 120, 58), (cx, cy - radius, radius * 2, radius * 2), -0.6, 0.6, 4)
            else:
                pygame.draw.ellipse(surface, (222, 157, 72), (cx - 23, cy - 9, 46, 28))
                for dx in (-12, 0, 12):
                    pygame.draw.circle(surface, (82, 65, 50), (cx + dx, cy + 12), 3)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (255, 248, 222), panel, border_radius=22)
        pygame.draw.rect(surface, (82, 65, 50), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (58, 49, 42))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (58, 49, 42))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
