"""Scene renderer for Stelle Incantate.

Draws the cached night backdrop plus the live connect-the-dots layer: big
numbered stars, glowing connection lines with a draw-in animation, a pulsing
invitation halo on the next star, gentle wobble feedback, Leo the owl as the
Activity's presenter, the curiosity-fact bubble and the big next-figure
control. Text is secondary support; every core action is visually obvious.
"""

from __future__ import annotations

import math
from typing import Final

import pygame

from greia_platform.activity_api import get_icon_path, get_shared_visual_path
from greia_platform.localization import LocalizedResources
from greia_platform.typography import FontRole, GreiaTypography

if __package__:
    from .sky_art import build_backdrop, build_star_sprite
    from .sky_model import SkyRound
else:
    from sky_art import build_backdrop, build_star_sprite
    from sky_model import SkyRound


REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600

#: Normalized sky play area mapped onto the reference frame.
SKY_RECT: Final[pygame.Rect] = pygame.Rect(48, 30, 928, 420)

STAR_RADIUS: Final[int] = 24
STAR_TAP_RADIUS: Final[int] = 46
LINE_COLOR: Final[tuple[int, int, int]] = (186, 214, 255)
LINE_WIDTH: Final[int] = 5

LEO_SIZE: Final[int] = 128
LEO_CENTER: Final[tuple[int, int]] = (REFERENCE_WIDTH - 104, REFERENCE_HEIGHT - 96)
FACT_BUTTON_RADIUS: Final[int] = 32
FACT_BUTTON_CENTER: Final[tuple[int, int]] = (
    LEO_CENTER[0] - LEO_SIZE // 2 - FACT_BUTTON_RADIUS - 16,
    LEO_CENTER[1] + 6,
)
NEXT_BUTTON_RECT: Final[pygame.Rect] = pygame.Rect(
    REFERENCE_WIDTH // 2 - 92, REFERENCE_HEIGHT - 96, 184, 68
)

CELEBRATE_SECONDS: Final[float] = 2.6


class SkyRenderer:
    """Own all presentation state and draw one complete frame."""

    def __init__(
        self,
        typography: GreiaTypography,
        resources: LocalizedResources,
    ) -> None:
        self.typography = typography
        self.resources = resources
        self._backdrop_size: tuple[int, int] | None = None
        self._backdrop: pygame.Surface | None = None
        self._star_sprite: pygame.Surface | None = None
        self._leo_frames: dict[str, pygame.Surface] = {}
        self._fact_icon: pygame.Surface | None = None

    # ------------------------------------------------------------------
    # Cached resources
    # ------------------------------------------------------------------

    def _ensure_backdrop(self, size: tuple[int, int]) -> pygame.Surface:
        if self._backdrop is None or self._backdrop_size != size:
            self._backdrop = build_backdrop(*size)
            self._backdrop_size = size
        return self._backdrop

    def _ensure_star_sprite(self, radius: int) -> pygame.Surface:
        size = radius * 2
        if self._star_sprite is None or self._star_sprite.get_width() != size:
            self._star_sprite = build_star_sprite(radius)
        return self._star_sprite

    def _leo(self, variant: str) -> pygame.Surface:
        frame = self._leo_frames.get(variant)
        if frame is None:
            try:
                path = get_shared_visual_path("character.leo", variant=variant)
                frame = pygame.image.load(str(path)).convert_alpha()
                frame = pygame.transform.smoothscale(frame, (LEO_SIZE, LEO_SIZE))
            except (OSError, ValueError, pygame.error):
                frame = pygame.Surface((LEO_SIZE, LEO_SIZE), pygame.SRCALPHA)
                pygame.draw.circle(frame, (150, 110, 70), (LEO_SIZE // 2, LEO_SIZE // 2), LEO_SIZE // 2 - 6)
            self._leo_frames[variant] = frame
        return frame

    def _ensure_fact_icon(self, size: int) -> pygame.Surface:
        size = max(20, size)
        if self._fact_icon is None or self._fact_icon.get_width() != size:
            try:
                path = get_icon_path("magnifier", 128)
                icon = pygame.image.load(str(path)).convert_alpha()
                self._fact_icon = pygame.transform.smoothscale(icon, (size, size))
            except (OSError, ValueError, pygame.error):
                self._fact_icon = pygame.Surface((size, size), pygame.SRCALPHA)
                pygame.draw.circle(
                    self._fact_icon, (255, 255, 255), (size // 2, size // 2), size // 3, width=4
                )
        return self._fact_icon

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def star_center(self, round_state: SkyRound, star_index: int) -> tuple[int, int]:
        star = round_state.constellation.stars[star_index]
        return (
            SKY_RECT.left + round(star.x * SKY_RECT.width),
            SKY_RECT.top + round(star.y * SKY_RECT.height),
        )

    def star_at(self, round_state: SkyRound, point: tuple[int, int]) -> int | None:
        """Return the tapped star index, or None when the tap is empty sky."""

        best: int | None = None
        best_distance = STAR_TAP_RADIUS
        for index in range(round_state.star_count):
            center = self.star_center(round_state, index)
            distance = math.hypot(point[0] - center[0], point[1] - center[1])
            if distance <= best_distance:
                best = index
                best_distance = distance
        return best

    def fact_button_contains(self, point: tuple[int, int]) -> bool:
        return (
            math.hypot(point[0] - FACT_BUTTON_CENTER[0], point[1] - FACT_BUTTON_CENTER[1])
            <= FACT_BUTTON_RADIUS + 8
        )

    # ------------------------------------------------------------------
    # Frame drawing
    # ------------------------------------------------------------------

    def draw_scene(
        self,
        surface: pygame.Surface,
        round_state: SkyRound,
        *,
        now: float,
        line_progress: float,
        wrong_star: int | None,
        wrong_age: float,
        celebrating: bool,
        fact_text: str | None,
        leo_happy: bool,
        name_text: str | None,
        show_next: bool,
        hovered_next: bool,
    ) -> None:
        size = surface.get_size()
        surface.blit(self._ensure_backdrop(size), (0, 0))

        constellation = round_state.constellation
        pulse = 0.5 + 0.5 * math.sin(now * 3.4)

        # Connection lines (with draw-in progress for the newest edge).
        completed_edges = tuple(
            edge
            for edge in constellation.edges
            if edge[0] in round_state.connected and edge[1] in round_state.connected
        )
        newest = round_state.last_connected
        newest_edges = tuple(
            edge for edge in completed_edges if newest is not None and newest in edge
        ) if celebrating is False else tuple()
        for edge in completed_edges:
            if edge in newest_edges and line_progress < 1.0:
                start = self.star_center(round_state, edge[0])
                end = self.star_center(round_state, edge[1])
                current = (
                    round(start[0] + (end[0] - start[0]) * line_progress),
                    round(start[1] + (end[1] - start[1]) * line_progress),
                )
                pygame.draw.line(surface, LINE_COLOR, start, current, LINE_WIDTH)
            else:
                start = self.star_center(round_state, edge[0])
                end = self.star_center(round_state, edge[1])
                pygame.draw.line(surface, LINE_COLOR, start, end, LINE_WIDTH)

        # Stars.
        sprite = self._ensure_star_sprite(STAR_RADIUS)
        for index in range(round_state.star_count):
            center = self.star_center(round_state, index)
            connected = index in round_state.connected
            is_next = (not celebrating) and index == round_state.next_star

            if connected:
                sprite_rect = sprite.get_rect(center=center)
                surface.blit(sprite, sprite_rect)
            else:
                dim = pygame.Surface((STAR_RADIUS * 2, STAR_RADIUS * 2), pygame.SRCALPHA)
                base_alpha = 150
                if is_next:
                    base_alpha = 190 + round(60 * pulse)
                pygame.draw.circle(
                    dim,
                    (220, 228, 255, base_alpha),
                    (STAR_RADIUS, STAR_RADIUS),
                    STAR_RADIUS // 2 + 2,
                )
                surface.blit(dim, dim.get_rect(center=center))
                if is_next:
                    # Pulsing invitation halo: the next action is obvious.
                    halo_radius = STAR_RADIUS + 8 + round(8 * pulse)
                    pygame.draw.circle(
                        surface,
                        (255, 236, 150),
                        center,
                        halo_radius,
                        width=4,
                    )

            # Big number label: the primary pre-reader instruction channel.
            number_color = (30, 34, 60) if connected else (255, 255, 255)
            label_size = 26 if connected else 30
            label = self.typography.font(FontRole.DISPLAY, label_size).render(
                str(index + 1), True, number_color
            )
            surface.blit(label, label.get_rect(center=center))

            # Wrong tap feedback: soft wobble ring on the mistaken star.
            if wrong_star == index and wrong_age < 0.6:
                wobble = math.sin(wrong_age * 26) * 5 * (1.0 - wrong_age / 0.6)
                offset_center = (center[0] + round(wobble), center[1])
                pygame.draw.circle(
                    surface,
                    (255, 170, 150),
                    offset_center,
                    STAR_TAP_RADIUS - 8,
                    width=4,
                )

        # Celebration: whole figure glows and breathes.
        if celebrating:
            glow_alpha = 120 + round(70 * pulse)
            glow = pygame.Surface(size, pygame.SRCALPHA)
            for index in range(round_state.star_count):
                center = self.star_center(round_state, index)
                pygame.draw.circle(glow, (255, 240, 170, glow_alpha), center, STAR_RADIUS + 14)
            surface.blit(glow, (0, 0))
            if name_text:
                self._draw_name_banner(surface, name_text)

        if show_next:
            self._draw_next_button(surface, hovered_next)

        self._draw_leo(surface, happy=leo_happy, now=now)
        self._draw_fact_button(surface, now=now)
        if fact_text:
            self._draw_fact_bubble(surface, fact_text)

    def _draw_name_banner(self, surface: pygame.Surface, name_text: str) -> None:
        font = self.typography.font(FontRole.DISPLAY, 34)
        label = font.render(name_text, True, (36, 44, 84))
        banner = pygame.Surface(
            (label.get_width() + 48, label.get_height() + 22), pygame.SRCALPHA
        )
        banner_rect = banner.get_rect()
        pygame.draw.rect(banner, (253, 250, 240, 238), banner_rect, border_radius=18)
        pygame.draw.rect(banner, (186, 214, 255, 255), banner_rect, width=3, border_radius=18)
        banner.blit(label, label.get_rect(center=banner_rect.center))
        surface.blit(banner, banner.get_rect(center=(SKY_RECT.centerx, SKY_RECT.top + 34)))

    def _draw_next_button(self, surface: pygame.Surface, hovered: bool) -> None:
        rect = NEXT_BUTTON_RECT.inflate(10 if hovered else 0, 10 if hovered else 0)
        rect.center = NEXT_BUTTON_RECT.center
        pygame.draw.rect(surface, (34, 197, 94), rect, border_radius=34)
        pygame.draw.rect(surface, (255, 255, 255), rect, width=4, border_radius=34)
        # Draw the play arrow as a polygon: the UI font has no triangle glyph.
        center = rect.center
        size = 26
        points = (
            (center[0] - size // 2 + 4, center[1] - size),
            (center[0] - size // 2 + 4, center[1] + size),
            (center[0] + size + 4, center[1]),
        )
        pygame.draw.polygon(surface, (255, 255, 255), points)

    def _draw_leo(self, surface: pygame.Surface, *, happy: bool, now: float) -> None:
        blink = (now % 4.2) < 0.16
        if happy:
            variant = "happy"
        elif blink:
            variant = "blink"
        else:
            variant = "default"
        frame = self._leo(variant)
        bob = round(math.sin(now * 1.6) * 3)
        surface.blit(frame, frame.get_rect(center=(LEO_CENTER[0], LEO_CENTER[1] + bob)))

    def _draw_fact_button(self, surface: pygame.Surface, *, now: float) -> None:
        pulse = 0.5 + 0.5 * math.sin(now * 2.2)
        radius = FACT_BUTTON_RADIUS + round(2 * pulse)
        pygame.draw.circle(surface, (250, 246, 235), FACT_BUTTON_CENTER, radius)
        pygame.draw.circle(surface, (234, 179, 8), FACT_BUTTON_CENTER, radius, width=4)
        icon_size = FACT_BUTTON_RADIUS
        icon = self._ensure_fact_icon(icon_size)
        surface.blit(icon, icon.get_rect(center=FACT_BUTTON_CENTER))

    def _draw_fact_bubble(self, surface: pygame.Surface, fact_text: str) -> None:
        font = self.typography.font(FontRole.BODY, 22)
        wrapped = self._wrap(fact_text, font, 560)
        line_height = font.get_linesize()
        bubble_w = max(font.size(line)[0] for line in wrapped) + 44
        bubble_h = line_height * len(wrapped) + 30
        bubble = pygame.Surface((bubble_w, bubble_h), pygame.SRCALPHA)
        rect = bubble.get_rect()
        pygame.draw.rect(bubble, (253, 250, 240, 242), rect, border_radius=20)
        pygame.draw.rect(bubble, (101, 119, 170, 255), rect, width=3, border_radius=20)
        for i, line in enumerate(wrapped):
            rendered = font.render(line, True, (44, 52, 90))
            bubble.blit(rendered, (22, 15 + i * line_height))
        bubble_center = (
            min(FACT_BUTTON_CENTER[0] - 40, REFERENCE_WIDTH - bubble_w // 2 - 20),
            SKY_RECT.bottom - bubble_h // 2 - 8,
        )
        surface.blit(bubble, bubble.get_rect(center=bubble_center))

    def _wrap(self, text: str, font: Any, max_width: int) -> tuple[str, ...]:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return tuple(lines) or (text,)
