"""Low-allocation, high-polish presentation for Luci di Momo."""

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
    pygame.Rect(394, 430, 108, 108),
    pygame.Rect(530, 430, 108, 108),
    pygame.Rect(666, 430, 108, 108),
)
REPLAY_RECT: Final = pygame.Rect(840, 430, 96, 96)
LANTERN_CENTER: Final = (215, 275)


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
            value: typography.render(str(value), FontRole.DISPLAY, 58, (120, 53, 15))
            for value in range(1, 6)
        }
        self._prompt = typography.render(
            resources.text("prompt.choose"),
            FontRole.TITLE,
            26,
            (254, 240, 138),
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
        self._art.draw_lantern(target, LANTERN_CENTER[0], LANTERN_CENTER[1], awake=True)
        count = round_.quantity if visible_count is None else max(0, min(round_.quantity, visible_count))
        radius = 16
        if level == 4:
            radius += sum(ord(ch) for ch in round_.round_id) % 6
        for x, y in round_.positions[:count]:
            self._art.draw_firefly(target, x, y, radius)

    def draw_choices(
        self,
        target: pygame.Surface,
        round_: FireflyRound,
        *,
        hovered_value: int | None = None,
        hovered_replay: bool = False,
    ) -> None:
        self._draw_base(target)
        self._art.draw_lantern(target, LANTERN_CENTER[0], LANTERN_CENTER[1], awake=False)

        # Prompt Banner
        p_x = REFERENCE_WIDTH // 2 - self._prompt.get_width() // 2
        p_y = 365
        banner_rect = pygame.Rect(p_x - 20, p_y - 6, self._prompt.get_width() + 40, self._prompt.get_height() + 12)
        pygame.draw.rect(target, (15, 23, 42, 180), banner_rect, border_radius=16)
        pygame.draw.rect(target, (217, 119, 6), banner_rect, width=2, border_radius=16)
        target.blit(self._prompt, (p_x, p_y))

        # 3 Choice Buttons with 3D bevel and tactile lift
        for rect, value in zip(CHOICE_RECTS, round_.choice_values):
            is_hovered = (value == hovered_value)
            draw_rect = rect.move(0, -4) if is_hovered else rect

            # Drop shadow
            shadow_rect = rect.move(0, 6)
            pygame.draw.rect(target, (5, 10, 20), shadow_rect, border_radius=28)

            # Button body (warm cream paper)
            pygame.draw.rect(target, (255, 251, 235), draw_rect, border_radius=28)

            # Border
            if is_hovered:
                pygame.draw.rect(target, (56, 189, 248), draw_rect, width=6, border_radius=28)
            else:
                pygame.draw.rect(target, (245, 158, 11), draw_rect, width=5, border_radius=28)

            # Top highlight line
            hl_rect = draw_rect.inflate(-16, -draw_rect.height + 8).move(0, -draw_rect.height // 2 + 8)
            pygame.draw.rect(target, (255, 255, 255), hl_rect, border_radius=4)

            # Numeral
            numeral = self._number_surfaces[value]
            target.blit(
                numeral,
                (draw_rect.centerx - numeral.get_width() // 2, draw_rect.centery - numeral.get_height() // 2),
            )

        # Replay Button
        r_draw = REPLAY_RECT.move(0, -4) if hovered_replay else REPLAY_RECT
        cx, cy = r_draw.center
        # Shadow
        pygame.draw.circle(target, (5, 10, 20), (REPLAY_RECT.centerx, REPLAY_RECT.centery + 6), REPLAY_RECT.width // 2)
        # Body
        pygame.draw.circle(target, (2, 132, 199) if hovered_replay else (14, 116, 144), (cx, cy), r_draw.width // 2)
        pygame.draw.circle(target, (255, 255, 255), (cx, cy), r_draw.width // 2, width=4)
        
        # Circular reload icon
        arc_rect = pygame.Rect(cx - 22, cy - 22, 44, 44)
        pygame.draw.arc(target, (255, 255, 255), arc_rect, 0.6, 5.8, width=5)
        pygame.draw.polygon(
            target,
            (255, 255, 255),
            [(cx + 18, cy - 16), (cx + 6, cy - 28), (cx + 20, cy - 28)],
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
            target.blit(self._art.momo, (30, 395))
