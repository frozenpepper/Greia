"""Octopus final-entry pilot: arms, camouflage, ink and three hearts."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        TOKEN_SHAPE_FELT_TAG,
        announce_focus_name,
        draw_animal_action_button,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_presenter, grid_step
    from .storybook_ink import inked_ellipse, inked_limb
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        TOKEN_SHAPE_FELT_TAG,
        announce_focus_name,
        draw_animal_action_button,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_presenter, grid_step
    from pages.storybook_ink import inked_ellipse, inked_limb


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

        self._focus_audio = FocusAudioTracker()
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
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.animals.octopus.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        disc = DISCOVERIES[self._selected]
        cue = encyclopedia_focus_cue(disc.discovery_id, "name")
        # Use deduped announce for focus changes
        if not self._focus_audio.announce_once(self.context.audio, cue):
            # Fallback to disc.cue_id if focus cue not yet integrated (will fail silently until audio exists)
            self._focus_audio.announce_once(self.context.audio, disc.cue_id)

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(DISCOVERIES) - 1, index))
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def _trigger_main(self) -> None:
        # Playful reaction — ink burst is most memorable
        self._ink_age = 2.6
        self._caption_key = "octopus.ink"
        announce_focus_name(self.context.audio, encyclopedia_focus_cue("animals", "octopus", "ink", "name"))
        self.context.audio.play("encyclopedia.animals.octopus.ink")

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
            if event.kind is PageInputKind.POINTER_PRESS:
                if (
                    self._action_hit.collidepoint(point)
                    or math.hypot(point[0] - 505, point[1] - 335) <= 100
                ):
                    self._trigger_main()
                    return
                if self._arrow_left_hit.collidepoint(point):
                    self._set_selected(self._selected - 1)
                    return
                if self._arrow_right_hit.collidepoint(point):
                    self._set_selected(self._selected + 1)
                    return
            hit = next(
                (i for i, rect in enumerate(self._hotspots) if rect.collidepoint(point)),
                None,
            )
            if event.kind is PageInputKind.POINTER_MOVE and hit is not None and hit != self._selected:
                disc = DISCOVERIES[hit]
                cue = encyclopedia_focus_cue("animals", "octopus", disc.discovery_id, "name")
                self._focus_audio.announce_once(self.context.audio, cue)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            if DISCOVERIES[self._selected].discovery_id == "ink":
                self._trigger_main()
                return
            self._activate(self._selected)
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
        if not draw_authored_scene(surface, self.context.visuals, "encyclopedia.animals.octopus.reef"):
            # Procedural fallback while the authored runtime rendition is absent.
            surface.fill((77, 156, 184))
            pygame.draw.rect(surface, (46, 116, 145), (0, 470, 1024, 130))
            pygame.draw.ellipse(surface, (198, 177, 130), (-40, 505, 1110, 150))
            for x in (95, 155, 850, 905):
                sway = int(math.sin(self._time * 1.4 + x) * 7)
                pygame.draw.line(surface, (74, 139, 89), (x, 550), (x + sway, 360), 12)
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("octopus.title"),
            self.context.palette.ink,
        )

        self._draw_octopus(surface)
        self._draw_hotspots(surface)
        # Unified focus chrome
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_animal_action_button(
            surface, (512, 460), animal="octopus", time=self._time, active=True
        )
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
        # Soft contact shadow beneath body — shallow depth
        shadow = pygame.Surface((140, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (40, 35, 50, 30), shadow.get_rect())
        surface.blit(shadow, (center[0] - 70, center[1] + 62))
        # Gentle ambient sway for arms — low-cost, not obscuring
        sway_phase = self._time * 0.9
        arm_paths = (
            ((475, 340), (440 + int(math.sin(sway_phase) * 3), 380), (400 + int(math.sin(sway_phase + 0.5) * 2), 415), (350, 430)),
            ((485, 345), (465, 395), (445, 440), (420, 475)),
            ((495, 346), (490, 405), (485, 455), (470, 500)),
            ((505, 348), (515, 405), (525, 455), (535, 500)),
            ((515, 346), (545, 395), (570, 440), (595, 475)),
            ((525, 340), (570, 380), (610 + int(math.cos(sway_phase) * 3), 415), (660, 430)),
            ((485, 335), (420, 350), (365, 345), (320, 325)),
            ((520, 335), (585, 350), (645, 345), (695, 320)),
        )
        light = tuple(min(255, channel + 48) for channel in color)
        for path in arm_paths:
            inked_limb(surface, color, path, (22, 19, 15))
            # Subtle sucker hint even without activation — tactile
            for point in (path[2], path[3]):
                pygame.draw.circle(surface, light, (point[0], point[1] + 3), 3)
        # Head (mantle) with one highlight, then a friendly face.
        inked_ellipse(surface, color, (445, 215, 120, 145))
        pygame.draw.ellipse(surface, light, (462, 228, 40, 22))
        for ex in (482, 528):
            pygame.draw.circle(surface, (255, 251, 235), (ex, 270), 14)
            pygame.draw.circle(surface, (75, 55, 47), (ex, 270), 14, 2)
            pygame.draw.circle(surface, (52, 44, 53), (ex + 2, 273), 7)
            pygame.draw.circle(surface, (255, 255, 255), (ex - 1, 268), 3)
        pygame.draw.arc(surface, (75, 55, 47), (493, 290, 24, 14), math.pi + 0.4, 2 * math.pi - 0.4, 3)
        pygame.draw.ellipse(surface, (253, 164, 175), (458, 290, 18, 10))
        pygame.draw.ellipse(surface, (253, 164, 175), (534, 290, 18, 10))

        if self._sucker_age > 0:
            for arm in arm_paths[:6]:
                for x, y in arm[1:]:
                    # Suckers with highlight
                    pygame.draw.circle(surface, (248, 224, 201), (x, y + 7), 6, 2)
                    pygame.draw.circle(surface, (255, 245, 230), (x - 1, y + 6), 2)
                    pygame.draw.circle(surface, (240, 210, 185), (x, y + 7), 2)
            # Arm shimmer when suckers active
            shimmer = pygame.Surface((1024, 600), pygame.SRCALPHA)
            for path in arm_paths[:3]:
                for px, py in path[1:]:
                    pygame.draw.circle(shimmer, (255, 255, 255, 22), (px, py), 14)
            surface.blit(shimmer, (0, 0))
        if self._heart_age > 0:
            # Three hearts plus pulsing glow
            pulse = 0.5 + 0.5 * math.sin(self._time * 6.0)
            for dx, dy in ((-26, 0), (0, -16), (26, 0)):
                self._draw_heart(surface, (center[0] + dx, center[1] + dy), 10 + int(pulse * 2))
            glow = pygame.Surface((90, 48), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (220, 100, 120, int(28 + pulse * 18)), glow.get_rect())
            surface.blit(glow, (center[0] - 45, center[1] - 12))
        if self._ink_age > 0:
            progress = 1.0 - self._ink_age / 2.6
            # Ink cloud with soft outer haze and inner core
            for i in range(22):
                angle = i * 0.62 + self._time * 0.32
                radius = 14 + int(progress * (38 + (i % 5) * 9))
                x = 650 + int(math.cos(angle) * radius)
                y = 330 + int(math.sin(angle) * radius * 0.62)
                size = 9 + (i % 4) * 3
                # Outer haze
                haze = pygame.Surface((size * 2 + 8, size * 2 + 8), pygame.SRCALPHA)
                pygame.draw.circle(haze, (35, 38, 55, 90), (size + 4, size + 4), size + 2)
                surface.blit(haze, (x - size - 4, y - size - 4))
                pygame.draw.circle(surface, (35, 38, 55), (x, y), size)
                pygame.draw.circle(surface, (65, 68, 85), (x - 2, y - 2), max(1, size // 3))
                pygame.draw.circle(surface, (85, 88, 105, 70), (x - 3, y - 3), max(1, size // 4))

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
        if discovery_id == "arms":
            pygame.draw.line(
                surface,
                (183, 103, 173),
                (center[0] - 20, center[1] + 15),
                (center[0] + 20, center[1] - 15),
                10,
            )
            for n in range(4):
                pygame.draw.circle(
                    surface,
                    (227, 170, 204),
                    (center[0] - 14 + n * 10, center[1] + 5 - n * 7),
                    4,
                )
        elif discovery_id == "camouflage":
            for n, swatch in enumerate(_BODY_COLORS):
                pygame.draw.circle(
                    surface,
                    swatch,
                    (
                        center[0] - 16 + (n % 2) * 32,
                        center[1] - 16 + (n // 2) * 32,
                    ),
                    10,
                )
        elif discovery_id == "ink":
            for dx, dy, radius in (
                (0, 0, 14),
                (-13, 8, 9),
                (14, 9, 10),
                (6, -12, 8),
            ):
                pygame.draw.circle(
                    surface,
                    (35, 38, 55),
                    (center[0] + dx, center[1] + dy),
                    radius,
                )
        else:
            for dx, dy in ((-14, 6), (0, -8), (14, 6)):
                self._draw_heart(
                    surface,
                    (center[0] + dx, center[1] + dy),
                    7,
                )

    def _draw_caption(self, surface: pygame.Surface) -> None:
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
        )

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
