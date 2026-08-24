"""Art and visual rendering for Officina dei Suoni."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.activity_api import get_shared_visual_path
from greia_platform.typography import FontRole, GreiaTypography


TILE_BG: Final = (254, 243, 199)
TILE_BORDER: Final = (217, 119, 6)
TILE_TEXT: Final = (120, 53, 15)


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

        # Deep twilight acoustic room gradient
        for y in range(height):
            t = y / height
            r = int(24 * (1 - t) + 18 * t)
            g = int(32 * (1 - t) + 24 * t)
            b = int(58 * (1 - t) + 42 * t)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

        # Acoustic pegboard panel in background
        pygame.draw.rect(surface, (15, 20, 35), (80, 20, width - 160, 360), border_radius=20)
        pygame.draw.rect(surface, (45, 55, 80), (80, 20, width - 160, 360), width=3, border_radius=20)

        # Pegboard acoustic holes
        for hx in range(120, width - 120, 48):
            for hy in range(50, 360, 48):
                pygame.draw.circle(surface, (10, 14, 26), (hx, hy), 4)

        # Brass musical pipes & acoustic resonator tubes
        for px, ph, pw in [(160, 140, 12), (200, 110, 12), (240, 160, 12), (780, 150, 12), (820, 120, 12), (860, 170, 12)]:
            pygame.draw.rect(surface, (10, 8, 6), (px - 2, 40, pw + 4, ph), border_radius=6)
            pygame.draw.rect(surface, (245, 158, 11), (px, 40, pw, ph), border_radius=6)
            pygame.draw.rect(surface, (254, 243, 199), (px + 2, 44, pw - 4, 4), border_radius=2)

        # Polished wooden synthesizer workbench
        pygame.draw.rect(surface, (10, 8, 6), (0, 385, width, 12))
        pygame.draw.rect(surface, (120, 75, 42), (0, 390, width, height - 390))
        pygame.draw.rect(surface, (160, 105, 60), (0, 390, width, 16))
        pygame.draw.line(surface, (78, 48, 26), (0, 406), (width, 406), 4)

        # Brass acoustic track rail across middle
        pygame.draw.rect(surface, (217, 119, 6), (120, 210, width - 240, 14), border_radius=7)
        pygame.draw.rect(surface, (254, 240, 138), (120, 212, width - 240, 3), border_radius=2)

        # Glowing harmonic beads on rail
        bead_colors = [(244, 63, 94), (251, 191, 36), (34, 197, 94), (56, 189, 248), (168, 85, 247), (236, 72, 153)]
        for i, col in enumerate(bead_colors):
            bx = 180 + i * ((width - 360) // (len(bead_colors) - 1))
            pygame.draw.circle(surface, (10, 8, 6), (bx, 217), 18)
            pygame.draw.circle(surface, col, (bx, 217), 16)
            pygame.draw.circle(surface, (255, 255, 255), (bx - 4, 213), 5)

        return surface

    def draw_letter_tile(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        letter: str,
        *,
        is_highlighted: bool = False,
        is_empty_target: bool = False,
        is_hovered: bool = False,
    ) -> None:
        """Render a chunky 3D wooden letter tile or drop target box."""
        draw_rect = rect.move(0, -6) if is_hovered else rect

        if is_empty_target:
            pygame.draw.rect(target, (15, 23, 42), rect.move(0, 4), border_radius=18)
            pygame.draw.rect(target, (30, 41, 59), draw_rect, border_radius=18)
            border_c = (56, 189, 248) if is_hovered else (94, 234, 212)
            pygame.draw.rect(target, border_c, draw_rect, width=3, border_radius=18)
            q_surf = self._get_rendered_text("?", FontRole.DISPLAY, 42, (148, 163, 184))
            target.blit(
                q_surf,
                (draw_rect.centerx - q_surf.get_width() // 2, draw_rect.centery - q_surf.get_height() // 2),
            )
            return

        # 3D Drop shadow
        pygame.draw.rect(target, (10, 8, 6, 90), rect.move(0, 8), border_radius=18)

        # Wooden tile body
        pygame.draw.rect(target, TILE_BG, draw_rect, border_radius=18)

        # Border styling
        if is_hovered:
            pygame.draw.rect(target, (56, 189, 248), draw_rect, width=5, border_radius=18)
        elif is_highlighted:
            pygame.draw.rect(target, (251, 191, 36), draw_rect, width=5, border_radius=18)
        else:
            pygame.draw.rect(target, TILE_BORDER, draw_rect, width=3, border_radius=18)

        # Gloss highlight on top edge
        hl = draw_rect.inflate(-8, -draw_rect.height + 6).move(0, -draw_rect.height // 2 + 6)
        pygame.draw.rect(target, (255, 255, 255, 160), hl, border_radius=3)

        # Bottom wooden bevel
        pygame.draw.rect(target, (217, 119, 6), (draw_rect.left + 4, draw_rect.bottom - 8, draw_rect.width - 8, 4), border_radius=2)

        txt_surf = self._get_rendered_text(letter, FontRole.DISPLAY, 46, TILE_TEXT)
        target.blit(
            txt_surf,
            (draw_rect.centerx - txt_surf.get_width() // 2, draw_rect.centery - txt_surf.get_height() // 2),
        )

    def draw_picture_card(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        symbol: str,
        *,
        is_hovered: bool = False,
    ) -> None:
        """Render a large picture card with drop shadow."""
        draw_rect = rect.move(0, -4) if is_hovered else rect
        pygame.draw.rect(target, (10, 8, 6, 80), rect.move(0, 8), border_radius=24)
        pygame.draw.rect(target, (255, 251, 235), draw_rect, border_radius=24)
        border_c = (56, 189, 248) if is_hovered else (217, 119, 6)
        pygame.draw.rect(target, border_c, draw_rect, width=4, border_radius=24)

        sym_surf = self._get_rendered_text(symbol, FontRole.DISPLAY, 72, (255, 255, 255))
        target.blit(
            sym_surf,
            (draw_rect.centerx - sym_surf.get_width() // 2, draw_rect.centery - sym_surf.get_height() // 2),
        )

    def _get_rendered_text(
        self,
        text: str,
        role: FontRole,
        size: int,
        color: tuple[int, int, int],
    ) -> pygame.Surface:
        key = (text, size, color)
        if key not in self._text_cache:
            self._text_cache[key] = self._typography.render(text, role, size, color)
        return self._text_cache[key]
