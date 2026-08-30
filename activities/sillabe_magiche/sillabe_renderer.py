from __future__ import annotations

"""Stateless draw helpers and presentation owners for Sillabe Magiche.

Entity classes (Particle, LeoCompanion, SyllableCard, FloatingOrb, WordTile)
are visual owners with explicit bounce/wobble state and bounded transient
effects. SillabeRenderer owns the prebaked meadow backdrop, bounded text
surfaces and small caches so the hot frame loop does not decode, scale or
construct fonts per frame.
"""

import math
import random

import pygame

if __package__:
    from .sillabe_content import (
        BG_GRASS_BACK,
        BG_GRASS_FRONT,
        BG_SKY_BOTTOM,
        BG_SKY_TOP,
        CARD_BG,
        CARD_BORDER,
        CORAL,
        DARK_TEXT,
        GOLD,
        GOLD_BORDER,
        LIGHT_TEXT,
        MINT_GREEN,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SHADOW_COLOR,
        SKY_BLUE,
        SYLLABLE_COLORS,
    )
else:
    from sillabe_content import (
        BG_GRASS_BACK,
        BG_GRASS_FRONT,
        BG_SKY_BOTTOM,
        BG_SKY_TOP,
        CARD_BG,
        CARD_BORDER,
        CORAL,
        DARK_TEXT,
        GOLD,
        GOLD_BORDER,
        LIGHT_TEXT,
        MINT_GREEN,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SHADOW_COLOR,
        SKY_BLUE,
        SYLLABLE_COLORS,
    )

from greia_platform.activity_ui import mix
from greia_platform.typography import FontRole, GreiaTypography

# Bounded text cache for reused syllable/word surfaces: finite inventory so
# unbounded growth is impossible on the Acer floor.
_MAX_TEXT_CACHE = 96


class Particle:
    def __init__(self, x: float, y: float, color: tuple[int, int, int]) -> None:
        self.x = x
        self.y = y
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2.5, 7.5)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.decay = random.uniform(0.025, 0.045)
        self.color = color
        self.size = random.randint(5, 11)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.10
        self.life -= self.decay
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        if self.life > 0:
            sz = max(1, int(self.size * self.life))
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), sz)
            pygame.draw.circle(surface, (255, 255, 255), (int(self.x), int(self.y)), max(1, sz // 2))


class LeoCompanion:
    """Leo the Scholar Owl — Canonical Greia reading & language mascot."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.bob = 0.0
        self.blink_timer = 3.0
        self.happy_timer = 0.0
        self.wiggle_timer = 0.0

    def cheer(self) -> None:
        self.happy_timer = 2.2

    def wiggle(self) -> None:
        self.wiggle_timer = 1.2

    def update(self) -> None:
        self.bob += 0.05
        self.blink_timer -= 0.02
        if self.blink_timer <= 0:
            self.blink_timer = random.uniform(2.5, 4.5)
        if self.happy_timer > 0:
            self.happy_timer -= 0.035
        if self.wiggle_timer > 0:
            self.wiggle_timer -= 0.04

    def contains(self, px: float, py: float) -> bool:
        return (self.x - px) ** 2 + (self.y - py) ** 2 <= 55 ** 2

    def draw(self, surface: pygame.Surface) -> None:
        mx = int(self.x)
        my = int(self.y + math.sin(self.bob) * 5)
        if self.happy_timer > 0:
            my += int(abs(math.sin(self.happy_timer * 14.0)) * -16)
        if self.wiggle_timer > 0:
            mx += int(math.sin(self.wiggle_timer * 18.0) * 8)

        # Shadow
        shadow_surf = pygame.Surface((96, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, SHADOW_COLOR, (0, 0, 96, 24))
        surface.blit(shadow_surf, (mx - 48, int(self.y) + 40))

        # Leo Owl Body Colors
        body_col = (110, 75, 160)
        belly_col = (255, 240, 215)
        wing_col = (90, 55, 140)
        beak_col = (255, 175, 45)
        glasses_col = (245, 90, 115)

        # Wings
        pygame.draw.ellipse(surface, wing_col, (mx - 46, my - 15, 26, 48))
        pygame.draw.ellipse(surface, wing_col, (mx + 20, my - 15, 26, 48))

        # Body Bean
        pygame.draw.ellipse(surface, body_col, (mx - 38, my - 44, 76, 84))
        pygame.draw.ellipse(surface, CARD_BORDER, (mx - 38, my - 44, 76, 84), width=3)

        # Feather Ear Tufts
        pygame.draw.polygon(surface, body_col, [(mx - 32, my - 36), (mx - 42, my - 58), (mx - 18, my - 42)])
        pygame.draw.polygon(surface, CARD_BORDER, [(mx - 32, my - 36), (mx - 42, my - 58), (mx - 18, my - 42)], width=2)
        pygame.draw.polygon(surface, body_col, [(mx + 32, my - 36), (mx + 42, my - 58), (mx + 18, my - 42)])
        pygame.draw.polygon(surface, CARD_BORDER, [(mx + 32, my - 36), (mx + 42, my - 58), (mx + 18, my - 42)], width=2)

        # Soft Belly Plumage
        pygame.draw.ellipse(surface, belly_col, (mx - 25, my - 6, 50, 42))
        pygame.draw.arc(surface, (180, 150, 130), (mx - 14, my + 6, 12, 8), math.pi, 2 * math.pi, 2)
        pygame.draw.arc(surface, (180, 150, 130), (mx + 2, my + 6, 12, 8), math.pi, 2 * math.pi, 2)
        pygame.draw.arc(surface, (180, 150, 130), (mx - 6, my + 18, 12, 8), math.pi, 2 * math.pi, 2)

        # Glasses
        gl_left = (mx - 16, my - 22)
        gl_right = (mx + 16, my - 22)
        gl_r = 16
        pygame.draw.line(surface, glasses_col, (mx - 6, my - 22), (mx + 6, my - 22), 4)
        pygame.draw.circle(surface, (255, 255, 255), gl_left, gl_r)
        pygame.draw.circle(surface, (255, 255, 255), gl_right, gl_r)

        if self.happy_timer > 0:
            pygame.draw.arc(surface, DARK_TEXT, (gl_left[0] - 10, gl_left[1] - 8, 20, 16), 0, math.pi, 3)
            pygame.draw.arc(surface, DARK_TEXT, (gl_right[0] - 10, gl_right[1] - 8, 20, 16), 0, math.pi, 3)
        elif self.blink_timer < 0.2:
            pygame.draw.line(surface, DARK_TEXT, (gl_left[0] - 8, gl_left[1]), (gl_left[0] + 8, gl_left[1]), 3)
            pygame.draw.line(surface, DARK_TEXT, (gl_right[0] - 8, gl_right[1]), (gl_right[0] + 8, gl_right[1]), 3)
        else:
            pygame.draw.circle(surface, (40, 30, 50), (gl_left[0] + 1, gl_left[1] - 1), 7)
            pygame.draw.circle(surface, (40, 30, 50), (gl_right[0] - 1, gl_right[1] - 1), 7)
            pygame.draw.circle(surface, (255, 255, 255), (gl_left[0] - 2, gl_left[1] - 4), 3)
            pygame.draw.circle(surface, (255, 255, 255), (gl_right[0] - 4, gl_right[1] - 4), 3)

        pygame.draw.circle(surface, glasses_col, gl_left, gl_r, width=3)
        pygame.draw.circle(surface, glasses_col, gl_right, gl_r, width=3)

        # Beak
        pygame.draw.polygon(surface, beak_col, [(mx - 7, my - 16), (mx + 7, my - 16), (mx, my - 4)])
        pygame.draw.polygon(surface, CARD_BORDER, [(mx - 7, my - 16), (mx + 7, my - 16), (mx, my - 4)], width=2)

        # Little Feet
        pygame.draw.ellipse(surface, beak_col, (mx - 22, my + 34, 18, 10))
        pygame.draw.ellipse(surface, beak_col, (mx + 4, my + 34, 18, 10))


class SyllableCard:
    """Juicy, bouncy card for single syllable in Station 1."""

    def __init__(self, syl: str, x: float, y: float, w: float = 114.0, h: float = 136.0, color_idx: int = 0) -> None:
        self.syl = syl
        self.rect = pygame.Rect(int(x), int(y), int(w), int(h))
        self.base_x = x
        self.base_y = y
        self.w = w
        self.h = h
        self.color_pair = SYLLABLE_COLORS[color_idx % len(SYLLABLE_COLORS)]
        self.bounce_timer = 0.0
        self.pulse = random.uniform(0, 2 * math.pi)

    def bounce(self) -> None:
        self.bounce_timer = 1.0

    def contains(self, px: float, py: float) -> bool:
        return self.rect.collidepoint(int(px), int(py))

    def update(self) -> None:
        self.pulse += 0.05
        if self.bounce_timer > 0:
            self.bounce_timer -= 0.055

    def draw(self, surface: pygame.Surface, typography: GreiaTypography) -> None:
        scale = 1.0
        if self.bounce_timer > 0:
            scale = 1.0 + math.sin(self.bounce_timer * math.pi) * 0.20

        bw = int(self.w * scale)
        bh = int(self.h * scale)
        bx = int(self.base_x + (self.w - bw) / 2)
        by = int(self.base_y + (self.h - bh) / 2)
        self.rect = pygame.Rect(bx, by, bw, bh)

        # Deep Drop Shadow
        shadow_surf = pygame.Surface((bw + 8, bh + 10), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, SHADOW_COLOR, (0, 0, bw, bh), border_radius=22)
        surface.blit(shadow_surf, (bx + 5, by + 8))

        # Main Card Body with 3D Border
        pygame.draw.rect(surface, self.color_pair[0], self.rect, border_radius=22)
        inner_rect = pygame.Rect(bx + 6, by + 6, bw - 12, bh - 12)
        pygame.draw.rect(surface, self.color_pair[1], inner_rect, border_radius=18)
        pygame.draw.rect(surface, CARD_BORDER, self.rect, width=3, border_radius=22)

        # Gloss Reflex
        gloss_rect = pygame.Rect(bx + 10, by + 10, bw - 20, int(bh * 0.32))
        pygame.draw.rect(surface, (255, 255, 255, 110), gloss_rect, border_radius=12)

        # Syllable Text
        text_surf = typography.render(self.syl, FontRole.DISPLAY, 46, DARK_TEXT)
        tx = bx + (bw - text_surf.get_width()) // 2
        ty = by + 22
        surface.blit(text_surf, (tx, ty))

        # Mini Speaker Icon
        icon_surf = typography.render("🔉", FontRole.DISPLAY, 22, (255, 255, 255))
        surface.blit(icon_surf, (bx + (bw - icon_surf.get_width()) // 2, by + bh - 36))


class FloatingOrb:
    """Floating syllable bubble for Station 2 (Acchiappa-Sillaba)."""

    def __init__(self, syl: str, x: float, y: float, is_target: bool = False, color_idx: int = 0) -> None:
        self.syl = syl
        self.x = x
        self.y = y
        self.base_y = y
        self.radius = 44.0
        self.is_target = is_target
        self.color_pair = SYLLABLE_COLORS[color_idx % len(SYLLABLE_COLORS)]
        self.phase = random.uniform(0, 2 * math.pi)
        self.vx = random.choice([-0.7, -0.4, 0.4, 0.7])
        self.wobble_timer = 0.0
        self.pulse = 0.0

    def update(self) -> None:
        self.phase += 0.035
        self.y = self.base_y + math.sin(self.phase) * 15.0
        self.x += self.vx
        if self.x < 150:
            self.x = 150
            self.vx = abs(self.vx)
        elif self.x > 880:
            self.x = 880
            self.vx = -abs(self.vx)
        if self.wobble_timer > 0:
            self.wobble_timer -= 0.05
        self.pulse += 0.04

    def wobble(self) -> None:
        self.wobble_timer = 1.0

    def contains(self, px: float, py: float) -> bool:
        return (self.x - px) ** 2 + (self.y - py) ** 2 <= (self.radius + 12) ** 2

    def draw(self, surface: pygame.Surface, typography: GreiaTypography) -> None:
        cx, cy = int(self.x), int(self.y)
        if self.wobble_timer > 0:
            cx += int(math.sin(self.wobble_timer * 20.0) * 9.0)

        # Target Glow Pulse
        if self.is_target:
            glow_r = int(self.radius + 12 + math.sin(self.pulse * 2.0) * 6)
            glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*GOLD, 110), (glow_r + 2, glow_r + 2), glow_r)
            surface.blit(glow_surf, (cx - glow_r - 2, cy - glow_r - 2))

        # Shadow
        shadow_surf = pygame.Surface((int(self.radius * 2 + 10), int(self.radius * 2 + 10)), pygame.SRCALPHA)
        pygame.draw.circle(shadow_surf, SHADOW_COLOR, (int(self.radius + 5), int(self.radius + 8)), int(self.radius))
        surface.blit(shadow_surf, (cx - int(self.radius + 5), cy - int(self.radius)))

        # Main Bubble Orb
        pygame.draw.circle(surface, self.color_pair[0], (cx, cy), int(self.radius))
        pygame.draw.circle(surface, self.color_pair[1], (cx - 7, cy - 7), int(self.radius * 0.68))
        pygame.draw.circle(surface, (255, 255, 255), (cx - 14, cy - 14), 9)
        pygame.draw.circle(surface, CARD_BORDER, (cx, cy), int(self.radius), width=3)

        # Syllable Text
        s_surf = typography.render(self.syl, FontRole.DISPLAY, 38, DARK_TEXT)
        sx = cx - s_surf.get_width() // 2
        sy = cy - s_surf.get_height() // 2
        surface.blit(s_surf, (sx, sy))


class WordTile:
    """Tile for 2-syllable word builder in Station 3."""

    def __init__(self, syl: str, x: float, y: float, w: float = 120.0, h: float = 98.0, color_idx: int = 0) -> None:
        self.syl = syl
        self.rect = pygame.Rect(int(x), int(y), int(w), int(h))
        self.base_x = x
        self.base_y = y
        self.w = w
        self.h = h
        self.color_pair = SYLLABLE_COLORS[color_idx % len(SYLLABLE_COLORS)]
        self.used = False
        self.wobble_timer = 0.0
        self.bounce_timer = 0.0

    def wobble(self) -> None:
        self.wobble_timer = 1.0

    def bounce(self) -> None:
        self.bounce_timer = 1.0

    def contains(self, px: float, py: float) -> bool:
        if self.used:
            return False
        return self.rect.collidepoint(int(px), int(py))

    def update(self) -> None:
        if self.wobble_timer > 0:
            self.wobble_timer -= 0.05
        if self.bounce_timer > 0:
            self.bounce_timer -= 0.05

    def draw(self, surface: pygame.Surface, typography: GreiaTypography) -> None:
        if self.used:
            return

        bx, by = int(self.base_x), int(self.base_y)
        if self.wobble_timer > 0:
            bx += int(math.sin(self.wobble_timer * 18.0) * 8.0)

        # Shadow
        shadow_surf = pygame.Surface((int(self.w + 8), int(self.h + 8)), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, SHADOW_COLOR, (0, 0, int(self.w), int(self.h)), border_radius=18)
        surface.blit(shadow_surf, (bx + 4, by + 6))

        self.rect = pygame.Rect(bx, by, int(self.w), int(self.h))
        pygame.draw.rect(surface, self.color_pair[0], self.rect, border_radius=18)
        inner_rect = pygame.Rect(bx + 5, by + 5, int(self.w) - 10, int(self.h) - 10)
        pygame.draw.rect(surface, self.color_pair[1], inner_rect, border_radius=14)
        pygame.draw.rect(surface, CARD_BORDER, self.rect, width=3, border_radius=18)

        t_surf = typography.render(self.syl, FontRole.DISPLAY, 42, DARK_TEXT)
        tx = bx + (int(self.w) - t_surf.get_width()) // 2
        ty = by + (int(self.h) - t_surf.get_height()) // 2
        surface.blit(t_surf, (tx, ty))


class SillabeRenderer:
    """Own the Meadow backdrop and bounded presentation caches.

    The renderer prepares the static meadow once (with convert() where the
    display is available) and keeps small bounded caches for reused text
    surfaces so the hot loop avoids per-frame decode/scale/font construction.
    All draw helpers remain stateless except for these caches.
    """

    def __init__(self, typography: GreiaTypography) -> None:
        self._typography = typography
        self._backdrop: pygame.Surface | None = None
        self._text_cache: dict[tuple[str, FontRole, int, tuple[int, int, int]], pygame.Surface] = {}
        # Star counter is tiny but changes every score event; cache last value.
        self._cached_stars: int | None = None
        self._cached_star_surf: pygame.Surface | None = None

    def backdrop(self) -> pygame.Surface:
        if self._backdrop is None:
            self._backdrop = self._build_backdrop()
        return self._backdrop

    def invalidate(self) -> None:
        # Backdrop is reference-sized, so no resize key is needed today, but
        # expose explicit invalidation for future viewport changes.
        self._backdrop = None
        self._text_cache.clear()
        if len(self._text_cache) > _MAX_TEXT_CACHE:
            self._text_cache.clear()

    def _build_backdrop(self) -> pygame.Surface:
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        # Convert once when a display mode exists; degrade gracefully in headless tests.
        try:
            if pygame.display.get_surface() is not None:
                surface = surface.convert()
        except Exception:
            pass
        for y in range(REFERENCE_HEIGHT):
            ratio = y / float(REFERENCE_HEIGHT)
            col = mix(BG_SKY_TOP, BG_SKY_BOTTOM, ratio)
            pygame.draw.line(surface, col, (0, y), (REFERENCE_WIDTH, y))
        pygame.draw.ellipse(surface, BG_GRASS_BACK, (-80, 480, 600, 240))
        pygame.draw.ellipse(surface, BG_GRASS_BACK, (420, 500, 700, 220))
        pygame.draw.ellipse(surface, BG_GRASS_FRONT, (-40, 520, 1100, 180))
        return surface

    def cached_text(self, text: str, role: FontRole, size: int, color: tuple[int, int, int]) -> pygame.Surface:
        key = (text, role, size, color)
        cached = self._text_cache.get(key)
        if cached is not None:
            return cached
        surf = self._typography.render(text, role, size, color)
        if len(self._text_cache) >= _MAX_TEXT_CACHE:
            # Bounded: drop oldest half rather than growing unbounded.
            keys = list(self._text_cache.keys())
            for k in keys[: _MAX_TEXT_CACHE // 2]:
                self._text_cache.pop(k, None)
        self._text_cache[key] = surf
        return surf

    def star_surface(self, stars: int) -> pygame.Surface:
        if self._cached_stars == stars and self._cached_star_surf is not None:
            return self._cached_star_surf
        surf = self._typography.render(f"⭐ {stars}", FontRole.CONTROL, 22, (220, 145, 10))
        self._cached_stars = stars
        self._cached_star_surf = surf
        return surf


__all__ = ["Particle", "LeoCompanion", "SyllableCard", "FloatingOrb", "WordTile", "SillabeRenderer"]
