"""Rainbow entry: viewing geometry, droplet optics, color separation, circular bow."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame
import pygame.gfxdraw

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        TOKEN_SHAPE_FELT_TAG,
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_entry_action_button,
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_presenter, grid_step
    from .storybook_ink import inked_circle
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        TOKEN_SHAPE_FELT_TAG,
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_entry_action_button,
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_presenter, grid_step
    from pages.storybook_ink import inked_circle


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


def _draw_band(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    center: tuple[int, int],
    radius_x: int,
    radius_y: int,
    thickness: int,
) -> None:
    """Fill one upper-half rainbow band as a single anti-aliased polygon."""

    cx, cy = center
    steps = 36
    outer = [
        (cx + math.cos(math.pi * i / steps) * radius_x, cy - math.sin(math.pi * i / steps) * radius_y)
        for i in range(steps + 1)
    ]
    inner = [
        (
            cx + math.cos(math.pi * i / steps) * (radius_x - thickness),
            cy - math.sin(math.pi * i / steps) * (radius_y - thickness),
        )
        for i in range(steps, -1, -1)
    ]
    points = [(int(round(x)), int(round(y))) for x, y in outer + inner]
    pygame.draw.polygon(surface, color, points)
    pygame.gfxdraw.aapolygon(surface, points, color)


class RainbowPage(EncyclopediaPage):
    page_id = "earth.rainbow"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
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
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    @property
    def _aligned(self) -> bool:
        return self._alignment_step == 2

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.earth.rainbow.intro")
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
        self._droplet_age = max(0.0, self._droplet_age - dt)
        self._colors_age = max(0.0, self._colors_age - dt)
        self._circle_age = max(0.0, self._circle_age - dt)

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
        authored = draw_authored_scene(surface, self.context.visuals, "encyclopedia.earth.rainbow.shower")
        if not authored:
            # Procedural fallback while the authored runtime rendition is absent.
            surface.fill((176, 221, 240))
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("rainbow.title"),
            self.context.palette.ink,
        )
        self._draw_rainbow_scene(surface, authored=authored)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_entry_action_button(
            surface, (512, 460), entry="rainbow", time=getattr(self, '_time', 0.0), active=True
        )
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

    def _draw_rainbow_scene(self, surface: pygame.Surface, *, authored: bool) -> None:
        if not authored:
            # Fallback meadow, observer and shower (baked in the authored scene).
            pygame.draw.rect(surface, (104, 173, 91), (0, 405, 1024, 195))
            viewer = (505, 390)
            pygame.draw.circle(surface, (238, 198, 151), (viewer[0], viewer[1] - 33), 12)
            pygame.draw.line(surface, (74, 70, 68), (viewer[0], viewer[1] - 20), (viewer[0], viewer[1] + 16), 5)
            for index in range(18):
                x = 420 + (index * 37) % 180
                y = 188 + (index * 53) % 115
                pygame.draw.line(surface, (78, 151, 201), (x, y), (x - 4, y + 13), 3)

        sun_positions = ((370, 310), (650, 260), (505, 475))
        sun = sun_positions[self._alignment_step]
        inked_circle(surface, (255, 210, 94), sun, 27)
        pygame.draw.ellipse(surface, (255, 243, 196), (sun[0] - 15, sun[1] - 16, 14, 9))
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
            # Sun rays to viewer with glow
            for y in range(435, 285, -22):
                pygame.draw.line(surface, (246, 203, 73), (505, y), (505, y - 12), 3)
                pygame.draw.circle(surface, (255, 235, 140, 60), (505, y - 6), 4)
            # Rainbow with soft outer glow and inner highlight
            for index, color in enumerate(_COLORS):
                inset = index * 7
                # Solid polygon bands avoid the moire gaps of thick arcs.
                _draw_band(surface, color, (505, 312), 155 - inset, 122 - inset, 8)

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
            if authored:
                # From the ground only the top half shows; the hidden lower
                # half is hinted with faint dots instead of masking the child.
                for index, color in enumerate(_COLORS):
                    radius = 105 - index * 8
                    _draw_band(surface, color, main_center, radius, radius, 7)
                    for step in range(1, 12):
                        angle = math.pi + step * math.pi / 12
                        dot = (
                            main_center[0] + int(math.cos(angle) * radius),
                            main_center[1] - int(math.sin(angle) * radius),
                        )
                        pygame.draw.circle(surface, color, dot, 2)
            else:
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
        for index, item in enumerate(DISCOVERIES):
            draw_discovery_token(
                surface,
                item.center,
                selected=index == self._selected,
                hovered=index == self._hovered,
                recently_activated=item.caption_key == self._caption_key,
                icon=lambda target, center, item=item: self._draw_icon(
                    target,
                    center,
                    item.discovery_id,
                ),
                token_shape=TOKEN_SHAPE_FELT_TAG,
            )

    def _draw_icon(
        self,
        surface: pygame.Surface,
        center: tuple[int, int],
        discovery_id: str,
    ) -> None:
        cx, cy = center[0], center[1] + 4  # sit below the felt tag's pin
        center = (cx, cy)
        if discovery_id == "position":
            pygame.draw.circle(surface, (248, 204, 65), (cx - 17, cy + 9), 9)
            pygame.draw.circle(surface, (235, 198, 151), (cx + 1, cy + 8), 6)
            for off in (-8, 7, 22):
                pygame.draw.line(surface, (81, 151, 199), (cx + 12 + off, cy - 18), (cx + 8 + off, cy - 5), 3)
        elif discovery_id == "droplet":
            pygame.draw.circle(surface, (211, 237, 246), (cx, cy), 22)
            pygame.draw.line(surface, (245, 221, 112), (cx - 27, cy - 9), (cx + 19, cy + 13), 4)
        elif discovery_id == "colors":
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

    def _draw_caption(self, surface: pygame.Surface) -> None:
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
        )
