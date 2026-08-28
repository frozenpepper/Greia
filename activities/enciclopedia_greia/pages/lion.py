"""Lion golden master: authored hero scene plus four tactile discoveries."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        TOKEN_SHAPE_FELT_TAG,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_title,
    )
    from .common import draw_presenter, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        TOKEN_SHAPE_FELT_TAG,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_title,
    )
    from pages.common import draw_presenter, grid_step


@dataclass(frozen=True, slots=True)
class LionDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    LionDiscovery("mane", "lion.mane", "encyclopedia.animals.lion.mane", (235, 195)),
    LionDiscovery("pride", "lion.pride", "encyclopedia.animals.lion.pride", (775, 195)),
    LionDiscovery("roar", "lion.roar", "encyclopedia.animals.lion.roar", (235, 405)),
    LionDiscovery(
        "forelegs",
        "lion.forelegs",
        "encyclopedia.animals.lion.forelegs",
        (775, 405),
    ),
)


class LionPage(EncyclopediaPage):
    page_id = "animals.lion"

    def __init__(self, context) -> None:
        super().__init__(context)
        self._selected = 0
        self._hovered: int | None = None
        self._mane_state = 0
        self._pride_age = 0.0
        self._roar_age = 0.0
        self._foreleg_age = 0.0
        self._caption_key = "lion.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 50, cy - 50, 100, 100)
            for cx, cy in (item.center for item in DISCOVERIES)
        )

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.animals.lion.intro")

    def update(self, dt: float) -> None:
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
        if discovery.discovery_id == "mane":
            self._mane_state = (self._mane_state + 1) % 3
        elif discovery.discovery_id == "pride":
            self._pride_age = 4.0
        elif discovery.discovery_id == "roar":
            self._roar_age = 3.0
        else:
            self._foreleg_age = 3.5
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        if not draw_authored_scene(
            surface,
            self.context.visuals,
            "encyclopedia.animals.lion.savanna",
        ):
            surface.fill((235, 216, 158))
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("lion.title"),
            self.context.palette.ink,
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
                token_shape=TOKEN_SHAPE_FELT_TAG,
            )
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
        )
        draw_presenter(
            surface,
            self.context.visuals,
            "tito",
            position=(130, 575),
            height=190,
            variant="happy",
            fallback_color=(247, 151, 77),
        )

    def _is_recent(self, discovery_id: str) -> bool:
        return (
            (discovery_id == "pride" and self._pride_age > 0)
            or (discovery_id == "roar" and self._roar_age > 0)
            or (discovery_id == "forelegs" and self._foreleg_age > 0)
        )

    def _draw_reveals(self, surface: pygame.Surface) -> None:
        if self._mane_state:
            # Two visible growth rings, growing outward, plus a mane
            # color shift to make the change clearly readable.
            outer = (125, 72, 40) if self._mane_state == 1 else (74, 54, 42)
            inner = (168, 100, 58) if self._mane_state == 1 else (122, 84, 58)
            pygame.draw.circle(
                surface,
                outer,
                (446, 336),
                96 + self._mane_state * 8,
                10,
            )
            pygame.draw.circle(
                surface,
                inner,
                (446, 336),
                80 + self._mane_state * 6,
                6,
            )
            # A few small "spike" marks showing the mane growing.
            import math
            for index in range(8):
                angle = index * (math.pi * 2 / 8) - math.pi / 2
                rx = 446 + int(math.cos(angle) * (108 + self._mane_state * 8))
                ry = 336 + int(math.sin(angle) * (108 + self._mane_state * 8))
                pygame.draw.circle(surface, (74, 54, 42), (rx, ry), 4)
        if self._pride_age > 0:
            for x in (620, 690, 755):
                pygame.draw.ellipse(surface, (202, 143, 70), (x - 22, 418, 44, 30))
                pygame.draw.circle(surface, (202, 143, 70), (x + 18, 420), 12)
        if self._roar_age > 0:
            for radius in (35, 58, 82):
                pygame.draw.arc(
                    surface,
                    (255, 229, 118),
                    (432 - radius, 327 - radius, radius * 2, radius * 2),
                    -0.5,
                    0.5,
                    4,
                )
        if self._foreleg_age > 0:
            for center in ((490, 520), (610, 520)):
                pygame.draw.ellipse(
                    surface,
                    (255, 218, 99),
                    (center[0] - 32, center[1] - 12, 64, 24),
                    5,
                )

    @staticmethod
    def _draw_icon(
        surface: pygame.Surface,
        center: tuple[int, int],
        discovery_id: str,
    ) -> None:
        cx, cy = center
        ink = (91, 65, 47)
        if discovery_id == "mane":
            pygame.draw.circle(surface, (143, 82, 45), center, 24)
            pygame.draw.circle(surface, (225, 161, 74), center, 13)
        elif discovery_id == "pride":
            for dx, dy in ((-18, 7), (0, -7), (18, 7)):
                pygame.draw.circle(surface, (205, 145, 72), (cx + dx, cy + dy), 10)
        elif discovery_id == "roar":
            for radius in (10, 20, 30):
                pygame.draw.arc(
                    surface,
                    (191, 120, 58),
                    (cx, cy - radius, radius * 2, radius * 2),
                    -0.6,
                    0.6,
                    4,
                )
        else:
            pygame.draw.ellipse(surface, (222, 157, 72), (cx - 24, cy - 10, 48, 30))
            for dx in (-12, 0, 12):
                pygame.draw.circle(surface, ink, (cx + dx, cy + 13), 3)
