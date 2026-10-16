"""Venus entry: Earth-size comparison, greenhouse heat, clouds and reverse spin."""

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
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_presenter, grid_step


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

# E4 authored scene; a missing rendition fails soft to the procedural fallback.
SCENE_ID = "encyclopedia.space.venus.observatory"


class VenusPage(EncyclopediaPage):
    page_id = "space.venus"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
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
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.venus.intro")
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
        self._compare_age = max(0.0, self._compare_age - dt)
        self._heat_age = max(0.0, self._heat_age - dt)
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
        authored = draw_authored_scene(surface, self.context.visuals, SCENE_ID)
        if not authored:
            surface.fill((27, 30, 58))
            for index in range(32):
                x = (index * 89 + 17) % 1000
                y = 78 + (index * 57) % 470
                pygame.draw.circle(surface, (228, 231, 242), (x, y), 1)
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("venus.title"),
            (246, 239, 215),
        )
        self._draw_venus(surface, authored=authored)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_entry_action_button(
            surface, (512, 460), entry="venus", time=getattr(self, '_time', 0.0), active=True
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

    def _draw_venus(self, surface: pygame.Surface, *, authored: bool) -> None:
        center = (505, 326)
        radius = 96

        # The authored scene bakes the cloud-covered planet. The rocky surface
        # is drawn only when needed: always in the fallback (under procedural
        # clouds) and over the authored clouds when the child lifts them.
        if not authored or self._clouds_hidden:
            self._draw_rocky_surface_and_clouds(surface, center, radius, authored=authored)

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

    def _draw_rocky_surface_and_clouds(
        self,
        surface: pygame.Surface,
        center: tuple[int, int],
        radius: int,
        *,
        authored: bool,
    ) -> None:
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

        if not self._clouds_hidden and not authored:
            pygame.draw.circle(surface, (222, 185, 103), center, radius)
            # Volumetric highlight
            hl = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(hl, (255, 235, 190, 32), (radius // 2, 8, radius, radius // 3))
            surface.blit(hl, (center[0] - radius, center[1] - radius))
            for index in range(8):
                y = center[1] - 65 + index * 19
                wave = int(math.sin(self._time * 0.45 + index) * 8)
                wobble = int(math.cos(self._time * 0.33 + index * 0.7) * 3)
                pygame.draw.arc(
                    surface,
                    (242, 218, 154),
                    (center[0] - 82 + wave, y - 8 + wobble, 164, 30),
                    0.05,
                    3.05,
                    5,
                )
                pygame.draw.arc(surface, (255, 245, 210, 22), (center[0] - 78 + wave, y - 6 + wobble, 156, 24), 0.05, 3.05, 2)

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
        if discovery_id == "compare":
            pygame.draw.circle(surface, (219, 181, 101), (cx - 13, cy), 18)
            pygame.draw.circle(surface, (72, 145, 215), (cx + 18, cy + 4), 17)
        elif discovery_id == "heat":
            pygame.draw.circle(surface, (219, 181, 101), (cx, cy), 17)
            for ring in (22, 28):
                pygame.draw.arc(surface, (232, 99, 51), (cx - ring, cy - ring, ring * 2, ring * 2), 0.3, 2.6, 3)
        elif discovery_id == "clouds":
            pygame.draw.circle(surface, (169, 104, 66), (cx, cy + 4), 20)
            pygame.draw.arc(surface, (232, 210, 155), (cx - 25, cy - 17, 50, 24), 0.1, 3.0, 6)
        else:
            pygame.draw.arc(surface, (219, 181, 101), (cx - 23, cy - 23, 46, 46), 0.2, 4.9, 5)
            pygame.draw.polygon(surface, (219, 181, 101), [(cx - 20, cy - 8), (cx - 29, cy + 2), (cx - 13, cy + 3)])

    def _draw_caption(self, surface: pygame.Surface) -> None:
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
            dark=True,
        )
