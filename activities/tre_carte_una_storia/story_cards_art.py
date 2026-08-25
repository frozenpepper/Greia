"""Art and visual rendering for Tre Carte Una Storia."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.child_text import display_text
from greia_platform.activity_api import get_shared_visual_path
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .story_cards_content import StoryCard
else:
    from story_cards_content import StoryCard


CARD_BG: Final = (255, 251, 235)  # Cream card paper
CARD_BORDER: Final = (217, 119, 6)


class StoryArt:
    """Own fairy-tale meadow background, Lilli mascot, card frames, and symbols."""

    def __init__(self, width: int, height: int, typography: GreiaTypography) -> None:
        self._typography = typography
        self.background = self._build_background(width, height)
        self.mascot = self._load_mascot()
        self._symbol_cache: dict[str, pygame.Surface] = {}

    def _load_mascot(self) -> pygame.Surface:
        try:
            path = get_shared_visual_path("character.lilli", variant="happy")
            img = pygame.image.load(path)
            if pygame.display.get_surface() is not None:
                img = img.convert_alpha()
            return pygame.transform.scale(img, (96, 96))
        except (OSError, ValueError, pygame.error, RuntimeError):
            surf = pygame.Surface((96, 96), pygame.SRCALPHA)
            pygame.draw.circle(surf, (236, 72, 153), (48, 48), 44)
            txt = self._typography.render(display_text("Lilli"), FontRole.BODY, 20, (255, 255, 255))
            surf.blit(txt, (48 - txt.get_width() // 2, 48 - txt.get_height() // 2))
            return surf

    @staticmethod
    def _build_background(width: int, height: int) -> pygame.Surface:
        surface = pygame.Surface((width, height))
        surface.fill((15, 23, 42))  # Deep night sky / midnight navy

        # Magic enchanted hill
        pygame.draw.ellipse(surface, (30, 41, 59), (-100, 380, width + 200, 400))
        pygame.draw.ellipse(surface, (51, 65, 85), (50, 420, width - 100, 360))

        # Glowing stars in sky
        stars = [(120, 50), (280, 70), (450, 40), (620, 80), (790, 45), (920, 65)]
        for sx, sy in stars:
            pygame.draw.circle(surface, (254, 240, 138), (sx, sy), 3)

        return surface

    def draw_card(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        card: StoryCard,
        *,
        is_selected: bool = False,
        is_hinted: bool = False,
        slot_number: int | None = None,
    ) -> None:
        """Render a narrative picture card with border, emblem, and optional slot badge."""
        # Shadow
        shadow_rect = rect.move(0, 6)
        pygame.draw.rect(target, (10, 15, 30), shadow_rect, border_radius=18)

        # Card base
        pygame.draw.rect(target, CARD_BG, rect, border_radius=18)

        # Border styling
        if is_selected:
            pygame.draw.rect(target, (56, 189, 248), rect, width=5, border_radius=18)
        elif is_hinted:
            pygame.draw.rect(target, (234, 179, 8), rect, width=5, border_radius=18)
        else:
            pygame.draw.rect(target, (217, 119, 6), rect, width=3, border_radius=18)

        # Inner vignette circle
        inner_rect = rect.inflate(-30, -50)
        pygame.draw.rect(target, card.accent_color, inner_rect, border_radius=14)
        pygame.draw.rect(target, (255, 255, 255), inner_rect, width=2, border_radius=14)

        # Draw central symbol / emoji
        if card.symbol not in self._symbol_cache:
            self._symbol_cache[card.symbol] = self._typography.render(
                card.symbol,
                FontRole.DISPLAY,
                64,
                (255, 255, 255),
            )
        em_surf = self._symbol_cache[card.symbol]
        target.blit(
            em_surf,
            (inner_rect.centerx - em_surf.get_width() // 2, inner_rect.centery - em_surf.get_height() // 2),
        )

        # Top slot badge if slot_number given
        if slot_number is not None:
            badge_rect = pygame.Rect(rect.centerx - 24, rect.top - 12, 48, 28)
            pygame.draw.rect(target, (2, 132, 199), badge_rect, border_radius=12)
            num_surf = self._typography.render(str(slot_number), FontRole.TITLE, 18, (255, 255, 255))
            target.blit(
                num_surf,
                (badge_rect.centerx - num_surf.get_width() // 2, badge_rect.centery - num_surf.get_height() // 2),
            )
