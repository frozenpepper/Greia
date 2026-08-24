"""Art and visual rendering for Officina dei Suoni."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.activity_api import get_shared_visual_path
from greia_platform.typography import FontRole, GreiaTypography


TILE_BG: Final = (254, 240, 138)
TILE_BORDER: Final = (202, 138, 4)
TILE_TEXT: Final = (133, 77, 14)


class SoundWorkshopArt:
    """Own background scenery, Leo mascot, sound boxes, and letter tiles."""

    def __init__(self, width: int, height: int, typography: GreiaTypography) -> None:
        self._typography = typography
        self.background = self._build_background(width, height)
        self.leo = self._load_leo()
        self._text_cache: dict[tuple[str, int, tuple[int, int, int]], pygame.Surface] = {}

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
        surface.fill((15, 23, 42))  # Slate dark workshop

        # Background workshop arches
        pygame.draw.circle(surface, (30, 41, 59), (width // 2, -100), 480)
        pygame.draw.circle(surface, (15, 23, 42), (width // 2, -100), 400)

        # Workshop counter workbench
        pygame.draw.rect(surface, (51, 65, 85), (0, 390, width, height - 390))
        pygame.draw.rect(surface, (71, 85, 105), (0, 390, width, 14))

        # Acoustic sound rail across the middle
        pygame.draw.rect(surface, (30, 58, 138), (80, 190, width - 160, 12), border_radius=6)

        # Colorful glowing sound beads on the rail
        bead_colors = [(236, 72, 153), (234, 179, 8), (34, 197, 94), (56, 189, 248), (168, 85, 247)]
        for i, col in enumerate(bead_colors):
            bx = 140 + i * ((width - 280) // (len(bead_colors) - 1))
            pygame.draw.circle(surface, col, (bx, 196), 14)
            pygame.draw.circle(surface, (255, 255, 255), (bx - 3, 193), 4)

        return surface

    def draw_letter_tile(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        letter: str,
        *,
        is_highlighted: bool = False,
        is_empty_target: bool = False,
    ) -> None:
        """Render a chunky wooden/golden letter tile or target box."""
        if is_empty_target:
            pygame.draw.rect(target, (30, 41, 59), rect, border_radius=18)
            pygame.draw.rect(target, (56, 189, 248), rect, width=3, border_radius=18)
            # Question mark inside empty target box
            q_surf = self._get_rendered_text("?", FontRole.DISPLAY, 40, (148, 163, 184))
            target.blit(
                q_surf,
                (rect.centerx - q_surf.get_width() // 2, rect.centery - q_surf.get_height() // 2),
            )
            return

        pygame.draw.rect(target, TILE_BG, rect, border_radius=18)
        if is_highlighted:
            pygame.draw.rect(target, (255, 255, 255), rect, width=4, border_radius=18)
        else:
            pygame.draw.rect(target, TILE_BORDER, rect, width=3, border_radius=18)

        # Bottom bevel / shadow
        pygame.draw.rect(target, TILE_BORDER, (rect.left + 4, rect.bottom - 8, rect.width - 8, 4), border_radius=2)

        txt_surf = self._get_rendered_text(letter, FontRole.DISPLAY, 46, TILE_TEXT)
        target.blit(
            txt_surf,
            (rect.centerx - txt_surf.get_width() // 2, rect.centery - txt_surf.get_height() // 2),
        )

    def draw_picture_card(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        symbol: str,
        *,
        is_highlighted: bool = False,
        bg_col: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        """Render a large picture card."""
        pygame.draw.rect(target, bg_col, rect, border_radius=22)
        if is_highlighted:
            pygame.draw.rect(target, (56, 189, 248), rect, width=4, border_radius=22)
        else:
            pygame.draw.rect(target, (203, 213, 225), rect, width=3, border_radius=22)

        sym_surf = self._get_rendered_text(symbol, FontRole.DISPLAY, 56, (255, 255, 255))
        target.blit(
            sym_surf,
            (rect.centerx - sym_surf.get_width() // 2, rect.centery - sym_surf.get_height() // 2),
        )

    def _get_rendered_text(
        self, text: str, role: FontRole, size: int, color: tuple[int, int, int]
    ) -> pygame.Surface:
        key = (text, size, color)
        if key not in self._text_cache:
            self._text_cache[key] = self._typography.render(text, role, size, color)
        return self._text_cache[key]
