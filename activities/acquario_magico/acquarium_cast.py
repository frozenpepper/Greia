"""Acquario Magico — Tito, the aquarium's companion (canonical cast).

Tito only appears while a mission invitation is open or while he is reacting,
so plain free play keeps the whole tank to itself. He uses the shared
``CastFeedback`` grammar (``pose_cheer`` for a found/fed friend) plus the
shared ``pose_point`` variant for graduated hints. Motion is a blit offset;
every pose is scaled once.
"""

from __future__ import annotations

from collections.abc import Callable
import time

import pygame

from greia_platform.activity_controls import ControlArt
from greia_platform.activity_feedback import CastFeedback


class AquariumCast:
    """Show/hide Tito with a short slide and route cheer/point reactions."""

    CHARACTER = "tito"
    SLIDE_SECONDS = 0.35
    POINT_SECONDS = 1.8

    def __init__(
        self,
        art: ControlArt,
        *,
        height: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._clock = clock
        self._art = art
        self._height = int(height)
        # The app owns speech (approved Tito takes); the cast owns presentation.
        self.feedback = CastFeedback(self.CHARACTER, height=height, art=art, clock=clock)
        self._point = art.image(f"character.{self.CHARACTER}", int(height), variant="pose_point")
        self._wanted = False
        self._shown = 0.0  # 0 hidden .. 1 fully shown
        self._point_until = 0.0

    @property
    def visible(self) -> bool:
        return self._shown > 0.0

    @property
    def animating(self) -> bool:
        target = 1.0 if self._wanted else 0.0
        return self._shown != target or self.feedback.animating or self._clock() < self._point_until

    def present(self, wanted: bool) -> None:
        self._wanted = bool(wanted)

    def cheer(self) -> None:
        self._point_until = 0.0
        self.feedback.correct()

    def point(self, seconds: float | None = None) -> None:
        self.feedback.reset()
        self._point_until = self._clock() + (self.POINT_SECONDS if seconds is None else seconds)

    def update(self, dt: float) -> None:
        """Advance the slide by one simulation step (``dt`` seconds)."""

        dt = max(0.0, min(0.1, float(dt)))
        target = 1.0 if (self._wanted or self.feedback.animating) else 0.0
        step = dt / self.SLIDE_SECONDS
        if self._shown < target:
            self._shown = min(target, self._shown + step)
        elif self._shown > target:
            self._shown = max(target, self._shown - step)
        self.feedback.update()

    def draw(self, surface: pygame.Surface, midbottom: tuple[int, int]) -> None:
        if self._shown <= 0.0:
            return
        drop = int((1.0 - self._shown) ** 2 * (self._height + 8))
        anchor = (midbottom[0], midbottom[1] + drop)
        if self._point is not None and self._clock() < self._point_until and not self.feedback.animating:
            surface.blit(self._art.presentable(self._point, surface), self._point.get_rect(midbottom=anchor))
            return
        self.feedback.draw(surface, anchor)


__all__ = ["AquariumCast"]
