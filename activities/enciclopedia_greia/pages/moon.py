"""Moon entry: phases, synchronous rotation, surface and low gravity."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from greia_platform.typography import FontRole

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        announce_focus_name,
        draw_entry_action_button,
        draw_focus_patch,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_centered_text, draw_presenter, focus_ring, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        announce_focus_name,
        draw_entry_action_button,
        draw_focus_patch,
        draw_navigation_arrows,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_centered_text, draw_presenter, focus_ring, grid_step


@dataclass(frozen=True, slots=True)
class MoonDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    MoonDiscovery("phases", "moon.phases", "encyclopedia.space.moon.phases", (250, 190)),
    MoonDiscovery("rotation", "moon.rotation", "encyclopedia.space.moon.rotation", (755, 190)),
    MoonDiscovery("surface", "moon.surface", "encyclopedia.space.moon.surface", (250, 420)),
    MoonDiscovery("gravity", "moon.gravity", "encyclopedia.space.moon.gravity", (755, 420)),
)


class MoonPhaseModel:
    """Own phase/orbit state; renderer only visualizes its finite geometry."""

    def __init__(self) -> None:
        self.phase_index = 4
        self.orbit_angle = 0.0
        self.orbit_demo_age = 0.0
        self.surface_age = 0.0
        self.gravity_age = 0.0

    def update(self, dt: float) -> None:
        if self.orbit_demo_age > 0.0:
            self.orbit_demo_age = max(0.0, self.orbit_demo_age - dt)
            self.orbit_angle = (self.orbit_angle + dt * 0.85) % math.tau
        self.surface_age = max(0.0, self.surface_age - dt)
        self.gravity_age = max(0.0, self.gravity_age - dt)

    def next_phase(self) -> None:
        self.phase_index = (self.phase_index + 1) % 8

    def demonstrate_rotation(self) -> None:
        self.orbit_demo_age = 5.0
        self.orbit_angle = 0.0

    def show_surface(self) -> None:
        self.surface_age = 4.5

    def show_gravity(self) -> None:
        self.gravity_age = 4.5


class MoonPage(EncyclopediaPage):
    page_id = "space.moon"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._model = MoonPhaseModel()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "moon.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.space.moon.intro")
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
        self._model.update(dt)

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
        if discovery.discovery_id == "phases":
            self._model.next_phase()
        elif discovery.discovery_id == "rotation":
            self._model.demonstrate_rotation()
        elif discovery.discovery_id == "surface":
            self._model.show_surface()
        else:
            self._model.show_gravity()
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((18, 24, 52))
        for index in range(34):
            x = (index * 101 + 19) % 1000
            y = 78 + (index * 59) % 470
            pygame.draw.circle(surface, (227, 233, 245), (x, y), 1)
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("moon.title"),
            center=(500, 92),
            size=40,
            color=(245, 241, 221),
            role=FontRole.DISPLAY,
        )
        self._draw_moon(surface)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_entry_action_button(
            surface, (512, 485), entry="moon", time=getattr(self, '_time', 0.0), active=True
        )
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "leo",
            position=(925, 565),
            height=142,
            variant="default",
            fallback_color=(227, 174, 87),
        )

    def _draw_moon(self, surface: pygame.Surface) -> None:
        center = (505, 326)
        radius = 92

        if self._model.orbit_demo_age > 0.0:
            earth = center
            orbit = pygame.Rect(385, 243, 240, 166)
            pygame.draw.circle(surface, (69, 143, 214), earth, 35)
            pygame.draw.arc(surface, (91, 178, 104), (486, 308, 38, 28), 0.1, 3.0, 5)
            pygame.draw.ellipse(surface, (78, 87, 118), orbit, 2)
            angle = self._model.orbit_angle
            moon_pos = (
                orbit.centerx + int(math.cos(angle) * orbit.width / 2),
                orbit.centery + int(math.sin(angle) * orbit.height / 2),
            )
            pygame.draw.circle(surface, (189, 187, 181), moon_pos, 18)
            # The marked near-side patch rotates with the Moon at the same rate
            # as its orbit, keeping it aimed toward Earth in this schematic.
            inward = angle + math.pi
            marker = (
                moon_pos[0] + int(math.cos(inward) * 9),
                moon_pos[1] + int(math.sin(inward) * 9),
            )
            pygame.draw.circle(surface, (88, 86, 83), marker, 5)
            pygame.draw.circle(surface, (251, 204, 70), (330, 326), 24)
            return

        pygame.draw.circle(surface, (67, 68, 75), center, radius)
        self._draw_phase(surface, center, radius, self._model.phase_index)

        if self._model.surface_age > 0.0:
            for dx, dy, crater_radius in (
                (-38, -28, 17),
                (30, -43, 12),
                (44, 18, 18),
                (-20, 43, 13),
                (4, 4, 9),
            ):
                x, y = center[0] + dx, center[1] + dy
                pygame.draw.circle(surface, (126, 125, 122), (x, y), crater_radius)
                pygame.draw.circle(surface, (206, 205, 198), (x - 3, y - 3), max(3, crater_radius - 5), 2)
            for rect in (
                pygame.Rect(447, 302, 48, 26),
                pygame.Rect(510, 345, 55, 31),
                pygame.Rect(493, 270, 37, 21),
            ):
                pygame.draw.ellipse(surface, (105, 106, 109), rect)

        if self._model.gravity_age > 0.0:
            ground_y = 447
            pygame.draw.line(surface, (205, 201, 188), (410, ground_y), (600, ground_y), 3)
            phase = (self._time * 0.8) % 1.0
            earth_x = 438
            moon_x = 560
            earth_y = ground_y - int(42 * 4 * phase * (1 - phase))
            moon_y = ground_y - int(88 * 4 * phase * (1 - phase))
            pygame.draw.circle(surface, (91, 181, 103), (earth_x, earth_y), 8)
            pygame.draw.circle(surface, (230, 215, 138), (moon_x, moon_y), 8)
            draw_centered_text(
                surface,
                self.context.typography,
                "1g",
                center=(earth_x, ground_y + 20),
                size=16,
                color=(225, 222, 210),
                role=FontRole.CONTROL,
            )
            draw_centered_text(
                surface,
                self.context.typography,
                "≈1/6g",
                center=(moon_x, ground_y + 20),
                size=16,
                color=(225, 222, 210),
                role=FontRole.CONTROL,
            )

    @staticmethod
    def _draw_phase(
        surface: pygame.Surface,
        center: tuple[int, int],
        radius: int,
        phase_index: int,
    ) -> None:
        """Draw one of eight deterministic phase silhouettes.

        This is a child-readable schematic, not a photometric lunar renderer.
        The lit fraction changes across a single fixed circular Moon.
        """
        lit = (214, 213, 207)
        dark = (67, 68, 75)
        pygame.draw.circle(surface, lit if phase_index == 4 else dark, center, radius)
        if phase_index == 0:
            return
        if phase_index == 4:
            return

        previous_clip = surface.get_clip()
        cx, cy = center
        if phase_index in (1, 2, 3):
            surface.set_clip(pygame.Rect(cx, cy - radius, radius, radius * 2))
            pygame.draw.circle(surface, lit, center, radius)
        else:
            surface.set_clip(pygame.Rect(cx - radius, cy - radius, radius, radius * 2))
            pygame.draw.circle(surface, lit, center, radius)
        surface.set_clip(previous_clip)

        if phase_index in (1, 3, 5, 7):
            width = int(radius * (1.12 if phase_index in (1, 7) else 0.56))
            overlay = pygame.Rect(cx - width // 2, cy - radius, width, radius * 2)
            pygame.draw.ellipse(
                surface,
                dark if phase_index in (1, 7) else lit,
                overlay,
            )

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (248, 245, 228), item.center, 37)
            pygame.draw.circle(surface, (70, 61, 58), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "phases":
                pygame.draw.circle(surface, (76, 77, 83), (cx, cy), 20)
                previous_clip = surface.get_clip()
                surface.set_clip(pygame.Rect(cx, cy - 20, 20, 40))
                pygame.draw.circle(surface, (214, 213, 207), (cx, cy), 20)
                surface.set_clip(previous_clip)
            elif item.discovery_id == "rotation":
                pygame.draw.circle(surface, (69, 143, 214), (cx - 5, cy), 10)
                pygame.draw.ellipse(surface, (143, 146, 155), (cx - 28, cy - 20, 56, 40), 3)
                pygame.draw.circle(surface, (190, 188, 182), (cx + 25, cy), 7)
            elif item.discovery_id == "surface":
                pygame.draw.circle(surface, (187, 185, 179), (cx, cy), 21)
                pygame.draw.circle(surface, (120, 119, 116), (cx - 7, cy - 5), 7)
                pygame.draw.ellipse(surface, (103, 104, 108), (cx + 4, cy + 3, 16, 9))
            else:
                pygame.draw.circle(surface, (69, 143, 214), (cx - 13, cy), 12)
                pygame.draw.circle(surface, (190, 188, 182), (cx + 17, cy), 8)
                pygame.draw.line(surface, (239, 198, 77), (cx - 13, cy + 19), (cx + 17, cy + 30), 4)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (248, 245, 228), panel, border_radius=22)
        pygame.draw.rect(surface, (70, 61, 58), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (54, 49, 58))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (54, 49, 58))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
