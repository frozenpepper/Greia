"""Sottomarino Giramondo — Cockpit Instruments, Radar & Viewport Presentation.

Renders the 3D underwater ocean through the circular porthole,
the radar sweep, analog depth dial, and chunky interactive buttons.
Optimized for Atom-class low-resource execution (cached surfaces, bounded blits).
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .sub_art import (
        PORTHOLE_CENTER_X,
        PORTHOLE_CENTER_Y,
        PORTHOLE_RADIUS,
        SubmarineArt,
    )
    from .sub_model import (
        BiomeType,
        EncounterType,
        MarineEntity3D,
        SubmarineModel,
        get_biome,
    )
else:
    from sub_art import (
        PORTHOLE_CENTER_X,
        PORTHOLE_CENTER_Y,
        PORTHOLE_RADIUS,
        SubmarineArt,
    )
    from sub_model import (
        BiomeType,
        EncounterType,
        MarineEntity3D,
        SubmarineModel,
        get_biome,
    )

REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600

# Radar sweep geometry
RADAR_CENTER_X = 140
RADAR_CENTER_Y = 490
RADAR_RADIUS = 65

# Depth dial geometry
DEPTH_CENTER_X = 884
DEPTH_CENTER_Y = 490
DEPTH_RADIUS = 65

# Chunky Cockpit Buttons Geometry: (x, y, w, h)
BUTTON_RECTS = {
    "light": pygame.Rect(228, 446, 100, 88),
    "sonar": pygame.Rect(351, 446, 100, 88),
    "action": pygame.Rect(472, 447, 80, 86),  # Central emergency beacon button
    "bubbles": pygame.Rect(573, 446, 100, 88),
    "horn": pygame.Rect(696, 446, 100, 88),
}


class CockpitPresenter:
    """Renders the complete cockpit dashboard and porthole ocean scene."""

    def __init__(self, art: SubmarineArt, typography: GreiaTypography) -> None:
        self.art = art
        self.typography = typography

    def render(
        self,
        surface: pygame.Surface,
        model: SubmarineModel,
        resources: LocalizedResources,
        hot_button: Optional[str] = None
    ) -> None:
        # 1. Render the 3D Ocean Viewport (drawn under the porthole)
        self._render_ocean_viewport(surface, model)

        # 2. Overlay the Cockpit Bulkhead & Riveted Porthole
        surface.blit(self.art.porthole_mask, (0, 0))

        # 3. Render Cockpit Lower Console / Dashboard Background
        self._render_dashboard_panel(surface, model)

        # 4. Render Radar Screen & Blips
        self._render_radar(surface, model)

        # 5. Render Analog Depth Meter
        self._render_depth_gauge(surface, model, resources)

        # 6. Render Chunky Push-Buttons
        self._render_buttons(surface, model, resources, hot_button)

        # 7. Render Marine Discovery Banner / Creature Name when recently discovered
        self._render_discovery_hud(surface, model, resources)

    def _render_ocean_viewport(self, surface: pygame.Surface, model: SubmarineModel) -> None:
        biome = get_biome(model.depth)

        # Background ocean color gradient based on biome and floodlight
        if biome == BiomeType.SHALLOW_REEF:
            top_color = (25, 140, 190)
            bot_color = (15, 80, 130)
        elif biome == BiomeType.TWILIGHT_KELP:
            top_color = (15, 60, 110)
            bot_color = (8, 30, 70)
        else:
            top_color = (8, 15, 45)
            bot_color = (3, 6, 20)

        if model.lights_on:
            top_color = (min(255, top_color[0] + 45), min(255, top_color[1] + 55), min(255, top_color[2] + 40))
            bot_color = (min(255, bot_color[0] + 35), min(255, bot_color[1] + 45), min(255, bot_color[2] + 35))

        view_rect = pygame.Rect(
            PORTHOLE_CENTER_X - PORTHOLE_RADIUS,
            PORTHOLE_CENTER_Y - PORTHOLE_RADIUS,
            PORTHOLE_RADIUS * 2,
            PORTHOLE_RADIUS * 2
        )
        surface.fill(top_color, view_rect)

        # Sunbeams in shallow reef
        if biome == BiomeType.SHALLOW_REEF and not model.lights_on:
            for ray in range(4):
                rx = PORTHOLE_CENTER_X - 100 + ray * 70
                ray_surf = pygame.Surface((40, PORTHOLE_RADIUS * 2), pygame.SRCALPHA)
                pygame.draw.polygon(ray_surf, (255, 255, 220, 25), [(10, 0), (30, 0), (40, PORTHOLE_RADIUS * 2), (0, PORTHOLE_RADIUS * 2)])
                surface.blit(ray_surf, (rx, PORTHOLE_CENTER_Y - PORTHOLE_RADIUS))

        # Sort entities by depth
        sorted_entities = sorted(model.entities, key=lambda e: e.z, reverse=True)

        for ent in sorted_entities:
            scale = 1.0 / max(0.1, ent.z)
            sx = PORTHOLE_CENTER_X + int(ent.x * 240.0 * scale)
            sy = PORTHOLE_CENTER_Y + int(ent.y * 240.0 * scale)

            sprite = self.art.get_sprite(ent.kind)
            if sprite is None:
                continue

            orig_w, orig_h = sprite.get_size()
            target_w = max(10, int(orig_w * ent.size_base * scale * 0.45))
            target_h = max(10, int(orig_h * ent.size_base * scale * 0.45))

            scaled_sprite = pygame.transform.smoothscale(sprite, (target_w, target_h))

            draw_x = sx - target_w // 2
            draw_y = sy - target_h // 2

            if (view_rect.left - target_w < draw_x < view_rect.right + target_w and
                view_rect.top - target_h < draw_y < view_rect.bottom + target_h):
                surface.blit(scaled_sprite, (draw_x, draw_y))

        # Render Encounter Creature right on the porthole glass
        if model.encounter.active_type != EncounterType.NONE:
            self._render_encounter_creature(surface, model)

    def _render_encounter_creature(self, surface: pygame.Surface, model: SubmarineModel) -> None:
        enc = model.encounter
        alpha = int(min(255, enc.progress * 255))
        if enc.solved:
            alpha = int(max(0, enc.solve_timer * 127))

        if enc.active_type == EncounterType.OCTOPUS_HUG:
            sprite = self.art.get_sprite("octopus")
        else:
            sprite = self.art.get_sprite("shark")

        if sprite is not None and alpha > 0:
            surf_copy = sprite.copy()
            surf_copy.set_alpha(alpha)
            w, h = surf_copy.get_size()
            cx = PORTHOLE_CENTER_X - w // 2
            cy = PORTHOLE_CENTER_Y - h // 2
            cy += int(math.sin(pygame.time.get_ticks() * 0.005) * 8)
            surface.blit(surf_copy, (cx, cy))

    def _render_dashboard_panel(self, surface: pygame.Surface, model: SubmarineModel) -> None:
        panel_rect = pygame.Rect(0, 435, REFERENCE_WIDTH, REFERENCE_HEIGHT - 435)
        pygame.draw.rect(surface, (32, 42, 54), panel_rect)
        pygame.draw.line(surface, (65, 85, 105), (0, 435), (REFERENCE_WIDTH, 435), 3)
        pygame.draw.line(surface, (20, 26, 34), (0, 438), (REFERENCE_WIDTH, 438), 2)

    def _render_radar(self, surface: pygame.Surface, model: SubmarineModel) -> None:
        cx, cy, r = RADAR_CENTER_X, RADAR_CENTER_Y, RADAR_RADIUS
        pygame.draw.circle(surface, (180, 140, 50), (cx, cy), r + 5, 4)
        pygame.draw.circle(surface, (10, 30, 20), (cx, cy), r)

        pygame.draw.circle(surface, (25, 75, 45), (cx, cy), r // 3, 1)
        pygame.draw.circle(surface, (25, 75, 45), (cx, cy), (r * 2) // 3, 1)
        pygame.draw.circle(surface, (35, 105, 60), (cx, cy), r, 1)

        pygame.draw.line(surface, (25, 75, 45), (cx - r, cy), (cx + r, cy), 1)
        pygame.draw.line(surface, (25, 75, 45), (cx, cy - r), (cx, cy + r), 1)

        rad = math.radians(model.radar_angle)
        sx = cx + int(r * math.cos(rad))
        sy = cy + int(r * math.sin(rad))
        sweep_color = (90, 255, 140) if model.sonar_active else (40, 180, 80)
        pygame.draw.line(surface, sweep_color, (cx, cy), (sx, sy), 2)

        for ent in model.entities:
            if ent.kind != "bubble":
                dist = min(1.0, ent.z / 1.5)
                bx = cx + int(ent.x * (r * 0.7))
                by = cy + int(dist * (r * 0.8) - (r * 0.4))
                if (bx - cx)**2 + (by - cy)**2 <= (r - 4)**2:
                    pygame.draw.circle(surface, (120, 255, 160), (bx, by), 3)

    def _render_depth_gauge(self, surface: pygame.Surface, model: SubmarineModel, resources: LocalizedResources) -> None:
        cx, cy, r = DEPTH_CENTER_X, DEPTH_CENTER_Y, DEPTH_RADIUS
        pygame.draw.circle(surface, (180, 140, 50), (cx, cy), r + 5, 4)
        pygame.draw.circle(surface, (240, 235, 220), (cx, cy), r)

        for d in range(0, 101, 10):
            frac = d / 100.0
            angle = math.radians(135 + frac * 270)
            t_outer = r - 4
            t_inner = r - 12 if d % 20 == 0 else r - 8
            x1 = cx + int(t_outer * math.cos(angle))
            y1 = cy + int(t_outer * math.sin(angle))
            x2 = cx + int(t_inner * math.cos(angle))
            y2 = cy + int(t_inner * math.sin(angle))
            pygame.draw.line(surface, (40, 40, 40), (x1, y1), (x2, y2), 2)

        depth_frac = min(1.0, max(0.0, model.depth / 100.0))
        needle_angle = math.radians(135 + depth_frac * 270)
        nx = cx + int((r - 14) * math.cos(needle_angle))
        ny = cy + int((r - 14) * math.sin(needle_angle))
        pygame.draw.line(surface, (220, 40, 30), (cx, cy), (nx, ny), 3)
        pygame.draw.circle(surface, (40, 40, 40), (cx, cy), 6)

        depth_txt = f"{int(model.depth)} m"
        txt_surf = self.typography.render(depth_txt, FontRole.BODY, 16, (30, 30, 30))
        surface.blit(txt_surf, (cx - txt_surf.get_width() // 2, cy + 20))

    def _render_buttons(
        self,
        surface: pygame.Surface,
        model: SubmarineModel,
        resources: LocalizedResources,
        hot_button: Optional[str] = None
    ) -> None:
        enc = model.encounter
        is_encounter = (enc.active_type != EncounterType.NONE and not enc.solved)

        # Highlight recommended action buttons during encounters
        pulse = (math.sin(pygame.time.get_ticks() * 0.012) + 1.0) * 0.5
        pulse_flash = pulse > 0.4

        button_configs = [
            ("light", "btn.light", (245, 210, 60), model.lights_on, "light", is_encounter and enc.active_type == EncounterType.SHARK_WAVE),
            ("sonar", "btn.sonar", (80, 190, 225), model.sonar_active, "sonar", False),
            ("bubbles", "btn.bubbles", (100, 220, 160), model.bubble_release_timer > 0, "bubbles", is_encounter and enc.active_type == EncounterType.OCTOPUS_HUG),
            ("horn", "btn.horn", (240, 120, 70), False, "horn", is_encounter and enc.active_type == EncounterType.OCTOPUS_HUG),
        ]

        for name, key, color, active, icon_type, is_hinted in button_configs:
            rect = BUTTON_RECTS[name]
            is_hover = (hot_button == name)
            flash = is_hinted and pulse_flash
            self._draw_tactile_button(
                surface, rect, color, active, is_hover, resources.text(key), icon_type, flash
            )

        action_rect = BUTTON_RECTS["action"]
        action_hover = (hot_button == "action")

        if is_encounter:
            action_color = (int(255), int(60 + pulse * 140), int(40))
        else:
            action_color = (220, 55, 55)

        self._draw_beacon_button(surface, action_rect, action_color, is_encounter, action_hover)

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
        shadow_rect = rect.copy()
        shadow_rect.y += 4
        pygame.draw.rect(surface, (15, 20, 28), shadow_rect, border_radius=14)

        if flashing:
            aura = pygame.Surface((rect.width + 20, rect.height + 20), pygame.SRCALPHA)
            pygame.draw.rect(aura, (255, 240, 100, 150), (0, 0, rect.width + 20, rect.height + 20), border_radius=18)
            surface.blit(aura, (rect.x - 10, rect.y - 10))

        btn_rect = rect.copy()
        if active or hover:
            btn_rect.y += 2

        if flashing:
            col = (min(255, base_color[0] + 45), min(255, base_color[1] + 45), min(255, base_color[2] + 45))
        else:
            col = (
                min(255, base_color[0] + 30),
                min(255, base_color[1] + 30),
                min(255, base_color[2] + 30)
            ) if (active or hover) else base_color

        pygame.draw.rect(surface, col, btn_rect, border_radius=14)
        border_col = (255, 255, 255, 220) if flashing else (255, 255, 255, 110)
        pygame.draw.rect(surface, border_col, btn_rect, width=3 if flashing else 2, border_radius=14)

        # Draw crisp, bold vector icon in upper portion of button
        icon_cy = btn_rect.top + 32
        icon_cx = btn_rect.centerx
        icon_col = (20, 24, 32)
        self._draw_button_icon(surface, icon_type, icon_cx, icon_cy, icon_col, active or hover)

        # Draw clear child-friendly label in lower portion of button
        txt_surf = self.typography.render(label, FontRole.CONTROL, 13, (25, 30, 38))
        surface.blit(txt_surf, (btn_rect.centerx - txt_surf.get_width() // 2, btn_rect.bottom - txt_surf.get_height() - 6))

    def _draw_button_icon(
        self,
        surface: pygame.Surface,
        icon_type: str,
        cx: int,
        cy: int,
        color: Tuple[int, int, int],
        active: bool,
    ) -> None:
        """Render bold, prominent vector symbols for instant pre-reader recognition."""
        if icon_type == "light":
            # Large bold light bulb with rays
            pygame.draw.circle(surface, color, (cx, cy - 4), 13)
            pygame.draw.polygon(surface, color, [
                (cx - 10, cy), (cx + 10, cy),
                (cx + 6, cy + 12), (cx - 6, cy + 12)
            ])
            pygame.draw.rect(surface, (100, 100, 100), (cx - 5, cy + 13, 10, 4), border_radius=2)
            # Bright inner glass glint
            pygame.draw.circle(surface, (255, 255, 255), (cx - 4, cy - 7), 3)
            # Bold radiating rays
            rays = [
                ((cx, cy - 20), (cx, cy - 26)),
                ((cx - 14, cy - 14), (cx - 20, cy - 19)),
                ((cx + 14, cy - 14), (cx + 20, cy - 19)),
                ((cx - 17, cy - 3), (cx - 23, cy - 3)),
                ((cx + 17, cy - 3), (cx + 23, cy - 3)),
            ]
            for p1, p2 in rays:
                pygame.draw.line(surface, color, p1, p2, 3)

        elif icon_type == "sonar":
            # Transmitter dish with radiating acoustic arcs
            pygame.draw.circle(surface, color, (cx, cy + 6), 5)
            pygame.draw.arc(surface, color, (cx - 13, cy - 7, 26, 26), 0.5, 2.64, 3)
            pygame.draw.arc(surface, color, (cx - 22, cy - 16, 44, 44), 0.5, 2.64, 3)
            # Antenna mast & solid pedestal
            pygame.draw.line(surface, color, (cx, cy + 6), (cx, cy + 18), 3)
            pygame.draw.line(surface, color, (cx - 9, cy + 18), (cx + 9, cy + 18), 3)

        elif icon_type == "bubbles":
            # Three ascending buoyant bubbles with glint dots and circular highlights
            # Bottom-left big bubble
            pygame.draw.circle(surface, color, (cx - 9, cy + 5), 11, 3)
            pygame.draw.circle(surface, (255, 255, 255), (cx - 6, cy + 2), 3)
            # Upper-right medium bubble
            pygame.draw.circle(surface, color, (cx + 9, cy - 5), 8, 3)
            pygame.draw.circle(surface, (255, 255, 255), (cx + 11, cy - 7), 2)
            # Top-left small bubble
            pygame.draw.circle(surface, color, (cx - 2, cy - 14), 5, 2)
            pygame.draw.circle(surface, (255, 255, 255), (cx - 1, cy - 15), 1)

        elif icon_type == "horn":
            # Acoustic horn / loudspeaker with soundwaves
            pygame.draw.rect(surface, color, (cx - 19, cy - 6, 9, 12), border_radius=2)
            pygame.draw.polygon(surface, color, [
                (cx - 10, cy - 6), (cx + 4, cy - 14),
                (cx + 4, cy + 14), (cx - 10, cy + 6)
            ])
            # Expanding sound waves
            pygame.draw.arc(surface, color, (cx + 3, cy - 9, 12, 18), -1.1, 1.1, 3)
            pygame.draw.arc(surface, color, (cx + 9, cy - 15, 18, 30), -1.1, 1.1, 3)

    def _draw_beacon_button(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        color: Tuple[int, int, int],
        flashing: bool,
        hover: bool
    ) -> None:
        cx, cy = rect.centerx, rect.centery
        radius = rect.width // 2

        # Sturdy metallic bezel ring
        pygame.draw.circle(surface, (18, 24, 32), (cx, cy + 4), radius + 5)
        pygame.draw.circle(surface, (100, 105, 115), (cx, cy), radius + 4, 3)

        if flashing:
            aura_surf = pygame.Surface((rect.width + 50, rect.height + 50), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (color[0], color[1], color[2], 100), (radius + 25, radius + 25), radius + 20)
            surface.blit(aura_surf, (rect.x - 25, rect.y - 25))

        btn_y = cy + (2 if hover else 0)
        # Deep red base ring
        pygame.draw.circle(surface, (140, 25, 25), (cx, btn_y), radius)
        # Red dome
        pygame.draw.circle(surface, color, (cx, btn_y), radius - 3)
        # Inner glossy rim
        pygame.draw.circle(surface, (255, 130, 130), (cx, btn_y), radius - 3, 2)
        # Subtle top crescent highlight
        pygame.draw.arc(surface, (255, 255, 255, 200), (cx - radius + 8, btn_y - radius + 6, (radius - 8) * 2, (radius - 8) * 2), 0.7, 2.44, 3)

        # Bold white alert star & exclamation in beacon center
        star_col = (255, 255, 255)
        s = 11
        pygame.draw.line(surface, star_col, (cx - s, btn_y), (cx + s, btn_y), 4)
        pygame.draw.line(surface, star_col, (cx, btn_y - s), (cx, btn_y + s), 4)
        s_diag = 7
        pygame.draw.line(surface, star_col, (cx - s_diag, btn_y - s_diag), (cx + s_diag, btn_y + s_diag), 3)
        pygame.draw.line(surface, star_col, (cx - s_diag, btn_y + s_diag), (cx + s_diag, btn_y - s_diag), 3)
        pygame.draw.circle(surface, star_col, (cx, btn_y), 5)

    def _render_discovery_hud(
        self,
        surface: pygame.Surface,
        model: SubmarineModel,
        resources: LocalizedResources
    ) -> None:
        biome = get_biome(model.depth)
        if biome == BiomeType.SHALLOW_REEF:
            b_name = resources.text("biome.shallow")
        elif biome == BiomeType.TWILIGHT_KELP:
            b_name = resources.text("biome.twilight")
        else:
            b_name = resources.text("biome.abyss")

        badge_txt = self.typography.render(b_name, FontRole.TITLE, 18, (240, 240, 240))
        surface.blit(badge_txt, (REFERENCE_WIDTH - badge_txt.get_width() - 30, 25))

        # Encounter prompt banner on top-center if encounter active
        if model.encounter.active_type != EncounterType.NONE and not model.encounter.solved:
            enc = model.encounter
            if enc.active_type == EncounterType.OCTOPUS_HUG:
                prompt_txt = resources.text("encounter.octopus.hint")
            else:
                prompt_txt = resources.text("encounter.shark.hint")

            banner_surf = self.typography.render(prompt_txt, FontRole.TITLE, 16, (255, 235, 100))
            bx = REFERENCE_WIDTH // 2 - banner_surf.get_width() // 2
            bg_rect = pygame.Rect(bx - 12, 18, banner_surf.get_width() + 24, banner_surf.get_height() + 8)
            pygame.draw.rect(surface, (15, 20, 25, 220), bg_rect, border_radius=8)
            surface.blit(banner_surf, (bx, 22))
