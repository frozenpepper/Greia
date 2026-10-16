"""Frame composition and light motion for Momo's Happy Faces.

The renderer only blits prepared surfaces from ``MomoArt``: no scaling, no
decoding and no text rendering per frame. Motion (Momo acting a feeling, the
story card sliding in, FX bursts, a help item flying to Momo) is computed from
the injected clock and applied as offsets.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
import math

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose

if __package__:
    from .momo_art import MomoArt
    from .momo_content import Emotion
    from .momo_layout import CARD_RECT, GUIDE_MIDBOTTOM, momo_head, momo_rect
else:
    from momo_art import MomoArt
    from momo_content import Emotion
    from momo_layout import CARD_RECT, GUIDE_MIDBOTTOM, momo_head, momo_rect

MAX_FX = 16
MAX_FLIGHTS = 4
CARD_SLIDE = 0.45
PULSE_SECONDS = 0.9

# How Momo "acts" each feeling: (seconds, FX name or None, FX size).
ACTS: dict[str, tuple[float, str | None, int]] = {
    Emotion.HAPPY.value: (0.9, "confetti", 280),
    Emotion.SAD.value: (1.3, None, 0),
    Emotion.ANGRY.value: (0.8, "dust_puff", 110),
    Emotion.SURPRISED.value: (0.6, "star_burst", 260),
    Emotion.SLEEPY.value: (2.2, None, 0),
    Emotion.SILLY.value: (1.1, "sparkle", 220),
    "appear": (0.3, None, 0),
}


@dataclass(slots=True)
class FxBurst:
    name: str
    center: tuple[int, int]
    start: float
    size: int
    duration: float = 0.9
    rise: int = 18
    behind: bool = False  # drawn behind Momo (his own feeling FX never hide his face)


@dataclass(slots=True)
class Flight:
    surface: pygame.Surface
    start_pos: tuple[int, int]
    end_pos: tuple[int, int]
    start: float
    duration: float = 0.7


@dataclass(slots=True)
class FrameView:
    """What the current frame shows (decided by the app, drawn here)."""

    momo: str | None                       # an Emotion value, "silhouette" or None
    momo_midbottom: tuple[int, int]
    momo_height: int
    story_id: str | None = None
    show_guide: bool = True


class SceneMotion:
    """Bounded, clock-driven presentation state (never gameplay state)."""

    def __init__(self, clock: Callable[[], float]) -> None:
        self._clock = clock
        self.fx: deque[FxBurst] = deque(maxlen=MAX_FX)
        self.flights: deque[Flight] = deque(maxlen=MAX_FLIGHTS)
        self.act_kind: str | None = None
        self.act_start = 0.0
        self.card_start: float | None = None
        self.card_pulse: float | None = None
        self.momo_pulse: float | None = None
        self.glow_id: str | None = None
        self.glow_until = 0.0
        self.wobble_id: str | None = None
        self.wobble_start = 0.0
        self.zzz_start: float | None = None

    def clear(self) -> None:
        self.fx.clear()
        self.flights.clear()
        self.act_kind = None
        self.card_start = None
        self.card_pulse = None
        self.momo_pulse = None
        self.glow_id = None
        self.wobble_id = None
        self.zzz_start = None

    def act(self, kind: str, head: tuple[int, int], *, fx: bool = True) -> None:
        """Momo acts a feeling: a motion plus (optionally) the matching library FX."""

        now = self._clock()
        self.act_kind = kind
        self.act_start = now
        _, fx_name, size = ACTS.get(kind, (0.5, None, 0))
        if fx and fx_name is not None:
            if kind == Emotion.ANGRY.value:
                for dx in (-96, 96):
                    self.add_fx(fx_name, (head[0] + dx, head[1] - 44), size, behind=True)
            else:
                self.add_fx(fx_name, (head[0], head[1] - 40), size, behind=True)
        if kind == Emotion.SLEEPY.value:
            self.zzz_start = now

    def add_fx(
        self,
        name: str,
        center: tuple[int, int],
        size: int,
        *,
        delay: float = 0.0,
        behind: bool = False,
    ) -> None:
        self.fx.append(FxBurst(name, (int(center[0]), int(center[1])), self._clock() + delay, size, behind=behind))

    def fly(self, flight: Flight) -> None:
        self.flights.append(flight)

    def wobble(self, control_id: str) -> None:
        self.wobble_id = control_id
        self.wobble_start = self._clock()

    def glow(self, control_id: str, seconds: float) -> None:
        self.glow_id = control_id
        self.glow_until = self._clock() + seconds

    def momo_offset(self) -> tuple[int, int]:
        kind = self.act_kind
        if kind is None:
            return (0, 0)
        t = self._clock() - self.act_start
        duration = ACTS.get(kind, (0.5, None, 0))[0]
        if t >= duration or t < 0:
            return (0, 0)
        if kind == Emotion.HAPPY.value:
            return (0, -int(abs(math.sin(math.pi * t / 0.45)) * 22))
        if kind == Emotion.SAD.value:
            return (0, int(math.sin(math.pi * t / duration) * 9))
        if kind == Emotion.ANGRY.value:
            return (int(math.sin(2 * math.pi * t * 9) * 7 * (1 - t / duration)), 0)
        if kind == Emotion.SURPRISED.value:
            return (0, -int(math.sin(math.pi * t / duration) * 30))
        if kind == Emotion.SLEEPY.value:
            return (int(math.sin(2 * math.pi * t / 1.1) * 5), int(math.sin(math.pi * t / duration) * 5))
        if kind == Emotion.SILLY.value:
            return (int(math.sin(2 * math.pi * t * 3) * 11 * (1 - t / duration)), 0)
        if kind == "appear":
            return (0, int(18 * (1 - t / duration)))
        return (0, 0)

    def card_offset(self) -> int:
        if self.card_start is None:
            return 0
        t = self._clock() - self.card_start
        if t >= CARD_SLIDE:
            return 0
        if t < 0:
            return -CARD_RECT.right - 20
        eased = 1 - (1 - t / CARD_SLIDE) ** 3
        return int((-CARD_RECT.right - 20) * (1 - eased))

    def card_bump(self) -> int:
        if self.card_pulse is None:
            return 0
        t = self._clock() - self.card_pulse
        if not 0 <= t < PULSE_SECONDS:
            return 0
        return -int(abs(math.sin(math.pi * t / (PULSE_SECONDS / 2))) * 10)

    def wobble_offset(self, control_id: str) -> int:
        if self.wobble_id != control_id:
            return 0
        t = self._clock() - self.wobble_start
        if t >= 0.45:
            return 0
        return int(9 * (1 - t / 0.45) * (1 if int(t * 40) % 2 else -1))

    def glowing(self, control_id: str) -> bool:
        return self.glow_id == control_id and self._clock() < self.glow_until

    def active(self) -> bool:
        now = self._clock()
        if self.act_kind is not None and now - self.act_start < ACTS.get(self.act_kind, (0.5, None, 0))[0]:
            return True
        if self.zzz_start is not None and now - self.zzz_start < 2.4:
            return True
        if any(now < burst.start + burst.duration for burst in self.fx):
            return True
        if any(now < flight.start + flight.duration for flight in self.flights):
            return True
        if self.card_start is not None and now - self.card_start < CARD_SLIDE:
            return True
        if self.card_pulse is not None and now - self.card_pulse < PULSE_SECONDS:
            return True
        if self.wobble_id is not None and now - self.wobble_start < 0.45:
            return True
        return self.glow_id is not None and now < self.glow_until

    def prune(self) -> None:
        now = self._clock()
        while self.fx and now >= self.fx[0].start + self.fx[0].duration:
            self.fx.popleft()
        while self.flights and now >= self.flights[0].start + self.flights[0].duration:
            self.flights.popleft()


class GuideCast:
    """The guide friend: shared cheer/think feedback plus a point pose for hints."""

    def __init__(self, feedback: CastFeedback, point: pygame.Surface | None, clock: Callable[[], float]) -> None:
        self.feedback = feedback
        self._point = point
        self._clock = clock
        self._point_until = 0.0

    @property
    def pose(self) -> CastPose:
        return self.feedback.pose

    @property
    def pointing(self) -> bool:
        return self._clock() < self._point_until and self.feedback.pose is CastPose.IDLE

    @property
    def animating(self) -> bool:
        return self.feedback.animating or self.pointing

    def correct(self) -> None:
        self._point_until = 0.0
        self.feedback.correct()

    def try_again(self) -> None:
        self._point_until = 0.0
        self.feedback.try_again()

    def point(self, seconds: float) -> None:
        self.feedback.reset()
        self._point_until = self._clock() + seconds

    def reset(self) -> None:
        self._point_until = 0.0
        self.feedback.reset()

    def update(self) -> bool:
        changed = self.feedback.update()
        if self._point_until and self._clock() >= self._point_until:
            self._point_until = 0.0
            changed = True
        return changed

    def draw(self, surface: pygame.Surface) -> None:
        if self.pointing and self._point is not None:
            bob = int(math.sin((self._point_until - self._clock()) * 7.0) * 3)
            surface.blit(self._point, self._point.get_rect(midbottom=(GUIDE_MIDBOTTOM[0], GUIDE_MIDBOTTOM[1] + bob)))
            return
        self.feedback.draw(surface, GUIDE_MIDBOTTOM)


class MomoRenderer:
    """Compose one frame from prepared art (blits only)."""

    def __init__(self, art: MomoArt, guide: GuideCast, motion: SceneMotion, clock: Callable[[], float]) -> None:
        self.art = art
        self.guide = guide
        self.motion = motion
        self._clock = clock

    def draw(self, surface: pygame.Surface, view: FrameView) -> None:
        surface.blit(self.art.background, (0, 0))
        if view.story_id is not None:
            card = self.art.story_card(view.story_id)
            if card is not None:
                rect = CARD_RECT.move(self.motion.card_offset(), self.motion.card_bump())
                surface.blit(card, rect)
        self._draw_fx(surface, behind=True)
        self._draw_momo(surface, view)
        self._draw_zzz(surface, view)
        if view.show_guide:
            self.guide.draw(surface)

    def draw_overlay(self, surface: pygame.Surface) -> None:
        """FX bursts and flying help items, above the answer tiles."""

        self._draw_fx(surface, behind=False)
        self._draw_flights(surface)

    def _draw_momo(self, surface: pygame.Surface, view: FrameView) -> None:
        if view.momo is None:
            return
        if view.momo == "silhouette":
            image = self.art.silhouette(view.momo_height)
        else:
            image = self.art.momo(view.momo, view.momo_height)
        if image is None:
            return
        dx, dy = self.motion.momo_offset()
        pulse = self.motion.momo_pulse
        if pulse is not None:
            t = self._clock() - pulse
            if 0 <= t < PULSE_SECONDS:
                dy -= int(abs(math.sin(math.pi * t / (PULSE_SECONDS / 2))) * 12)
        rect = momo_rect(view.momo_midbottom, view.momo_height).move(dx, dy)
        surface.blit(image, rect)

    def _draw_fx(self, surface: pygame.Surface, *, behind: bool) -> None:
        now = self._clock()
        for burst in self.motion.fx:
            if burst.behind is not behind:
                continue
            t = now - burst.start
            if t < 0 or t >= burst.duration:
                continue
            frames = self.art.fx_frames(burst.name, burst.size)
            if not frames:
                continue
            progress = t / burst.duration
            frame = frames[min(len(frames) - 1, int(progress * len(frames)))]
            center = (burst.center[0], burst.center[1] - int(burst.rise * progress))
            surface.blit(frame, frame.get_rect(center=center))

    def _draw_zzz(self, surface: pygame.Surface, view: FrameView) -> None:
        start = self.motion.zzz_start
        if start is None or view.momo in (None, "silhouette"):
            return
        t = self._clock() - start
        if not 0 <= t < 2.4:
            return
        head = momo_head(view.momo_midbottom, view.momo_height)
        for index, size in enumerate((34, 44, 56)):
            local = t - index * 0.35
            if local < 0:
                continue
            glyph = self.art.zzz(size)
            x = head[0] + 70 + index * 26 + int(math.sin(local * 3) * 6)
            y = head[1] - 30 - index * 34 - int(local * 16)
            surface.blit(glyph, glyph.get_rect(center=(x, y)))

    def _draw_flights(self, surface: pygame.Surface) -> None:
        now = self._clock()
        for flight in self.motion.flights:
            t = now - flight.start
            if t < 0 or t >= flight.duration:
                continue
            p = t / flight.duration
            eased = 1 - (1 - p) ** 2
            x = flight.start_pos[0] + (flight.end_pos[0] - flight.start_pos[0]) * eased
            y = flight.start_pos[1] + (flight.end_pos[1] - flight.start_pos[1]) * eased - math.sin(math.pi * p) * 90
            surface.blit(flight.surface, flight.surface.get_rect(center=(int(x), int(y))))

    def draw_glow(self, surface: pygame.Surface, control_id: str, rect: pygame.Rect) -> None:
        """Hint glow around a control (drawn after the controls)."""

        if not self.motion.glowing(control_id):
            return
        halo = self.art.halo(rect.size)
        # A soft breathing glow (alpha only: no new surfaces per frame).
        halo.set_alpha(150 + int(105 * abs(math.sin(self._clock() * math.pi * 1.6))))
        surface.blit(halo, halo.get_rect(center=rect.center))


__all__ = [
    "ACTS",
    "Flight",
    "FrameView",
    "FxBurst",
    "GuideCast",
    "MomoRenderer",
    "SceneMotion",
]
