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


POSTCARD_BG: Final = (255, 251, 235)  # Warm antique cream paper
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
                scaled = pygame.transform.scale(img, (64, 64))
                avatars[r.recipient_id] = scaled
            except (OSError, ValueError, pygame.error, RuntimeError):
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

        # Rich mahogany writing desk wood grain gradient
        for y in range(height):
            t = y / height
            r = int(55 * (1 - t) + 38 * t)
            g = int(38 * (1 - t) + 24 * t)
            b = int(28 * (1 - t) + 16 * t)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

        # Vertical wood plank lines
        for x in range(0, width, 72):
            pygame.draw.line(surface, (28, 18, 12), (x, 0), (x, height), 2)
            pygame.draw.line(surface, (68, 46, 32), (x + 2, 0), (x + 2, height), 1)

        # Forest green leather writing desk blotter mat with golden embossed border
        mat_rect = pygame.Rect(44, 16, width - 88, height - 32)
        pygame.draw.rect(surface, (10, 8, 6), mat_rect.move(0, 6), border_radius=24)
        pygame.draw.rect(surface, (15, 42, 32), mat_rect, border_radius=24)
        pygame.draw.rect(surface, (217, 119, 6), mat_rect, width=3, border_radius=24)
        pygame.draw.rect(surface, (245, 158, 11), mat_rect.inflate(-8, -8), width=1, border_radius=20)

        # Brass corner protectors on desk mat
        for cx, cy in [
            (mat_rect.left + 12, mat_rect.top + 12),
            (mat_rect.right - 12, mat_rect.top + 12),
            (mat_rect.left + 12, mat_rect.bottom - 12),
            (mat_rect.right - 12, mat_rect.bottom - 12),
        ]:
            pygame.draw.circle(surface, (245, 158, 11), (cx, cy), 10)
            pygame.draw.circle(surface, (180, 83, 9), (cx, cy), 10, 2)

        return surface

    def draw_stamp(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        stamp: Stamp,
        *,
        is_selected: bool = False,
        is_hovered: bool = False,
    ) -> None:
        """Render a postage stamp with perforated border, drop shadow, and crisp symbol."""
        draw_rect = rect.move(0, -4) if (is_hovered or is_selected) else rect

        # Drop shadow
        pygame.draw.rect(target, (10, 8, 6, 80), rect.move(0, 6), border_radius=8)

        # Stamp body
        pygame.draw.rect(target, stamp.bg_color, draw_rect, border_radius=8)

        # Border
        if is_hovered:
            pygame.draw.rect(target, (56, 189, 248), draw_rect, width=4, border_radius=8)
        elif is_selected:
            pygame.draw.rect(target, (251, 191, 36), draw_rect, width=4, border_radius=8)
            pygame.draw.rect(target, stamp.border_color, draw_rect.inflate(-6, -6), width=2, border_radius=6)
        else:
            pygame.draw.rect(target, stamp.border_color, draw_rect, width=2, border_radius=8)

        # Scalloped perforated border dots
        for x in range(draw_rect.left + 4, draw_rect.right, 8):
            pygame.draw.circle(target, (15, 42, 32), (x, draw_rect.top), 2)
            pygame.draw.circle(target, (15, 42, 32), (x, draw_rect.bottom), 2)
        for y in range(draw_rect.top + 4, draw_rect.bottom, 8):
            pygame.draw.circle(target, (15, 42, 32), (draw_rect.left, y), 2)
            pygame.draw.circle(target, (15, 42, 32), (draw_rect.right, y), 2)

        # Draw stamp emoji
        if stamp.symbol not in self._emoji_cache:
            self._emoji_cache[stamp.symbol] = self._typography.render(
                stamp.symbol,
                FontRole.DISPLAY,
                min(draw_rect.width, draw_rect.height) // 2 + 4,
                (255, 255, 255),
            )
        em_surf = self._emoji_cache[stamp.symbol]
        target.blit(
            em_surf,
            (draw_rect.centerx - em_surf.get_width() // 2, draw_rect.centery - em_surf.get_height() // 2),
        )
