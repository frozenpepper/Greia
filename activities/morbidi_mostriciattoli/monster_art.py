"""Prepared visual assets and procedural monster compositor for Morbidi Mostriciattoli."""

from __future__ import annotations

import math
from typing import Final

import pygame

from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .monster_content import (
        BODY_COLORS,
        ColorOption,
        MonsterOption,
    )
    from .monster_model import MonsterRecipe
else:
    from monster_content import (
        BODY_COLORS,
        ColorOption,
        MonsterOption,
    )
    from monster_model import MonsterRecipe


COLORS_BY_ID: Final[dict[str, ColorOption]] = {c.option_id: c for c in BODY_COLORS}


class MonsterArt:
    """Own studio background and composite soft monster portraits."""

    def __init__(self, width: int, height: int, typography: GreiaTypography) -> None:
        self.width = width
        self.height = height
        self._typography = typography
        self.background = self._build_background(width, height)
        self._text_cache: dict[tuple[str, int, tuple[int, int, int]], pygame.Surface] = {}

    @staticmethod
    def _build_background(width: int, height: int) -> pygame.Surface:
        surface = pygame.Surface((width, height))

        # Soft creative studio violet-slate gradient
        for y in range(height):
            t = y / height
            r = int(35 * (1 - t) + 20 * t)
            g = int(25 * (1 - t) + 16 * t)
            b = int(65 * (1 - t) + 45 * t)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

        # Studio soft spotlight circle in the monster easel area
        spot_center = (330, 290)
        for r in range(260, 80, -20):
            alpha = int(35 * (1.0 - r / 260.0))
            spot = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(spot, (254, 240, 138, alpha), (r, r), r)
            surface.blit(spot, (spot_center[0] - r, spot_center[1] - r))

        # Floating colorful studio paint confetti dots
        confetti = [
            (80, 70, (244, 114, 182)), (180, 45, (253, 224, 71)), (920, 50, (134, 239, 172)),
            (860, 110, (125, 211, 252)), (960, 140, (216, 180, 254)), (70, 380, (253, 186, 116)),
        ]
        for cx, cy, col in confetti:
            pygame.draw.circle(surface, col, (cx, cy), 6)
            pygame.draw.circle(surface, (255, 255, 255), (cx, cy), 2)

        return surface

    def draw_monster(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        recipe: MonsterRecipe,
        *,
        squash_progress: float = 0.0,
    ) -> None:
        """Compose a cute, soft fluffy monster with drop shadow, tuft, eyes, mouth, and accessory."""
        col_opt = COLORS_BY_ID.get(recipe.body_color, BODY_COLORS[0])
        body_col = col_opt.primary_color
        accent_col = col_opt.accent_color

        # Squash & stretch calculation (scale height by 1 - 0.15*sin, width by 1 + 0.15*sin)
        squash_factor = math.sin(math.pi * squash_progress) if squash_progress > 0.0 else 0.0
        scale_x = 1.0 + 0.12 * squash_factor
        scale_y = 1.0 - 0.12 * squash_factor

        cx, cy = rect.centerx, rect.centery + int(10 * squash_factor)
        w = int(rect.width * 0.75 * scale_x)
        h = int(rect.height * 0.75 * scale_y)

        # 1. Contact Drop Shadow
        shadow_w = int(w * 0.85)
        shadow_rect = pygame.Rect(cx - shadow_w // 2, rect.bottom - 24, shadow_w, 24)
        pygame.draw.ellipse(target, (10, 8, 20, 90), shadow_rect)

        # 2. Tuft / Horn / Headgear (drawn behind body or top)
        self._draw_tuft(target, cx, cy - h // 2, recipe.tuft, accent_col)

        # 3. Body Shape
        self._draw_body(target, cx, cy, w, h, recipe.body_shape, body_col, accent_col)

        # 4. Eyes & Rosy Cheeks
        self._draw_eyes_and_cheeks(target, cx, cy - int(h * 0.08), w, h, recipe.eyes)

        # 5. Mouth
        self._draw_mouth(target, cx, cy + int(h * 0.18), w, h, recipe.mouth)

        # 6. Accessory
        self._draw_accessory(target, cx, cy + int(h * 0.38), w, h, recipe.accessory)

    def _draw_body(
        self,
        target: pygame.Surface,
        cx: int,
        cy: int,
        w: int,
        h: int,
        shape: str,
        body_col: tuple[int, int, int],
        accent_col: tuple[int, int, int],
    ) -> None:
        body_rect = pygame.Rect(cx - w // 2, cy - h // 2, w, h)

        if shape == "round":
            pygame.draw.circle(target, body_col, (cx, cy), min(w, h) // 2)
            pygame.draw.circle(target, accent_col, (cx, cy), min(w, h) // 2, 4)
            # Fluffy ears/lobes on sides
            pygame.draw.circle(target, body_col, (cx - w // 2 + 10, cy - h // 4), w // 5)
            pygame.draw.circle(target, body_col, (cx + w // 2 - 10, cy - h // 4), w // 5)
        elif shape == "pear":
            pygame.draw.circle(target, body_col, (cx, cy - h // 6), int(w * 0.36))
            pygame.draw.circle(target, body_col, (cx, cy + h // 6), int(w * 0.46))
            pygame.draw.circle(target, accent_col, (cx, cy + h // 6), int(w * 0.46), 4)
        elif shape == "square":
            pygame.draw.rect(target, body_col, body_rect, border_radius=32)
            pygame.draw.rect(target, accent_col, body_rect, width=4, border_radius=32)
        elif shape == "bean":
            pygame.draw.ellipse(target, body_col, body_rect)
            pygame.draw.ellipse(target, accent_col, body_rect, 4)
        elif shape == "egg":
            pygame.draw.ellipse(target, body_col, pygame.Rect(cx - w // 2, cy - h // 2, w, int(h * 1.1)))
            pygame.draw.ellipse(target, accent_col, pygame.Rect(cx - w // 2, cy - h // 2, w, int(h * 1.1)), 4)
        else:  # star shape
            pts = []
            for i in range(10):
                r = (w // 2) if (i % 2 == 0) else int(w * 0.32)
                angle = i * (math.pi / 5.0) - math.pi / 2.0
                pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
            pygame.draw.polygon(target, body_col, pts)
            pygame.draw.polygon(target, accent_col, pts, 4)

        # Gloss highlight: a small translucent glint on the upper-left shoulder.
        # It must sit above the face (eyes start near cy - 0.08h) and be blended
        # as alpha; drawn opaque it used to become a white blob over the face.
        gw, gh = max(6, w // 9), max(4, h // 14)
        glint = pygame.Surface((gw, gh), pygame.SRCALPHA)
        pygame.draw.ellipse(glint, (255, 255, 255, 110), glint.get_rect())
        target.blit(glint, (cx - int(w * 0.19) - gw // 2, cy - int(h * 0.29) - gh // 2))

    def _draw_tuft(
        self,
        target: pygame.Surface,
        cx: int,
        cy: int,
        tuft_id: str,
        accent_col: tuple[int, int, int],
    ) -> None:
        if tuft_id == "single_horn":
            horn_pts = [(cx, cy - 45), (cx - 16, cy + 4), (cx + 16, cy + 4)]
            pygame.draw.polygon(target, (254, 240, 138), horn_pts)
            pygame.draw.polygon(target, (217, 119, 6), horn_pts, width=3)
            pygame.draw.line(target, (217, 119, 6), (cx - 10, cy - 15), (cx + 10, cy - 15), 2)
        elif tuft_id == "bunny_ears":
            for ox in (-24, 24):
                pygame.draw.ellipse(target, accent_col, (cx + ox - 12, cy - 50, 24, 55))
                pygame.draw.ellipse(target, (254, 205, 211), (cx + ox - 6, cy - 42, 12, 38))
        elif tuft_id == "little_antennas":
            for ox in (-20, 20):
                pygame.draw.line(target, accent_col, (cx, cy + 5), (cx + ox * 1.5, cy - 35), 4)
                pygame.draw.circle(target, (254, 240, 138), (int(cx + ox * 1.5), cy - 35), 10)
        elif tuft_id == "dino_spikes":
            for ox in (-28, 0, 28):
                pts = [(cx + ox, cy - 28), (cx + ox - 12, cy + 4), (cx + ox + 12, cy + 4)]
                pygame.draw.polygon(target, (34, 197, 94), pts)
                pygame.draw.polygon(target, (22, 163, 74), pts, 2)
        elif tuft_id == "fuzzy_pom":
            pygame.draw.circle(target, (244, 114, 182), (cx, cy - 20), 22)
            pygame.draw.circle(target, (255, 255, 255), (cx - 4, cy - 24), 6)
        elif tuft_id == "crown":
            crown_pts = [(cx - 24, cy + 2), (cx - 24, cy - 20), (cx - 12, cy - 8), (cx, cy - 26), (cx + 12, cy - 8), (cx + 24, cy - 20), (cx + 24, cy + 2)]
            pygame.draw.polygon(target, (251, 191, 36), crown_pts)
            pygame.draw.polygon(target, (217, 119, 6), crown_pts, 3)

    def _draw_eyes_and_cheeks(
        self,
        target: pygame.Surface,
        cx: int,
        cy: int,
        w: int,
        h: int,
        eyes_id: str,
    ) -> None:
        # Rosy blush cheeks
        pygame.draw.ellipse(target, (244, 63, 94, 140), (cx - w // 3, cy + 18, 20, 14))
        pygame.draw.ellipse(target, (244, 63, 94, 140), (cx + w // 3 - 20, cy + 18, 20, 14))

        if eyes_id == "cyclops":
            pygame.draw.ellipse(target, (255, 255, 255), (cx - 26, cy - 28, 52, 56))
            pygame.draw.ellipse(target, (30, 27, 75), (cx - 26, cy - 28, 52, 56), 3)
            pygame.draw.circle(target, (30, 27, 75), (cx, cy), 14)
            pygame.draw.circle(target, (255, 255, 255), (cx - 4, cy - 4), 5)
        elif eyes_id == "two_dots":
            for ox in (-26, 26):
                pygame.draw.circle(target, (255, 255, 255), (cx + ox, cy), 18)
                pygame.draw.circle(target, (30, 27, 75), (cx + ox, cy), 18, 3)
                pygame.draw.circle(target, (30, 27, 75), (cx + ox, cy), 8)
                pygame.draw.circle(target, (255, 255, 255), (cx + ox - 2, cy - 2), 3)
        elif eyes_id == "three_sparkles":
            for ox, oy in [(-30, 4), (0, -12), (30, 4)]:
                pygame.draw.circle(target, (255, 255, 255), (cx + ox, cy + oy), 14)
                pygame.draw.circle(target, (30, 27, 75), (cx + ox, cy + oy), 14, 2)
                pygame.draw.circle(target, (245, 158, 11), (cx + ox, cy + oy), 6)
                pygame.draw.circle(target, (255, 255, 255), (cx + ox - 2, cy + oy - 2), 2)
        elif eyes_id == "sleepy_winks":
            for ox in (-24, 24):
                pygame.draw.arc(target, (30, 27, 75), (cx + ox - 14, cy - 10, 28, 20), 3.4, 6.0, 4)
        elif eyes_id == "big_goggles":
            pygame.draw.line(target, (71, 85, 105), (cx - 45, cy), (cx + 45, cy), 6)
            for ox in (-26, 26):
                pygame.draw.circle(target, (245, 158, 11), (cx + ox, cy), 22, 5)
                pygame.draw.circle(target, (186, 230, 253), (cx + ox, cy), 18)
                pygame.draw.circle(target, (30, 27, 75), (cx + ox, cy), 7)
        else:  # happy_lashes
            for ox in (-24, 24):
                pygame.draw.arc(target, (30, 27, 75), (cx + ox - 14, cy - 10, 28, 20), 3.4, 6.0, 4)
                pygame.draw.line(target, (30, 27, 75), (cx + ox + 10, cy - 6), (cx + ox + 16, cy - 12), 3)

    def _draw_mouth(
        self,
        target: pygame.Surface,
        cx: int,
        cy: int,
        w: int,
        h: int,
        mouth_id: str,
    ) -> None:
        if mouth_id == "toothy_smile":
            pygame.draw.arc(target, (131, 24, 67), (cx - 24, cy - 10, 48, 24), 3.4, 6.0, 4)
            # 2 tiny white teeth
            pygame.draw.rect(target, (255, 255, 255), (cx - 8, cy + 2, 6, 6), border_radius=1)
            pygame.draw.rect(target, (255, 255, 255), (cx + 2, cy + 2, 6, 6), border_radius=1)
        elif mouth_id == "tongue_out":
            pygame.draw.arc(target, (131, 24, 67), (cx - 22, cy - 10, 44, 20), 3.4, 6.0, 4)
            pygame.draw.ellipse(target, (244, 63, 94), (cx - 8, cy + 4, 16, 16))
            pygame.draw.ellipse(target, (131, 24, 67), (cx - 8, cy + 4, 16, 16), 2)
        elif mouth_id == "tiny_o":
            pygame.draw.circle(target, (131, 24, 67), (cx, cy + 4), 9)
            pygame.draw.circle(target, (255, 205, 210), (cx, cy + 4), 6)
        elif mouth_id == "snaggle_tooth":
            pygame.draw.arc(target, (131, 24, 67), (cx - 20, cy - 8, 40, 20), 3.4, 6.0, 4)
            pygame.draw.polygon(target, (255, 255, 255), [(cx - 6, cy + 2), (cx - 1, cy + 2), (cx - 3, cy + 9)])
        elif mouth_id == "broad_grin":
            pygame.draw.arc(target, (131, 24, 67), (cx - 30, cy - 12, 60, 30), 3.3, 6.1, 5)
        else:  # cat_whiskers
            pygame.draw.circle(target, (131, 24, 67), (cx, cy + 2), 4)
            # Whiskers
            for wy in (-4, 4):
                pygame.draw.line(target, (131, 24, 67), (cx - 12, cy + 2 + wy), (cx - 38, cy + 2 + wy * 2), 2)
                pygame.draw.line(target, (131, 24, 67), (cx + 12, cy + 2 + wy), (cx + 38, cy + 2 + wy * 2), 2)

    def _draw_accessory(
        self,
        target: pygame.Surface,
        cx: int,
        cy: int,
        w: int,
        h: int,
        acc_id: str,
    ) -> None:
        if acc_id == "bow_tie":
            pygame.draw.polygon(target, (245, 158, 11), [(cx - 20, cy - 10), (cx, cy), (cx - 20, cy + 10)])
            pygame.draw.polygon(target, (245, 158, 11), [(cx + 20, cy - 10), (cx, cy), (cx + 20, cy + 10)])
            pygame.draw.circle(target, (251, 191, 36), (cx, cy), 6)
        elif acc_id == "star_pin":
            pts = []
            for i in range(10):
                r = 14 if (i % 2 == 0) else 6
                angle = i * (math.pi / 5.0) - math.pi / 2.0
                pts.append((cx - 28 + r * math.cos(angle), cy + r * math.sin(angle)))
            pygame.draw.polygon(target, (251, 191, 36), pts)
        elif acc_id == "monocle":
            pygame.draw.circle(target, (245, 158, 11), (cx + 24, cy - 40), 18, 3)
            pygame.draw.line(target, (245, 158, 11), (cx + 24, cy - 22), (cx + 36, cy + 4), 2)
        elif acc_id == "flowered_lei":
            for ox, col in [(-24, (244, 114, 182)), (-8, (253, 224, 71)), (8, (134, 239, 172)), (24, (125, 211, 252))]:
                pygame.draw.circle(target, col, (cx + ox, cy), 9)
                pygame.draw.circle(target, (255, 255, 255), (cx + ox, cy), 3)
        elif acc_id == "striped_scarf":
            pygame.draw.rect(target, (225, 29, 72), (cx - 36, cy - 6, 72, 14), border_radius=7)
            for sx in (-20, 0, 20):
                pygame.draw.rect(target, (255, 255, 255), (cx + sx, cy - 6, 8, 14))
        elif acc_id == "party_hat":
            pts = [(cx + 20, cy - 100), (cx + 4, cy - 50), (cx + 36, cy - 50)]
            pygame.draw.polygon(target, (168, 85, 247), pts)
            pygame.draw.circle(target, (251, 191, 36), (cx + 20, cy - 100), 6)
