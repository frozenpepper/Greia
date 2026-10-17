"""Storybook scene presentation for La Casa del Dieci.

The renderer owns the night garden, the ten-frame house, fireflies (resting,
waiting, flying), hint halos, count badges, the roof sign, the number-bond
strip, Dani and FX. Kit controls (answer cards, the "house is ready" button,
replay voice, progress dots) and their focus ring are drawn afterwards by the
shared ``ControlLayer`` (ADR 0037). Per-frame work is blits only: every
surface comes prepared from ``TenHouseArt``; motion is expressed as offsets.
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
    from .ten_house_art import BOND_DISC, TenHouseArt, Tone
    from .ten_house_layout import (
        BOND_CENTER,
        DANI_MIDBOTTOM,
        FIREFLY_IN_ROOM,
        GUEST_SLOTS,
        ROOM_RECTS,
        SIGN_RECT,
        SKY_SLOTS,
    )
    from .ten_house_model import ROOM_COUNT, OperationMode, RoomState, TenHouseSession
else:
    from ten_house_art import BOND_DISC, TenHouseArt, Tone
    from ten_house_layout import (
        BOND_CENTER,
        DANI_MIDBOTTOM,
        FIREFLY_IN_ROOM,
        GUEST_SLOTS,
        ROOM_RECTS,
        SIGN_RECT,
        SKY_SLOTS,
    )
    from ten_house_model import ROOM_COUNT, OperationMode, RoomState, TenHouseSession

FLIGHT_SECONDS = 0.62
BADGE_HOLD_SECONDS = 1.0  # the whole count stays visible this long after the last badge
HALO_SECONDS = 1.5
SIGN_PULSE_SECONDS = 0.6
BOND_RISE_SECONDS = 0.3
WOBBLE_SECONDS = 0.4
MAX_FLIGHTS = 16
MAX_FX = 14
FX_SECONDS = {"sparkle": 0.42, "star_burst": 0.75, "heart_pop": 0.9, "confetti": 1.5}
FX_DEFAULT_SECONDS = 0.5
FX_RISE = {"heart_pop": -34.0, "confetti": 70.0}


class TenHouseCast:
    """Dani with the shared feedback grammar plus a pointing hint pose.

    ``CastFeedback`` owns cheer (correct) and think (try again); this wrapper
    adds ``point`` for graduated hints and round starts, drawn only while the
    feedback friend is idle so the grammar stays unambiguous.
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
    """One firefly travelling along a small arc (in or out of the house)."""

    start: float
    origin: tuple[int, int]
    dest: tuple[int, int]
    duration: float = FLIGHT_SECONDS
    lift: float = 70.0

    def position(self, now: float) -> tuple[int, int] | None:
        t = (now - self.start) / self.duration
        if t < 0.0 or t >= 1.0:
            return None
        eased = 1.0 - (1.0 - t) ** 2
        x = self.origin[0] + (self.dest[0] - self.origin[0]) * eased
        y = self.origin[1] + (self.dest[1] - self.origin[1]) * eased - self.lift * math.sin(math.pi * t)
        return (int(x), int(y))


@dataclass(slots=True)
class BondItem:
    """One element of the number-bond strip: a disc or a symbol."""

    text: str
    tone: Tone | None = None  # None -> symbol (+, -, =)


@dataclass(slots=True)
class HouseMotion:
    """Bounded, time-stamped presentation state owned by the app."""

    flights: list[Flight] = field(default_factory=list)
    arrivals: dict[int, float] = field(default_factory=dict)  # room -> landing time
    trial: dict[int, float] = field(default_factory=dict)  # "how many more?" try-out rooms
    outside: list[tuple[float, tuple[int, int]]] = field(default_factory=list)  # (land, pos) no room left
    waiting: list[int] = field(default_factory=list)  # guest slots still outside (ADD)
    sky: int = 0  # fireflies resting in the sky after flying home
    sky_since: dict[int, float] = field(default_factory=dict)
    badges: dict[int, tuple[float, float, int, Tone]] = field(default_factory=dict)  # room -> (start, end, n, tone)
    halos: dict[int, float] = field(default_factory=dict)
    guest_pulse: float | None = None
    fx: list[tuple[str, tuple[int, int], float]] = field(default_factory=list)
    sign_number: int | None = None  # the whole, revealed after an add / take-away answer
    sign_pulse: float | None = None
    bond: tuple[BondItem, ...] = ()
    bond_started: float = 0.0
    wobble_id: str | None = None
    wobble_started: float | None = None

    def clear(self) -> None:
        self.flights.clear()
        self.arrivals.clear()
        self.trial.clear()
        self.outside.clear()
        self.waiting.clear()
        self.sky = 0
        self.sky_since.clear()
        self.badges.clear()
        self.halos.clear()
        self.guest_pulse = None
        self.fx.clear()
        self.sign_number = None
        self.sign_pulse = None
        self.bond = ()
        self.wobble_id = None
        self.wobble_started = None

    def fly(self, flight: Flight) -> None:
        self.flights.append(flight)
        del self.flights[:-MAX_FLIGHTS]

    def add_fx(self, name: str, position: tuple[int, int], now: float) -> None:
        self.fx.append((name, position, now))
        del self.fx[:-MAX_FX]

    def active(self, now: float) -> bool:
        if any(now - f.start < f.duration for f in self.flights):
            return True
        if any(now < landing for landing in self.arrivals.values()):
            return True
        if any(now < end for _, end, _, _ in self.badges.values()):
            return True
        if any(now - start < HALO_SECONDS for start in self.halos.values()):
            return True
        if self.guest_pulse is not None and now - self.guest_pulse < HALO_SECONDS:
            return True
        if self.sign_pulse is not None and now - self.sign_pulse < SIGN_PULSE_SECONDS:
            return True
        if self.bond and now - self.bond_started < BOND_RISE_SECONDS:
            return True
        if self.wobble_started is not None and now - self.wobble_started < WOBBLE_SECONDS:
            return True
        return any(now - start < _fx_seconds(name) for name, _, start in self.fx)

    def prune(self, now: float) -> None:
        self.flights = [f for f in self.flights if now - f.start < f.duration]
        self.fx = [entry for entry in self.fx if now - entry[2] < _fx_seconds(entry[0])]
        for room in [key for key, (_, end, _, _) in self.badges.items() if now >= end]:
            del self.badges[room]
        for room in [key for key, start in self.halos.items() if now - start >= HALO_SECONDS]:
            del self.halos[room]
        for room in [key for key, landing in self.arrivals.items() if now >= landing]:
            del self.arrivals[room]


def _fx_seconds(name: str) -> float:
    return FX_SECONDS.get(name, FX_DEFAULT_SECONDS)


def _ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


class TenHouseRenderer:
    """Compose one frame of the Ten House from prepared surfaces."""

    def __init__(
        self,
        art: TenHouseArt,
        cast: TenHouseCast | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.art = art
        self.cast = cast
        self._clock = clock

    def draw(self, target: pygame.Surface, session: TenHouseSession, motion: HouseMotion) -> None:
        now = self._clock()
        target.blit(self.art.background, (0, 0))
        self._draw_sky(target, motion, now)
        if session.current_challenge is not None:
            self._draw_rooms(target, session, motion, now)
            self._draw_sign(target, session, motion, now)
            self._draw_waiting(target, motion, now)
        self._draw_outside(target, motion, now)
        self._draw_flights(target, motion, now)
        self._draw_badges(target, motion, now)
        if self.cast is not None:
            self.cast.draw(target, DANI_MIDBOTTOM)
        self._draw_bond(target, motion, now)
        self._draw_fx(target, motion, now)

    # -- house ----------------------------------------------------------------

    def _draw_rooms(self, target: pygame.Surface, session: TenHouseSession, motion: HouseMotion, now: float) -> None:
        resting = self.art.firefly("room")
        for index in range(ROOM_COUNT):
            state = session.room_state(index)
            if state is RoomState.DARK:
                landing = motion.trial.get(index)
                if landing is None or now < landing:
                    self._draw_halo(target, index, motion, now)
                    continue
                state = RoomState.GUEST
            elif now < motion.arrivals.get(index, 0.0):
                continue  # its firefly is still on the way
            window = self.art.windows.get(state)
            if window is not None:
                target.blit(window, ROOM_RECTS[index].topleft)
            if resting is not None:
                target.blit(resting, resting.get_rect(center=FIREFLY_IN_ROOM[index]))
            self._draw_halo(target, index, motion, now)

    def _draw_halo(self, target: pygame.Surface, index: int, motion: HouseMotion, now: float) -> None:
        start = motion.halos.get(index)
        if start is None or now - start >= HALO_SECONDS:
            return
        if int((now - start) * 5) % 2 == 0:
            target.blit(self.art.halo, self.art.halo.get_rect(center=ROOM_RECTS[index].center))

    def _draw_sign(self, target: pygame.Surface, session: TenHouseSession, motion: HouseMotion, now: float) -> None:
        challenge = session.current_challenge
        assert challenge is not None
        if motion.sign_number is not None:
            face = self.art.sign_face(motion.sign_number, dots=False)
        elif challenge.mode in {OperationMode.COMPOSE, OperationMode.MISSING_PART}:
            face = self.art.sign_face(challenge.target, dots=session.presentation.sign_dots)
        else:
            face = self.art.sign_face(None, dots=False)
        lift = 0
        if motion.sign_pulse is not None and now - motion.sign_pulse < SIGN_PULSE_SECONDS:
            lift = -int(8 * math.sin(math.pi * (now - motion.sign_pulse) / SIGN_PULSE_SECONDS))
        target.blit(face, SIGN_RECT.move(0, lift).topleft)

    def _draw_waiting(self, target: pygame.Surface, motion: HouseMotion, now: float) -> None:
        guest = self.art.firefly("guest")
        if guest is None:
            return
        pulsing = motion.guest_pulse is not None and now - motion.guest_pulse < HALO_SECONDS
        for order, slot_index in enumerate(motion.waiting):
            slot = GUEST_SLOTS[slot_index]
            hop = 0
            if pulsing and order == 0:
                hop = -int(12 * abs(math.sin(math.pi * (now - motion.guest_pulse) * 2.4)))  # type: ignore[operator]
            target.blit(guest, guest.get_rect(center=(slot[0], slot[1] + hop)))

    # -- fireflies outside the house ---------------------------------------------

    def _draw_sky(self, target: pygame.Surface, motion: HouseMotion, now: float) -> None:
        image = self.art.firefly("sky")
        if image is None:
            return
        for index in range(min(motion.sky, len(SKY_SLOTS))):
            if now >= motion.sky_since.get(index, 0.0):
                target.blit(image, image.get_rect(center=SKY_SLOTS[index]))

    def _draw_outside(self, target: pygame.Surface, motion: HouseMotion, now: float) -> None:
        image = self.art.firefly("flying")
        if image is None:
            return
        for landing, position in motion.outside:
            if now >= landing:
                target.blit(image, image.get_rect(center=position))

    def _draw_flights(self, target: pygame.Surface, motion: HouseMotion, now: float) -> None:
        image = self.art.firefly("flying")
        if image is None:
            return
        for flight in motion.flights:
            position = flight.position(now)
            if position is not None:
                target.blit(image, image.get_rect(center=position))

    # -- numbers -------------------------------------------------------------------

    def _draw_badges(self, target: pygame.Surface, motion: HouseMotion, now: float) -> None:
        for room, (start, end, number, tone) in motion.badges.items():
            age = now - start
            if age < 0.0 or now >= end or not 0 <= room < ROOM_COUNT:
                continue
            rect = ROOM_RECTS[room]
            rise = int(10 * _ease_out(age / 0.3))
            badge = self.art.badge(number, tone)
            target.blit(badge, badge.get_rect(center=(rect.centerx, rect.top + 4 - rise)))

    def _draw_bond(self, target: pygame.Surface, motion: HouseMotion, now: float) -> None:
        if not motion.bond:
            return
        pieces: list[pygame.Surface] = []
        for item in motion.bond:
            if item.tone is None:
                pieces.append(self.art.symbol(item.text))
            else:
                pieces.append(self.art.bond_disc(int(item.text), item.tone))
        gap = 14
        total = sum(piece.get_width() for piece in pieces) + gap * (len(pieces) - 1)
        x = BOND_CENTER[0] - total // 2
        rise = int(30 * (1.0 - _ease_out((now - motion.bond_started) / BOND_RISE_SECONDS)))
        for piece in pieces:
            target.blit(piece, piece.get_rect(midleft=(x, BOND_CENTER[1] + rise)))
            x += piece.get_width() + gap

    def _draw_fx(self, target: pygame.Surface, motion: HouseMotion, now: float) -> None:
        for name, position, start in motion.fx:
            frames = self.art.fx_frames(name)
            duration = _fx_seconds(name)
            age = now - start
            if not frames or age < 0.0 or age >= duration:
                continue
            frame = frames[min(len(frames) - 1, int(age / duration * len(frames)))]
            drift = int(FX_RISE.get(name, 0.0) * age / duration)
            target.blit(frame, frame.get_rect(center=(position[0], position[1] + drift)))


__all__ = [
    "BOND_DISC",
    "BondItem",
    "Flight",
    "HouseMotion",
    "TenHouseCast",
    "TenHouseRenderer",
]
