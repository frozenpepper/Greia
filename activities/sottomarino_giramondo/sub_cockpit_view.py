"""Sottomarino Giramondo — cockpit and porthole presentation.

Renders the ocean through the brass porthole, the radar sweep, the depth
dial, the helm wheel, the throttle telegraph and the chunky cockpit buttons
(the Activity's own cockpit look, kept from the original). Static cockpit
parts are baked once into one colour-keyed layer; buttons are cached per
state; creatures are blitted from the art owner's bounded perspective cache.
Kit controls (prompt banner, stars, focus ring) are drawn by the app's
``ControlLayer`` on top of this.
"""

from __future__ import annotations

from collections import OrderedDict
import math
from typing import Dict, List, Optional, Tuple

import pygame

from greia_platform.localization import LocalizationError, LocalizedResources
from greia_platform.pygame_blit import PreparedSurfaces
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .sub_art import (
        ICON_INK,
        INSTRUMENT_COLOURS,
        PORTHOLE_CENTER_X,
        PORTHOLE_CENTER_Y,
        PORTHOLE_RADIUS,
        SubmarineArt,
        draw_instrument_icon,
    )
    from .sub_model import (
        ENCOUNTER_HELPERS,
        BiomeType,
        EncounterType,
        MarineEntity3D,
        SubmarineModel,
        get_biome,
    )
else:
    from sub_art import (
        ICON_INK,
        INSTRUMENT_COLOURS,
        PORTHOLE_CENTER_X,
        PORTHOLE_CENTER_Y,
        PORTHOLE_RADIUS,
        SubmarineArt,
        draw_instrument_icon,
    )
    from sub_model import (
        ENCOUNTER_HELPERS,
        BiomeType,
        EncounterType,
        MarineEntity3D,
        SubmarineModel,
        get_biome,
    )

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600
DASHBOARD_TOP = 435

# Radar sweep geometry
RADAR_CENTER_X = 140
RADAR_CENTER_Y = 490
RADAR_RADIUS = 65

# Depth dial geometry
DEPTH_CENTER_X = 884
DEPTH_CENTER_Y = 490
DEPTH_RADIUS = 65

# Helm wheel and throttle telegraph (pointer drag affordances)
WHEEL_CENTER = (135, 235)
WHEEL_RADIUS = 58
WHEEL_HIT_RADIUS = 72
LEVER_CENTER = (890, 215)
LEVER_HIT_RECT = pygame.Rect(845, 140, 90, 150)

# Captain Leo stands on the dashboard edge, left of the porthole.
CAPTAIN_MIDBOTTOM = (304, DASHBOARD_TOP + 6)
CAPTAIN_HEIGHT = 150

# Chunky cockpit buttons: (x, y, w, h)
BUTTON_RECTS = {
    # Lower console instrument buttons
    "light": pygame.Rect(222, 464, 102, 86),
    "sonar": pygame.Rect(344, 464, 102, 86),
    "action": pygame.Rect(466, 464, 92, 86),  # central alarm beacon
    "bubbles": pygame.Rect(578, 464, 102, 86),
    "horn": pygame.Rect(700, 464, 102, 86),
    # Steering (under the helm wheel)
    "steer_left": pygame.Rect(45, 335, 80, 56),
    "steer_right": pygame.Rect(145, 335, 80, 56),
    # Engine telegraph (under the throttle lever)
    "ahead": pygame.Rect(795, 335, 85, 56),
    "stop": pygame.Rect(895, 335, 85, 56),
    # Depth: Surface (up) and Dive (down), above the lever
    "surface": pygame.Rect(795, 66, 85, 56),
    "dive": pygame.Rect(895, 66, 85, 56),
}

PORTHOLE_VIEW = pygame.Rect(
    PORTHOLE_CENTER_X - PORTHOLE_RADIUS,
    PORTHOLE_CENTER_Y - PORTHOLE_RADIUS,
    PORTHOLE_RADIUS * 2,
    PORTHOLE_RADIUS * 2,
)

# Kinds drawn mirrored when they swim left (library art faces right).
_DIRECTIONAL = frozenset({"clownfish", "turtle", "dolphin", "angler", "whale"})
_MAX_BUTTON_CACHE = 64
_ENCOUNTER_SIZE = {EncounterType.OCTOPUS_HUG: ("octopus", 330), EncounterType.SHARK_WAVE: ("shark", 300)}


def in_porthole(point: Tuple[float, float], margin: float = 0.0) -> bool:
    dx = point[0] - PORTHOLE_CENTER_X
    dy = point[1] - PORTHOLE_CENTER_Y
    return dx * dx + dy * dy <= (PORTHOLE_RADIUS - margin) ** 2


def project(ent: MarineEntity3D) -> Tuple[int, int, float]:
    """Camera-space entity -> (screen x, screen y, perspective scale)."""

    scale = 1.0 / max(0.1, ent.z)
    sx = PORTHOLE_CENTER_X + int(ent.x * 240.0 * scale)
    sy = PORTHOLE_CENTER_Y + int(ent.y * 240.0 * scale)
    return sx, sy, scale


class CockpitPresenter:
    """Renders the cockpit dashboard and the porthole ocean scene."""

    def __init__(self, art: SubmarineArt, typography: GreiaTypography) -> None:
        self._fast = PreparedSurfaces(max_entries=96)  # RLE copies of per-frame sprites (pygame_blit)
        self.art = art
        self.typography = typography
        self._cockpit = self._bake_cockpit()
        self._buttons: OrderedDict[tuple, pygame.Surface] = OrderedDict()
        self._plaques: Dict[str, pygame.Surface] = {}
        # Creatures drawn last frame, nearest last (for tap hit-testing).
        self.creature_rects: List[Tuple[pygame.Rect, str]] = []
        self._ticks = 0

    # -- static bake -----------------------------------------------------------

    def _bake_cockpit(self) -> pygame.Surface:
        surface = self.art.bulkhead.copy()
        # Lower console
        pygame.draw.rect(surface, (32, 42, 54), (0, DASHBOARD_TOP, REFERENCE_WIDTH, REFERENCE_HEIGHT - DASHBOARD_TOP))
        pygame.draw.line(surface, (65, 85, 105), (0, DASHBOARD_TOP), (REFERENCE_WIDTH, DASHBOARD_TOP), 3)
        pygame.draw.line(surface, (20, 26, 34), (0, DASHBOARD_TOP + 3), (REFERENCE_WIDTH, DASHBOARD_TOP + 3), 2)
        # Radar screen
        cx, cy, r = RADAR_CENTER_X, RADAR_CENTER_Y, RADAR_RADIUS
        pygame.draw.circle(surface, (180, 140, 50), (cx, cy), r + 5, 4)
        pygame.draw.circle(surface, (10, 30, 20), (cx, cy), r)
        pygame.draw.circle(surface, (25, 75, 45), (cx, cy), r // 3, 1)
        pygame.draw.circle(surface, (25, 75, 45), (cx, cy), (r * 2) // 3, 1)
        pygame.draw.circle(surface, (35, 105, 60), (cx, cy), r, 1)
        pygame.draw.line(surface, (25, 75, 45), (cx - r, cy), (cx + r, cy), 1)
        pygame.draw.line(surface, (25, 75, 45), (cx, cy - r), (cx, cy + r), 1)
        # Depth dial face
        cx, cy, r = DEPTH_CENTER_X, DEPTH_CENTER_Y, DEPTH_RADIUS
        pygame.draw.circle(surface, (180, 140, 50), (cx, cy), r + 5, 4)
        pygame.draw.circle(surface, (240, 235, 220), (cx, cy), r)
        # Zone colour bands on the dial so depth reads without numbers.
        for start, end, colour in ((0, 25, (25, 140, 190)), (25, 65, (15, 60, 110)), (65, 100, (40, 30, 90))):
            a0 = math.radians(135 + start / 100.0 * 270)
            a1 = math.radians(135 + end / 100.0 * 270)
            steps = max(2, int((end - start) / 3))
            pts_outer = [(cx + (r - 2) * math.cos(a0 + (a1 - a0) * i / steps), cy + (r - 2) * math.sin(a0 + (a1 - a0) * i / steps)) for i in range(steps + 1)]
            pts_inner = [(cx + (r - 9) * math.cos(a1 - (a1 - a0) * i / steps), cy + (r - 9) * math.sin(a1 - (a1 - a0) * i / steps)) for i in range(steps + 1)]
            pygame.draw.polygon(surface, colour, pts_outer + pts_inner)
        for d in range(0, 101, 10):
            angle = math.radians(135 + d / 100.0 * 270)
            t_outer = r - 10
            t_inner = r - 18 if d % 20 == 0 else r - 14
            pygame.draw.line(
                surface, (40, 40, 40),
                (cx + int(t_outer * math.cos(angle)), cy + int(t_outer * math.sin(angle))),
                (cx + int(t_inner * math.cos(angle)), cy + int(t_inner * math.sin(angle))), 2)
        # Throttle telegraph base plate
        tcx, tcy = LEVER_CENTER
        pygame.draw.rect(surface, (24, 30, 40), (tcx - 45, tcy - 75, 90, 150), border_radius=16)
        pygame.draw.rect(surface, (180, 140, 60), (tcx - 45, tcy - 75, 90, 150), width=3, border_radius=16)
        for rx, ry in ((tcx - 36, tcy - 66), (tcx + 36, tcy - 66), (tcx - 36, tcy + 66), (tcx + 36, tcy + 66)):
            pygame.draw.circle(surface, (215, 175, 55), (rx, ry), 4)
        pygame.draw.rect(surface, (10, 14, 20), (tcx - 8, tcy - 58, 16, 115), border_radius=8)
        for ny in (tcy - 45, tcy - 18, tcy + 10, tcy + 40):
            pygame.draw.line(surface, (180, 140, 60), (tcx - 18, ny), (tcx - 10, ny), 2)
            pygame.draw.line(surface, (180, 140, 60), (tcx + 10, ny), (tcx + 18, ny), 2)
        return surface

    # -- frame -------------------------------------------------------------------

    def render(
        self,
        surface: pygame.Surface,
        model: SubmarineModel,
        resources: LocalizedResources,
        hot_button: Optional[str] = None,
        *,
        pressed_button: Optional[str] = None,
    ) -> None:
        self._ticks = pygame.time.get_ticks()
        self._render_ocean_viewport(surface, model)
        surface.blit(self._fast(self._cockpit), (0, 0))
        self._render_biome_plaque(surface, model, resources)
        self._render_radar(surface, model)
        self._render_depth_gauge(surface, model)
        self._render_helm_wheel(surface, model)
        self._render_throttle_lever(surface, model)
        self._render_buttons(surface, model, resources, hot_button, pressed_button)

    def _pulse(self) -> float:
        return (math.sin(self._ticks * 0.012) + 1.0) * 0.5

    def _render_ocean_viewport(self, surface: pygame.Surface, model: SubmarineModel) -> None:
        biome = get_biome(model.depth)
        surface.blit(self._fast(self.art.backdrop(biome.value, model.lights_on)), PORTHOLE_VIEW.topleft)
        previous_clip = surface.get_clip()
        surface.set_clip(PORTHOLE_VIEW)
        rects: List[Tuple[pygame.Rect, str]] = []
        for ent in sorted(model.entities, key=lambda e: e.z, reverse=True):
            sx, sy, scale = project(ent)
            longest = self.art.unit_size(ent.kind, ent.size_base, scale)
            if abs(sx - PORTHOLE_CENTER_X) > PORTHOLE_RADIUS + longest or abs(sy - PORTHOLE_CENTER_Y) > PORTHOLE_RADIUS + longest:
                continue
            flip = ent.kind in _DIRECTIONAL and ent.vx < -0.005
            sprite = self.art.scaled(ent.kind, longest, flip=flip)
            if sprite is None:
                continue
            rect = sprite.get_rect(center=(sx, sy))
            surface.blit(self._fast(sprite), rect)
            if ent.kind != "bubble":
                rects.append((rect, ent.kind))
        if model.encounter.active_type != EncounterType.NONE:
            self._render_encounter_creature(surface, model)
        surface.blit(self._fast(self.art.glass_sheen), PORTHOLE_VIEW.topleft)
        surface.set_clip(previous_clip)
        self.creature_rects = rects

    def _render_encounter_creature(self, surface: pygame.Surface, model: SubmarineModel) -> None:
        enc = model.encounter
        alpha = int(min(255, enc.progress * 255))
        if enc.solved:
            alpha = int(max(0, min(255, enc.solve_timer * 127)))
        kind, size = _ENCOUNTER_SIZE.get(enc.active_type, ("octopus", 330))
        sprite = self.art.encounter_sprite(kind, size)
        if sprite is None or alpha <= 0:
            return
        faded = self._fast.faded(sprite, alpha / 255.0, steps=16)
        if faded is None:
            return
        bob = int(math.sin(self._ticks * 0.005) * 8)
        sway = int(math.sin(self._ticks * 0.003) * 10) if kind == "shark" else 0
        surface.blit(faded, sprite.get_rect(center=(PORTHOLE_CENTER_X + sway, PORTHOLE_CENTER_Y + bob + 10)))

    def _render_biome_plaque(self, surface: pygame.Surface, model: SubmarineModel, resources: LocalizedResources) -> None:
        key = {
            BiomeType.SHALLOW_REEF: "biome.shallow",
            BiomeType.TWILIGHT_KELP: "biome.twilight",
            BiomeType.MIDNIGHT_ABYSS: "biome.abyss",
        }[get_biome(model.depth)]
        text = self._copy(resources, key)
        plaque = self._plaques.get(text)
        if plaque is None:
            label = self._fitted_label(text, FontRole.TITLE, 16, 200, (70, 45, 10))
            w = max(150, label.get_width() + 36)
            plaque = pygame.Surface((w, 30), pygame.SRCALPHA)
            pygame.draw.rect(plaque, (125, 85, 20), (0, 0, w, 30), border_radius=15)
            pygame.draw.rect(plaque, (240, 200, 95), (2, 2, w - 4, 26), border_radius=13)
            pygame.draw.rect(plaque, (255, 236, 160), (10, 5, w - 20, 5), border_radius=3)
            for bx in (10, w - 10):
                pygame.draw.circle(plaque, (150, 105, 30), (bx, 15), 3)
            plaque.blit(label, label.get_rect(center=(w // 2, 15)))
            self._plaques[text] = plaque
        surface.blit(self._fast(plaque), plaque.get_rect(center=(PORTHOLE_CENTER_X, PORTHOLE_CENTER_Y + PORTHOLE_RADIUS + 22)))

    def _render_radar(self, surface: pygame.Surface, model: SubmarineModel) -> None:
        cx, cy, r = RADAR_CENTER_X, RADAR_CENTER_Y, RADAR_RADIUS
        rad = math.radians(model.radar_angle)
        sweep_color = (90, 255, 140) if model.sonar_active else (40, 180, 80)
        pygame.draw.line(surface, sweep_color, (cx, cy), (cx + int(r * math.cos(rad)), cy + int(r * math.sin(rad))), 2)
        if model.sonar_active:
            ring = int((2.5 - model.sonar_timer) / 2.5 * r)
            if 4 < ring < r:
                pygame.draw.circle(surface, (90, 255, 140), (cx, cy), ring, 2)
        for ent in model.entities:
            if ent.kind == "bubble":
                continue
            dist = min(1.0, ent.z / 1.5)
            bx = cx + int(ent.x * (r * 0.7))
            by = cy + int(dist * (r * 0.8) - (r * 0.4))
            if (bx - cx) ** 2 + (by - cy) ** 2 <= (r - 4) ** 2:
                pygame.draw.circle(surface, (120, 255, 160), (bx, by), 3)

    def _render_depth_gauge(self, surface: pygame.Surface, model: SubmarineModel) -> None:
        cx, cy, r = DEPTH_CENTER_X, DEPTH_CENTER_Y, DEPTH_RADIUS
        depth_frac = min(1.0, max(0.0, model.depth / 100.0))
        needle_angle = math.radians(135 + depth_frac * 270)
        nx = cx + int((r - 14) * math.cos(needle_angle))
        ny = cy + int((r - 14) * math.sin(needle_angle))
        pygame.draw.line(surface, (220, 40, 30), (cx, cy), (nx, ny), 3)
        pygame.draw.circle(surface, (40, 40, 40), (cx, cy), 6)
        txt_surf = self.typography.render(f"{int(model.depth)} m", FontRole.BODY, 16, (30, 30, 30))
        surface.blit(txt_surf, (cx - txt_surf.get_width() // 2, cy + 20))

    def _order_hint(self, model: SubmarineModel, *names: str) -> bool:
        order = model.current_order
        return order.waiting and order.hinted and order.target in names

    def _render_aura(self, surface: pygame.Surface, rect: pygame.Rect, radius: int) -> None:
        if self._pulse() <= 0.3:
            return
        aura = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(aura, (255, 235, 90, 90), aura.get_rect(), border_radius=radius)
        surface.blit(aura, rect)

    def _render_helm_wheel(self, surface: pygame.Surface, model: SubmarineModel) -> None:
        """Nautical wooden helm wheel with brass hub and turned handles."""
        cx, cy = WHEEL_CENTER
        hradius = WHEEL_RADIUS
        if self._order_hint(model, "steer_left", "steer_right"):
            self._render_aura(surface, pygame.Rect(cx - hradius - 25, cy - hradius - 25, hradius * 2 + 50, hradius * 2 + 50), hradius + 25)
        pygame.draw.circle(surface, (120, 75, 35), (cx, cy), hradius, 9)
        pygame.draw.circle(surface, (180, 130, 70), (cx, cy), hradius - 4, 3)
        for i in range(8):
            a = math.radians(model.wheel_angle + i * 45.0)
            ca, sa = math.cos(a), math.sin(a)
            pygame.draw.line(surface, (150, 95, 45), (cx + int(16 * ca), cy + int(16 * sa)),
                             (cx + int((hradius - 5) * ca), cy + int((hradius - 5) * sa)), 6)
            hx2, hy2 = cx + int((hradius + 16) * ca), cy + int((hradius + 16) * sa)
            pygame.draw.line(surface, (110, 65, 30), (cx + int(hradius * ca), cy + int(hradius * sa)), (hx2, hy2), 8)
            pygame.draw.circle(surface, (215, 175, 55), (hx2, hy2), 6)
        pygame.draw.circle(surface, (215, 175, 55), (cx, cy), 22)
        pygame.draw.circle(surface, (150, 110, 25), (cx, cy), 22, 3)
        pygame.draw.circle(surface, (60, 45, 20), (cx, cy), 8)

    def _render_throttle_lever(self, surface: pygame.Surface, model: SubmarineModel) -> None:
        """Brass engine telegraph lever (base plate is baked)."""
        tcx, tcy = LEVER_CENTER
        if self._order_hint(model, "ahead", "stop"):
            self._render_aura(surface, pygame.Rect(tcx - 70, tcy - 95, 140, 190), 22)
            # Redraw the plate's edge so the aura reads as a glow around it.
            pygame.draw.rect(surface, (24, 30, 40), (tcx - 45, tcy - 75, 90, 150), border_radius=16)
            pygame.draw.rect(surface, (180, 140, 60), (tcx - 45, tcy - 75, 90, 150), width=3, border_radius=16)
            pygame.draw.rect(surface, (10, 14, 20), (tcx - 8, tcy - 58, 16, 115), border_radius=8)
        pivot_x, pivot_y = tcx, tcy + 42
        norm_speed = min(1.0, max(0.0, model.speed))
        lever_angle = math.radians(-32.0 + norm_speed * 64.0)
        tip_x = pivot_x + int(82 * math.sin(lever_angle))
        tip_y = pivot_y - int(82 * math.cos(lever_angle))
        pygame.draw.line(surface, (215, 180, 65), (pivot_x, pivot_y), (tip_x, tip_y), 9)
        pygame.draw.circle(surface, (150, 110, 30), (pivot_x, pivot_y), 16)
        pygame.draw.circle(surface, (50, 40, 20), (pivot_x, pivot_y), 7)
        pygame.draw.circle(surface, (210, 45, 45), (tip_x, tip_y), 17)
        pygame.draw.circle(surface, (255, 120, 120), (tip_x - 4, tip_y - 4), 5)

    # -- buttons -------------------------------------------------------------------

    def button_states(self, model: SubmarineModel) -> Dict[str, Tuple[bool, bool]]:
        """name -> (lit/active, hinted) for every cockpit button."""

        enc = model.encounter
        helpers = ENCOUNTER_HELPERS.get(enc.active_type, ()) if model.encounter_waiting() else ()
        order = model.current_order
        target = order.target if (order.waiting and order.hinted) else ""
        lit = {
            "light": model.lights_on,
            "sonar": model.sonar_active,
            "bubbles": model.bubble_release_timer > 0,
            "horn": False,
            "steer_left": model.heading < -0.15,
            "steer_right": model.heading > 0.15,
            "ahead": model.speed > 0.4,
            "stop": model.speed <= 0.1,
            "surface": model.target_depth < model.depth - 0.5,
            "dive": model.target_depth > model.depth + 0.5,
            "action": model.encounter_waiting(),
        }
        return {name: (lit[name], name == target or name in helpers) for name in BUTTON_RECTS}

    def _render_buttons(
        self,
        surface: pygame.Surface,
        model: SubmarineModel,
        resources: LocalizedResources,
        hot_button: Optional[str],
        pressed_button: Optional[str],
    ) -> None:
        flash_on = self._pulse() > 0.4
        for name, (active, hinted) in self.button_states(model).items():
            rect = BUTTON_RECTS[name]
            if name == "action":
                beacon = int(self._pulse() * 4) if active else -1
                image = self._button_surface(name, resources, active, hot_button == name, pressed_button == name, beacon)
                if active:
                    aura = self._aura_surface(rect.inflate(24, 24).size)
                    if flash_on:
                        surface.blit(self._fast(aura), rect.inflate(24, 24))
            else:
                flash = hinted and flash_on
                image = self._button_surface(name, resources, active, hot_button == name, pressed_button == name, int(flash))
                if flash:
                    surface.blit(self._fast(self._aura_surface(rect.inflate(20, 20).size)), rect.inflate(20, 20))
            surface.blit(self._fast(image), (rect.x, rect.y))

    def _aura_surface(self, size: Tuple[int, int]) -> pygame.Surface:
        key = ("aura", size)
        cached = self._buttons.get(key)
        if cached is None:
            cached = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.rect(cached, (255, 240, 100, 150), cached.get_rect(), border_radius=18)
            self._store(key, cached)
        return cached

    def _store(self, key: tuple, image: pygame.Surface) -> None:
        self._buttons[key] = image
        while len(self._buttons) > _MAX_BUTTON_CACHE:
            self._buttons.popitem(last=False)

    def _button_surface(
        self,
        name: str,
        resources: LocalizedResources,
        active: bool,
        hover: bool,
        pressed: bool,
        flash: int,
    ) -> pygame.Surface:
        label = self._copy(resources, f"btn.{name}")
        key = (name, label, active, hover, pressed, flash)
        cached = self._buttons.get(key)
        if cached is not None:
            self._buttons.move_to_end(key)
            return cached
        rect = BUTTON_RECTS[name]
        image = pygame.Surface((rect.width, rect.height + 6), pygame.SRCALPHA)
        local = pygame.Rect(0, 0, rect.width, rect.height)
        if name == "action":
            self._draw_beacon_button(image, local, flash, hover or pressed, label)
        else:
            self._draw_tactile_button(image, local, INSTRUMENT_COLOURS[name], active or pressed, hover, label, name, bool(flash))
        self._store(key, image)
        return image

    def _draw_tactile_button(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        base_color: Tuple[int, int, int],
        active: bool,
        hover: bool,
        label: str,
        icon_type: str,
        flashing: bool = False,
    ) -> None:
        shadow_rect = rect.move(0, 4)
        pygame.draw.rect(surface, (15, 20, 28), shadow_rect, border_radius=14)
        btn_rect = rect.move(0, 2) if (active or hover) else rect.copy()
        boost = 45 if flashing else (30 if (active or hover) else 0)
        col = tuple(min(255, c + boost) for c in base_color)
        pygame.draw.rect(surface, col, btn_rect, border_radius=14)
        border_col = (255, 255, 255, 220) if flashing else (255, 255, 255, 110)
        pygame.draw.rect(surface, border_col, btn_rect, width=3 if flashing else 2, border_radius=14)
        compact = btn_rect.height <= 60
        icon_cy = btn_rect.top + (20 if compact else 32)
        draw_instrument_icon(surface, icon_type, btn_rect.centerx, icon_cy, ICON_INK)
        size = 13 if compact else 15
        txt = self._fitted_label(label, FontRole.CONTROL, size, btn_rect.width - 8, (25, 30, 38))
        surface.blit(txt, (btn_rect.centerx - txt.get_width() // 2, btn_rect.bottom - txt.get_height() - (3 if compact else 6)))

    def _draw_beacon_button(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        beacon: int,
        hover: bool,
        label: str,
    ) -> None:
        """The central red alarm beacon (glows in steps while a visitor waits)."""
        flashing = beacon >= 0
        intensity = max(0, beacon) / 4.0
        color = (255, int(60 + intensity * 140), 40) if flashing else (220, 50, 50)
        cx = rect.centerx
        cy = rect.top + 34
        radius = 26
        pygame.draw.rect(surface, (15, 20, 28), rect.move(0, 4), border_radius=14)
        btn_rect = rect.copy()
        if hover:
            btn_rect.y += 2
            cy += 2
        pygame.draw.rect(surface, (45, 25, 28), btn_rect, border_radius=14)
        pygame.draw.rect(surface, (200, 70, 70) if flashing else (130, 60, 60), btn_rect, width=2, border_radius=14)
        pygame.draw.circle(surface, (20, 24, 30), (cx, cy + 2), radius + 4)
        pygame.draw.circle(surface, (180, 140, 60), (cx, cy), radius + 3, 2)
        pygame.draw.circle(surface, (150, 25, 25), (cx, cy), radius)
        pygame.draw.circle(surface, color, (cx, cy), radius - 3)
        pygame.draw.circle(surface, (255, 140, 140), (cx, cy), radius - 3, 2)
        pygame.draw.line(surface, (255, 210, 210), (cx - 9, cy - radius + 7), (cx - 9, cy + radius - 7), 2)
        pygame.draw.line(surface, (255, 255, 255), (cx, cy - radius + 4), (cx, cy + radius - 4), 2)
        pygame.draw.line(surface, (255, 210, 210), (cx + 9, cy - radius + 7), (cx + 9, cy + radius - 7), 2)
        pygame.draw.arc(surface, (220, 180, 80), (cx - radius + 3, cy - radius + 3, (radius - 3) * 2, (radius - 3) * 2), 0.5, 2.64, 2)
        pygame.draw.line(surface, (220, 180, 80), (cx, cy - radius + 2), (cx, cy + radius - 2), 2)
        pygame.draw.circle(surface, (255, 255, 255), (cx - 8, cy - 8), 3)
        txt_col = (255, 245, 245) if flashing else (230, 215, 215)
        txt = self._fitted_label(label, FontRole.CONTROL, 14, btn_rect.width - 8, txt_col)
        surface.blit(txt, (btn_rect.centerx - txt.get_width() // 2, btn_rect.bottom - txt.get_height() - 5))

    # -- creatures -------------------------------------------------------------------

    def creature_at(self, point: Tuple[float, float]) -> Optional[str]:
        """Kind of the nearest creature drawn under ``point`` (last frame)."""

        if not in_porthole(point):
            return None
        for rect, kind in reversed(self.creature_rects):
            if rect.inflate(-rect.width // 5, -rect.height // 5).collidepoint(point):
                return kind
        return None

    # -- text helpers ---------------------------------------------------------------

    def _fitted_label(
        self,
        text: str,
        role: FontRole,
        size: int,
        max_width: int,
        color: Tuple[int, int, int],
    ) -> pygame.Surface:
        """Render a label at the largest size (down to a floor) that fits."""
        fitted = size
        while fitted > 9 and self.typography.measure(text, role, fitted).width > max_width:
            fitted -= 1
        return self.typography.render(text, role, fitted, color)

    @staticmethod
    def _copy(resources: LocalizedResources, key: str, **variables: str) -> str:
        """Resolve child-visible copy; a missing key degrades to no caption."""
        try:
            return resources.text(key, variables or None).strip()
        except LocalizationError:
            return ""
