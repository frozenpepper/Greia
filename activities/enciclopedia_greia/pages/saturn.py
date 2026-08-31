"""Saturn golden master: authored observatory scene plus low-cost factual reveals."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        TOKEN_SHAPE_TELESCOPE_CARD,
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_entry_action_button,
        draw_focus_patch,
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_presenter, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        TOKEN_SHAPE_TELESCOPE_CARD,
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_entry_action_button,
        draw_focus_patch,
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
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

        self._focus_audio = FocusAudioTracker()
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
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.saturn.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        disc = DISCOVERIES[self._selected]
        # Use helper that avoids ledger fragment
        cue = encyclopedia_focus_cue(disc.discovery_id, "name")
        if not self._focus_audio.announce_once(self.context.audio, cue):
            self._focus_audio.announce_once(self.context.audio, disc.cue_id)

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(DISCOVERIES) - 1, index))
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def _trigger_main(self) -> None:
        self._activate(self._selected)
        # Announce is handled by _activate's audio; no extra cue needed
        disc = DISCOVERIES[0]
        cue = encyclopedia_focus_cue(disc.discovery_id, "name")
        announce_focus_name(self.context.audio, cue)

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
            if event.kind is PageInputKind.POINTER_PRESS:
                if self._action_hit.collidepoint(point):
                    self._trigger_main()
                    return
                if self._arrow_left_hit.collidepoint(point):
                    self._set_selected(self._selected - 1)
                    return
                if self._arrow_right_hit.collidepoint(point):
                    self._set_selected(self._selected + 1)
                    return
            hit = next(
                (index for index, rect in enumerate(self._hotspots) if rect.collidepoint(point)),
                None,
            )
            if event.kind is PageInputKind.POINTER_MOVE and hit is not None and hit != self._selected:
                disc = DISCOVERIES[hit]
                cue = encyclopedia_focus_cue(disc.discovery_id, "name")
                self._focus_audio.announce_once(self.context.audio, cue)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            if DISCOVERIES[self._selected].discovery_id == DISCOVERIES[0].discovery_id:
                self._trigger_main()
                return
            self._activate(self._selected)
        # Announce is handled by _activate's audio; no extra cue needed
            return
        prev = self._selected
        self._selected = grid_step(
            self._selected,
            event.command,
            columns=2,
            count=len(DISCOVERIES),
        )
        if self._selected != prev:
            self._announce_selected()
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
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_entry_action_button(
            surface, (512, 485), entry="saturn", time=getattr(self, '_time', 0.0), active=True
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
            # More detailed ring particles with shadow and highlight
            for index in range(32):
                angle = self._time * 0.32 + index * 0.68
                base_r = 148 + (index % 5) * 8
                x = 510 + int(math.cos(angle) * base_r)
                y = 335 + int(math.sin(angle) * (base_r * 0.28))
                size = 2 + (index % 3)
                # Particle with highlight
                pygame.draw.circle(surface, (210, 198, 165), (x + 1, y + 1), size)
                pygame.draw.circle(surface, (246, 232, 197), (x, y), size)
                pygame.draw.circle(surface, (255, 255, 255, 38), (x - 1, y - 1), max(1, size // 2))
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
