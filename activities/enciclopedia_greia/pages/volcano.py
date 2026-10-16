"""Volcano final-entry pilot: magma, vents, gas pressure and eruption styles."""
from __future__ import annotations
from dataclasses import dataclass
import math
import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        TOKEN_SHAPE_FELT_TAG,
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discover_button,
        draw_discovery_token,
        draw_erupt_button,
        draw_navigation_arrows,
        draw_smoke_toggle,
        draw_speed_slider,
        draw_title,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_presenter, grid_step
    from .storybook_ink import inked_circle, inked_limb, inked_polygon
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        TOKEN_SHAPE_FELT_TAG,
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discover_button,
        draw_discovery_token,
        draw_erupt_button,
        draw_navigation_arrows,
        draw_smoke_toggle,
        draw_speed_slider,
        draw_title,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_presenter, grid_step
    from pages.storybook_ink import inked_circle, inked_limb, inked_polygon


@dataclass(frozen=True, slots=True)
class VolcanoDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    VolcanoDiscovery("magma", "volcano.magma", "encyclopedia.earth.volcano.magma", (260, 205)),
    VolcanoDiscovery("vent", "volcano.vent", "encyclopedia.earth.volcano.vent", (745, 205)),
    VolcanoDiscovery("style", "volcano.style", "encyclopedia.earth.volcano.style", (260, 410)),
    VolcanoDiscovery("ash", "volcano.ash", "encyclopedia.earth.volcano.ash", (745, 410)),
)
_FLOW = "flow"
_EXPLOSIVE = "explosive"


class VolcanoModel:
    """Own bounded teaching state; this is not a physical volcano simulation."""

    def __init__(self) -> None:
        self.pressure = 0.15
        self.eruption_style = _FLOW
        self.eruption_age = 0.0
        self.vent_age = 0.0
        self.ash_age = 0.0
        # Tranche 3 toy state — bounded, low-cost
        self.strength = 1  # 0=gentle, 1=medium, 2=strong
        self.smoke_enabled = True
        self.rumble_age = 0.0

    def update(self, dt: float) -> None:
        self.pressure += (0.15 - self.pressure) * min(1.0, dt * 0.35)
        self.eruption_age = max(0.0, self.eruption_age - dt)
        self.vent_age = max(0.0, self.vent_age - dt)
        self.ash_age = max(0.0, self.ash_age - dt)
        self.rumble_age = max(0.0, self.rumble_age - dt)

    def pump_magma(self) -> None:
        self.pressure = min(1.0, self.pressure + 0.28)
        if self.pressure >= 0.95:
            self.erupt()

    def show_vent(self) -> None:
        self.vent_age = 3.0
        self.pressure = min(1.0, self.pressure + 0.12)

    def toggle_style(self) -> None:
        self.eruption_style = _EXPLOSIVE if self.eruption_style == _FLOW else _FLOW
        self.pressure = 1.0 if self.eruption_style == _EXPLOSIVE else 0.72
        self.erupt()

    def show_ash(self) -> None:
        self.eruption_style = _EXPLOSIVE
        self.ash_age = 3.2
        self.pressure = 1.0
        self.erupt()

    def erupt(self) -> None:
        # Legacy path — medium eruption
        self.erupt_with_strength(self.strength)

    def erupt_with_strength(self, strength: int) -> None:
        strength = max(0, min(2, strength))
        self.strength = strength
        self.rumble_age = 0.9 + strength * 0.3
        # Duration scales with strength so the cause/effect is readable
        self.eruption_age = 2.2 + strength * 1.0
        if self.eruption_style == _EXPLOSIVE or strength == 2:
            self.ash_age = max(self.ash_age, 2.4 + strength * 0.8)
        self.pressure = 0.18

    def set_strength(self, level: int) -> None:
        self.strength = max(0, min(2, int(level)))

    def toggle_smoke(self) -> None:
        self.smoke_enabled = not self.smoke_enabled
        if not self.smoke_enabled:
            self.ash_age = 0.0


class VolcanoPage(EncyclopediaPage):
    page_id = "earth.volcano"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._model = VolcanoModel()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "volcano.intro"
        self._frame: pygame.Surface | None = None
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        # Standard chrome hits — same grammar as section pages
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._discover_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        # Main toy hits
        self._erupt_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._strength_hits: tuple[pygame.Rect, pygame.Rect, pygame.Rect] = (
            pygame.Rect(0, 0, 0, 0),
            pygame.Rect(0, 0, 0, 0),
            pygame.Rect(0, 0, 0, 0),
        )
        self._smoke_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.earth.volcano.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        disc = DISCOVERIES[self._selected]
        cue = encyclopedia_focus_cue("earth", "volcano", disc.discovery_id, "name")
        # Provisional — fail-soft until dedicated name cues are produced
        if not self._focus_audio.announce_once(self.context.audio, cue):
            self._focus_audio.announce_once(self.context.audio, disc.cue_id)

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(DISCOVERIES) - 1, index))
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def update(self, dt: float) -> None:
        self._time += dt
        self._model.update(dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {PageInputKind.POINTER_MOVE, PageInputKind.POINTER_PRESS}:
            point = (int(event.position[0]), int(event.position[1]))
            if event.kind is PageInputKind.POINTER_PRESS:
                if (
                    self._erupt_hit.collidepoint(point)
                    or (380 <= point[0] <= 644 and 160 <= point[1] <= 360)
                ):
                    self._trigger_eruption()
                    return
                for lvl, hit in enumerate(self._strength_hits):
                    if hit.collidepoint(point):
                        self._model.set_strength(lvl)
                        return
                if self._smoke_hit.collidepoint(point):
                    self._model.toggle_smoke()
                    return
                if self._discover_hit.collidepoint(point):
                    self._activate(self._selected)
                    return
                if self._arrow_left_hit.collidepoint(point):
                    self._set_selected(self._selected - 1)
                    return
                if self._arrow_right_hit.collidepoint(point):
                    self._set_selected(self._selected + 1)
                    return
            hit = next((index for index, rect in enumerate(self._hotspots) if rect.collidepoint(point)), None)
            if event.kind is PageInputKind.POINTER_MOVE and hit is not None and hit != self._selected:
                disc = DISCOVERIES[hit]
                cue = encyclopedia_focus_cue("earth", "volcano", disc.discovery_id, "name")
                self._focus_audio.announce_once(self.context.audio, cue)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            self._activate(self._selected)
            return
        prev = self._selected
        self._selected = grid_step(self._selected, event.command, columns=2, count=len(DISCOVERIES))
        if self._selected != prev:
            self._announce_selected()

    def _trigger_eruption(self) -> None:
        self._model.erupt_with_strength(self._model.strength)
        self._caption_key = "volcano.style" if self._model.strength == 2 else "volcano.magma"
        # Purposeful haptic audio hook — fail-soft
        announce_focus_name(self.context.audio, encyclopedia_focus_cue("earth", "volcano", "erupt", "name"))
        self.context.audio.play("encyclopedia.earth.volcano.style")

    def _activate(self, index: int) -> None:
        discovery = DISCOVERIES[index]
        self._caption_key = discovery.caption_key
        if discovery.discovery_id == "magma":
            self._model.pump_magma()
        elif discovery.discovery_id == "vent":
            self._model.show_vent()
        elif discovery.discovery_id == "style":
            self._model.toggle_style()
        else:
            self._model.show_ash()
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        # Rumble shake — tiny translation when the volcano is groaning
        shake_x = 0
        shake_y = 0
        if self._model.rumble_age > 0:
            shake_x = int(math.sin(self._time * 38) * 3 * min(1.0, self._model.rumble_age))
            shake_y = int(math.cos(self._time * 44) * 2 * min(1.0, self._model.rumble_age))
        # One reusable frame surface lets the rumble shake offset the whole
        # picture without allocating a full-screen surface every frame.
        base = self._frame
        if base is None or base.get_size() != surface.get_size():
            base = self._frame = pygame.Surface(surface.get_size()).convert()
        authored = draw_authored_scene(base, self.context.visuals, "encyclopedia.earth.volcano.cross_section")
        if not authored:
            # Procedural fallback while the authored runtime rendition is absent.
            base.fill((187, 224, 235))
            pygame.draw.rect(base, (153, 117, 82), (0, 345, 1024, 255))
            pygame.draw.rect(base, (115, 83, 60), (0, 455, 1024, 145))
        self._draw_cross_section(base, authored=authored)
        # The title sits above a tall explosive column rather than under it.
        draw_title(
            base,
            self.context.typography,
            self.context.resources.text("volcano.title"),
            self.context.palette.ink,
        )
        self._draw_hotspots(base)
        self._draw_caption(base)
        # Standard navigation chrome — same grammar as section pages
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            base, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        self._discover_hit = draw_discover_button(
            base, (820, 485), active=True, time=self._time, enabled=True
        )
        # Main toy chrome — Erupt trigger + strength + smoke
        _, self._strength_hits = draw_speed_slider(
            base, (185, 485), time=self._time, level=self._model.strength, paused=False
        )
        # Re-label slider notches visually as strength via subtle size pulse already; keep generic
        self._erupt_hit = draw_erupt_button(
            base,
            (512, 460),
            time=self._time,
            enabled=True,
            erupting=self._model.eruption_age > 0,
        )
        self._smoke_hit = draw_smoke_toggle(
            base, (700, 485), time=self._time, enabled=self._model.smoke_enabled
        )
        draw_presenter(
            base, self.context.visuals, "tito", position=(925, 565), height=142,
            variant="surprised", fallback_color=(247, 151, 77),
        )
        if shake_x or shake_y:
            surface.blit(base, (shake_x, shake_y))
            # Fill exposed edge with sky/ground to avoid tearing
            if shake_x > 0:
                pygame.draw.rect(surface, (187, 224, 235), (0, 0, shake_x, 600))
            elif shake_x < 0:
                pygame.draw.rect(surface, (115, 83, 60), (1024 + shake_x, 345, -shake_x, 255))
        else:
            surface.blit(base, (0, 0))

    def _draw_cross_section(self, surface: pygame.Surface, *, authored: bool) -> None:
        cx = 505
        crater_y = 205
        if authored:
            self._draw_live_magma(surface)
        else:
            self._draw_procedural_cone(surface, cx, crater_y)
        self._draw_eruption(surface, cx)

    def _draw_live_magma(self, surface: pygame.Surface) -> None:
        """Pressure and vent glow over the authored cut-open volcano."""

        breathe = math.sin(self._time * 1.6) * 0.5 + 0.5
        chamber = pygame.Rect(431, 360, 148, 64)
        glow = int((10 + breathe * 6) * (0.5 + self._model.pressure * 0.8))
        pygame.draw.ellipse(surface, (249, 162, 60), chamber.inflate(glow, glow // 2), max(3, 8 - glow // 3))
        if self._model.vent_age > 0 or self._model.eruption_age > 0:
            pygame.draw.line(surface, (246, 119, 45), (505, 372), (505, 198), 15)
            pygame.draw.line(surface, (252, 197, 106), (505, 366), (505, 204), 5)
        # Pressure bubbles rise inside the chamber itself, so the always-on
        # pressure reading stays visible above the page controls.
        for index in range(4):
            filled = (index + 1) / 4 <= self._model.pressure + 0.02
            x = 457 + index * 32
            y = 396 - int(math.sin(self._time * 2.2 + index) * 2)
            if filled:
                inked_circle(surface, (255, 222, 120), (x, y), 9, outline=2)
                pygame.draw.circle(surface, (255, 248, 214), (x - 3, y - 3), 3)
            else:
                pygame.draw.circle(surface, (176, 72, 44), (x, y), 9, 3)

    def _draw_procedural_cone(self, surface: pygame.Surface, cx: int, crater_y: int) -> None:
        """Fallback cone used only when the authored scene is missing."""

        # Mountain silhouette — tactile storybook with soft shading and snow hint
        pygame.draw.polygon(surface, (92, 78, 68), [(355, 345), (470, 185), (540, 185), (655, 345)])
        # Light side
        pygame.draw.polygon(surface, (137, 105, 83), [(445, 225), (470, 185), (540, 185), (565, 225)])
        # Shadow side
        pygame.draw.polygon(surface, (115, 88, 70), [(515, 225), (540, 185), (655, 345), (560, 345)])
        # Crater rim with highlight
        pygame.draw.ellipse(surface, (78, 68, 61), (470, 174, 70, 24))
        pygame.draw.ellipse(surface, (105, 90, 78), (472, 176, 66, 20), 2)
        # Snow cap
        snow = pygame.Surface((70, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(snow, (250, 250, 248, 210), snow.get_rect())
        pygame.draw.ellipse(snow, (220, 220, 218, 140), (4, 4, 62, 16), 2)
        surface.blit(snow, (470, 174))
        # Magma chamber — glows with pressure + breathe
        chamber = pygame.Rect(435, 430, 140, 74)
        pygame.draw.ellipse(surface, (221, 78, 48), chamber)
        breathe = math.sin(self._time * 1.6) * 0.5 + 0.5
        glow = int((10 + breathe * 6) * (0.5 + self._model.pressure * 0.8))
        pygame.draw.ellipse(
            surface, (246, 135, 55), chamber.inflate(glow, glow // 2), max(3, 8 - glow // 3)
        )
        vent_color = (246, 119, 45) if self._model.vent_age > 0 or self._model.eruption_age > 0 else (168, 84, 58)
        pygame.draw.line(surface, vent_color, (505, 440), (505, crater_y + 2), 18)
        # Pressure dots — always visible teaching affordance
        for index in range(4):
            filled = (index + 1) / 4 <= self._model.pressure + 0.02
            color = (255, 190, 73) if filled else (102, 79, 65)
            pygame.draw.circle(surface, color, (455 + index * 34, 525), 11)
            pygame.draw.circle(surface, (80, 61, 53), (455 + index * 34, 525), 11, 2)

    def _draw_eruption(self, surface: pygame.Surface, cx: int) -> None:
        breathe = math.sin(self._time * 1.6) * 0.5 + 0.5
        # Ambient idle smoke wisp — sparse, not obscuring
        if self._model.smoke_enabled and self._model.eruption_age == 0 and self._model.rumble_age == 0:
            sway = int(math.sin(self._time * 0.9) * 4)
            wx = cx + sway
            for i, (dx, dy, r) in enumerate(((0, 155, 6), (5, 140, 5), (-4, 128, 4))):
                alpha = 55 + int(breathe * 25) - i * 8
                s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (210, 210, 205, alpha), (r, r), r)
                surface.blit(s, (wx + dx - r, dy))
        if self._model.eruption_age > 0:
            intensity = min(1.0, self._model.eruption_age / (1.6 + self._model.strength * 0.6))
            strength = self._model.strength
            if self._model.eruption_style == _FLOW:
                thick = 14 + strength * 5
                inked_limb(
                    surface,
                    (232, 86, 43),
                    [(520, 205), (585, 280), (625, 342)],
                    [thick + 4, thick - 1],
                )
                pygame.draw.line(surface, (252, 160, 64), (526, 214), (586, 285), max(3, thick // 3))
                # Extra lava tongue for strong
                if strength == 2:
                    pygame.draw.line(surface, (255, 200, 90), (520, 205), (600, 295), 6)
            else:
                height = 70 + int((40 + strength * 28) * intensity)
                width = 18 + strength * 6
                inked_polygon(
                    surface,
                    (239, 89, 39),
                    [(cx - width, 195), (cx, 195 - height), (cx + width, 195)],
                )
                # Central bright column
                pygame.draw.polygon(
                    surface,
                    (255, 165, 70),
                    [(cx - 6, 195), (cx, 195 - height + 12), (cx + 6, 195)],
                )
        if self._model.ash_age > 0 and self._model.smoke_enabled:
            # Ash amount scales with strength and remaining age
            count = 16 + self._model.strength * 6
            spread = 1.0 - min(1.0, self._model.ash_age / (3.0 + self._model.strength * 0.9))
            for index in range(count):
                angle = index * 0.81 + self._time * (0.23 + self._model.strength * 0.04)
                radius = 18 + int(spread * (32 + index % 6 * 9))
                x = cx + int(math.cos(angle) * radius * 1.55)
                y = 135 + int(math.sin(angle) * radius * 0.55) - index % 3 * 4
                r = 4 + index % 4
                if self._model.strength == 2:
                    r += 1
                pygame.draw.circle(surface, (86, 82, 79), (x, y), r)
                # Occasional glowing ember
                if index % 7 == 0 and self._model.eruption_age > 0:
                    pygame.draw.circle(surface, (255, 170, 60), (x + 1, y - 1), 2)

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
        if discovery_id == "magma":
            pygame.draw.ellipse(surface, (225, 79, 45), (cx - 23, cy - 13, 46, 26))
            pygame.draw.circle(surface, (255, 184, 65), (cx, cy - 2), 8)
        elif discovery_id == "vent":
            pygame.draw.polygon(surface, (111, 92, 79), [(cx - 24, cy + 20), (cx, cy - 25), (cx + 24, cy + 20)])
            pygame.draw.line(surface, (240, 100, 42), (cx, cy + 12), (cx, cy - 18), 7)
        elif discovery_id == "style":
            pygame.draw.line(surface, (232, 86, 43), (cx - 22, cy + 10), (cx - 2, cy - 12), 8)
            pygame.draw.polygon(surface, (239, 89, 39), [(cx + 4, cy + 12), (cx + 16, cy - 22), (cx + 28, cy + 12)])
        else:
            for dx, dy, radius in ((-13, 5, 9), (0, -8, 12), (15, 5, 8), (4, 11, 10)):
                pygame.draw.circle(surface, (91, 87, 83), (cx + dx, cy + dy), radius)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
        )
