"""Storybook scene presentation for Luci di Momo.

The renderer owns the night meadow, the glimpse of fireflies, hint halos,
count badges, flights into Momo's jar, the jar itself, Momo and FX. Kit
controls (answer cards, look again, listen, progress dots) and their focus
ring are drawn afterwards by the shared ``ControlLayer`` (ADR 0037).

Per-frame work is blits only: every surface comes prepared from
``FireflyArt``; motion is a blit offset or a choice between prepared sizes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import math
import time

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose
from greia_platform.pygame_blit import PreparedSurfaces

if __package__:
    from .firefly_art import BADGE_SIZE, GROUP_BADGE_SIZE, FireflyArt
    from .firefly_layout import FRAME_RECT, JAR_GLOW_CENTER, JAR_SLOTS, JAR_TOPLEFT, MOMO_MIDBOTTOM
    from .firefly_model import FIELD_CENTER, Arrangement, FireflyRound
else:
    from firefly_art import BADGE_SIZE, GROUP_BADGE_SIZE, FireflyArt
    from firefly_layout import FRAME_RECT, JAR_GLOW_CENTER, JAR_SLOTS, JAR_TOPLEFT, MOMO_MIDBOTTOM
    from firefly_model import FIELD_CENTER, Arrangement, FireflyRound

POP_SECONDS = 0.12
BLINK_SECONDS = 0.12
CUE_SECONDS = 0.9
FLIGHT_SECONDS = 0.7
HALO_SECONDS = 1.4
BADGE_RISE_SECONDS = 0.25
LIGHT_POP_SECONDS = 0.35
WOBBLE_SECONDS = 0.4
PULSE_SECONDS = 1.6
MAX_FLIGHTS = 12
MAX_FX = 16
MAX_BADGES = 12
FX_SECONDS = {"sparkle": 0.45, "star_burst": 0.8, "confetti": 1.6, "firework": 1.2}
FX_DEFAULT_SECONDS = 0.5


class MomoCast:
    """Momo with the shared feedback grammar plus a pointing hint pose.

    ``CastFeedback`` owns cheer (correct) and think (try again); this wrapper
    adds ``point`` ("watch!", idle hints, counting together), drawn only while
    the feedback friend is idle so the grammar stays unambiguous.
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


@dataclass(slots=True)
class Flight:
    """One firefly gliding along a small arc into Momo's jar."""

    start: float
    origin: tuple[int, int]
    dest: tuple[int, int]
    duration: float = FLIGHT_SECONDS
    lift: float = 90.0

    def position(self, now: float) -> tuple[int, int] | None:
        t = (now - self.start) / self.duration
        if t < 0.0 or t >= 1.0:
            return None
        eased = t * t * (3.0 - 2.0 * t)
        x = self.origin[0] + (self.dest[0] - self.origin[0]) * eased
        y = self.origin[1] + (self.dest[1] - self.origin[1]) * eased - self.lift * math.sin(math.pi * t)
        return (int(x), int(y))


@dataclass(slots=True)
class Badge:
    """A numeral that rises above a firefly (or above a whole group)."""

    start: float
    number: int
    position: tuple[int, int]
    group: bool = False


@dataclass(slots=True)
class FieldMotion:
    """Bounded, time-stamped presentation state owned by the app."""

    shown_from: float | None = None  # fireflies glow from this time ...
    hide_at: float | None = None  # ... until this time (None: they stay)
    cue_start: float | None = None  # "watch!" glow before a glimpse
    halos: dict[int, float] = field(default_factory=dict)  # firefly index -> start
    badges: list[Badge] = field(default_factory=list)
    flights: list[Flight] = field(default_factory=list)
    jar_lights: int = 0
    jar_light_since: float = 0.0
    replay_pulse: float | None = None
    fx: list[tuple[str, tuple[int, int], float]] = field(default_factory=list)
    wobble_id: str | None = None
    wobble_started: float | None = None

    def clear_round(self) -> None:
        """Forget everything that belongs to one glimpse (the jar stays)."""

        self.shown_from = None
        self.hide_at = None
        self.cue_start = None
        self.halos.clear()
        self.badges.clear()
        self.flights.clear()
        self.replay_pulse = None
        self.fx.clear()
        self.wobble_id = None
        self.wobble_started = None

    def show(self, start: float, until: float | None) -> None:
        self.shown_from = start
        self.hide_at = until

    def hide(self, at: float) -> None:
        self.hide_at = at

    def fly(self, flight: Flight) -> None:
        self.flights.append(flight)
        del self.flights[:-MAX_FLIGHTS]

    def badge(self, badge: Badge) -> None:
        self.badges.append(badge)
        del self.badges[:-MAX_BADGES]

    def add_fx(self, name: str, position: tuple[int, int], start: float) -> None:
        self.fx.append((name, position, start))
        del self.fx[:-MAX_FX]

    def add_light(self, now: float) -> None:
        self.jar_lights = min(len(JAR_SLOTS), self.jar_lights + 1)
        self.jar_light_since = now

    def active(self, now: float) -> bool:
        """True while something time-based is still moving on screen."""

        if self.shown_from is not None:
            if now < self.shown_from + POP_SECONDS:
                return True
            if self.hide_at is not None and now < self.hide_at + BLINK_SECONDS:
                return True
        if self.cue_start is not None and now - self.cue_start < CUE_SECONDS:
            return True
        if any(now - f.start < f.duration for f in self.flights):
            return True
        if any(now - start < HALO_SECONDS for start in self.halos.values()):
            return True
        if any(now - b.start < BADGE_RISE_SECONDS for b in self.badges):
            return True
        if now - self.jar_light_since < LIGHT_POP_SECONDS:
            return True
        if self.replay_pulse is not None and now - self.replay_pulse < PULSE_SECONDS:
            return True
        if self.wobble_started is not None and now - self.wobble_started < WOBBLE_SECONDS:
            return True
        return any(now - start < _fx_seconds(name) for name, _, start in self.fx)

    def prune(self, now: float) -> None:
        self.flights = [f for f in self.flights if now - f.start < f.duration]
        self.fx = [entry for entry in self.fx if now - entry[2] < _fx_seconds(entry[0])]
        for index in [key for key, start in self.halos.items() if now - start >= HALO_SECONDS]:
            del self.halos[index]


def _fx_seconds(name: str) -> float:
    return FX_SECONDS.get(name, FX_DEFAULT_SECONDS)


def _ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


class FireflyRenderer:
    """Compose one frame of the night meadow from prepared surfaces."""

    def __init__(
        self,
        art: FireflyArt,
        cast: MomoCast | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.art = art
        self.cast = cast
        self._clock = clock

    def draw(self, target: pygame.Surface, round_: FireflyRound | None, motion: FieldMotion) -> None:
        now = self._clock()
        target.blit(self.art.background, (0, 0))
        if round_ is not None:
            if round_.arrangement is Arrangement.TEN_FRAME:
                target.blit(self.art.ten_frame, FRAME_RECT.topleft)
            self._draw_cue(target, motion, now)
            self._draw_fireflies(target, round_, motion, now)
        self._draw_jar(target, motion, now)
        if self.cast is not None:
            self.cast.draw(target, MOMO_MIDBOTTOM)
        self._draw_flights(target, motion, now)
        self._draw_badges(target, motion, now)
        self._draw_fx(target, motion, now)

    def draw_replay_pulse(self, target: pygame.Surface, rect: pygame.Rect, motion: FieldMotion) -> None:
        """Soft blinking glow behind "look again" while Momo suggests it."""

        start = motion.replay_pulse
        now = self._clock()
        if start is None or now - start >= PULSE_SECONDS:
            return
        if int((now - start) * 4) % 2 == 0:
            glow = self.art.cue_glow
            target.blit(glow, glow.get_rect(center=rect.center))

    # -- the glimpse ------------------------------------------------------------

    def _draw_cue(self, target: pygame.Surface, motion: FieldMotion, now: float) -> None:
        start = motion.cue_start
        if start is None or now - start >= CUE_SECONDS:
            return
        # Two soft blinks where the fireflies will appear: "watch here!"
        if int((now - start) / (CUE_SECONDS / 4)) % 2 == 0:
            glow = self.art.cue_glow
            target.blit(glow, glow.get_rect(center=FIELD_CENTER))

    def _draw_fireflies(self, target: pygame.Surface, round_: FireflyRound, motion: FieldMotion, now: float) -> None:
        start = motion.shown_from
        if start is None or now < start:
            return
        role = round_.arrangement.value
        if now - start < POP_SECONDS:
            role = f"{role}.pop"
        if motion.hide_at is not None:
            if now >= motion.hide_at + BLINK_SECONDS:
                return
            if now >= motion.hide_at:
                role = f"{round_.arrangement.value}.blink"
        image = self.art.firefly(role)
        if image is None:
            return
        glow = self.art.glow(role)
        second_glow = self.art.glow(role, second=True)
        split = round_.groups[0] if round_.arrangement is Arrangement.GROUPS else round_.quantity
        halo = self.art.halo
        for index, position in enumerate(round_.positions):
            halo_start = motion.halos.get(index)
            light = glow if index < split else second_glow
            if halo_start is not None and 0.0 <= now - halo_start < HALO_SECONDS:
                target.blit(halo, halo.get_rect(center=position))
            elif light is not None:
                target.blit(light, light.get_rect(center=position))
            target.blit(image, image.get_rect(center=position))

    # -- the jar ------------------------------------------------------------------

    def _draw_jar(self, target: pygame.Surface, motion: FieldMotion, now: float) -> None:
        lights = motion.jar_lights
        alpha = self.art.jar_glow_alpha(lights)
        if alpha:
            glow = self.art.jar_glow
            glow.set_alpha(alpha)
            target.blit(glow, glow.get_rect(center=JAR_GLOW_CENTER))
        if self.art.jar_back is not None:
            target.blit(self.art.jar_back, JAR_TOPLEFT)
        resting = self.art.firefly("jar")
        light = self.art.glow("jar")
        if resting is not None:
            for index in range(lights):
                x, y = JAR_SLOTS[index]
                if index == lights - 1 and now - motion.jar_light_since < LIGHT_POP_SECONDS:
                    y -= int(10 * math.sin(math.pi * (now - motion.jar_light_since) / LIGHT_POP_SECONDS))
                if light is not None:
                    target.blit(light, light.get_rect(center=(x, y + 6)))
                target.blit(resting, resting.get_rect(center=(x, y)))
        if self.art.jar_front is not None:
            target.blit(self.art.jar_front, JAR_TOPLEFT)

    def _draw_flights(self, target: pygame.Surface, motion: FieldMotion, now: float) -> None:
        image = self.art.firefly("flying")
        glow = self.art.glow("flying")
        if image is None:
            return
        for flight in motion.flights:
            position = flight.position(now)
            if position is not None:
                if glow is not None:
                    target.blit(glow, glow.get_rect(center=position))
                target.blit(image, image.get_rect(center=position))

    # -- numbers and FX -------------------------------------------------------------

    def _draw_badges(self, target: pygame.Surface, motion: FieldMotion, now: float) -> None:
        for badge in motion.badges:
            age = now - badge.start
            if age < 0.0:
                continue
            rise = int(12 * _ease_out(age / BADGE_RISE_SECONDS))
            image = self.art.badge(badge.number, group=badge.group)
            size = GROUP_BADGE_SIZE if badge.group else BADGE_SIZE
            x, y = badge.position
            target.blit(image, image.get_rect(center=(x, y - size // 2 - rise)))

    def _draw_fx(self, target: pygame.Surface, motion: FieldMotion, now: float) -> None:
        for name, position, start in motion.fx:
            frames = self.art.fx_frames(name)
            duration = _fx_seconds(name)
            age = now - start
            if not frames or age < 0.0 or age >= duration:
                continue
            frame = frames[min(len(frames) - 1, int(age / duration * len(frames)))]
            target.blit(frame, frame.get_rect(center=position))


__all__ = ["Badge", "FieldMotion", "FireflyRenderer", "Flight", "MomoCast"]
