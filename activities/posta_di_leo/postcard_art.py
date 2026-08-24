"""Art and visual asset rendering for Posta di Leo."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.activity_api import get_shared_visual_path
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .postcard_content import RECIPIENTS, STAMPS, Recipient, Stamp
else:
    from postcard_content import RECIPIENTS, STAMPS, Recipient, Stamp


POSTCARD_BG: Final = (255, 251, 235)  # Soft cream paper
POSTCARD_BORDER: Final = (217, 119, 6)
RULED_LINE_COLOR: Final = (226, 232, 240)


class PostcardArt:
    """Own background scenery, character avatars, stamps, and paper rendering."""

    def __init__(self, width: int, height: int, typography: GreiaTypography) -> None:
        self._typography = typography
        self.background = self._build_background(width, height)
        self._avatars = self._load_avatars()
        self._emoji_cache: dict[str, pygame.Surface] = {}

    def _load_avatars(self) -> dict[str, pygame.Surface]:
        avatars: dict[str, pygame.Surface] = {}
        for r in RECIPIENTS:
            try:
                path = get_shared_visual_path(r.avatar_key, variant="happy")
                img = pygame.image.load(path)
                if pygame.display.get_surface() is not None:
                    img = img.convert_alpha()
                # Scale to 64x64
                scaled = pygame.transform.scale(img, (64, 64))
                avatars[r.recipient_id] = scaled
            except (OSError, ValueError, pygame.error, RuntimeError):
                # Fallback circular avatar
                surf = pygame.Surface((64, 64), pygame.SRCALPHA)
                pygame.draw.circle(surf, (2, 132, 199), (32, 32), 30)
                txt = self._typography.render(r.recipient_id[0].upper(), FontRole.DISPLAY, 32, (255, 255, 255))
                surf.blit(txt, (32 - txt.get_width() // 2, 32 - txt.get_height() // 2))
                avatars[r.recipient_id] = surf
        return avatars

    def get_avatar(self, recipient_id: str) -> pygame.Surface:
        return self._avatars.get(recipient_id, next(iter(self._avatars.values())))

    @staticmethod
    def _build_background(width: int, height: int) -> pygame.Surface:
        surface = pygame.Surface((width, height))
        surface.fill((30, 41, 59))  # Dark slate wooden desk tone

        # Vintage postal desk mat (soft warm teal/navy)
        mat_rect = pygame.Rect(40, 20, width - 80, height - 40)
        pygame.draw.rect(surface, (15, 23, 42), mat_rect, border_radius=28)
        pygame.draw.rect(surface, (51, 65, 85), mat_rect, width=3, border_radius=28)

        return surface

    def draw_stamp(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        stamp: Stamp,
        *,
        is_selected: bool = False,
    ) -> None:
        """Render a postage stamp with perforated border and central picture symbol."""
        pygame.draw.rect(target, stamp.bg_color, rect, border_radius=8)
        if is_selected:
            pygame.draw.rect(target, (255, 255, 255), rect, width=4, border_radius=8)
            pygame.draw.rect(target, stamp.border_color, rect.inflate(-6, -6), width=2, border_radius=6)
        else:
            pygame.draw.rect(target, stamp.border_color, rect, width=2, border_radius=8)

        # Scalloped perforated border dots
        for x in range(rect.left + 4, rect.right, 8):
            pygame.draw.circle(target, (15, 23, 42), (x, rect.top), 2)
            pygame.draw.circle(target, (15, 23, 42), (x, rect.bottom), 2)
        for y in range(rect.top + 4, rect.bottom, 8):
            pygame.draw.circle(target, (15, 23, 42), (rect.left, y), 2)
            pygame.draw.circle(target, (15, 23, 42), (rect.right, y), 2)

        # Draw stamp emoji
        if stamp.symbol not in self._emoji_cache:
            self._emoji_cache[stamp.symbol] = self._typography.render(
                stamp.symbol,
                FontRole.DISPLAY,
                min(rect.width, rect.height) // 2 + 4,
                (255, 255, 255),
            )
        em_surf = self._emoji_cache[stamp.symbol]
        target.blit(
            em_surf,
            (rect.centerx - em_surf.get_width() // 2, rect.centery - em_surf.get_height() // 2),
        )
