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
START_BTN_RECT: Final = pygame.Rect(422, 190, 180, 180)
LISTEN_BTN_RECT: Final = pygame.Rect(145, 500, 150, 48)
MASCOT_RECT: Final = pygame.Rect(25, 435, 120, 120)
LANTERN_CENTER: Final = (160, 230)


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
        # Localized captions resolve once; ``LocalizedResources.text`` already
        # applies the child letter-case policy. A missing resource shows no
        # fixed-language sentence: the play triangle and speaker stay readable.
        self._prompt_surface = self._caption("prompt.tap_to_play", 22, (254, 240, 138))
        self._listen_surface = self._caption("button.listen", 18, (120, 53, 15))
        self._hud_surfaces: dict[tuple[int, int], pygame.Surface] = {}
        self._choice_prompt = typography.render("✨ ❓", FontRole.DISPLAY, 36, (254, 240, 138))

    def _caption(self, key: str, size: int, color: tuple[int, int, int]) -> pygame.Surface | None:
        try:
            text = self._resources.text(key)
        except Exception:
            return None
        return self._typography.render(text, FontRole.TITLE, size, color)

    def start_contains(self, point: tuple[int, int]) -> bool:
        return START_BTN_RECT.collidepoint(point)

    def listen_contains(self, point: tuple[int, int]) -> bool:
        return LISTEN_BTN_RECT.collidepoint(point) or MASCOT_RECT.collidepoint(point)

    def choice_at(self, point: tuple[int, int], round_: FireflyRound) -> int | None:
        for rect, value in zip(CHOICE_RECTS, round_.choice_values):
            if rect.collidepoint(point):
                return value
        return None

    def replay_contains(self, point: tuple[int, int]) -> bool:
        return REPLAY_RECT.collidepoint(point)

    def draw_ready(
        self,
        target: pygame.Surface,
        round_: FireflyRound,
        *,
        round_index: int,
        total_rounds: int,
        hovered_start: bool = False,
    ) -> None:
        """Render the ready screen with a VERY BIG PLAY BUTTON at the center."""
        self._draw_base(target, awake=False)
        self._draw_hud(target, round_index, total_rounds)

        # VERY BIG START BUTTON WITH PLAY ICON
        cx, cy = START_BTN_RECT.center
        draw_rect = START_BTN_RECT.move(0, -6) if hovered_start else START_BTN_RECT
        dcx, dcy = draw_rect.center
        radius = draw_rect.width // 2

        # Glowing soft aura
        for r in range(radius + 28, radius + 4, -4):
            alpha = int(45 * (1.0 - (r - radius) / 28.0))
            aura = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (253, 224, 71, alpha), (r, r), r)
            target.blit(aura, (dcx - r, dcy - r))

        # Drop shadow
        pygame.draw.circle(target, (5, 10, 20), (cx, cy + 8), radius)

        # Vibrant emerald play circle
        body_color = (22, 163, 74) if hovered_start else (34, 197, 94)
        pygame.draw.circle(target, body_color, (dcx, dcy), radius)
        pygame.draw.circle(target, (254, 240, 138), (dcx, dcy), radius, width=6)
        pygame.draw.circle(target, (217, 119, 6), (dcx, dcy), radius - 6, width=2)

        # Highlight crescent safely inside circle
        hl = pygame.Rect(dcx - (radius - 28), dcy - radius + 14, (radius - 28) * 2, radius // 2)
        pygame.draw.ellipse(target, (134, 239, 172, 140), hl)

        # Large white triangular play icon
        tri_points = [
            (dcx - 20, dcy - 44),
            (dcx - 20, dcy + 44),
            (dcx + 38, dcy),
        ]
        pygame.draw.polygon(target, (21, 128, 61), [(x, y + 4) for x, y in tri_points])
        pygame.draw.polygon(target, (255, 255, 255), tri_points)

        # Prompt capsule below button
        prompt_surf = self._prompt_surface
        if prompt_surf is None:
            return
        p_x = REFERENCE_WIDTH // 2 - prompt_surf.get_width() // 2
        p_y = 395
        banner_rect = pygame.Rect(p_x - 24, p_y - 6, prompt_surf.get_width() + 48, prompt_surf.get_height() + 12)
        pygame.draw.rect(target, (15, 23, 42, 220), banner_rect, border_radius=18)
        pygame.draw.rect(target, (217, 119, 6), banner_rect, width=2, border_radius=18)
        target.blit(prompt_surf, (p_x, p_y))

    def draw_reveal(
        self,
        target: pygame.Surface,
        round_: FireflyRound,
        *,
        level: int,
        round_index: int,
        total_rounds: int,
        visible_count: int | None = None,
    ) -> None:
        self._draw_base(target, awake=True)
        self._draw_hud(target, round_index, total_rounds)

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
        round_index: int,
        total_rounds: int,
        hovered_value: int | None = None,
        hovered_replay: bool = False,
    ) -> None:
        self._draw_base(target, awake=False)
        self._draw_hud(target, round_index, total_rounds)

        # Visual Prompt Banner: Glowing firefly + Question Mark
        prompt_surf = self._choice_prompt
        p_x = REFERENCE_WIDTH // 2 - prompt_surf.get_width() // 2
        p_y = 355
        banner_rect = pygame.Rect(p_x - 24, p_y - 6, prompt_surf.get_width() + 48, prompt_surf.get_height() + 12)
        pygame.draw.rect(target, (15, 23, 42, 220), banner_rect, border_radius=20)
        pygame.draw.rect(target, (217, 119, 6), banner_rect, width=3, border_radius=20)
        target.blit(prompt_surf, (p_x, p_y))

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

    def _draw_base(self, target: pygame.Surface, *, awake: bool) -> None:
        target.blit(self._art.background, (0, 0))
        self._art.draw_lantern(target, LANTERN_CENTER[0], LANTERN_CENTER[1], awake=awake)

    def _draw_hud(self, target: pygame.Surface, round_index: int, total_rounds: int) -> None:
        if self._art.momo is not None:
            target.blit(self._art.momo, (25, 435))

        # Speech replay capsule beside Momo
        pygame.draw.rect(target, (10, 5, 20), LISTEN_BTN_RECT.move(0, 4), border_radius=25)
        pygame.draw.rect(target, (254, 240, 138), LISTEN_BTN_RECT, border_radius=25)
        pygame.draw.rect(target, (217, 119, 6), LISTEN_BTN_RECT, width=3, border_radius=25)

        l_surf = self._listen_surface
        if l_surf is not None:
            target.blit(
                l_surf,
                (LISTEN_BTN_RECT.centerx - l_surf.get_width() // 2, LISTEN_BTN_RECT.centery - l_surf.get_height() // 2),
            )

        badge_rect = pygame.Rect(870, 24, 130, 44)
        pygame.draw.rect(target, (15, 23, 42, 200), badge_rect, border_radius=22)
        pygame.draw.rect(target, (254, 240, 138), badge_rect, width=2, border_radius=22)

        txt_surf = self._hud_surfaces.get((round_index, total_rounds))
        if txt_surf is None:
            if len(self._hud_surfaces) >= 32:
                self._hud_surfaces.clear()
            txt_surf = self._typography.render(
                f"{round_index + 1} / {total_rounds}", FontRole.TITLE, 22, (254, 240, 138)
            )
            self._hud_surfaces[(round_index, total_rounds)] = txt_surf
        target.blit(
            txt_surf,
            (badge_rect.centerx - txt_surf.get_width() // 2, badge_rect.centery - txt_surf.get_height() // 2),
        )


