"""Prepared opaque completion presentation for low-resource Pygame Activities.

Victory/completion is a terminal Activity state, not a translucent overlay that
should keep the live game simulating and repainting underneath. This module owns
the reusable Pygame presentation half of that contract:

* the full logical frame is opaque;
* finite text and geometry are prepared only when content changes;
* repeated ``draw`` calls are one opaque blit;
* the primary action hit target is stable and queryable by the Activity.

The Activity lifecycle owner remains responsible for stopping active simulation
and for invalidating/re-preparing the completion screen only when its semantic
content actually changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Protocol

import pygame

from .typography import FontRole, GreiaTypography


RgbColor = tuple[int, int, int]


class CompletionTypography(Protocol):
    """Narrow rendering seam used by the prepared completion screen."""

    def render(
        self,
        text: str,
        role: FontRole,
        size: int,
        color: RgbColor,
    ) -> pygame.Surface: ...


@dataclass(frozen=True, slots=True)
class CompletionPalette:
    """Opaque colors for one completion presentation."""

    background: RgbColor = (30, 41, 59)
    panel: RgbColor = (255, 252, 245)
    panel_border: RgbColor = (234, 179, 8)
    title: RgbColor = (180, 83, 9)
    body: RgbColor = (71, 85, 105)
    primary: RgbColor = (34, 197, 94)
    primary_text: RgbColor = (255, 255, 255)
    achievement: RgbColor = (234, 179, 8)
    achievement_inner: RgbColor = (254, 240, 138)


@dataclass(frozen=True, slots=True)
class CompletionContent:
    """Semantic content that determines one prepared terminal frame."""

    title: str
    primary_label: str
    body_lines: tuple[str, ...] = ()
    achievement_count: int = 0

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("completion title must not be empty")
        if not self.primary_label.strip():
            raise ValueError("completion primary label must not be empty")
        if self.achievement_count < 0:
            raise ValueError("completion achievement_count must be >= 0")


class PygameCompletionScreen:
    """Prepare and replay one opaque low-cost Activity completion frame.

    ``prepare`` is semantic invalidation: it rebuilds only when content or palette
    changes. ``draw`` never creates fonts, text surfaces, alpha overlays or other
    frame-sized resources. The retained frame is intentionally bounded to one
    logical surface.
    """

    DEFAULT_WIDTH: Final = 1024
    DEFAULT_HEIGHT: Final = 600

    def __init__(
        self,
        typography: CompletionTypography | GreiaTypography,
        *,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        palette: CompletionPalette = CompletionPalette(),
        primary_rect: pygame.Rect | None = None,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("completion dimensions must be positive")
        self._typography = typography
        self._width = int(width)
        self._height = int(height)
        self._palette = palette
        self._content: CompletionContent | None = None
        self._frame: pygame.Surface | None = None
        self._primary_rect = (
            primary_rect.copy() if primary_rect is not None else self._compute_primary_rect()
        )
        if not pygame.Rect(0, 0, self._width, self._height).contains(self._primary_rect):
            raise ValueError("completion primary_rect must fit inside logical frame")

    @property
    def is_prepared(self) -> bool:
        return self._frame is not None

    @property
    def primary_rect(self) -> pygame.Rect:
        return self._primary_rect.copy()

    @property
    def prepared_surface(self) -> pygame.Surface | None:
        """Expose the retained surface read-only for diagnostics/tests."""

        return self._frame

    def prepare(
        self,
        content: CompletionContent,
        *,
        palette: CompletionPalette | None = None,
    ) -> None:
        """Prepare one terminal frame, rebuilding only for semantic changes."""

        resolved_palette = palette or self._palette
        if (
            self._frame is not None
            and self._content == content
            and self._palette == resolved_palette
        ):
            return

        self._palette = resolved_palette
        self._content = content
        self._frame = self._build_frame(content, resolved_palette)

    def clear(self) -> None:
        """Release terminal content when the Activity restarts."""

        self._content = None
        self._frame = None

    def draw(self, target: pygame.Surface) -> None:
        """Blit the prepared opaque frame to the logical Activity surface."""

        frame = self._frame
        if frame is None:
            raise RuntimeError("completion screen must be prepared before draw")
        target.blit(frame, (0, 0))

    def primary_contains(self, point: tuple[int, int]) -> bool:
        return self._primary_rect.collidepoint(point)

    def _compute_primary_rect(self) -> pygame.Rect:
        button_width = min(320, max(220, self._width // 3))
        button_height = 64
        return pygame.Rect(
            self._width // 2 - button_width // 2,
            self._height // 2 + 92,
            button_width,
            button_height,
        )

    def _build_frame(
        self,
        content: CompletionContent,
        palette: CompletionPalette,
    ) -> pygame.Surface:
        # No SRCALPHA: a completion screen replaces the active game presentation
        # rather than dimming a still-running frame underneath it.
        frame = pygame.Surface((self._width, self._height))
        frame.fill(palette.background)

        card_width = min(560, self._width - 96)
        card_height = min(360, self._height - 96)
        card = pygame.Rect(
            self._width // 2 - card_width // 2,
            self._height // 2 - card_height // 2,
            card_width,
            card_height,
        )
        pygame.draw.rect(frame, palette.panel, card, border_radius=30)
        pygame.draw.rect(frame, palette.panel_border, card, width=5, border_radius=30)

        title = self._typography.render(
            content.title,
            FontRole.DISPLAY,
            32,
            palette.title,
        )
        frame.blit(title, (card.centerx - title.get_width() // 2, card.top + 38))

        body_y = card.top + 100
        for line in content.body_lines[:3]:
            rendered = self._typography.render(
                line,
                FontRole.DISPLAY,
                20,
                palette.body,
            )
            frame.blit(
                rendered,
                (card.centerx - rendered.get_width() // 2, body_y),
            )
            body_y += rendered.get_height() + 8

        count = min(content.achievement_count, 8)
        if count:
            spacing = 46
            total_width = (count - 1) * spacing
            start_x = card.centerx - total_width // 2
            achievement_y = max(body_y + 18, card.centery + 26)
            for index in range(count):
                x = start_x + index * spacing
                pygame.draw.circle(frame, palette.achievement, (x, achievement_y), 18)
                pygame.draw.circle(
                    frame,
                    palette.achievement_inner,
                    (x, achievement_y),
                    8,
                )

        pygame.draw.rect(
            frame,
            palette.primary,
            self._primary_rect,
            border_radius=20,
        )
        label = self._typography.render(
            content.primary_label,
            FontRole.DISPLAY,
            22,
            palette.primary_text,
        )
        frame.blit(
            label,
            (
                self._primary_rect.centerx - label.get_width() // 2,
                self._primary_rect.centery - label.get_height() // 2,
            ),
        )
        return frame


__all__ = [
    "CompletionContent",
    "CompletionPalette",
    "CompletionTypography",
    "PygameCompletionScreen",
]
