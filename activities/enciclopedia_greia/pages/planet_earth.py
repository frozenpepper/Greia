"""Earth-as-a-planet entry: rotation, water, seasons and atmosphere/life."""

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
class EarthDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    EarthDiscovery("rotation", "planet_earth.rotation", "encyclopedia.space.earth.rotation", (250, 190)),
    EarthDiscovery("water", "planet_earth.water", "encyclopedia.space.earth.water", (755, 190)),
    EarthDiscovery("seasons", "planet_earth.seasons", "encyclopedia.space.earth.seasons", (250, 420)),
    EarthDiscovery("life", "planet_earth.life", "encyclopedia.space.earth.life", (755, 420)),
)

# E4 authored scene; a missing rendition fails soft to the procedural fallback.
SCENE_ID = "encyclopedia.space.earth.observatory"


class EarthPlanetPage(EncyclopediaPage):
    page_id = "space.earth"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "planet_earth.intro"
        self._rotation_age = 0.0
        self._water_age = 0.0
        self._season_state = 0
        self._season_age = 0.0
        self._life_age = 0.0
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.earth.intro")
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
        self._rotation_age = max(0.0, self._rotation_age - dt)
        self._water_age = max(0.0, self._water_age - dt)
        self._season_age = max(0.0, self._season_age - dt)
        self._life_age = max(0.0, self._life_age - dt)

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
        if discovery.discovery_id == "rotation":
            self._rotation_age = 4.0
        elif discovery.discovery_id == "water":
            self._water_age = 4.0
        elif discovery.discovery_id == "seasons":
            self._season_state = 1 - self._season_state
            self._season_age = 4.5
        else:
            self._life_age = 4.0
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        authored = draw_authored_scene(surface, self.context.visuals, SCENE_ID)
        if not authored:
            surface.fill((17, 28, 60))
            for index in range(34):
                x = (index * 79 + 37) % 1000
                y = 78 + (index * 67) % 470
                pygame.draw.circle(surface, (224, 231, 244), (x, y), 1)
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("planet_earth.title"),
            (245, 241, 219),
        )
        self._draw_earth(surface, authored=authored)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_entry_action_button(
            surface, (512, 460), entry="earth", time=getattr(self, '_time', 0.0), active=True
        )
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "leo",
            position=(925, 565),
            height=142,
            variant="happy",
            fallback_color=(227, 174, 87),
        )

    def _draw_earth(self, surface: pygame.Surface, *, authored: bool) -> None:
        center = (505, 326)
        radius = 108
        angle = self._time * (1.15 if self._rotation_age > 0 else 0.20)

        # The authored observatory scene bakes the planet; only the fallback
        # draws the sprite/procedural globe.
        if not authored:
            # VisualLibrary owns package lookup, decode, scaling, and its bounded
            # cache. Test/dummy visual providers may omit planet(); in that case
            # use the existing procedural renderer rather than touching disk here.
            diam = radius * 2 + 8
            planet_loader = getattr(self.context.visuals, "planet", None)
            sprite = planet_loader("earth", diam) if callable(planet_loader) else None
            if sprite is not None:
                # Soft atmospheric glow behind the sprite
                glow_surf = pygame.Surface((diam + 18, diam + 18), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (128, 203, 242, 55), (diam // 2 + 9, diam // 2 + 9), radius + 12, 7)
                surface.blit(glow_surf, (center[0] - diam // 2 - 9, center[1] - diam // 2 - 9))
                surface.blit(sprite, sprite.get_rect(center=center))
                # Subtle terminator / highlight for depth when not in rotation demo
                if self._rotation_age == 0:
                    highlight = pygame.Surface((diam, diam), pygame.SRCALPHA)
                    pygame.draw.ellipse(highlight, (255, 255, 255, 18), (radius // 2, 6, radius, radius - 12))
                    surface.blit(highlight, (center[0] - radius, center[1] - radius))
                inner_shadow = pygame.Surface((diam, diam), pygame.SRCALPHA)
                pygame.draw.circle(inner_shadow, (0, 0, 0, 0), (radius, radius), radius)
                pygame.draw.circle(inner_shadow, (20, 40, 90, 22), (radius, radius), radius, 4)
                surface.blit(inner_shadow, (center[0] - radius, center[1] - radius))
            else:
                # Fallback procedural — more continents, clouds, depth
                pygame.draw.circle(surface, (128, 203, 242), center, radius + 7, 5)
                pygame.draw.circle(surface, (63, 137, 210), center, radius)
                # Volumetric highlight
                hl = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.ellipse(hl, (255, 255, 255, 26), (radius // 2, 10, radius, radius // 2))
                surface.blit(hl, (center[0] - radius, center[1] - radius))
                land_color = (96, 168, 92)
                land_dark = (76, 142, 71)
                land_light = (122, 192, 118)
                # Eight continents with varied sizes, slowly rotating — more realistic distribution
                for base_angle, spread, phase, jitter in (
                    (0.18, 0.52, 0.14, 0.0),
                    (0.95, 0.44, -0.18, 0.22),
                    (1.88, 0.58, 0.09, -0.15),
                    (2.75, 0.42, -0.10, 0.30),
                    (3.55, 0.48, 0.16, -0.18),
                    (4.42, 0.40, -0.06, 0.25),
                    (5.15, 0.46, 0.20, -0.28),
                    (5.95, 0.36, -0.09, 0.12),
                ):
                    theta = base_angle + angle * (0.90 + phase * 0.12)
                    r = 50 + 10 * math.sin(theta * 1.6 + jitter)
                    x = center[0] + int(math.cos(theta) * r)
                    y = center[1] + int(math.sin(theta) * (r * 0.66))
                    w = int(38 * spread + 12 * math.cos(theta + jitter))
                    h = int(26 * spread + 10 * math.sin(theta + jitter))
                    # Base land with subtle variation
                    pygame.draw.ellipse(surface, land_color, (x - w // 2, y - h // 2, w, h))
                    # Lighter edge for relief
                    pygame.draw.ellipse(surface, land_light, (x - w // 3, y - h // 3 - 2, w // 2, h // 3))
                    # Darker core
                    pygame.draw.ellipse(surface, land_dark, (x - w // 4, y - h // 4 + 1, w // 3, h // 3))
                # Cloud veil — layered, subtle, slowly drifting
                cloud = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                for ca, cr, alpha in ((0.75, 0.56, 36), (2.55, 0.50, 30), (4.65, 0.53, 34), (1.60, 0.48, 26)):
                    ct = ca + angle * 0.28
                    cx = radius + int(math.cos(ct) * (42 + 6 * math.sin(ct)))
                    cy = radius + int(math.sin(ct) * (28 + 4 * math.cos(ct)))
                    w, h = 48 + int(8 * math.cos(ct)), 22 + int(6 * math.sin(ct))
                    pygame.draw.ellipse(cloud, (255, 255, 255, alpha), (cx - w // 2, cy - h // 2, w, h))
                    pygame.draw.ellipse(cloud, (255, 255, 255, alpha - 8), (cx - w // 3, cy - h // 3, w // 2, h // 2))
                surface.blit(cloud, (center[0] - radius, center[1] - radius))
                # Subtle ocean texture — faint wave lines
                for wy in range(-radius + 18, radius - 12, 22):
                    y = center[1] + wy + int(2 * math.sin(angle + wy * 0.04))
                    pygame.draw.arc(surface, (71, 158, 221, 18), (center[0] - radius + 14, y, radius * 2 - 28, 14), 0.15, 3.0, 2)

        if self._rotation_age > 0:
            # Fixed Sun at left; clipped shade on the opposite half makes the
            # day/night relation visible without a lighting engine.
            pygame.draw.circle(surface, (250, 204, 65), (365, 326), 25)
            previous_clip = surface.get_clip()
            surface.set_clip(pygame.Rect(center[0], center[1] - radius - 8, radius + 12, radius * 2 + 16))
            pygame.draw.circle(surface, (26, 43, 78), center, radius)
            surface.set_clip(previous_clip)
            pygame.draw.line(surface, (231, 224, 183), (505, 232), (505, 420), 2)

        if self._water_age > 0:
            for index in range(8):
                y = 273 + index * 14
                pygame.draw.arc(
                    surface,
                    (157, 221, 246),
                    (438, y, 134, 25),
                    0.15,
                    2.9,
                    3,
                )

        if self._season_age > 0:
            tilt = -0.38 if self._season_state == 0 else 0.38
            length = 126
            dx = int(math.sin(tilt) * length / 2)
            dy = int(math.cos(tilt) * length / 2)
            pygame.draw.line(
                surface,
                (250, 224, 115),
                (center[0] - dx, center[1] + dy),
                (center[0] + dx, center[1] - dy),
                5,
            )
            north = (center[0] + dx, center[1] - dy)
            south = (center[0] - dx, center[1] + dy)
            pygame.draw.circle(surface, (255, 232, 127), north if self._season_state == 0 else south, 13, 3)
            pygame.draw.circle(surface, (181, 205, 230), south if self._season_state == 0 else north, 13, 3)

        if self._life_age > 0:
            # A few abstract leaf/wave marks signal known life without implying
            # exact geography or a complete biosphere inventory.
            for x, y, flip in ((470, 300, 1), (535, 285, -1), (520, 355, 1), (458, 360, -1)):
                pygame.draw.ellipse(surface, (196, 231, 114), (x - 9, y - 5, 18, 10))
                pygame.draw.line(surface, (77, 124, 70), (x, y), (x + 8 * flip, y - 12), 2)

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
        if discovery_id == "rotation":
            pygame.draw.circle(surface, (65, 139, 210), (cx, cy), 18)
            pygame.draw.arc(surface, (240, 194, 63), (cx - 25, cy - 25, 50, 50), 0.2, 4.9, 5)
        elif discovery_id == "water":
            pygame.draw.circle(surface, (65, 139, 210), (cx, cy), 20)
            pygame.draw.arc(surface, (162, 222, 245), (cx - 18, cy - 4, 36, 20), 0.2, 2.9, 4)
        elif discovery_id == "seasons":
            pygame.draw.circle(surface, (65, 139, 210), (cx, cy), 18)
            pygame.draw.line(surface, (239, 196, 72), (cx - 10, cy + 24), (cx + 10, cy - 24), 5)
        else:
            pygame.draw.circle(surface, (65, 139, 210), (cx, cy), 20)
            pygame.draw.ellipse(surface, (111, 181, 100), (cx - 12, cy - 8, 24, 16))
            pygame.draw.arc(surface, (159, 218, 244), (cx - 25, cy - 25, 50, 50), 0, math.tau, 4)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
            dark=True,
        )
