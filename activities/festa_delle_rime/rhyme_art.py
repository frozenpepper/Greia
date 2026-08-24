"""Art and visual rendering for Festa delle Rime."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.activity_api import get_shared_visual_path
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .rhyme_content import RhymeItem
else:
    from rhyme_content import RhymeItem


LANTERN_PALETTES: Final[tuple[tuple[tuple[int, int, int], tuple[int, int, int]], ...]] = (
    ((254, 240, 138), (202, 138, 4)),   # Gold
    ((254, 205, 211), (225, 29, 72)),   # Rose
    ((187, 247, 208), (22, 163, 74)),   # Mint
    ((191, 219, 254), (37, 99, 235)),   # Sky
    ((233, 213, 255), (147, 51, 234)),  # Lavender
)


class RhymeArt:
    """Own background scenery, Leo mascot, and lantern rendering."""

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
        surface.fill((15, 23, 42))  # Deep night sky

        # Twilight meadow hills
        pygame.draw.circle(surface, (20, 35, 60), (width // 4, height + 300), 500)
        pygame.draw.circle(surface, (30, 48, 80), (3 * width // 4, height + 320), 520)

        # Festival lawn
        pygame.draw.rect(surface, (16, 50, 40), (0, 380, width, height - 380))
        pygame.draw.rect(surface, (22, 78, 60), (0, 380, width, 16))

        # String light festoon line across the top
        pygame.draw.arc(surface, (100, 116, 139), pygame.Rect(40, -40, width - 80, 200), 3.3, 6.1, 2)

        # Tiny fairy string lights
        for i in range(12):
            lx = 80 + i * ((width - 160) // 11)
            ly = 50 + int(30 * (1 - ((i - 5.5) / 5.5) ** 2))
            pygame.draw.circle(surface, (254, 240, 138), (lx, ly), 5)
            pygame.draw.circle(surface, (255, 255, 255), (lx, ly), 3)

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
    ) -> None:
        """Render a festive hanging lantern containing a large picture emoji."""
        bg_col, border_col = LANTERN_PALETTES[color_idx % len(LANTERN_PALETTES)]
        if not is_lit:
            bg_col = (51, 65, 85)
            border_col = (100, 116, 139)

        # Hanging string
        pygame.draw.line(target, (100, 116, 139), (rect.centerx, 0), (rect.centerx, rect.top), 2)

        # Top cap
        pygame.draw.circle(target, (120, 53, 15), (rect.centerx, rect.top - 6), 8, width=3)
        pygame.draw.rect(target, (120, 53, 15), (rect.centerx - 28, rect.top, 56, 12), border_radius=4)

        # Lantern body
        body_rect = pygame.Rect(rect.left, rect.top + 10, rect.width, rect.height - 20)
        pygame.draw.rect(target, bg_col, body_rect, border_radius=24)
        if is_highlighted:
            pygame.draw.rect(target, (255, 255, 255), body_rect, width=4, border_radius=24)
        else:
            pygame.draw.rect(target, border_col, body_rect, width=3, border_radius=24)

        # Bottom cap
        pygame.draw.rect(target, (120, 53, 15), (rect.centerx - 24, rect.bottom - 10, 48, 10), border_radius=4)

        # Draw Picture Symbol / Emoji in center of lantern
        if item.symbol not in self._emoji_cache:
            self._emoji_cache[item.symbol] = self._typography.render(
                item.symbol,
                FontRole.DISPLAY,
                52,
                (255, 255, 255),
            )
        emoji_surf = self._emoji_cache[item.symbol]
        target.blit(
            emoji_surf,
            (body_rect.centerx - emoji_surf.get_width() // 2, body_rect.centery - emoji_surf.get_height() // 2),
        )
