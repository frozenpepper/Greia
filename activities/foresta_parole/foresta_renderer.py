"""Foresta Parole — drawing helpers, cached presentation, entity renderers.

Owns pre-baked static scenery, bounded text caches and stateless helpers for
the owl, letter orbs and particles. No storage, no event IO, no audio.
"""

from __future__ import annotations

import math
import random

import pygame

from greia_platform.activity_ui import mix
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .foresta_content import (
        BRANCH_BROWN,
        CANOPY_DARK,
        CANOPY_LIGHT,
        CARD_BG,
        CARD_BORDER,
        DARK_TEXT,
        FOREST_SKY_BOTTOM,
        FOREST_SKY_TOP,
        GOLD,
        LEAF_GREEN,
        LEAF_LIGHT,
        ORB_COLORS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WHITE,
    )
else:
    from foresta_content import (  # type: ignore[no-redef]
        BRANCH_BROWN,
        CANOPY_DARK,
        CANOPY_LIGHT,
        CARD_BG,
        CARD_BORDER,
        DARK_TEXT,
        FOREST_SKY_BOTTOM,
        FOREST_SKY_TOP,
        GOLD,
        LEAF_GREEN,
        LEAF_LIGHT,
        ORB_COLORS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        WHITE,
    )

_CARD_RECT = pygame.Rect(280, 14, 480, 96)
_AUDIO_BTN_RECT = pygame.Rect(670, 24, 76, 76)
_HUD_RECT = pygame.Rect(785, 14, 215, 60)

_MAX_TEXT_CACHE = 64
_MAX_LETTER_CACHE = 40


# ---------------------------------------------------------------------------
# Legacy entity helpers — preserved for compatibility and visual playfulness.
# ---------------------------------------------------------------------------


class Particle:
    """Small celebratory particle with gravity."""

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
        self.vy += 0.08
        self.life -= self.decay
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        if self.life > 0:
            sz = max(1, int(self.size * self.life))
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), sz)
            pygame.draw.circle(surface, WHITE, (int(self.x), int(self.y)), max(1, sz // 2))


class LetterOrb:
    """Floating letter bubble with wobble/pulse animation."""

    def __init__(self, letter: str, x: float, y: float) -> None:
        self.letter = letter
        self.x = x
        self.y = y
        self.base_y = y
        self.radius = 38.0
        self.color_pair = random.choice(ORB_COLORS)
        self.phase = random.uniform(0, 2 * math.pi)
        self.vx = random.choice([-0.8, -0.5, 0.5, 0.8])
        self.wobble_timer = 0.0
        self.pulse = 0.0

    def update(self) -> None:
        self.phase += 0.035
        self.y = self.base_y + math.sin(self.phase) * 16.0
        self.x += self.vx
        if self.x < 180:
            self.x = 180
            self.vx = abs(self.vx)
        elif self.x > 940:
            self.x = 940
            self.vx = -abs(self.vx)
        if self.wobble_timer > 0:
            self.wobble_timer -= 0.05
        self.pulse += 0.04

    def wobble(self) -> None:
        self.wobble_timer = 1.0

    def contains(self, px: float, py: float) -> bool:
        return (self.x - px) ** 2 + (self.y - py) ** 2 <= (self.radius + 10) ** 2

    def draw(self, surface: pygame.Surface, typography: GreiaTypography) -> None:
        # This helper keeps historical per-orb font rendering path for headless tests;
        # the real Activity renderer uses the cached letter surface from ForestaRenderer
        # so the 30 Hz path does not construct fonts/transient text per frame.
        cx, cy = int(self.x), int(self.y)
        if self.wobble_timer > 0:
            cx += int(math.sin(self.wobble_timer * 18.0) * 8.0)

        glow_r = int(self.radius + 8 + math.sin(self.pulse) * 4)
        glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.color_pair[1], 80), (glow_r + 2, glow_r + 2), glow_r)
        surface.blit(glow_surf, (cx - glow_r - 2, cy - glow_r - 2))

        pygame.draw.circle(surface, self.color_pair[0], (cx, cy), int(self.radius))
        pygame.draw.circle(surface, self.color_pair[1], (cx - 8, cy - 8), int(self.radius * 0.65))
        pygame.draw.circle(surface, WHITE, (cx - 12, cy - 12), 7)
        pygame.draw.circle(surface, DARK_TEXT, (cx, cy), int(self.radius), width=3)

        letter_surf = typography.render(self.letter, FontRole.DISPLAY, 36, DARK_TEXT)
        lx = cx - letter_surf.get_width() // 2
        ly = cy - letter_surf.get_height() // 2
        surface.blit(letter_surf, (lx, ly))


class OwlCompanion:
    """Enchanted forest owl companion with bob/blink/cheer behaviour."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.blink_timer = 3.0
        self.happy_timer = 0.0
        self.bob = 0.0

    def cheer(self) -> None:
        self.happy_timer = 2.5

    def update(self) -> None:
        self.bob += 0.04
        self.blink_timer -= 0.02
        if self.blink_timer <= 0:
            self.blink_timer = random.uniform(2.5, 5.0)
        if self.happy_timer > 0:
            self.happy_timer -= 0.035

    def draw(self, surface: pygame.Surface) -> None:
        ox = int(self.x)
        oy = int(self.y + math.sin(self.bob) * 5)
        if self.happy_timer > 0:
            oy += int(abs(math.sin(self.happy_timer * 12.0)) * -14)

        pygame.draw.rect(surface, BRANCH_BROWN, (ox - 50, oy + 40, 100, 14), border_radius=6)
        pygame.draw.circle(surface, LEAF_GREEN, (ox + 50, oy + 38), 16)
        pygame.draw.circle(surface, LEAF_LIGHT, (ox + 56, oy + 34), 12)

        pygame.draw.ellipse(surface, (145, 95, 60), (ox - 32, oy - 26, 64, 72))
        pygame.draw.ellipse(surface, (235, 205, 170), (ox - 22, oy - 8, 44, 48))

        pygame.draw.polygon(surface, (120, 75, 45), [(ox - 28, oy - 24), (ox - 18, oy - 46), (ox - 6, oy - 24)])
        pygame.draw.polygon(surface, (120, 75, 45), [(ox + 6, oy - 24), (ox + 18, oy - 46), (ox + 28, oy - 24)])

        if self.blink_timer > 0.18:
            pygame.draw.circle(surface, WHITE, (ox - 14, oy - 8), 13)
            pygame.draw.circle(surface, WHITE, (ox + 14, oy - 8), 13)
            pygame.draw.circle(surface, DARK_TEXT, (ox - 12, oy - 8), 7)
            pygame.draw.circle(surface, DARK_TEXT, (ox + 12, oy - 8), 7)
            pygame.draw.circle(surface, WHITE, (ox - 14, oy - 10), 3)
            pygame.draw.circle(surface, WHITE, (ox + 10, oy - 10), 3)
        else:
            pygame.draw.line(surface, DARK_TEXT, (ox - 22, oy - 8), (ox - 6, oy - 8), 3)
            pygame.draw.line(surface, DARK_TEXT, (ox + 6, oy - 8), (ox + 22, oy - 8), 3)

        pygame.draw.polygon(surface, (255, 175, 35), [(ox, oy + 6), (ox - 6, oy - 2), (ox + 6, oy - 2)])

        if self.happy_timer > 0:
            pygame.draw.ellipse(surface, (120, 75, 45), (ox - 46, oy - 14, 20, 36))
            pygame.draw.ellipse(surface, (120, 75, 45), (ox + 26, oy - 14, 20, 36))
        else:
            pygame.draw.ellipse(surface, (120, 75, 45), (ox - 36, oy - 4, 16, 42))
            pygame.draw.ellipse(surface, (120, 75, 45), (ox + 20, oy - 4, 16, 42))


# ---------------------------------------------------------------------------
# Cached renderer — the real 30 Hz presentation owner.
# ---------------------------------------------------------------------------


class ForestaRenderer:
    """Own the Word Forest Pygame presentation and bounded caches.

    - Sky/canopy/ground scenery is baked into one opaque backdrop at
      construction and reused every frame. No per-frame gradient loop.
    - Letter glyphs for the floating orbs are cached per letter (≤40 entries).
    - Card/hud/feedback text surfaces are LRU-bounded to avoid unbounded growth.
    - The backdrop and scale caches invalidate on resize.
    """

    def __init__(self, typography: GreiaTypography) -> None:
        self._typography = typography
        raw_backdrop = self._build_backdrop()
        try:
            self._backdrop = raw_backdrop.convert()
        except pygame.error:
            self._backdrop = raw_backdrop
        self._letter_cache: dict[str, pygame.Surface] = {}
        self._text_cache: dict[tuple[str, FontRole, int, tuple[int, int, int]], pygame.Surface] = {}
        self._text_order: list[tuple[str, FontRole, int, tuple[int, int, int]]] = []
        self._hud_value: tuple[int, int] | None = None
        self._hud_surface: pygame.Surface | None = None

    # -- cache lifecycle ---------------------------------------------------

    def invalidate(self) -> None:
        """Clear derived caches after a display-size change.

        The backdrop is rebuilt because a resize creates a new reference
        canvas. Text caches are cleared because a different viewport may
        change future layout keys; letter glyphs remain valid (size/style
        are constant) so they are kept.
        """

        raw_backdrop = self._build_backdrop()
        try:
            self._backdrop = raw_backdrop.convert()
        except pygame.error:
            self._backdrop = raw_backdrop
        self._text_cache.clear()
        self._text_order.clear()
        self._hud_value = None
        self._hud_surface = None

    def _build_backdrop(self) -> pygame.Surface:
        surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT))
        # Sky gradient: original drew 60 rects per frame; bake once.
        for y in range(0, REFERENCE_HEIGHT, 10):
            ratio = y / float(REFERENCE_HEIGHT)
            col = mix(FOREST_SKY_BOTTOM, FOREST_SKY_TOP, ratio)
            pygame.draw.rect(surface, col, (0, y, REFERENCE_WIDTH, 10))
        pygame.draw.circle(surface, CANOPY_DARK, (80, 520), 220)
        pygame.draw.circle(surface, CANOPY_DARK, (940, 520), 240)
        pygame.draw.circle(surface, CANOPY_LIGHT, (512, 590), 380)
        for fx in range(120, 920, 140):
            pygame.draw.circle(surface, LEAF_GREEN, (fx, 580), 28)
            pygame.draw.circle(surface, LEAF_LIGHT, (fx + 10, 574), 18)
        return surface

    def _cached_letter(self, letter: str) -> pygame.Surface:
        cached = self._letter_cache.get(letter)
        if cached is not None:
            return cached
        if len(self._letter_cache) >= _MAX_LETTER_CACHE:
            oldest = next(iter(self._letter_cache))
            del self._letter_cache[oldest]
        rendered = self._typography.render(letter, FontRole.DISPLAY, 36, DARK_TEXT)
        # Cache the original; caller copies positioning but not mutates.
        self._letter_cache[letter] = rendered
        return rendered

    def _cached_text(self, text: str, role: FontRole, size: int, color: tuple[int, int, int]) -> pygame.Surface:
        key = (text, role, size, color)
        cached = self._text_cache.get(key)
        if cached is not None:
            return cached
        rendered = self._typography.render(text, role, size, color)
        if len(self._text_cache) >= _MAX_TEXT_CACHE:
            oldest = self._text_order.pop(0)
            self._text_cache.pop(oldest, None)
        self._text_cache[key] = rendered
        self._text_order.append(key)
        return rendered

    # -- public draw api ---------------------------------------------------

    def draw_background(self, surface: pygame.Surface) -> None:
        surface.blit(self._backdrop, (0, 0))

    def draw_orbs(
        self,
        surface: pygame.Surface,
        orbs: list[LetterOrb],
    ) -> None:
        for orb in orbs:
            cx, cy = int(orb.x), int(orb.y)
            if orb.wobble_timer > 0:
                cx += int(math.sin(orb.wobble_timer * 18.0) * 8.0)
            glow_r = int(orb.radius + 8 + math.sin(orb.pulse) * 4)
            glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*orb.color_pair[1], 80), (glow_r + 2, glow_r + 2), glow_r)
            surface.blit(glow_surf, (cx - glow_r - 2, cy - glow_r - 2))
            pygame.draw.circle(surface, orb.color_pair[0], (cx, cy), int(orb.radius))
            pygame.draw.circle(surface, orb.color_pair[1], (cx - 8, cy - 8), int(orb.radius * 0.65))
            pygame.draw.circle(surface, WHITE, (cx - 12, cy - 12), 7)
            pygame.draw.circle(surface, DARK_TEXT, (cx, cy), int(orb.radius), width=3)
            letter_surf = self._cached_letter(orb.letter)
            surface.blit(letter_surf, (cx - letter_surf.get_width() // 2, cy - letter_surf.get_height() // 2))

    def draw_owl(self, surface: pygame.Surface, owl: OwlCompanion) -> None:
        owl.draw(surface)

    def draw_particles(self, surface: pygame.Surface, particles: list[Particle]) -> None:
        for p in particles:
            p.draw(surface)

    def draw_card(  # noqa: PLR0913 - card needs model truth for reference UX
        self,
        surface: pygame.Surface,
        cur_letter: str,
        cur_word: str,
        cur_emoji: str,
        matches_needed: int,
        matches_current: int,
    ) -> None:
        # Shadow + card body
        pygame.draw.rect(
            surface, (15, 20, 30), (_CARD_RECT.x + 3, _CARD_RECT.y + 4, _CARD_RECT.width, _CARD_RECT.height), border_radius=16
        )
        pygame.draw.rect(surface, CARD_BG, _CARD_RECT, border_radius=16)
        pygame.draw.rect(surface, CARD_BORDER, _CARD_RECT, width=3, border_radius=16)

        letter_pill = pygame.Rect(_CARD_RECT.x + 12, _CARD_RECT.y + 10, 76, 76)
        pygame.draw.rect(surface, GOLD, letter_pill, border_radius=14)
        pygame.draw.rect(surface, CARD_BORDER, letter_pill, width=3, border_radius=14)
        big_l_surf = self._cached_text(cur_letter, FontRole.DISPLAY, 52, DARK_TEXT)
        surface.blit(big_l_surf, (letter_pill.centerx - big_l_surf.get_width() // 2, letter_pill.centery - big_l_surf.get_height() // 2))

        hint_str = f"{cur_word} {cur_emoji}"
        hint_surf = self._cached_text(hint_str, FontRole.TITLE, 34, DARK_TEXT)
        surface.blit(hint_surf, (_CARD_RECT.x + 104, _CARD_RECT.y + 12))

        for s_i in range(matches_needed):
            dot_x = _CARD_RECT.x + 108 + s_i * 38
            dot_y = _CARD_RECT.y + 60
            if s_i < matches_current:
                star_surf = self._cached_text("⭐", FontRole.BODY, 28, GOLD)
                surface.blit(star_surf, (dot_x, dot_y - 4))
            else:
                pygame.draw.circle(surface, (210, 195, 175), (dot_x + 12, dot_y + 12), 10)
                pygame.draw.circle(surface, CARD_BORDER, (dot_x + 12, dot_y + 12), 10, width=2)

        pygame.draw.rect(surface, (255, 225, 90), _AUDIO_BTN_RECT, border_radius=14)
        pygame.draw.rect(surface, CARD_BORDER, _AUDIO_BTN_RECT, width=3, border_radius=14)
        speaker_surf = self._cached_text("🔊", FontRole.DISPLAY, 38, DARK_TEXT)
        surface.blit(
            speaker_surf,
            (_AUDIO_BTN_RECT.centerx - speaker_surf.get_width() // 2, _AUDIO_BTN_RECT.centery - speaker_surf.get_height() // 2),
        )

    def draw_hud(self, surface: pygame.Surface, stars: int, score: int) -> None:
        pygame.draw.rect(surface, CARD_BG, _HUD_RECT, border_radius=16)
        pygame.draw.rect(surface, CARD_BORDER, _HUD_RECT, width=3, border_radius=16)
        key = (stars, score)
        if self._hud_value != key or self._hud_surface is None:
            hud_text = f"⭐ {stars}   🏆 {score}"
            self._hud_surface = self._cached_text(hud_text, FontRole.TITLE, 24, DARK_TEXT)
            self._hud_value = key
        assert self._hud_surface is not None
        surface.blit(
            self._hud_surface,
            (_HUD_RECT.centerx - self._hud_surface.get_width() // 2, _HUD_RECT.centery - self._hud_surface.get_height() // 2),
        )

    def draw_feedback(self, surface: pygame.Surface, feedback_text: str) -> None:
        if not feedback_text:
            return
        fb_surf = self._cached_text(feedback_text, FontRole.TITLE, 28, GOLD)
        fb_bg = pygame.Rect(
            REFERENCE_WIDTH // 2 - fb_surf.get_width() // 2 - 24, 120, fb_surf.get_width() + 48, 48
        )
        pygame.draw.rect(surface, (20, 28, 44), fb_bg, border_radius=12)
        pygame.draw.rect(surface, GOLD, fb_bg, width=2, border_radius=12)
        surface.blit(fb_surf, (REFERENCE_WIDTH // 2 - fb_surf.get_width() // 2, 128))

    # Geometry helpers exposed for hit-testing so app and renderer agree.
    @staticmethod
    def card_rect() -> pygame.Rect:
        return _CARD_RECT.copy()

    @staticmethod
    def audio_btn_rect() -> pygame.Rect:
        return _AUDIO_BTN_RECT.copy()

    @staticmethod
    def hud_rect() -> pygame.Rect:
        return _HUD_RECT.copy()


__all__ = ["ForestaRenderer", "LetterOrb", "OwlCompanion", "Particle"]
