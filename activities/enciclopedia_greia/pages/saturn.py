"""Saturn golden master: authored observatory scene plus low-cost factual reveals."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        TOKEN_SHAPE_TELESCOPE_CARD,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_title,
    )
    from .common import draw_presenter, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        TOKEN_SHAPE_TELESCOPE_CARD,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_title,
    )
    from pages.common import draw_presenter, grid_step


@dataclass(frozen=True, slots=True)
class SaturnDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    SaturnDiscovery("place", "saturn.place", "encyclopedia.space.saturn.place", (235, 195)),
    SaturnDiscovery("gas", "saturn.gas", "encyclopedia.space.saturn.gas", (775, 195)),
    SaturnDiscovery("rings", "saturn.rings", "encyclopedia.space.saturn.rings", (235, 405)),
    SaturnDiscovery("tilt", "saturn.tilt", "encyclopedia.space.saturn.tilt", (775, 405)),
)


class SaturnPage(EncyclopediaPage):
    page_id = "space.saturn"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "saturn.intro"
        self._tilt_state = 0
        self._rings_age = 0.0
        self._place_age = 0.0
        self._gas_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 50, cy - 50, 100, 100)
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
        else:
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
        else:
            self._tilt_state = (self._tilt_state + 1) % 3
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        if not draw_authored_scene(
            surface,
            self.context.visuals,
            "encyclopedia.space.saturn.observatory",
        ):
            surface.fill((22, 26, 59))
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("saturn.title"),
            (250, 240, 205),
        )
        self._draw_reveals(surface)
        for index, item in enumerate(DISCOVERIES):
            draw_discovery_token(
                surface,
                item.center,
                selected=index == self._selected,
                hovered=index == self._hovered,
                recently_activated=self._is_recent(item.discovery_id),
                icon=lambda target, center, item=item: self._draw_icon(
                    target,
                    center,
                    item.discovery_id,
                ),
                token_shape=TOKEN_SHAPE_TELESCOPE_CARD,
            )
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
            dark=True,
        )
        draw_presenter(
            surface,
            self.context.visuals,
            "leo",
            position=(228, 575),
            height=190,
            variant="surprised",
        )

    def _is_recent(self, discovery_id: str) -> bool:
        return (
            (discovery_id == "place" and self._place_age > 0)
            or (discovery_id == "gas" and self._gas_age > 0)
            or (discovery_id == "rings" and self._rings_age > 0)
        )

    def _draw_reveals(self, surface: pygame.Surface) -> None:
        if self._place_age > 0:
            # Sun (top-left of the orbit, smaller than Saturn but clearly the sun).
            pygame.draw.circle(surface, (255, 200, 90), (218, 174), 14)
            pygame.draw.circle(surface, (255, 234, 138), (218, 174), 7)
            # Long dotted orbit path from the sun past Saturn, so the
            # child sees "Saturn is far out from the sun".
            for index in range(34):
                px = 226 + index * 18
                pygame.draw.circle(surface, (200, 220, 255), (px, 174), 1.4)
            # Earth (small) along the orbit.
            pygame.draw.circle(surface, (72, 143, 214), (640, 174), 18)
            pygame.draw.ellipse(surface, (90, 177, 104), (630, 165, 18, 10))
            # Saturn marker along the same orbit (the planet itself is
            # the large hero; we just label its position here).
            pygame.draw.circle(surface, (255, 220, 117), (842, 174), 5)
        if self._gas_age > 0:
            for dy in (-35, -15, 8, 28):
                shift = int(math.sin(self._time * 2.2 + dy) * 8)
                pygame.draw.arc(
                    surface,
                    (255, 232, 180),
                    (420 + shift, 300 + dy, 180, 34),
                    0.1,
                    3.0,
                    3,
                )
        if self._rings_age > 0:
            for index in range(28):
                angle = self._time * 0.3 + index * 0.71
                x = 510 + int(math.cos(angle) * (160 + index % 5 * 9))
                y = 335 + int(math.sin(angle) * (42 + index % 3 * 4))
                pygame.draw.circle(surface, (246, 232, 197), (x, y), 2 + index % 2)
        if self._tilt_state:
            color = ((255, 220, 117), (176, 199, 240))[self._tilt_state - 1]
            pygame.draw.line(surface, color, (510, 210), (510, 455), 4)
            pygame.draw.line(surface, color, (450, 335), (570, 335), 3)

    @staticmethod
    def _draw_icon(
        surface: pygame.Surface,
        center: tuple[int, int],
        discovery_id: str,
    ) -> None:
        cx, cy = center
        if discovery_id == "place":
            pygame.draw.circle(surface, (249, 205, 64), (cx - 17, cy), 10)
            for index in range(5):
                pygame.draw.circle(
                    surface,
                    (103, 141, 200),
                    (cx + index * 10, cy),
                    3 + index // 2,
                )
        elif discovery_id == "gas":
            for dy in (-14, 0, 14):
                pygame.draw.arc(
                    surface,
                    (192, 149, 91),
                    (cx - 22, cy + dy - 6, 44, 12),
                    0,
                    math.pi,
                    4,
                )
        elif discovery_id == "rings":
            pygame.draw.ellipse(surface, (205, 176, 112), (cx - 28, cy - 13, 56, 26), 6)
            for dx in (-20, -8, 8, 20):
                pygame.draw.circle(surface, (92, 87, 82), (cx + dx, cy), 3)
        else:
            pygame.draw.ellipse(surface, (205, 176, 112), (cx - 26, cy - 8, 52, 16), 5)
            pygame.draw.line(surface, (92, 87, 82), (cx, cy - 23), (cx, cy + 23), 3)
