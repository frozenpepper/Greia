"""Frame composition for Mondo Contrari.

One frame = the cached meadow backdrop (one blit) -> the current pair scene
-> short library FX flipbooks -> Flash (canonical cast, shared feedback
grammar). Kit controls are drawn afterwards by the app. There is no text in
the play area: the concept word is spoken, and its caption appears in the
kit caption only after the child has made it happen.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose
from greia_platform.pygame_blit import PreparedSurfaces

if __package__:
    from .contrari_art import ContrariArt
    from .contrari_layout import FLASH_MIDBOTTOM
    from .contrari_scenes import PairScene
else:
    from contrari_art import ContrariArt
    from contrari_layout import FLASH_MIDBOTTOM
    from contrari_scenes import PairScene

FX_SECONDS: Final = 0.5
MAX_FX: Final = 16


class ContrariCast:
    """Flash with the shared feedback grammar plus a pointing hint pose.

    ``CastFeedback`` owns cheer (correct) and think (try again); this wrapper
    adds ``point`` for prompts and idle hints, drawn only while the feedback
    friend is idle so the grammar stays unambiguous.
    """

    def __init__(self, feedback: CastFeedback, point: pygame.Surface | None, clock: Callable[[], float]) -> None:
        self.feedback = feedback
        self._point = point
        self._fast = PreparedSurfaces(max_entries=2)  # RLE copy of the pose (opaque targets only)
        self._clock = clock
        self._point_until = 0.0

    @property
    def pose(self) -> CastPose:
        return self.feedback.pose

    @property
    def pointing(self) -> bool:
        return self._point is not None and self._clock() < self._point_until

    @property
    def animating(self) -> bool:
        return self.feedback.animating or self.pointing

    def point(self, seconds: float = 1.8) -> None:
        self._point_until = self._clock() + seconds

    def correct(self) -> None:
        self._point_until = 0.0
        self.feedback.correct()

    def try_again(self) -> None:
        self._point_until = 0.0
        self.feedback.try_again()

    def reset(self) -> None:
        self._point_until = 0.0
        self.feedback.reset()

    def update(self) -> bool:
        was_pointing = self._point_until > 0.0
        changed = self.feedback.update()
        if was_pointing and not self.pointing:
            self._point_until = 0.0
            changed = True
        return changed

    def draw(self, target: pygame.Surface, midbottom: tuple[int, int]) -> None:
        if self.pointing and self.feedback.pose is CastPose.IDLE and self._point is not None:
            target.blit(self._fast.for_target(self._point, target), self._point.get_rect(midbottom=midbottom))
            return
        self.feedback.draw(target, midbottom)


@dataclass(frozen=True, slots=True)
class FxBurst:
    name: str
    position: tuple[int, int]
    start: float


class FxPlayer:
    """Bounded queue of short library FX flipbooks (``fx.*`` frames)."""

    def __init__(self, art: ContrariArt, clock: Callable[[], float]) -> None:
        self._art = art
        self._clock = clock
        self._bursts: deque[FxBurst] = deque(maxlen=MAX_FX)

    def add(self, name: str, position: tuple[int, int], delay: float = 0.0) -> None:
        self._bursts.append(FxBurst(name, (int(position[0]), int(position[1])), self._clock() + delay))

    def clear(self) -> None:
        self._bursts.clear()

    def active(self, now: float) -> bool:
        return any(burst.start + FX_SECONDS > now for burst in self._bursts)

    def prune(self, now: float) -> None:
        while self._bursts and self._bursts[0].start + FX_SECONDS <= now:
            self._bursts.popleft()

    def draw(self, surface: pygame.Surface, now: float) -> None:
        for burst in self._bursts:
            elapsed = now - burst.start
            if elapsed < 0 or elapsed >= FX_SECONDS:
                continue
            frames = self._art.fx_frames(burst.name)
            if not frames:
                continue
            frame = frames[min(len(frames) - 1, int(elapsed / FX_SECONDS * len(frames)))]
            surface.blit(frame, frame.get_rect(center=burst.position))


class ContrariRenderer:
    """Compose the play frame (controls are drawn by the app's kit layer)."""

    def __init__(self, art: ContrariArt, cast: ContrariCast, fx: FxPlayer, *, clock: Callable[[], float]) -> None:
        self.art = art
        self.cast = cast
        self.fx = fx
        self._clock = clock

    def draw(self, surface: pygame.Surface, scene: PairScene | None) -> None:
        now = self._clock()
        surface.blit(self.art.background, (0, 0))
        if scene is not None:
            scene.draw(surface, now)
        self.fx.draw(surface, now)
        self.cast.draw(surface, FLASH_MIDBOTTOM)


__all__ = ["ContrariCast", "ContrariRenderer", "FxBurst", "FxPlayer"]
