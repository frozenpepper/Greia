"""Presentation renderer for Cucciolo Mio.

Owns pre-rendered backdrop, bounded text caches, and stateless draw helpers.
No Greia IO or game rules; all surfaces are prepared once and reused.
"""

from __future__ import annotations

import math
import random
from typing import Final

import pygame

from greia_platform.typography import FontRole, GreiaTypography
from greia_platform.ui_core import BoundedCache

if __package__:
    from .cucciolo_content import (
        ACCENT_BLUE,
        DARK_TEXT,
        GOLD,
        NIGHT_FLOOR,
        NIGHT_WALL,
        PINK,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ROOM_FLOOR,
        ROOM_WALL,
        WHITE,
    )
    from .cucciolo_model import Particle, PetEntity
else:
    from cucciolo_content import (  # type: ignore[import-not-found,no-redef]
        ACCENT_BLUE,
        DARK_TEXT,
        GOLD,
        NIGHT_FLOOR,
        NIGHT_WALL,
        PINK,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        ROOM_FLOOR,
        ROOM_WALL,
        WHITE,
    )
    from cucciolo_model import Particle, PetEntity  # type: ignore[import-not-found,no-redef]


_MAX_LABEL_CACHE: Final = 64
_MAX_VALUE_CACHE: Final = 32


class CuccioloRenderer:
    """Own backdrop and bounded text surfaces; stateless drawing otherwise."""

    def __init__(self, typography: GreiaTypography) -> None:
        self._typography = typography
        self._backdrop_day: pygame.Surface | None = None
        self._backdrop_night: pygame.Surface | None = None
        # Bounded caches: key -> Surface
        self._label_cache: BoundedCache[tuple[str, int, tuple[int, int, int]], pygame.Surface] = BoundedCache(
            _MAX_LABEL_CACHE
        )
        self._value_cache: BoundedCache[tuple[str, int, tuple[int, int, int], bool], pygame.Surface] = BoundedCache(
            _MAX_VALUE_CACHE
        )
        self._tab_cache: BoundedCache[tuple[str, bool, str], pygame.Surface] = BoundedCache(_MAX_LABEL_CACHE)
        self._hud_cache: BoundedCache[tuple[int, bool], pygame.Surface] = BoundedCache(16)
        # Feedback cache is small and bounded
        self._feedback_cache: BoundedCache[tuple[str, int], pygame.Surface] = BoundedCache(8)
        self._build_backdrops()

    def invalidate(self) -> None:
        """Clear derived caches after resize/theme change."""
        self._label_cache.clear()
        self._value_cache.clear()
        self._tab_cache.clear()
        self._hud_cache.clear()
        self._feedback_cache.clear()
        self._build_backdrops()

    def _build_backdrops(self) -> None:
        # Use opaque surface + convert() once for fast blit; one per day/night mode.
        day = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        day.fill(ROOM_WALL)
        pygame.draw.rect(day, ROOM_FLOOR, (0, 420, REFERENCE_WIDTH, 180))
        pygame.draw.line(day, (200, 170, 140), (0, 420), (REFERENCE_WIDTH, 420), 4)
        rug_col = (255, 210, 220)
        pygame.draw.ellipse(day, rug_col, (262, 380, 500, 120))
        pygame.draw.ellipse(day, (255, 190, 205), (282, 390, 460, 100))
        # convert() requires display initialized; guard for headless import
        try:
            if pygame.display.get_surface() is not None:
                day = day.convert()
        except Exception:
            pass
        self._backdrop_day = day

        night = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        night.fill(NIGHT_WALL)
        pygame.draw.rect(night, NIGHT_FLOOR, (0, 420, REFERENCE_WIDTH, 180))
        pygame.draw.line(night, (45, 38, 65), (0, 420), (REFERENCE_WIDTH, 420), 4)
        rug_col_n = (50, 45, 80)
        pygame.draw.ellipse(night, rug_col_n, (262, 380, 500, 120))
        pygame.draw.ellipse(night, (65, 58, 100), (282, 390, 460, 100))
        try:
            if pygame.display.get_surface() is not None:
                night = night.convert()
        except Exception:
            pass
        self._backdrop_night = night

    # ------------------------------------------------------------------ #
    # Public render entrypoint

    def render(
        self,
        surface: pygame.Surface,
        pet: PetEntity,
        happiness: int,
        hunger: int,
        cleanliness: int,
        active_tab: str,
        active_locale: str,
        particles: list[Particle],
        bubbles: list[tuple[float, float, float]],
        ball_pos: list[float],
        feedback_msg: str,
    ) -> None:
        # Backdrop
        is_sleeping = pet.is_sleeping
        backdrop = self._backdrop_night if is_sleeping else self._backdrop_day
        if backdrop is not None:
            surface.blit(backdrop, (0, 0))
        else:
            # Fallback without cache (headless)
            wall_col = NIGHT_WALL if is_sleeping else ROOM_WALL
            floor_col = NIGHT_FLOOR if is_sleeping else ROOM_FLOOR
            surface.fill(wall_col)
            pygame.draw.rect(surface, floor_col, (0, 420, REFERENCE_WIDTH, 180))
            pygame.draw.line(surface, (200, 170, 140) if not is_sleeping else (45, 38, 65), (0, 420), (REFERENCE_WIDTH, 420), 4)
            rug_col = (255, 210, 220) if not is_sleeping else (50, 45, 80)
            pygame.draw.ellipse(surface, rug_col, (262, 380, 500, 120))
            pygame.draw.ellipse(surface, (255, 190, 205) if not is_sleeping else (65, 58, 100), (282, 390, 460, 100))

        if is_sleeping:
            # Deterministic night stars
            random.seed(99)
            for _ in range(25):
                sx = random.randint(30, REFERENCE_WIDTH - 30)
                sy = random.randint(20, 360)
                pygame.draw.circle(surface, (255, 255, 200), (sx, sy), 3)
            random.seed()

        card_bg = (255, 255, 255) if not is_sleeping else (45, 40, 70)
        border_col = (61, 44, 31) if not is_sleeping else (120, 100, 150)
        txt_col = DARK_TEXT if not is_sleeping else WHITE

        # Stats pills
        stats_data = [
            ("💖", happiness, 5, PINK, 138),
            ("🍎", hunger, 5, (255, 150, 40), 246),
            ("✨", cleanliness, 5, ACCENT_BLUE, 354),
        ]
        for s_icon, s_val, s_max, s_col, s_x in stats_data:
            pill_rect = pygame.Rect(s_x, 10, 104, 66)
            pygame.draw.rect(surface, card_bg, pill_rect, border_radius=16)
            pygame.draw.rect(surface, border_col, pill_rect, width=2, border_radius=16)

            i_surf = self._cached_render(s_icon, FontRole.DISPLAY, 36, txt_col)
            surface.blit(i_surf, (s_x + 6, 12))
            v_key = (f"{s_val}/{s_max}", 20, txt_col, is_sleeping)
            v_surf = self._cached_value_render(f"{s_val}/{s_max}", FontRole.TITLE, 20, txt_col, is_sleeping)
            surface.blit(v_surf, (s_x + 50, 18))

            bar_bg = pygame.Rect(s_x + 10, 50, 84, 14)
            pygame.draw.rect(surface, (225, 225, 230) if not is_sleeping else (60, 55, 85), bar_bg, border_radius=7)
            fill_w = int(84 * (s_val / float(s_max)))
            if fill_w > 0:
                bar_fill = pygame.Rect(s_x + 10, 50, fill_w, 14)
                pygame.draw.rect(surface, s_col, bar_fill, border_radius=7)

        for s_idx, (spec_id, spec_icon) in enumerate([("cat", "🐱"), ("bunny", "🐰"), ("puppy", "🐶")]):
            bx = 470 + s_idx * 78
            is_sel = (pet.species == spec_id)
            btn_bg = GOLD if is_sel else card_bg
            btn_rect = pygame.Rect(bx, 10, 72, 66)
            pygame.draw.rect(surface, btn_bg, btn_rect, border_radius=18)
            pygame.draw.rect(surface, (220, 150, 20) if is_sel else border_col, btn_rect, width=3 if is_sel else 2, border_radius=18)
            s_icon = self._cached_species_icon(spec_icon, 46, txt_col)
            surface.blit(s_icon, s_icon.get_rect(center=btn_rect.center))

        hud_rect = pygame.Rect(775, 10, 230, 66)
        pygame.draw.rect(surface, card_bg, hud_rect, border_radius=18)
        pygame.draw.rect(surface, border_col, hud_rect, width=2, border_radius=18)
        hud_col = (180, 90, 20) if not is_sleeping else GOLD
        hud_str = f"⭐ {happiness}   🏆 {happiness * 20}"
        h_surf = self._cached_hud(hud_str, 26, hud_col, is_sleeping)
        surface.blit(h_surf, h_surf.get_rect(center=hud_rect.center))

        # Pet
        _draw_pet(surface, pet)

        if active_tab == "feed" and not is_sleeping:
            pygame.draw.rect(surface, WHITE, (290, 90, 444, 76), border_radius=22)
            pygame.draw.rect(surface, PINK, (290, 90, 444, 76), width=3, border_radius=22)
            f_treats = self._cached_render("🐟   🍓   🍪   🥛   🧁", FontRole.DISPLAY, 46, DARK_TEXT)
            surface.blit(f_treats, f_treats.get_rect(center=(512, 128)))
        elif active_tab == "bath":
            for bx, by, br in bubbles:
                pygame.draw.circle(surface, (220, 240, 255, 180), (int(bx), int(by)), int(br))
                pygame.draw.circle(surface, WHITE, (int(bx - 4), int(by - 4)), int(br // 3))
        elif active_tab == "play" and not is_sleeping:
            bx, by = int(ball_pos[0]), int(ball_pos[1])
            pygame.draw.circle(surface, (255, 90, 90), (bx, by), 26)
            pygame.draw.ellipse(surface, (255, 220, 50), (bx - 13, by - 26, 26, 52))
            pygame.draw.circle(surface, WHITE, (bx - 7, by - 7), 7)

        for p in particles:
            self._draw_particle(surface, p)

        if feedback_msg:
            f_rect = pygame.Rect(262, 440, 500, 50)
            pygame.draw.rect(surface, WHITE, f_rect, border_radius=16)
            pygame.draw.rect(surface, PINK, f_rect, width=3, border_radius=16)
            t_msg = self._cached_feedback(feedback_msg, 26, DARK_TEXT)
            surface.blit(t_msg, t_msg.get_rect(center=f_rect.center))

        tabs = [
            ("feed", "🐟", "Pappa" if active_locale == "it" else "Treats"),
            ("bath", "🧼", "Bagnetto" if active_locale == "it" else "Bath"),
            ("play", "🎾", "Giochi" if active_locale == "it" else "Play"),
            ("sleep", "🌙", "Nanna" if active_locale == "it" else "Sleep"),
            ("dress", "🎀", "Look" if active_locale == "it" else "Dress"),
        ]
        for idx, (tab_id, tab_icon, tab_label) in enumerate(tabs):
            tx = 95 + idx * 170
            t_active = (active_tab == tab_id)
            t_bg = PINK if t_active else WHITE
            t_border = (220, 80, 130) if t_active else (210, 195, 185)
            t_txt_col = WHITE if t_active else DARK_TEXT

            tab_rect = pygame.Rect(tx, 500, 155, 84)
            pygame.draw.rect(surface, t_bg, tab_rect, border_radius=20)
            pygame.draw.rect(surface, t_border, tab_rect, width=3, border_radius=20)

            i_surf = self._cached_tab_icon(tab_icon, 40, t_txt_col, t_active)
            surface.blit(i_surf, i_surf.get_rect(center=(tx + 77, 526)))

            l_surf = self._cached_tab_label(tab_label, 17, t_txt_col, t_active)
            surface.blit(l_surf, l_surf.get_rect(center=(tx + 77, 564)))

    # ------------------------------------------------------------------ #
    # Cached text helpers

    def _cached_render(self, text: str, role: FontRole, size: int, color: tuple[int, int, int]) -> pygame.Surface:
        key = (text, int(size), tuple(color))
        cached = self._label_cache.get(key)
        if cached is not None:
            return cached
        surf = self._typography.render(text, role, size, color)
        self._label_cache[key] = surf
        return surf

    def _cached_value_render(self, text: str, role: FontRole, size: int, color: tuple[int, int, int], is_sleeping: bool) -> pygame.Surface:
        key = (text, int(size), tuple(color), bool(is_sleeping))
        cached = self._value_cache.get(key)
        if cached is not None:
            return cached
        surf = self._typography.render(text, role, size, color)
        self._value_cache[key] = surf
        return surf

    def _cached_species_icon(self, text: str, size: int, color: tuple[int, int, int]) -> pygame.Surface:
        key = (text, int(size), tuple(color))
        cached = self._label_cache.get(key)
        if cached is not None:
            return cached
        surf = self._typography.render(text, FontRole.DISPLAY, size, color)
        self._label_cache[key] = surf
        return surf

    def _cached_hud(self, text: str, size: int, color: tuple[int, int, int], is_sleeping: bool) -> pygame.Surface:
        key = (text, bool(is_sleeping))
        cached = self._hud_cache.get(key)
        if cached is not None:
            return cached
        surf = self._typography.render(text, FontRole.TITLE, size, color)
        self._hud_cache[key] = surf
        return surf

    def _cached_feedback(self, text: str, size: int, color: tuple[int, int, int]) -> pygame.Surface:
        key = (text, int(size))
        cached = self._feedback_cache.get(key)
        if cached is not None:
            return cached
        surf = self._typography.render(text, FontRole.TITLE, size, color)
        self._feedback_cache[key] = surf
        return surf

    def _cached_tab_icon(self, text: str, size: int, color: tuple[int, int, int], active: bool) -> pygame.Surface:
        key = (text, bool(active), f"icon:{color}")
        cached = self._tab_cache.get(key)
        if cached is not None:
            return cached
        surf = self._typography.render(text, FontRole.DISPLAY, size, color)
        self._tab_cache[key] = surf
        return surf

    def _cached_tab_label(self, text: str, size: int, color: tuple[int, int, int], active: bool) -> pygame.Surface:
        key = (text, bool(active), f"label:{color}")
        cached = self._tab_cache.get(key)
        if cached is not None:
            return cached
        surf = self._typography.render(text, FontRole.TITLE, size, color)
        self._tab_cache[key] = surf
        return surf

    def _draw_particle(self, surface: pygame.Surface, particle: Particle) -> None:
        if particle.life > 0:
            sz = max(12, int(28 * particle.life))
            # Particles are short-lived and size varies, avoid unbounded cache; direct render is bounded by MAX_PARTICLES
            p_surf = self._typography.render(particle.symbol, FontRole.DISPLAY, sz, particle.color)
            surface.blit(p_surf, (int(particle.x) - p_surf.get_width() // 2, int(particle.y) - p_surf.get_height() // 2))


def _draw_pet(surface: pygame.Surface, pet: PetEntity) -> None:
    """Stateless pet drawing, extracted from former PetEntity.draw."""

    px = int(pet.x)
    py = int(pet.y)

    body_col = (255, 175, 110) if pet.species == "cat" else ((240, 235, 230) if pet.species == "bunny" else (225, 160, 100))
    tummy_col = (255, 250, 245)

    tail_wag = math.sin(pet.wag_angle) * 16.0
    if pet.species == "cat":
        pygame.draw.circle(surface, body_col, (px + 60 + int(tail_wag * 0.5), py + 35), 14)
    elif pet.species == "puppy":
        pygame.draw.ellipse(surface, (190, 120, 60), (px + 45, py + 20 - int(tail_wag), 20, 36))
    else:
        pygame.draw.circle(surface, WHITE, (px + 50, py + 35), 16)

    pygame.draw.ellipse(surface, body_col, (px - 50, py - 20, 100, 90))
    pygame.draw.ellipse(surface, tummy_col, (px - 32, py - 10, 64, 70))

    pygame.draw.circle(surface, tummy_col, (px - 30, py + 65), 14)
    pygame.draw.circle(surface, tummy_col, (px + 30, py + 65), 14)

    pygame.draw.ellipse(surface, body_col, (px - 55, py - 95, 110, 95))

    if pet.species == "cat":
        pygame.draw.polygon(surface, body_col, [(px - 50, py - 75), (px - 45, py - 130), (px - 10, py - 85)])
        pygame.draw.polygon(surface, PINK, [(px - 44, py - 80), (px - 40, py - 120), (px - 16, py - 88)])
        pygame.draw.polygon(surface, body_col, [(px + 10, py - 85), (px + 45, py - 130), (px + 50, py - 75)])
        pygame.draw.polygon(surface, PINK, [(px + 16, py - 88), (px + 40, py - 120), (px + 44, py - 80)])
    elif pet.species == "bunny":
        pygame.draw.ellipse(surface, body_col, (px - 45, py - 170, 32, 90))
        pygame.draw.ellipse(surface, PINK, (px - 37, py - 160, 16, 70))
        pygame.draw.ellipse(surface, body_col, (px + 15, py - 170, 32, 90))
        pygame.draw.ellipse(surface, PINK, (px + 23, py - 160, 16, 70))
    else:
        pygame.draw.ellipse(surface, (170, 105, 50), (px - 65, py - 85, 34, 75))
        pygame.draw.ellipse(surface, (170, 105, 50), (px + 31, py - 85, 34, 75))

    pygame.draw.ellipse(surface, tummy_col, (px - 38, py - 45, 76, 45))

    pygame.draw.circle(surface, (255, 130, 160), (px - 36, py - 30), 10)
    pygame.draw.circle(surface, (255, 130, 160), (px + 36, py - 30), 10)

    if pet.is_sleeping:
        pygame.draw.arc(surface, DARK_TEXT, (px - 38, py - 60, 24, 18), 0, math.pi, 3)
        pygame.draw.arc(surface, DARK_TEXT, (px + 14, py - 60, 24, 18), 0, math.pi, 3)
    elif pet.blink_timer > 0.18:
        pygame.draw.ellipse(surface, (30, 25, 35), (px - 36, py - 65, 24, 30))
        pygame.draw.ellipse(surface, (30, 25, 35), (px + 12, py - 65, 24, 30))
        pygame.draw.circle(surface, WHITE, (px - 28, py - 58), 6)
        pygame.draw.circle(surface, WHITE, (px - 20, py - 48), 3)
        pygame.draw.circle(surface, WHITE, (px + 20, py - 58), 6)
        pygame.draw.circle(surface, WHITE, (px + 28, py - 48), 3)
    else:
        pygame.draw.line(surface, DARK_TEXT, (px - 36, py - 50), (px - 14, py - 50), 3)
        pygame.draw.line(surface, DARK_TEXT, (px + 14, py - 50), (px + 36, py - 50), 3)

    pygame.draw.polygon(surface, (245, 110, 140), [(px, py - 34), (px - 6, py - 40), (px + 6, py - 40)])

    if pet.chew_timer > 0:
        chew_h = int(abs(math.sin(pet.chew_timer * 18.0)) * 8) + 2
        pygame.draw.ellipse(surface, (240, 80, 110), (px - 10, py - 30, 20, chew_h))
    else:
        pygame.draw.arc(surface, DARK_TEXT, (px - 14, py - 34, 14, 12), math.pi, 2 * math.pi, 2)
        pygame.draw.arc(surface, DARK_TEXT, (px, py - 34, 14, 12), math.pi, 2 * math.pi, 2)

    if pet.accessory == "bow":
        bx, by = px - 35, py - 90
        pygame.draw.polygon(surface, PINK, [(bx, by), (bx - 14, by - 10), (bx - 14, by + 10)])
        pygame.draw.polygon(surface, PINK, [(bx, by), (bx + 14, by - 10), (bx + 14, by + 10)])
        pygame.draw.circle(surface, (255, 80, 120), (bx, by), 6)
    elif pet.accessory == "crown":
        cx, cy = px, py - 100
        pygame.draw.polygon(surface, GOLD, [(cx - 22, cy), (cx - 22, cy - 20), (cx - 11, cy - 8), (cx, cy - 24), (cx + 11, cy - 8), (cx + 22, cy - 20), (cx + 22, cy)])
    elif pet.accessory == "glasses":
        gx, gy = px - 24, py - 50
        pygame.draw.circle(surface, (40, 40, 50), (gx, gy), 14, 3)
        pygame.draw.circle(surface, (40, 40, 50), (gx + 48, gy), 14, 3)
        pygame.draw.line(surface, (40, 40, 50), (gx + 14, gy), (gx + 34, gy), 3)
    elif pet.accessory == "party_hat":
        hx, hy = px, py - 95
        pygame.draw.polygon(surface, (130, 90, 240), [(hx, hy - 45), (hx - 22, hy), (hx + 22, hy)])
        pygame.draw.circle(surface, GOLD, (hx, hy - 45), 7)


__all__ = ["CuccioloRenderer"]
