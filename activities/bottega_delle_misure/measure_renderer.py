"""Storybook scene presentation for La Bottega delle Misure.

The renderer owns the workshop (backdrop, job card, Leo), the measuring
boards with their start stops, crates and laid unit blocks, the toy balance,
the parcels, blocks hopping between crate and board, counting badges, the
try-again demonstration marks and FX. Kit controls (check, count tiles,
listen, progress dots) and their focus ring are drawn afterwards by the
shared ``ControlLayer``. Per-frame work is blits plus a few short guide
lines: every surface comes prepared from ``MeasureArt``; motion is offsets,
prepared sizes and pre-rotated beam frames.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import math
import time

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose

if __package__:
    from .measure_art import BOW_HEIGHT, MeasureArt
    from .measure_content import (
        BEAM_HALF,
        BENCH_TOP,
        COMPARE_ROWS,
        GUIDE_MIDBOTTOM,
        LYING_HEIGHTS,
        MEASURE_ROW,
        PAN_HANG,
        PAN_RIM,
        PIVOT,
        SIGN_FACE,
        SIGN_POS,
        STAND_PIVOT,
        TILT_DEGREES,
        WEIGH_HOME_X,
        WEIGH_SIZES,
        RowGeometry,
        standing_rect,
        twin_rows,
    )
    from .measure_model import Parcel, Task, TaskKind
else:
    from measure_art import BOW_HEIGHT, MeasureArt
    from measure_content import (
        BEAM_HALF,
        BENCH_TOP,
        COMPARE_ROWS,
        GUIDE_MIDBOTTOM,
        LYING_HEIGHTS,
        MEASURE_ROW,
        PAN_HANG,
        PAN_RIM,
        PIVOT,
        SIGN_FACE,
        SIGN_POS,
        STAND_PIVOT,
        TILT_DEGREES,
        WEIGH_HOME_X,
        WEIGH_SIZES,
        RowGeometry,
        standing_rect,
        twin_rows,
    )
    from measure_model import Parcel, Task, TaskKind

HOP_SECONDS = 0.34
PAN_HOP_SECONDS = 0.5
POP_SECONDS = 0.3
BADGE_SECONDS = 1.1
DROP_SECONDS = 0.45
EXIT_SECONDS = 0.7
SIGN_HOP_SECONDS = 0.3
WOBBLE_SECONDS = 0.45
SWING_SECONDS = 1.3
DEMO_MARK_SECONDS = 2.8
PULSE_SECONDS = 0.45
MAX_FX = 10
FX_SECONDS = {"sparkle": 0.42, "star_burst": 0.75, "confetti": 1.5, "check_pop": 0.6, "dust_puff": 0.5}
FX_DEFAULT_SECONDS = 0.5
FX_DRIFT = {"confetti": 70.0}
INK = (75, 55, 47)
SUNSHINE = (255, 194, 52)


def rows_for(task: Task) -> tuple[RowGeometry, ...]:
    """The measuring boards a job uses (none for the bench/balance jobs)."""

    if task.kind is TaskKind.MEASURE:
        return (MEASURE_ROW,)
    if task.kind is TaskKind.MEASURE_COMPARE:
        return twin_rows(task.stagger)
    if task.kind is TaskKind.COMPARE_LENGTH:
        return COMPARE_ROWS
    return ()


def balance_ends(degrees: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """Hanging points of the left and right pans (positive angle = right side down)."""

    radians = math.radians(degrees)
    dx, dy = BEAM_HALF * math.cos(radians), BEAM_HALF * math.sin(radians)
    return ((PIVOT[0] - dx, PIVOT[1] - dy), (PIVOT[0] + dx, PIVOT[1] + dy))


def parcel_rect(task: Task, parcel: Parcel, *, degrees: float = 0.0) -> pygame.Rect:
    """Resting box rectangle of a parcel (without the bow)."""

    if task.kind is TaskKind.COMPARE_HEIGHT:
        return pygame.Rect(standing_rect(parcel.parcel_id, parcel.units))
    if task.kind is TaskKind.WEIGH:
        width, height = WEIGH_SIZES[parcel.size]
        if task.on_pan[parcel.parcel_id]:
            hx, hy = balance_ends(degrees)[parcel.parcel_id]
            bottom = int(hy - PAN_HANG[1] + PAN_RIM)
            return pygame.Rect(int(hx) - width // 2, bottom - height, width, height)
        cx = WEIGH_HOME_X[parcel.parcel_id]
        return pygame.Rect(cx - width // 2, BENCH_TOP - height, width, height)
    row = rows_for(task)[parcel.parcel_id]
    return pygame.Rect(row.parcel_rect(parcel.units, LYING_HEIGHTS[parcel.depth]))


def _ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


class MeasureCast:
    """The guide (Leo) with the shared feedback grammar plus a pointing hint pose.

    ``CastFeedback`` owns cheer (correct) and think (try again); this wrapper
    adds ``point`` for graduated hints and job starts, drawn only while the
    feedback friend is idle so the grammar stays unambiguous.
    """

    def __init__(self, feedback: CastFeedback, point: pygame.Surface | None, clock: Callable[[], float]) -> None:
        self.feedback = feedback
        self._point = point
        self._clock = clock
        self._point_until = 0.0

    @property
    def animating(self) -> bool:
        return self.feedback.animating or self.pointing

    @property
    def pointing(self) -> bool:
        return self._clock() < self._point_until and self._point is not None

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
        if self.pointing and self.feedback.pose is CastPose.IDLE:
            target.blit(self._point, self._point.get_rect(midbottom=midbottom))  # type: ignore[union-attr]
            return
        self.feedback.draw(target, midbottom)


@dataclass(slots=True)
class BlockHop:
    """One unit block travelling between a crate and its place on a board."""

    start: float
    row: int
    index: int
    into_board: bool


@dataclass(slots=True)
class SceneMotion:
    """Bounded, time-stamped animation state owned by the app."""

    job_started: float = -10.0
    exit_started: float | None = None
    hops: dict[tuple[int, int], BlockHop] = field(default_factory=dict)  # (row, index) -> hop
    pan_hops: dict[int, float] = field(default_factory=dict)  # parcel id -> start
    pops: dict[tuple[int, int], float] = field(default_factory=dict)  # (row, index) -> start
    pulses: dict[int, float] = field(default_factory=dict)  # parcel id -> start (hint / demo)
    crate_pulses: dict[int, float] = field(default_factory=dict)  # row -> start
    # (row, place) -> (start, number); a start in the future holds the badge.
    badges: dict[tuple[int, int], tuple[float, int]] = field(default_factory=dict)
    fx: list[tuple[str, tuple[int, int], float]] = field(default_factory=list)
    sign_hop: float = -10.0
    wobble: tuple[int, float] | None = None  # (parcel id, start)
    lit: int | None = None  # parcel celebrated / highlighted
    # Balance: displayed angle swings from ``swing_from`` to ``swing_to``.
    swing_from: float = 0.0
    swing_to: float = 0.0
    swing_started: float = -10.0
    # Try-again marks.
    marks_started: float = -10.0
    missing: dict[int, range] = field(default_factory=dict)  # row -> block places
    extra: dict[int, range] = field(default_factory=dict)
    guide_x: int | None = None  # vertical end line (lengths)
    guide_y: int | None = None  # horizontal top line (heights)
    guide_span: tuple[int, int] = (0, 0)

    def clear(self, now: float) -> None:
        self.job_started = now
        self.exit_started = None
        self.hops.clear()
        self.pan_hops.clear()
        self.pops.clear()
        self.pulses.clear()
        self.crate_pulses.clear()
        self.badges.clear()
        self.fx.clear()
        self.wobble = None
        self.lit = None
        self.swing_from = self.swing_to = 0.0
        self.swing_started = -10.0
        self.clear_marks()

    def clear_marks(self) -> None:
        self.marks_started = -10.0
        self.missing.clear()
        self.extra.clear()
        self.guide_x = None
        self.guide_y = None

    def add_fx(self, name: str, position: tuple[int, int], now: float) -> None:
        self.fx.append((name, position, now))
        del self.fx[:-MAX_FX]

    def swing(self, target: float, now: float, *, start: float | None = None) -> None:
        self.swing_from = self.angle(now) if start is None else start
        self.swing_to = target
        self.swing_started = now

    def angle(self, now: float) -> float:
        """Damped swing toward the target angle (a toy balance settling)."""

        t = now - self.swing_started
        if t >= SWING_SECONDS:
            return self.swing_to
        delta = self.swing_from - self.swing_to
        value = self.swing_to + delta * math.exp(-3.2 * t) * math.cos(7.5 * t)
        return max(-TILT_DEGREES - 2, min(TILT_DEGREES + 2, value))

    def marks_visible(self, now: float) -> bool:
        return now - self.marks_started < DEMO_MARK_SECONDS

    def active(self, now: float) -> bool:
        if now - self.job_started < DROP_SECONDS + 0.1:
            return True
        if self.exit_started is not None and now - self.exit_started < EXIT_SECONDS:
            return True
        if any(now - hop.start < HOP_SECONDS for hop in self.hops.values()):
            return True
        if any(now - start < PAN_HOP_SECONDS for start in self.pan_hops.values()):
            return True
        if any(now - start < POP_SECONDS for start in self.pops.values()):
            return True
        if any(now - start < PULSE_SECONDS for start in (*self.pulses.values(), *self.crate_pulses.values())):
            return True
        if any(now - start < BADGE_SECONDS for start, _ in self.badges.values()):
            return True
        if now - self.sign_hop < SIGN_HOP_SECONDS or now - self.swing_started < SWING_SECONDS:
            return True
        if self.wobble is not None and now - self.wobble[1] < WOBBLE_SECONDS:
            return True
        if self.marks_started > 0 and self.marks_visible(now):
            return True
        return any(now - start < _fx_seconds(name) for name, _, start in self.fx)

    def prune(self, now: float) -> None:
        self.fx = [entry for entry in self.fx if now - entry[2] < _fx_seconds(entry[0])]
        for store, limit in (
            (self.pops, POP_SECONDS),
            (self.pulses, PULSE_SECONDS),
            (self.crate_pulses, PULSE_SECONDS),
        ):
            for key in [key for key, start in store.items() if now - start >= limit]:
                del store[key]
        for key in [key for key, hop in self.hops.items() if now - hop.start >= HOP_SECONDS]:
            del self.hops[key]
        for key in [key for key, start in self.pan_hops.items() if now - start >= PAN_HOP_SECONDS]:
            del self.pan_hops[key]
        for key in [key for key, (start, _) in self.badges.items() if now - start >= BADGE_SECONDS]:
            del self.badges[key]
        if self.wobble is not None and now - self.wobble[1] >= WOBBLE_SECONDS:
            self.wobble = None
        if self.marks_started > 0 and not self.marks_visible(now):
            self.clear_marks()


def _fx_seconds(name: str) -> float:
    return FX_SECONDS.get(name, FX_DEFAULT_SECONDS)


class MeasureRenderer:
    """Compose one frame of the workshop from prepared surfaces."""

    def __init__(
        self, art: MeasureArt, cast: MeasureCast | None = None, *, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.art = art
        self.cast = cast
        self._clock = clock

    def draw(self, target: pygame.Surface, task: Task, motion: SceneMotion) -> None:
        now = self._clock()
        target.blit(self.art.background, (0, 0))
        self._draw_sign(target, task, motion, now)
        rows = rows_for(task)
        for index, row in enumerate(rows):
            self._draw_board(target, task, index, row, motion, now)
        if task.kind is TaskKind.COMPARE_LENGTH:
            self._draw_shared_stop(target, rows)
        degrees = motion.angle(now)
        if task.kind is TaskKind.WEIGH:
            self._draw_balance(target, task, motion, degrees)
        exit_dx = self._exit_offset(motion, now)
        for parcel in task.parcels:
            self._draw_parcel(target, task, parcel, motion, now, degrees, exit_dx)
        for index, row in enumerate(rows):
            self._draw_marks(target, task, index, row, motion, now)
        self._draw_guides(target, motion, now)
        for hop in motion.hops.values():
            self._draw_hop(target, rows, hop, now)
        self._draw_badges(target, rows, motion, now)
        if self.cast is not None:
            self.cast.draw(target, GUIDE_MIDBOTTOM)
        self._draw_fx(target, motion, now)

    # -- job card ----------------------------------------------------------------

    def _draw_sign(self, target: pygame.Surface, task: Task, motion: SceneMotion, now: float) -> None:
        age = now - motion.sign_hop
        lift = int(8 * math.sin(math.pi * age / SIGN_HOP_SECONDS)) if 0 <= age < SIGN_HOP_SECONDS else 0
        x, y = SIGN_POS[0], SIGN_POS[1] - lift
        if self.art.sign is not None:
            target.blit(self.art.sign, (x, y))
        face = self.art.goal_face(task.kind, task.goal)  # centred on the cream face
        fx, fy, fw, fh = SIGN_FACE
        target.blit(face, face.get_rect(center=(x + fx + fw // 2, y + fy + fh // 2)))

    # -- boards and blocks ---------------------------------------------------------

    def _draw_shared_stop(self, target: pygame.Surface, rows: tuple[RowGeometry, ...]) -> None:
        """Lining up: one start stop runs through both shelves."""

        x, top, _, _ = rows[0].stop_rect
        bottom = rows[-1].top + 50
        stop = self.art.tall_stop(bottom - top)
        if stop is not None:
            target.blit(stop, (x, top))

    def _draw_board(
        self, target: pygame.Surface, task: Task, index: int, row: RowGeometry, motion: SceneMotion, now: float
    ) -> None:
        plank = self.art.board if task.kind.lays_blocks else self.art.shelf
        if plank is not None:
            target.blit(plank, row.board_rect[:2])
        if row.crate and self.art.crate is not None:
            x, y, w, h = row.crate_rect
            start = motion.crate_pulses.get(index)
            lift = 0
            if start is not None and now - start < PULSE_SECONDS:
                lift = int(9 * math.sin(math.pi * (now - start) / PULSE_SECONDS))
            target.blit(self.art.crate, (x, y - lift))
        if index < len(task.rows):
            hopping = {key[1] for key, hop in motion.hops.items() if key[0] == index}
            for place in range(task.rows[index]):
                if place in hopping:
                    continue
                self._blit_block(target, row, index, place, motion, now)
        if self.art.stop is not None and task.kind.lays_blocks:
            target.blit(self.art.stop, row.stop_rect[:2])

    def _blit_block(
        self, target: pygame.Surface, row: RowGeometry, index: int, place: int, motion: SceneMotion, now: float
    ) -> None:
        x, y, w, h = row.block_rect(place)
        popping = now - motion.pops.get((index, place), -10.0) < POP_SECONDS
        image = self.art.block_pop if popping else self.art.block
        if image is not None:
            target.blit(image, image.get_rect(center=(x + w // 2, y + h // 2)))

    def _draw_hop(self, target: pygame.Surface, rows: tuple[RowGeometry, ...], hop: BlockHop, now: float) -> None:
        if hop.row >= len(rows) or self.art.block is None:
            return
        row = rows[hop.row]
        t = max(0.0, min(1.0, (now - hop.start) / HOP_SECONDS))
        cx, cy, cw, ch = row.crate_rect
        crate = (cx + cw / 2, cy + ch * 0.35)
        bx, by, bw, bh = row.block_rect(hop.index)
        place = (bx + bw / 2, by + bh / 2)
        start, end = (crate, place) if hop.into_board else (place, crate)
        x = start[0] + (end[0] - start[0]) * t
        y = start[1] + (end[1] - start[1]) * t - 70.0 * math.sin(math.pi * t)
        target.blit(self.art.block, self.art.block.get_rect(center=(int(x), int(y))))

    def _draw_marks(
        self, target: pygame.Surface, task: Task, index: int, row: RowGeometry, motion: SceneMotion, now: float
    ) -> None:
        if not motion.marks_visible(now):
            return
        blink = int(now * 4) % 2 == 0
        for place in motion.missing.get(index, ()):
            x, y, w, h = row.block_rect(place)
            ghost = self.art.missing_ghost
            if blink or place == motion.missing[index].start:
                target.blit(ghost, ghost.get_rect(center=(x + w // 2, y + h // 2)))
        for place in motion.extra.get(index, ()):
            x, y, w, h = row.block_rect(place)
            ring = self.art.extra_ring
            target.blit(ring, ring.get_rect(center=(x + w // 2, y + h // 2)))

    def _draw_guides(self, target: pygame.Surface, motion: SceneMotion, now: float) -> None:
        if not motion.marks_visible(now):
            return
        low, high = motion.guide_span
        if motion.guide_x is not None:
            x = motion.guide_x
            _dashed(target, (x, low), (x, high))
        if motion.guide_y is not None:
            y = motion.guide_y
            _dashed(target, (low, y), (high, y))

    def _draw_badges(
        self, target: pygame.Surface, rows: tuple[RowGeometry, ...], motion: SceneMotion, now: float
    ) -> None:
        for (row_index, place), (start, number) in motion.badges.items():
            age = now - start
            if age >= BADGE_SECONDS or row_index >= len(rows):
                continue
            x, y, w, h = rows[row_index].block_rect(place)
            rise = 8 if age < 0 else int(8 * _ease_out(age / 0.3))  # age < 0: held
            badge = self.art.badge(number)
            target.blit(badge, badge.get_rect(center=(x + w // 2, y + h // 2 - rise)))

    # -- balance -------------------------------------------------------------------

    def _draw_balance(self, target: pygame.Surface, task: Task, motion: SceneMotion, degrees: float) -> None:
        if self.art.stand is not None:
            target.blit(self.art.stand, (PIVOT[0] - STAND_PIVOT[0], PIVOT[1] - STAND_PIVOT[1]))
        if self.art.pan is not None:
            for hx, hy in balance_ends(degrees):
                target.blit(self.art.pan, (int(hx) - PAN_HANG[0], int(hy) - PAN_HANG[1]))
        beam = self.art.beam(degrees)
        if beam is not None:
            target.blit(beam, beam.get_rect(center=PIVOT))

    # -- parcels ---------------------------------------------------------------------

    def _exit_offset(self, motion: SceneMotion, now: float) -> int:
        if motion.exit_started is None:
            return 0
        t = max(0.0, min(1.0, (now - motion.exit_started) / EXIT_SECONDS))
        return int(1100 * t * t)

    def _draw_parcel(
        self,
        target: pygame.Surface,
        task: Task,
        parcel: Parcel,
        motion: SceneMotion,
        now: float,
        degrees: float,
        exit_dx: int,
    ) -> None:
        rect = parcel_rect(task, parcel, degrees=degrees)
        hop_start = motion.pan_hops.get(parcel.parcel_id)
        if hop_start is not None and now - hop_start < PAN_HOP_SECONDS:
            width, height = rect.size
            home = WEIGH_HOME_X[parcel.parcel_id]
            t = (now - hop_start) / PAN_HOP_SECONDS
            sx, sy = home, BENCH_TOP
            ex, ey = rect.centerx, rect.bottom
            x = sx + (ex - sx) * t
            y = sy + (ey - sy) * t - 120.0 * math.sin(math.pi * t)
            rect = pygame.Rect(int(x) - width // 2, int(y) - height, width, height)
        dx = exit_dx
        drop = (now - motion.job_started - 0.08 * parcel.parcel_id) / DROP_SECONDS
        dy = 0
        if drop < 1.0:
            if drop <= 0.0:
                return
            dy = -int(70 * (1.0 - _ease_out(drop)))
        if motion.wobble is not None and motion.wobble[0] == parcel.parcel_id:
            elapsed = now - motion.wobble[1]
            if elapsed < WOBBLE_SECONDS:
                dx += int(7 * (1 - elapsed / WOBBLE_SECONDS) * (1 if int(elapsed * 36) % 2 else -1))
        pulse = motion.pulses.get(parcel.parcel_id)
        if pulse is not None and now - pulse < PULSE_SECONDS:
            dy -= int(10 * math.sin(math.pi * (now - pulse) / PULSE_SECONDS))
        lit = motion.lit == parcel.parcel_id
        image = self.art.parcel(rect.size, parcel.colour, lit=lit)
        target.blit(image, (rect.x + dx, rect.y - BOW_HEIGHT + dy))

    # -- FX -------------------------------------------------------------------------

    def _draw_fx(self, target: pygame.Surface, motion: SceneMotion, now: float) -> None:
        for name, position, start in motion.fx:
            frames = self.art.fx_frames(name)
            duration = _fx_seconds(name)
            age = now - start
            if not frames or age >= duration:
                continue
            frame = frames[min(len(frames) - 1, int(age / duration * len(frames)))]
            drift = int(FX_DRIFT.get(name, 0.0) * age / duration)
            target.blit(frame, frame.get_rect(center=(position[0], position[1] + drift)))


def _dashed(target: pygame.Surface, start: tuple[int, int], end: tuple[int, int]) -> None:
    """Sunshine guide line with an ink edge, drawn as short dashes."""

    (x0, y0), (x1, y1) = start, end
    length = max(1.0, math.hypot(x1 - x0, y1 - y0))
    pitch, dash = 18, 12
    for step in range(int(length // pitch) + 1):
        a = step * pitch / length
        b = min(1.0, (step * pitch + dash) / length)
        p = (int(x0 + (x1 - x0) * a), int(y0 + (y1 - y0) * a))
        q = (int(x0 + (x1 - x0) * b), int(y0 + (y1 - y0) * b))
        pygame.draw.line(target, INK, p, q, 10)
        pygame.draw.line(target, SUNSHINE, p, q, 5)


__all__ = [
    "BlockHop",
    "MeasureCast",
    "MeasureRenderer",
    "SceneMotion",
    "balance_ends",
    "parcel_rect",
    "rows_for",
]
