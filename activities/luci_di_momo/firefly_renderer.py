"""Low-allocation Pygame presentation for Luci di Momo."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .firefly_art import FireflyArt
    from .firefly_model import FireflyRound, REFERENCE_WIDTH
else:
    from firefly_art import FireflyArt
    from firefly_model import FireflyRound, REFERENCE_WIDTH


CHOICE_RECTS: Final = (
    pygame.Rect(394, 430, 104, 104),
    pygame.Rect(530, 430, 104, 104),
    pygame.Rect(666, 430, 104, 104),
)
REPLAY_RECT: Final = pygame.Rect(850, 430, 88, 88)
LANTERN_CENTER: Final = (215, 286)


class FireflyRenderer:
    """Render the prepared scene and expose stable semantic hit geometry."""

    def __init__(
        self,
        art: FireflyArt,
        typography: GreiaTypography,
        resources: LocalizedResources,
    ) -> None:
        self._art = art
        self._typography = typography
        self._resources = resources
        self._number_surfaces = {
            value: typography.render(str(value), FontRole.DISPLAY, 56, (55, 43, 27))
            for value in range(1, 6)
        }
        self._prompt = typography.render(
            resources.text("prompt.choose"),
            FontRole.TITLE,
            28,
            (255, 248, 215),
        )

    def draw_reveal(
        self,
        target: pygame.Surface,
        round_: FireflyRound,
        *,
        level: int,
        visible_count: int | None = None,
    ) -> None:
        self._draw_base(target)
        self._draw_lantern(target, awake=True)
        count = round_.quantity if visible_count is None else max(0, min(round_.quantity, visible_count))
        radius = 15
        if level == 4:
            radius += sum(ord(ch) for ch in round_.round_id) % 6
        for x, y in round_.positions[:count]:
            self._draw_firefly(target, x, y, radius)

    def draw_choices(self, target: pygame.Surface, round_: FireflyRound) -> None:
        self._draw_base(target)
        self._draw_lantern(target, awake=False)
        target.blit(
            self._prompt,
            (REFERENCE_WIDTH // 2 - self._prompt.get_width() // 2, 365),
        )
        for rect, value in zip(CHOICE_RECTS, round_.choice_values):
            pygame.draw.rect(target, (255, 246, 215), rect, border_radius=26)
            pygame.draw.rect(target, (236, 192, 83), rect, width=5, border_radius=26)
            numeral = self._number_surfaces[value]
            target.blit(
                numeral,
                (rect.centerx - numeral.get_width() // 2, rect.centery - numeral.get_height() // 2),
            )
        cx, cy = REPLAY_RECT.center
        pygame.draw.circle(target, (67, 110, 128), (cx, cy), REPLAY_RECT.width // 2)
        pygame.draw.circle(target, (255, 255, 255), (cx, cy), REPLAY_RECT.width // 2, width=3)
        # Circular reload arrow
        arc_rect = pygame.Rect(cx - 20, cy - 20, 40, 40)
        pygame.draw.arc(target, (255, 255, 255), arc_rect, 0.6, 5.8, width=4)
        pygame.draw.polygon(
            target,
            (255, 255, 255),
            [(cx + 16, cy - 14), (cx + 6, cy - 24), (cx + 18, cy - 24)],
        )

    def choice_at(self, point: tuple[int, int], round_: FireflyRound) -> int | None:
        for rect, value in zip(CHOICE_RECTS, round_.choice_values):
            if rect.collidepoint(point):
                return value
        return None

    def replay_contains(self, point: tuple[int, int]) -> bool:
        return REPLAY_RECT.collidepoint(point)

    def _draw_base(self, target: pygame.Surface) -> None:
        target.blit(self._art.background, (0, 0))
        if self._art.momo is not None:
            target.blit(self._art.momo, (28, 330))
        else:
            pygame.draw.circle(target, (238, 151, 192), (115, 425), 65)
            pygame.draw.circle(target, (45, 44, 57), (92, 410), 5)
            pygame.draw.circle(target, (45, 44, 57), (138, 410), 5)
            pygame.draw.arc(target, (45, 44, 57), (91, 412, 48, 34), 3.4, 6.0, 4)

    @staticmethod
    def _draw_lantern(target: pygame.Surface, *, awake: bool) -> None:
        x, y = LANTERN_CENTER
        glow = (255, 211, 89) if awake else (139, 132, 106)
        pygame.draw.circle(target, glow, (x, y), 54)
        pygame.draw.rect(target, (88, 65, 48), (x - 44, y - 50, 88, 100), width=8, border_radius=20)
        pygame.draw.arc(target, (88, 65, 48), (x - 34, y - 84, 68, 66), 3.15, 6.25, 7)

    @staticmethod
    def _draw_firefly(target: pygame.Surface, x: int, y: int, radius: int) -> None:
        pygame.draw.circle(target, (255, 218, 81), (x, y), radius)
        pygame.draw.circle(target, (255, 248, 181), (x, y), max(5, radius // 2))
        pygame.draw.ellipse(target, (198, 231, 226), (x - radius - 10, y - 7, radius, 14))
        pygame.draw.ellipse(target, (198, 231, 226), (x + 10, y - 7, radius, 14))
