"""Il Viaggio del Delfino — Tito, the journey's companion (canonical cast).

Tito slides up in the bottom-left corner only while he has something to do:
welcoming the swimmer, telling a recorded fact when a sea friend is met,
pointing at what to swim to next (``pose_point``), or reacting through the
shared feedback grammar (``CastFeedback``: ``pose_cheer`` / gentle
``pose_think``). Every pose is scaled once; motion is a blit offset.
"""

from __future__ import annotations

from collections.abc import Callable
import math
import time

import pygame

from greia_platform.activity_controls import ControlArt
from greia_platform.activity_feedback import CastFeedback


class DelfinoCast:
    """Show/hide Tito with a short slide and route his poses."""

    CHARACTER = "tito"
    SLIDE_SECONDS = 0.35
    POINT_SECONDS = 2.2
    WAVE_SECONDS = 1.0

    def __init__(
        self,
        art: ControlArt,
        *,
        height: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._clock = clock
        self._height = int(height)
        # The app owns speech (approved recordings); the cast owns presentation.
        self.feedback = CastFeedback(self.CHARACTER, height=height, art=art, clock=clock)
        asset = f"character.{self.CHARACTER}"
        self._point = art.image(asset, int(height), variant="pose_point")
        self._wave = art.image(asset, int(height), variant="pose_wave")
        self._wanted = False
        self._shown = 0.0  # 0 hidden .. 1 fully shown
        self._point_until = 0.0
        self._wave_until = 0.0
        self._talk_until = 0.0

    @property
    def visible(self) -> bool:
        return self._shown > 0.0

    @property
    def talking(self) -> bool:
        return self._clock() < self._talk_until

    @property
    def pointing(self) -> bool:
        return self._clock() < self._point_until

    @property
    def animating(self) -> bool:
        """True while Tito's picture changes on its own (slide, pose, talk bob)."""

        if self.feedback.animating or self.talking or self.pointing or self._clock() < self._wave_until:
            return True
        return self._shown < 1.0 if self._wanted else self._shown > 0.0

    def present(self, wanted: bool) -> None:
        """Keep Tito on screen (picker, welcome) even when he is idle."""

        self._wanted = bool(wanted)

    def talk(self, seconds: float) -> None:
        """Tito speaks: a wave hello, then a gentle talking bob."""

        now = self._clock()
        self.feedback.reset()
        self._point_until = 0.0
        self._wave_until = now + self.WAVE_SECONDS
        self._talk_until = now + max(0.0, float(seconds))

    def stop_talking(self) -> None:
        self._talk_until = 0.0
        self._wave_until = 0.0

    def wave(self) -> None:
        self.feedback.reset()
        self._wave_until = self._clock() + self.WAVE_SECONDS

    def cheer(self) -> None:
        self._point_until = 0.0
        self._wave_until = 0.0
        self.feedback.correct()

    def think(self) -> None:
        self._point_until = 0.0
        self.feedback.try_again()

    def point(self, seconds: float | None = None) -> None:
        self.feedback.reset()
        self._wave_until = 0.0
        self._point_until = self._clock() + (self.POINT_SECONDS if seconds is None else seconds)

    def update(self, dt: float) -> None:
        """Advance the slide by one simulation step (``dt`` seconds)."""

        dt = max(0.0, min(0.1, float(dt)))
        busy = (
            self._wanted
            or self.feedback.animating
            or self.talking
            or self.pointing
            or self._clock() < self._wave_until
        )
        target = 1.0 if busy else 0.0
        step = dt / self.SLIDE_SECONDS
        if self._shown < target:
            self._shown = min(target, self._shown + step)
        elif self._shown > target:
            self._shown = max(target, self._shown - step)
        self.feedback.update()

    def _drop(self) -> int:
        return int((1.0 - self._shown) ** 2 * (self._height + 8))

    def draw(self, surface: pygame.Surface, midbottom: tuple[int, int]) -> None:
        if self._shown <= 0.0:
            return
        now = self._clock()
        anchor = (midbottom[0], midbottom[1] + self._drop())
        if self.feedback.animating:
            self.feedback.draw(surface, anchor)
            return
        pose: pygame.Surface | None = None
        if now < self._point_until:
            pose = self._point
        elif now < self._wave_until:
            pose = self._wave
        if pose is not None:
            surface.blit(pose, pose.get_rect(midbottom=anchor))
            return
        if self.talking:
            anchor = (anchor[0], anchor[1] - int(abs(math.sin(now * 7.0)) * 4))
        self.feedback.draw(surface, anchor)


__all__ = ["DelfinoCast"]
