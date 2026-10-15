"""Cast feedback for Activities: one grammar for correct / try-again (ADR 0037).

Every Activity reacts the same way: a canonical cast friend cheers
(``pose_cheer``) for a correct answer and thinks gently (``pose_think``) for a
try-again, then returns to an idle expression. Sound and speech stay owned by
the Activity through optional hooks; this module only owns the presentation.

Poses are shared catalogue art (``character.<id>`` variants), scaled once at
construction. Motion is a tiny hop/sway computed from the clock and applied as
a blit offset, so drawing never scales, rotates or renders text.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
import math
import time

import pygame

from .activity_controls import ControlArt

CANONICAL_CAST = ("lilli", "leo", "flash", "dani", "tito", "momo")


class CastPose(StrEnum):
    """Presentation states of a ``CastFeedback`` friend."""

    IDLE = "idle"
    CHEER = "cheer"
    THINK = "think"


_POSE_VARIANTS = {
    CastPose.CHEER: "pose_cheer",
    CastPose.THINK: "pose_think",
}


class CastFeedback:
    """Show one canonical cast friend reacting to Activity results.

    ``correct()`` and ``try_again()`` switch to the matching pose for
    ``hold_seconds`` and call the Activity-owned sound hook, if any. ``update``
    returns whether the presentation changed so event-driven Activities can
    invalidate only when needed; ``animating`` tells them when to keep drawing.
    """

    HOP_SECONDS = 0.42

    def __init__(
        self,
        character: str,
        *,
        height: int,
        art: ControlArt,
        idle_variant: str = "happy",
        hold_seconds: float = 1.6,
        clock: Callable[[], float] = time.monotonic,
        on_correct: Callable[[], object] | None = None,
        on_try_again: Callable[[], object] | None = None,
    ) -> None:
        if character not in CANONICAL_CAST:
            raise ValueError(f"unknown canonical cast character: {character!r}")
        if height < 16:
            raise ValueError("cast feedback height is too small")
        if hold_seconds <= 0:
            raise ValueError("hold_seconds must be positive")
        self.character = character
        self._clock = clock
        self._hold = float(hold_seconds)
        self._on_correct = on_correct
        self._on_try_again = on_try_again
        asset_id = f"character.{character}"
        self._surfaces: dict[CastPose, pygame.Surface | None] = {
            CastPose.IDLE: art.image(asset_id, int(height), variant=idle_variant),
            CastPose.CHEER: art.image(asset_id, int(height), variant=_POSE_VARIANTS[CastPose.CHEER]),
            CastPose.THINK: art.image(asset_id, int(height), variant=_POSE_VARIANTS[CastPose.THINK]),
        }
        self._height = int(height)
        self._pose = CastPose.IDLE
        self._since = clock()
        self._last_offset = (0, 0)

    @property
    def pose(self) -> CastPose:
        return self._pose

    @property
    def available(self) -> bool:
        return self._surfaces[CastPose.IDLE] is not None

    @property
    def animating(self) -> bool:
        return self._pose is not CastPose.IDLE

    def correct(self) -> None:
        """React to a correct answer (cheer + optional Activity sound hook)."""

        self._set(CastPose.CHEER)
        if self._on_correct is not None:
            self._on_correct()

    def try_again(self) -> None:
        """React to a wrong answer with a gentle think pose (never a 'fail')."""

        self._set(CastPose.THINK)
        if self._on_try_again is not None:
            self._on_try_again()

    def reset(self) -> None:
        self._set(CastPose.IDLE)

    def update(self) -> bool:
        """Advance time; return True when the drawn frame would change."""

        if self._pose is CastPose.IDLE:
            return False
        if self._clock() - self._since >= self._hold:
            self._set(CastPose.IDLE)
            return True
        offset = self._offset()
        if offset != self._last_offset:
            self._last_offset = offset
            return True
        return False

    def draw(self, target: pygame.Surface, midbottom: tuple[int, int]) -> None:
        surface = self._surfaces.get(self._pose) or self._surfaces[CastPose.IDLE]
        if surface is None:
            return
        dx, dy = self._offset()
        rect = surface.get_rect(midbottom=(midbottom[0] + dx, midbottom[1] + dy))
        target.blit(surface, rect)

    def _set(self, pose: CastPose) -> None:
        self._pose = pose
        self._since = self._clock()
        self._last_offset = (0, 0)

    def _offset(self) -> tuple[int, int]:
        elapsed = self._clock() - self._since
        if self._pose is CastPose.CHEER and elapsed < self.HOP_SECONDS:
            return (0, -int(round(math.sin(math.pi * elapsed / self.HOP_SECONDS) * self._height * 0.09)))
        if self._pose is CastPose.THINK and elapsed < self.HOP_SECONDS * 1.5:
            return (int(round(math.sin(2 * math.pi * elapsed / (self.HOP_SECONDS * 1.5)) * self._height * 0.025)), 0)
        return (0, 0)


__all__ = ["CANONICAL_CAST", "CastFeedback", "CastPose"]
