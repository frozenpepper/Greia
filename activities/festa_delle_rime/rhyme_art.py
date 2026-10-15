"""Art and visual rendering for Festa delle Rime."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.activity_api import get_shared_visual_path
from greia_platform.child_text import display_text
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .rhyme_content import RhymeItem
else:
    from rhyme_content import RhymeItem


LANTERN_PALETTES: Final[tuple[tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]], ...]] = (
    ((254, 240, 138), (202, 138, 4), (253, 224, 71)),   # Gold
    ((254, 205, 211), (225, 29, 72), (251, 113, 133)),  # Rose
    ((187, 247, 208), (22, 163, 74), (134, 239, 172)),  # Mint
    ((191, 219, 254), (37, 99, 235), (147, 197, 253)),  # Sky
    ((233, 213, 255), (147, 51, 234), (216, 180, 254)), # Lavender
)


class RhymeArt:
    """Own background scenery, Leo mascot, and festive hanging lantern rendering."""

    def __init__(self, width: int, height: int, typography: GreiaTypography) -> None:
        self._typography = typography
        self.background = self._build_background(width, height)
        self.leo = self._load_leo()
        self._emoji_cache: dict[str, pygame.Surface] = {}

    @staticmethod
    def _load_leo() -> pygame.Surface | None:
        try:
            path = get_shared_visual_path("character.leo", variant="happy")
            image = pygame.image.load(path)
            if pygame.display.get_surface() is not None:
                image = image.convert_alpha()
            return pygame.transform.scale(image, (170, 170))
        except (OSError, ValueError, pygame.error, RuntimeError):
            return None

    @staticmethod
    def _build_background(width: int, height: int) -> pygame.Surface:
        surface = pygame.Surface((width, height))

        # Deep twilight gradient
        for y in range(height):
            t = y / height
            r = int(15 * (1 - t) + 12 * t)
            g = int(23 * (1 - t) + 40 * t)
            b = int(42 * (1 - t) + 52 * t)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

        # Distant rolling hills
        pygame.draw.ellipse(surface, (15, 38, 48), (-100, 320, 650, 400))
        pygame.draw.ellipse(surface, (20, 50, 60), (500, 330, 650, 400))

        # Festival lawn
        pygame.draw.rect(surface, (18, 65, 48), (0, 390, width, height - 390))
        pygame.draw.rect(surface, (24, 88, 65), (0, 390, width, 18))

        # Crescent Moon
        moon_center = (920, 80)
        pygame.draw.circle(surface, (254, 240, 138), moon_center, 24)
        pygame.draw.circle(surface, (15, 23, 42), (moon_center[0] - 8, moon_center[1] - 6), 20)

        # Colorful Bunting Pennants across the top
        pennant_colors = [(244, 63, 94), (56, 189, 248), (251, 191, 36), (168, 85, 247), (52, 211, 153), (251, 146, 60)]
        pygame.draw.arc(surface, (203, 213, 225), pygame.Rect(40, -60, width - 80, 160), 3.4, 6.0, 2)
        for i in range(12):
            px = 80 + i * ((width - 160) // 11)
            py = 20 + int(24 * (1 - ((i - 5.5) / 5.5) ** 2))
            c = pennant_colors[i % len(pennant_colors)]
            pygame.draw.polygon(surface, c, [(px - 14, py), (px + 14, py), (px, py + 26)])
            pygame.draw.circle(surface, (255, 255, 255), (px, py), 3)

        # Fairy string lights with glowing auras
        for i in range(10):
            lx = 120 + i * 90
            ly = 68 + (i % 3) * 6
            glow = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(glow, (254, 240, 138, 80), (10, 10), 10)
            surface.blit(glow, (lx - 10, ly - 10))
            pygame.draw.circle(surface, (255, 255, 255), (lx, ly), 4)

        return surface

    def draw_lantern(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        item: RhymeItem,
        color_idx: int = 0,
        *,
        is_lit: bool = True,
        is_highlighted: bool = False,
        is_hovered: bool = False,
    ) -> None:
        """Render an ornate hanging festival paper lantern containing a crisp emoji picture."""
        bg_col, border_col, hl_col = LANTERN_PALETTES[color_idx % len(LANTERN_PALETTES)]
        if not is_lit:
            bg_col = (51, 65, 85)
            border_col = (100, 116, 139)
            hl_col = (71, 85, 105)

        draw_rect = rect.move(0, -6) if is_hovered else rect

        # Drop shadow
        pygame.draw.rect(target, (10, 15, 25, 80), rect.move(0, 8), border_radius=26)

        # Hanging braided rope
        pygame.draw.line(target, (217, 119, 6), (draw_rect.centerx, 0), (draw_rect.centerx, draw_rect.top), 3)

        # Brass hanging loop & wooden lantern roof cap
        pygame.draw.circle(target, (245, 158, 11), (draw_rect.centerx, draw_rect.top - 8), 10, width=3)
        pygame.draw.rect(target, (180, 83, 9), (draw_rect.centerx - 32, draw_rect.top, 64, 14), border_radius=6)
        pygame.draw.rect(target, (245, 158, 11), (draw_rect.centerx - 28, draw_rect.top + 2, 56, 4), border_radius=2)

        # Lantern main body
        body_rect = pygame.Rect(draw_rect.left, draw_rect.top + 12, draw_rect.width, draw_rect.height - 24)
        pygame.draw.rect(target, bg_col, body_rect, border_radius=26)

        # Border styling
        if is_hovered:
            pygame.draw.rect(target, (56, 189, 248), body_rect, width=5, border_radius=26)
        elif is_highlighted:
            pygame.draw.rect(target, (254, 240, 138), body_rect, width=5, border_radius=26)
        else:
            pygame.draw.rect(target, border_col, body_rect, width=3, border_radius=26)

        # Paper lantern ribs (horizontal curved lines)
        for rib_y in (body_rect.top + 22, body_rect.centery, body_rect.bottom - 22):
            pygame.draw.line(target, border_col, (body_rect.left + 8, rib_y), (body_rect.right - 8, rib_y), 2)

        # Bottom wooden base & red tassel
        pygame.draw.rect(target, (180, 83, 9), (draw_rect.centerx - 24, body_rect.bottom - 4, 48, 12), border_radius=4)
        pygame.draw.line(target, (225, 29, 72), (draw_rect.centerx, body_rect.bottom + 8), (draw_rect.centerx, body_rect.bottom + 26), 4)
        pygame.draw.circle(target, (225, 29, 72), (draw_rect.centerx, body_rect.bottom + 28), 6)

        # Emoji image inside lantern
        if item.symbol not in self._emoji_cache:
            self._emoji_cache[item.symbol] = self._typography.render(
                item.symbol,
                FontRole.DISPLAY,
                58,
                (255, 255, 255),
            )
        em_surf = self._emoji_cache[item.symbol]
        target.blit(
            em_surf,
            (body_rect.centerx - em_surf.get_width() // 2, body_rect.centery - em_surf.get_height() // 2 - 10),
        )

        # Word label tag at bottom of lantern
        tag_rect = pygame.Rect(body_rect.centerx - 52, body_rect.bottom - 36, 104, 26)
        pygame.draw.rect(target, (15, 23, 42, 220), tag_rect, border_radius=12)
        word_surf = self._typography.render(display_text(item.item_id[:10]), FontRole.TITLE, 16, (254, 240, 138))
        target.blit(
            word_surf,
            (tag_rect.centerx - word_surf.get_width() // 2, tag_rect.centery - word_surf.get_height() // 2),
        )
