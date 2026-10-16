"""Sun entry: star/plasma, scale, fusion and differential rotation."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        TOKEN_SHAPE_TELESCOPE_CARD,
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
    from .common import draw_centered_text, draw_presenter, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        TOKEN_SHAPE_TELESCOPE_CARD,
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
    from pages.common import draw_centered_text, draw_presenter, grid_step


@dataclass(frozen=True, slots=True)
class SunDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    SunDiscovery("plasma", "sun.plasma", "encyclopedia.space.sun.plasma", (250, 190)),
    SunDiscovery("scale", "sun.scale", "encyclopedia.space.sun.scale", (755, 190)),
    SunDiscovery("fusion", "sun.fusion", "encyclopedia.space.sun.fusion", (250, 420)),
    SunDiscovery("rotation", "sun.rotation", "encyclopedia.space.sun.rotation", (755, 420)),
)

# E4-B authored observatory scene. The Sun disc/corona is baked at the same
# center/radius the reveal overlays use; a missing rendition fails soft to the
# procedural star field and Sun below.
SCENE_ID = "encyclopedia.space.sun.observatory"
SUN_CENTER = (505, 326)
SUN_RADIUS = 112


class SunPage(EncyclopediaPage):
    page_id = "space.sun"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "sun.intro"
        self._plasma_age = 0.0
        self._scale_age = 0.0
        self._fusion_age = 0.0
        self._rotation_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.sun.intro")
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
        self._plasma_age = max(0.0, self._plasma_age - dt)
        self._scale_age = max(0.0, self._scale_age - dt)
        self._fusion_age = max(0.0, self._fusion_age - dt)
        self._rotation_age = max(0.0, self._rotation_age - dt)

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
        if discovery.discovery_id == "plasma":
            self._plasma_age = 4.0
        elif discovery.discovery_id == "scale":
            self._scale_age = 4.0
        elif discovery.discovery_id == "fusion":
            self._fusion_age = 4.0
        else:
            self._rotation_age = 4.0
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        authored = draw_authored_scene(surface, self.context.visuals, SCENE_ID)
        if not authored:
            surface.fill((18, 25, 57))
            for index in range(34):
                x = (index * 97 + 23) % 1000
                y = 80 + (index * 53) % 470
                pygame.draw.circle(surface, (229, 235, 246), (x, y), 1)
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("sun.title"),
            (248, 240, 207),
        )
        self._draw_sun(surface, authored=authored)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_entry_action_button(
            surface, (512, 460), entry="sun", time=getattr(self, '_time', 0.0), active=True
        )
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

    def _draw_sun(self, surface: pygame.Surface, *, authored: bool) -> None:
        center = SUN_CENTER
        radius = SUN_RADIUS
        if not authored:
            self._draw_fallback_sun(surface)
        self._draw_reveals(surface, center, radius)

    def _draw_fallback_sun(self, surface: pygame.Surface) -> None:
        center = SUN_CENTER
        radius = SUN_RADIUS
        pulse = int(4 * math.sin(self._time * 2.0))
        # Corona with soft glow
        glow = pygame.Surface((radius * 2 + 40, radius * 2 + 40), pygame.SRCALPHA)
        pygame.draw.circle(glow, (231, 116, 37, 38), (radius + 20, radius + 20), radius + 20, 8)
        pygame.draw.circle(glow, (248, 169, 48, 22), (radius + 20, radius + 20), radius + 14, 4)
        surface.blit(glow, (center[0] - radius - 20, center[1] - radius - 20))
        pygame.draw.circle(surface, (231, 116, 37), center, radius + 13 + pulse, 4)
        pygame.draw.circle(surface, (248, 169, 48), center, radius)
        # Inner highlight for depth
        hl = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(hl, (255, 235, 140, 40), (radius - 18, radius - 22), radius // 2)
        surface.blit(hl, (center[0] - radius, center[1] - radius))
        pygame.draw.circle(surface, (255, 206, 76), center, radius - 22)
        pygame.draw.circle(surface, (255, 230, 120, 30), center, radius - 30)

        for index in range(12):
            angle = self._time * 0.22 + index * math.tau / 12
            inner = 62 + (index % 3) * 9
            start = (
                center[0] + int(math.cos(angle) * inner),
                center[1] + int(math.sin(angle) * inner),
            )
            end = (
                center[0] + int(math.cos(angle + 0.42) * (inner + 24)),
                center[1] + int(math.sin(angle + 0.42) * (inner + 24)),
            )
            pygame.draw.line(surface, (255, 231, 120), start, end, 4)

    def _draw_reveals(
        self,
        surface: pygame.Surface,
        center: tuple[int, int],
        radius: int,
    ) -> None:
        if self._plasma_age > 0:
            pygame.draw.circle(surface, (255, 242, 156), center, radius - 8, 5)
            for index in range(6):
                angle = self._time * 0.8 + index * math.tau / 6
                x = center[0] + int(math.cos(angle) * 83)
                y = center[1] + int(math.sin(angle) * 83)
                pygame.draw.circle(surface, (255, 239, 141), (x, y), 8, 3)

        if self._fusion_age > 0:
            pygame.draw.circle(surface, (255, 249, 205), center, 29)
            for ring in range(4):
                phase = (self._time * 36 + ring * 26) % 94
                pygame.draw.circle(
                    surface,
                    (255, 232, 126),
                    center,
                    32 + int(phase),
                    2,
                )

        if self._rotation_age > 0:
            equator_angle = self._time * 1.45
            polar_angle = self._time * 0.78
            pygame.draw.ellipse(surface, (186, 91, 35), (395, 305, 220, 42), 2)
            pygame.draw.ellipse(surface, (186, 91, 35), (470, 214, 70, 220), 2)
            eq = (
                center[0] + int(math.cos(equator_angle) * 106),
                center[1] + int(math.sin(equator_angle) * 18),
            )
            pole = (
                center[0] + int(math.cos(polar_angle) * 30),
                center[1] + int(math.sin(polar_angle) * 104),
            )
            pygame.draw.circle(surface, (91, 70, 55), eq, 8)
            pygame.draw.circle(surface, (91, 70, 55), pole, 8)

        if self._scale_age > 0:
            earth_center = (630, 368)
            pygame.draw.circle(surface, (73, 146, 214), earth_center, 8)
            pygame.draw.arc(surface, (94, 182, 110), (624, 361, 11, 11), 0.2, 2.8, 3)
            badge = pygame.Rect(614, 391, 72, 38)
            pygame.draw.rect(surface, (250, 244, 218), badge, border_radius=14)
            draw_centered_text(
                surface,
                self.context.typography,
                "≈100×",
                center=badge.center,
                size=19,
                color=(52, 47, 63),
                role=FontRole.CONTROL,
            )

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, item in enumerate(DISCOVERIES):
            draw_discovery_token(
                surface,
                item.center,
                selected=index == self._selected,
                hovered=index == self._hovered,
                recently_activated=self._caption_key == item.caption_key,
                icon=lambda target, center, item=item: self._draw_icon(
                    target,
                    center,
                    item.discovery_id,
                ),
                token_shape=TOKEN_SHAPE_TELESCOPE_CARD,
            )

    def _draw_icon(
        self,
        surface: pygame.Surface,
        center: tuple[int, int],
        discovery_id: str,
    ) -> None:
        cx, cy = center
        if discovery_id == "plasma":
            pygame.draw.circle(surface, (247, 167, 49), (cx, cy), 19)
            pygame.draw.arc(surface, (230, 102, 36), (cx - 22, cy - 15, 44, 30), 0.2, 2.9, 4)
        elif discovery_id == "scale":
            pygame.draw.circle(surface, (247, 167, 49), (cx - 11, cy), 18)
            pygame.draw.circle(surface, (73, 146, 214), (cx + 21, cy + 7), 6)
        elif discovery_id == "fusion":
            pygame.draw.circle(surface, (255, 218, 81), (cx, cy), 19)
            pygame.draw.circle(surface, (255, 247, 194), (cx, cy), 8)
        else:
            pygame.draw.arc(surface, (231, 127, 45), (cx - 23, cy - 23, 46, 46), 0.2, 5.0, 5)
            pygame.draw.circle(surface, (73, 61, 57), (cx + 19, cy - 10), 4)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
            dark=True,
        )
