"""High-performance one-pass game renderer and HUD for Il Volo del Draghetto."""

from __future__ import annotations

import math
from typing import Any, Final

import pygame

from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.typography import FontRole, GreiaTypography

try:
    from dragon_art import (
        DARK_TEXT,
        GOLD,
        GOLD_DARK,
        PINK,
        WHITE,
        DragonArtLibrary,
    )
    from dragon_model import (
        FlightWorldState,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )
except ImportError:
    from .dragon_art import (
        DARK_TEXT,
        GOLD,
        GOLD_DARK,
        PINK,
        WHITE,
        DragonArtLibrary,
    )
    from .dragon_model import (
        FlightWorldState,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
    )


class DragonRenderer:
    """Composites game elements, parallax sky, dragon, particles, and tactile HUD."""

    def __init__(
        self,
        art: DragonArtLibrary,
        typography: GreiaTypography,
        look_label: str = "",
    ) -> None:
        self._art = art
        self._typography = typography
        # Localized caption (case policy already applied); empty = crown only.
        self._accessory_caption = " ".join(part for part in ("👑", look_label.strip()) if part)
        self._text_cache: dict[tuple[str, str, int, tuple[int, int, int]], pygame.Surface] = {}

    def _render_cached_text(
        self, text: str, role: FontRole, size: int, color: tuple[int, int, int]
    ) -> pygame.Surface:
        key = (text, role.name, size, color)
        cached = self._text_cache.get(key)
        if cached is not None:
            return cached
        surf = self._typography.render(text, role, size, color)
        if len(self._text_cache) > 200:
            self._text_cache.clear()
        self._text_cache[key] = surf
        return surf

    def render_world(
        self,
        surface: pygame.Surface,
        world: FlightWorldState,
        feedback_message: str = "",
    ) -> None:
        """Composite the active gameplay frame in one fast hardware-friendly pass."""
        cam_x = world.dragon.x - 200.0

        # 1. Sky Background Blit (1.8 ms fast blit)
        surface.blit(self._art.get_sky_background(), (0, 0))

        # 2. Distant Parallax Clouds (0.2 ms ultra-fast colorkey blits)
        c1, c2, c3 = self._art.get_distant_clouds()
        x1 = int(140 - cam_x * 0.12) % (REFERENCE_WIDTH + 200) - 100
        surface.blit(c1, (x1, 70))
        x2 = int(540 - cam_x * 0.20) % (REFERENCE_WIDTH + 260) - 130
        surface.blit(c2, (x2, 100))
        x3 = int(920 - cam_x * 0.16) % (REFERENCE_WIDTH + 220) - 110
        surface.blit(c3, (x3, 65))

        # 3. Clouds (Bouncy Obstacles)
        cloud_sprite = self._art.get_cloud_obstacle_sprite()
        cw, ch = cloud_sprite.get_size()
        for cl in world.clouds:
            sx = int(cl.x - cam_x)
            sy = int(cl.y)
            if -cw <= sx <= REFERENCE_WIDTH + cw:
                surface.blit(cloud_sprite, (sx - cw // 2, sy - ch // 2))

        # 4. Rainbow Arches (Super Turbo Boost Gates)
        gate_sprite = self._art.get_rainbow_gate_sprite()
        gw, gh = gate_sprite.get_size()
        for gate in world.rainbow_gates:
            sx = int(gate.x - cam_x)
            sy = int(gate.y)
            if -gw <= sx <= REFERENCE_WIDTH + gw:
                surface.blit(gate_sprite, (sx - gw // 2, sy - gh + 35))

        # 5. Collectible Stars
        star_sprite = self._art.get_star_sprite()
        sw, sh = star_sprite.get_size()
        for star in world.stars:
            if not star.collected:
                sx = int(star.x - cam_x)
                sy = int(star.effective_y)
                if -sw <= sx <= REFERENCE_WIDTH + sw:
                    surface.blit(star_sprite, (sx - sw // 2, sy - sh // 2))

        # 6. Dragon Player
        dragon_sprite = self._art.get_dragon_sprite(
            world.dragon.wing_flap_phase,
            world.dragon.accessory,
            world.dragon.is_dashing,
        )
        dw, dh = dragon_sprite.get_size()
        dsx = int(world.dragon.x - cam_x)
        dsy = int(world.dragon.y)
        surface.blit(dragon_sprite, (dsx - 80, dsy - 75))

        # 7. Visual Particles (Cached pre-rendered glyphs/shapes)
        for p in world.particles:
            if p.life > 0.0:
                psx = int(p.x - cam_x)
                psy = int(p.y)
                if -40 <= psx <= REFERENCE_WIDTH + 40:
                    p_sz = max(8, int(p.size * p.life))
                    p_sprite = self._art.get_particle_sprite(p.kind, p_sz, p.color)
                    pw, ph = p_sprite.get_size()
                    surface.blit(p_sprite, (psx - pw // 2, psy - ph // 2))

        # 8. HUD Overlays (Pills for Stars, Score, Accessory)
        self._render_hud(surface, world)

    def _render_hud(
        self,
        surface: pygame.Surface,
        world: FlightWorldState,
    ) -> None:
        # Accessory Button (Top Right: x=580..710, y=14..58)
        acc_box = pygame.Rect(580, 14, 136, 44)
        pygame.draw.rect(surface, WHITE, acc_box, border_radius=14)
        pygame.draw.rect(surface, (190, 140, 210), acc_box, width=2, border_radius=14)
        acc_label = self._render_cached_text(self._accessory_caption, FontRole.TITLE, 20, DARK_TEXT)
        surface.blit(acc_label, acc_label.get_rect(center=acc_box.center))

        # Star & Score HUD (Top Right: x=728..988, y=14..58)
        hud_box = pygame.Rect(728, 14, 260, 44)
        pygame.draw.rect(surface, WHITE, hud_box, border_radius=14)
        pygame.draw.rect(surface, (245, 180, 30), hud_box, width=2, border_radius=14)

        # Star count badge with continuous total stars
        star_str = f"⭐ {world.total_stars}   🏆 {world.score}"
        hud_label = self._render_cached_text(star_str, FontRole.TITLE, 22, (180, 85, 15))
        surface.blit(hud_label, hud_label.get_rect(center=hud_box.center))
