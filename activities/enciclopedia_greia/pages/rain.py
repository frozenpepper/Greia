"""Rain entry: a bounded, child-readable water-cycle demonstration."""

from __future__ import annotations

from dataclasses import dataclass

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
class RainDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    RainDiscovery("evaporation", "rain.evaporation", "encyclopedia.earth.rain.evaporation", (250, 190)),
    RainDiscovery("condensation", "rain.condensation", "encyclopedia.earth.rain.condensation", (755, 190)),
    RainDiscovery("precipitation", "rain.precipitation", "encyclopedia.earth.rain.precipitation", (250, 420)),
    RainDiscovery("ground", "rain.ground", "encyclopedia.earth.rain.ground", (755, 420)),
)


class WaterCycleModel:
    """Own the finite quantities used by the familiar rain-path demonstration."""

    def __init__(self) -> None:
        self.vapor = 0.0
        self.cloud = 0.25
        self.rain_age = 0.0
        self.ground_age = 0.0

    def update(self, dt: float) -> None:
        self.vapor = max(0.0, self.vapor - dt * 0.08)
        self.cloud = max(0.18, self.cloud - dt * 0.018)
        self.rain_age = max(0.0, self.rain_age - dt)
        self.ground_age = max(0.0, self.ground_age - dt)

    def evaporate(self) -> None:
        self.vapor = min(1.0, self.vapor + 0.45)

    def condense(self) -> None:
        # The visual demo may be requested directly; it does not require the
        # child to complete a rigid conveyor-belt sequence first.
        self.vapor = max(self.vapor, 0.35)
        self.cloud = min(1.0, self.cloud + 0.42)

    def precipitate(self) -> None:
        self.cloud = max(self.cloud, 0.72)
        self.rain_age = 4.2

    def show_ground_paths(self) -> None:
        self.ground_age = 4.5


class RainPage(EncyclopediaPage):
    page_id = "earth.rain"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._model = WaterCycleModel()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "rain.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = getattr(self, '_time', 0.0)
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.earth.rain.intro")
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
        if discovery.discovery_id == "evaporation":
            self._model.evaporate()
        elif discovery.discovery_id == "condensation":
            self._model.condense()
        elif discovery.discovery_id == "precipitation":
            self._model.precipitate()
        else:
            self._model.show_ground_paths()
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((176, 220, 238))
        draw_centered_text(
            surface,
            self.context.typography,
            self.context.resources.text("rain.title"),
            center=(500, 92),
            size=40,
            color=(53, 66, 72),
            role=FontRole.DISPLAY,
        )
        self._draw_cycle(surface)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=getattr(self, '_time', 0.0), can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_entry_action_button(
            surface, (512, 485), entry="rain", time=getattr(self, '_time', 0.0), active=True
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

    def _draw_cycle(self, surface: pygame.Surface) -> None:
        sun = (395, 210)
        # Sun with glow
        glow = pygame.Surface((80, 80), pygame.SRCALPHA)
        pygame.draw.circle(glow, (251, 211, 73, 38), (40, 40), 34)
        pygame.draw.circle(glow, (255, 230, 120, 22), (40, 40), 44)
        surface.blit(glow, (sun[0] - 40, sun[1] - 40))
        pygame.draw.circle(surface, (251, 211, 73), sun, 34)
        pygame.draw.circle(surface, (255, 235, 140), (sun[0] - 8, sun[1] - 8), 12)
        water = pygame.Rect(380, 407, 250, 86)
        # Water with highlight
        pygame.draw.ellipse(surface, (58, 140, 180), (382, 409, 250, 86))
        pygame.draw.ellipse(surface, (71, 159, 196), water)
        pygame.draw.ellipse(surface, (120, 185, 210), (410, 418, 80, 28))
        pygame.draw.polygon(surface, (115, 173, 91), [(350, 454), (450, 332), (535, 454)])
        pygame.draw.polygon(surface, (130, 188, 106), [(365, 452), (450, 344), (520, 452)])
        pygame.draw.rect(surface, (116, 85, 58), (577, 394, 20, 70), border_radius=6)
        pygame.draw.circle(surface, (84, 157, 76), (587, 375), 39)
        pygame.draw.circle(surface, (105, 175, 95), (582, 368), 18)

        vapor_count = int(round(self._model.vapor * 12))
        for index in range(vapor_count):
            x = 426 + (index % 4) * 29
            y = 405 - (index // 4) * 38 - int((self._time * 18 + index * 7) % 18)
            pygame.draw.arc(surface, (232, 242, 244), (x, y, 20, 28), 0.4, 2.7, 3)

        cloud_center = (570, 225)
        cloud_scale = 0.72 + self._model.cloud * 0.38
        blobs = ((-54, 8, 33), (-18, -11, 39), (22, -5, 42), (58, 10, 30), (3, 18, 45))
        for dx, dy, radius in blobs:
            rr = max(10, int(radius * cloud_scale))
            pygame.draw.circle(surface, (243, 246, 247), (cloud_center[0] + dx, cloud_center[1] + dy), rr)
        # Tiny droplets inside the cloud are deliberately visible only as a
        # teaching magnification, preventing the cloud from reading as vapor.
        if self._model.cloud > 0.5:
            for index in range(9):
                x = 523 + (index % 3) * 28
                y = 210 + (index // 3) * 17
                pygame.draw.circle(surface, (125, 185, 212), (x, y), 3)

        if self._model.rain_age > 0:
            for index in range(16):
                x = 505 + (index % 8) * 19
                fall = int((self._time * 115 + index * 27) % 150)
                y = 265 + fall
                pygame.draw.line(surface, (67, 142, 199), (x, y), (x - 5, y + 15), 3)

        if self._model.ground_age > 0:
            # Runoff follows the slope while infiltration heads into soil.
            pygame.draw.lines(surface, (68, 149, 196), False, [(467, 352), (500, 382), (533, 416), (565, 438)], 6)
            for x in (470, 492, 514):
                pygame.draw.line(surface, (62, 131, 180), (x, 448), (x, 483), 4)
                pygame.draw.polygon(surface, (62, 131, 180), [(x, 487), (x - 6, 476), (x + 6, 476)])

        # Continuous arrows communicate movement without claiming every water
        # molecule follows one fixed loop.
        pygame.draw.line(surface, (245, 184, 66), (423, 250), (433, 335), 4)
        pygame.draw.polygon(surface, (245, 184, 66), [(434, 342), (426, 328), (442, 329)])
        pygame.draw.line(surface, (110, 157, 180), (492, 300), (533, 263), 3)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, (item, rect) in enumerate(zip(DISCOVERIES, self._hotspots)):
            pygame.draw.circle(surface, (255, 249, 232), item.center, 37)
            pygame.draw.circle(surface, (73, 71, 60), item.center, 37, 3)
            cx, cy = item.center
            if item.discovery_id == "evaporation":
                pygame.draw.circle(surface, (246, 201, 68), (cx - 12, cy - 6), 12)
                for off in (-9, 6, 21):
                    pygame.draw.arc(surface, (91, 163, 190), (cx + off - 9, cy - 1, 18, 28), 0.4, 2.7, 3)
            elif item.discovery_id == "condensation":
                for ox, oy, rr in ((-14, 4, 14), (3, -7, 17), (18, 5, 13)):
                    pygame.draw.circle(surface, (211, 225, 231), (cx + ox, cy + oy), rr)
                pygame.draw.circle(surface, (87, 157, 194), (cx, cy + 13), 4)
            elif item.discovery_id == "precipitation":
                pygame.draw.ellipse(surface, (211, 225, 231), (cx - 24, cy - 17, 48, 25))
                for off in (-14, 0, 14):
                    pygame.draw.line(surface, (69, 143, 199), (cx + off, cy + 9), (cx + off - 4, cy + 24), 3)
            else:
                pygame.draw.line(surface, (112, 157, 84), (cx - 25, cy - 2), (cx + 25, cy - 2), 5)
                pygame.draw.line(surface, (70, 142, 190), (cx - 17, cy + 3), (cx - 17, cy + 25), 4)
                pygame.draw.line(surface, (70, 142, 190), (cx + 6, cy + 3), (cx + 25, cy + 18), 4)
            focus_ring(surface, rect, index == self._selected or index == self._hovered)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(305, 510, 400, 68)
        pygame.draw.rect(surface, (255, 249, 232), panel, border_radius=22)
        pygame.draw.rect(surface, (73, 71, 60), panel, 3, border_radius=22)
        text = self.context.resources.text(self._caption_key)
        rendered = self.context.typography.render(text, FontRole.BODY, 18, (55, 55, 53))
        if rendered.get_width() > panel.width - 26:
            rendered = self.context.typography.render(text, FontRole.BODY, 15, (55, 55, 53))
        surface.blit(rendered, rendered.get_rect(center=panel.center))
