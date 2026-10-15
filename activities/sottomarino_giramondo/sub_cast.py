"""Sottomarino Giramondo — Captain Leo (canonical cast).

Leo already voices the submarine's recorded lines; now he is also seen. He
pops up beside the porthole only while he has something to do: waving hello
at the start, giving an order (pointing at the right instrument once the
hint is due), telling a sea fact, or reacting (``CastFeedback``:
``pose_cheer``). Every pose is scaled once; motion is a blit offset.
"""

from __future__ import annotations

from collections.abc import Callable
import math
import time

import pygame

from greia_platform.activity_controls import ControlArt
from greia_platform.activity_feedback import CastFeedback


class SubmarineCaptain:
    """Show/hide Leo with a short slide and route his poses."""

    CHARACTER = "leo"
    SLIDE_SECONDS = 0.35
    WAVE_SECONDS = 2.2

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
        self._pointing = False
        self._shown = 0.0  # 0 hidden .. 1 fully shown
        self._wave_until = clock() + self.WAVE_SECONDS
        self._talk_until = 0.0

    @property
    def visible(self) -> bool:
        return self._shown > 0.0

    @property
    def pointing(self) -> bool:
        return self._pointing and not self.feedback.animating

    @property
    def talking(self) -> bool:
        return self._clock() < self._talk_until

    def present(self, wanted: bool, *, pointing: bool = False) -> None:
        """Stay up while an order waits (pointing once its hint is due)."""

        self._wanted = bool(wanted)
        self._pointing = bool(pointing) and self._wanted

    def talk(self, seconds: float) -> None:
        self._talk_until = self._clock() + max(0.0, float(seconds))

    def cheer(self) -> None:
        self._wave_until = 0.0
        self.feedback.correct()

    def update(self, dt: float) -> None:
        dt = max(0.0, min(0.1, float(dt)))
        now = self._clock()
        busy = self._wanted or self.feedback.animating or self.talking or now < self._wave_until
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
        if self.pointing:
            pose = self._point
        elif now < self._wave_until:
            pose = self._wave
        if pose is not None:
            surface.blit(pose, pose.get_rect(midbottom=anchor))
            return
        if self.talking:
            anchor = (anchor[0], anchor[1] - int(abs(math.sin(now * 7.0)) * 4))
        self.feedback.draw(surface, anchor)


__all__ = ["SubmarineCaptain"]
