"""Storybook presentation for Little Vet Clinic.

The renderer owns the vet-corner frame: the patient (walking in, hopping,
gently shaking its head), its problem marks, tools flying from the tray to
the patient, hint glows, library FX and Momo. Kit controls (tray tiles,
"where does it hurt?" hotspots, progress dots) and their focus ring are drawn
afterwards by the shared ``ControlLayer`` (ADR 0037). Per-frame work is
blits only: every surface comes prepared from ``ClinicArt``; motion is
expressed as offsets.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import math
import time

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose

if __package__:
    from .clinic_art import ClinicArt
    from .clinic_content import Overlay, PatientLook, Tool
    from .clinic_layout import MOMO_MIDBOTTOM, PATIENT_HOME, PATIENT_OFFSTAGE_X, to_screen
    from .clinic_model import ClinicDay, Phase
else:
    from clinic_art import ClinicArt
    from clinic_content import Overlay, PatientLook, Tool
    from clinic_layout import MOMO_MIDBOTTOM, PATIENT_HOME, PATIENT_OFFSTAGE_X, to_screen
    from clinic_model import ClinicDay, Phase

FLIGHT_SECONDS = 0.5
WORK_SECONDS = 0.6
HOP_SECONDS = 0.45
SHAKE_SECONDS = 0.7
HALO_SECONDS = 2.0
TOOL_HOP_SECONDS = 1.6
MAX_FLIGHTS = 4
MAX_FX = 12
MAX_HALOS = 4
FX_SECONDS = {
    "sparkle": 0.5,
    "bubble_pop": 0.6,
    "heart_pop": 0.9,
    "beat_ring": 0.5,
    "star_burst": 0.8,
    "check_pop": 0.6,
    "ripple": 0.6,
}
FX_RISE = {"heart_pop": -40.0}
_OVERLAY_NUDGE = {Overlay.THROB: (26, -6)}


class ClinicCast:
    """Momo with the shared feedback grammar plus a pointing hint pose.

    ``CastFeedback`` owns cheer (correct) and think (try again); this wrapper
    adds ``point`` for graduated hints and phase starts, drawn only while the
    feedback friend is idle so the grammar stays unambiguous.
    """

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
            target.blit(self._point, self._point.get_rect(midbottom=midbottom))
            return
        self.feedback.draw(target, midbottom)


@dataclass(slots=True)
class ToolFlight:
    """A tool travelling from its tray tile to the patient, then working there."""

    tool: Tool
    start: float
    origin: tuple[int, int]
    dest: tuple[int, int]
    duration: float = FLIGHT_SECONDS
    work: float = WORK_SECONDS

    @property
    def end(self) -> float:
        return self.start + self.duration + self.work

    def position(self, now: float) -> tuple[int, int] | None:
        t = (now - self.start) / self.duration
        if t < 0.0 or now >= self.end:
            return None
        if t < 1.0:
            eased = 1.0 - (1.0 - t) ** 2
            x = self.origin[0] + (self.dest[0] - self.origin[0]) * eased
            y = self.origin[1] + (self.dest[1] - self.origin[1]) * eased - 90 * math.sin(math.pi * t)
            return (int(x), int(y))
        # Working on the spot: a small scrub / pat wiggle.
        local = now - self.start - self.duration
        return (int(self.dest[0] + 9 * math.sin(local * 26)), int(self.dest[1] + 3 * math.sin(local * 13)))


@dataclass(slots=True)
class ClinicMotion:
    """Bounded, time-stamped presentation state owned by the app."""

    patient_from_x: int = PATIENT_OFFSTAGE_X
    patient_to_x: int = PATIENT_HOME[0]
    move_start: float = 0.0
    move_seconds: float = 0.0
    hop_start: float | None = None
    shake_start: float | None = None
    frozen_look: PatientLook | None = None
    frozen_until: float = 0.0
    flights: list[ToolFlight] = field(default_factory=list)
    fx: list[tuple[str, tuple[int, int], float]] = field(default_factory=list)
    halos: list[tuple[tuple[int, int], float]] = field(default_factory=list)
    tool_hop: tuple[str, float] | None = None
    wobble: tuple[str, float] | None = None

    def clear(self) -> None:
        self.hop_start = None
        self.shake_start = None
        self.frozen_look = None
        self.frozen_until = 0.0
        self.flights.clear()
        self.fx.clear()
        self.halos.clear()
        self.tool_hop = None
        self.wobble = None

    def walk(self, from_x: int, to_x: int, now: float, seconds: float) -> None:
        self.patient_from_x = from_x
        self.patient_to_x = to_x
        self.move_start = now
        self.move_seconds = seconds

    def patient_x(self, now: float) -> int:
        if self.move_seconds <= 0.0:
            return self.patient_to_x
        t = max(0.0, min(1.0, (now - self.move_start) / self.move_seconds))
        eased = 1.0 - (1.0 - t) ** 2
        return int(self.patient_from_x + (self.patient_to_x - self.patient_from_x) * eased)

    def walking(self, now: float) -> bool:
        return self.move_seconds > 0.0 and now - self.move_start < self.move_seconds

    def fly(self, flight: ToolFlight) -> None:
        self.flights.append(flight)
        del self.flights[:-MAX_FLIGHTS]

    def add_fx(self, name: str, position: tuple[int, int], at: float) -> None:
        self.fx.append((name, position, at))
        del self.fx[:-MAX_FX]

    def add_halo(self, position: tuple[int, int], at: float) -> None:
        self.halos.append((position, at))
        del self.halos[:-MAX_HALOS]

    def freeze_look(self, look: PatientLook, until: float) -> None:
        """Keep showing ``look`` until a flying tool has done its work."""

        self.frozen_look = look
        self.frozen_until = until

    def active(self, now: float) -> bool:
        if self.walking(now):
            return True
        if self.hop_start is not None and now - self.hop_start < HOP_SECONDS:
            return True
        if self.shake_start is not None and now - self.shake_start < SHAKE_SECONDS:
            return True
        if any(now < flight.end for flight in self.flights):
            return True
        if any(now - start < HALO_SECONDS for _, start in self.halos):
            return True
        if self.tool_hop is not None and now - self.tool_hop[1] < TOOL_HOP_SECONDS:
            return True
        if self.wobble is not None and now - self.wobble[1] < 0.4:
            return True
        if self.frozen_look is not None and now < self.frozen_until:
            return True
        return any(now - start < _fx_seconds(name) for name, _, start in self.fx)

    def prune(self, now: float) -> None:
        self.flights = [flight for flight in self.flights if now < flight.end]
        self.fx = [entry for entry in self.fx if now - entry[2] < _fx_seconds(entry[0])]
        self.halos = [entry for entry in self.halos if now - entry[1] < HALO_SECONDS]
        if self.frozen_look is not None and now >= self.frozen_until:
            self.frozen_look = None


def _fx_seconds(name: str) -> float:
    return FX_SECONDS.get(name, 0.5)


class ClinicRenderer:
    """Compose one frame of the vet corner from prepared surfaces."""

    def __init__(
        self,
        art: ClinicArt,
        cast: ClinicCast | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.art = art
        self.cast = cast
        self._clock = clock

    def patient_midbottom(self, motion: ClinicMotion, now: float | None = None) -> tuple[int, int]:
        now = self._clock() if now is None else now
        x = motion.patient_x(now)
        y = PATIENT_HOME[1]
        if motion.walking(now):
            y -= int(14 * abs(math.sin((now - motion.move_start) * 9.0)))
        elif motion.hop_start is not None and 0.0 <= now - motion.hop_start < HOP_SECONDS:
            y -= int(26 * math.sin(math.pi * (now - motion.hop_start) / HOP_SECONDS))
        if motion.shake_start is not None and 0.0 <= now - motion.shake_start < SHAKE_SECONDS:
            age = now - motion.shake_start
            x += int(12 * (1.0 - age / SHAKE_SECONDS) * math.sin(age * 28.0))
        return (x, y)

    def draw(self, target: pygame.Surface, day: ClinicDay, motion: ClinicMotion) -> None:
        now = self._clock()
        target.blit(self.art.background, (0, 0))
        if day.phase is not Phase.DONE:
            self._draw_patient(target, day, motion, now)
        self._draw_flights(target, motion, now)
        self._draw_halos(target, motion, now)
        self._draw_fx(target, motion, now)
        if self.cast is not None:
            self.cast.draw(target, MOMO_MIDBOTTOM)

    def _draw_patient(self, target: pygame.Surface, day: ClinicDay, motion: ClinicMotion, now: float) -> None:
        look = motion.frozen_look if motion.frozen_look is not None and now < motion.frozen_until else day.look
        midbottom = self.patient_midbottom(motion, now)
        sprite = self.art.patient(day.case.species_id, look.variant)
        if sprite is not None:
            target.blit(sprite, sprite.get_rect(midbottom=midbottom))
        for overlay, anchor in look.overlays:
            image = self.art.overlays.get(overlay)
            if image is None:
                continue
            x, y = to_screen(anchor, midbottom)
            nudge = _OVERLAY_NUDGE.get(overlay, (0, 0))
            bob = int(3 * math.sin(now * 6.0)) if overlay in {Overlay.THROB, Overlay.SWIRL} else 0
            target.blit(image, image.get_rect(center=(x + nudge[0] + bob, y + nudge[1])))

    def _draw_flights(self, target: pygame.Surface, motion: ClinicMotion, now: float) -> None:
        for flight in motion.flights:
            position = flight.position(now)
            image = self.art.flight_icons.get(flight.tool)
            if position is not None and image is not None:
                target.blit(image, image.get_rect(center=position))

    def _draw_halos(self, target: pygame.Surface, motion: ClinicMotion, now: float) -> None:
        for position, start in motion.halos:
            age = now - start
            if 0.0 <= age < HALO_SECONDS and int(age * 5) % 2 == 0:
                target.blit(self.art.halo, self.art.halo.get_rect(center=position))

    def _draw_fx(self, target: pygame.Surface, motion: ClinicMotion, now: float) -> None:
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
    "ClinicCast",
    "ClinicMotion",
    "ClinicRenderer",
    "FLIGHT_SECONDS",
    "HALO_SECONDS",
    "TOOL_HOP_SECONDS",
    "ToolFlight",
    "WORK_SECONDS",
]
