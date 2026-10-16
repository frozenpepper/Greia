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
from .frame_governor import FramePolicy

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


class IdleHintScheduler:
    """Back-off schedule for idle hints: a few, then silence until input.

    Hints exist for a child who is stuck, not to nag one who walked away, and
    each hint animates at full frame rate (costly on the reference floor).  The
    schedule is therefore bounded: hint 1 after ``gaps[0]`` quiet seconds,
    hint 2 a further ``gaps[1]``, hint 3 a further ``gaps[2]`` (default 6 / 12 /
    24 s), then nothing until the next child input calls ``reset``.

    The Activity keeps its own graduated hint content and uses the returned
    1-based step to pick it (point, then demonstrate, ...).  ``poll`` is called
    from ``step()``; it never sleeps or draws.  ``since`` lets an Activity that
    tracks a "quiet since" stamp (speech ended, a round started) delay the next
    hint without restarting the schedule.
    """

    DEFAULT_GAPS: tuple[float, ...] = (6.0, 12.0, 24.0)

    def __init__(
        self,
        gaps: tuple[float, ...] = DEFAULT_GAPS,
        *,
        now: float = 0.0,
        policy: FramePolicy | None = None,
    ) -> None:
        if not gaps or any(gap <= 0.0 for gap in gaps):
            raise ValueError("idle hint gaps must be positive")
        self._gaps = tuple(float(gap) for gap in gaps)
        self._policy = policy if policy is not None else FramePolicy.from_environment()
        self._anchor = float(now)
        self._count = 0

    @property
    def count(self) -> int:
        """Hints fired since the last child input (0 when none)."""

        return self._count

    @property
    def max_hints(self) -> int:
        return len(self._gaps)

    @property
    def exhausted(self) -> bool:
        return self._count >= len(self._gaps)

    def reset(self, now: float) -> None:
        """A child input (or a new round) restarts the whole schedule."""

        self._anchor = float(now)
        self._count = 0

    def is_due(self, now: float, since: float | None = None, *, patience: float = 1.0) -> bool:
        """True when the next step's wait has elapsed (does not consume it).

        ``patience`` stretches every gap (e.g. 1.5 for a harder level whose
        child needs longer to think) without changing the back-off shape.

        Use with ``fire`` when the Activity must first check that a hint
        makes sense (a target exists) before spending one of the few steps.
        """

        if self._count >= len(self._gaps):
            return False
        anchor = self._anchor if since is None else max(self._anchor, since)
        return now - anchor >= self._gaps[self._count] * patience

    def fire(self, now: float) -> int:
        """Consume the next step and return its 1-based number."""

        if self._count >= len(self._gaps):
            raise RuntimeError("idle hint schedule is exhausted")
        self._count += 1
        self._anchor = float(now)
        return self._count

    def poll(self, now: float, since: float | None = None, *, patience: float = 1.0) -> int:
        """Return the new 1-based hint step when one is due, otherwise 0.

        The wait for the next step is measured from the later of the previous
        hint (or the last reset) and ``since``.
        """

        return self.fire(now) if self.is_due(now, since, patience=patience) else 0

    def animation_seconds(self, nominal: float) -> float:
        """Hint animation length, shortened on the low-end frame profile."""

        return self._policy.hint_animation_seconds(nominal)


__all__ = ["CANONICAL_CAST", "CastFeedback", "CastPose", "IdleHintScheduler"]
