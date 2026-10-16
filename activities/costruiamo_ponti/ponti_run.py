"""The GO test as a small deterministic timeline (no Pygame).

``BridgeRun`` turns a ``TrialResult`` into what the child watches: the hinged
planks swing down (``lowered`` 0 -> 1), then the friend walks from the left
bank. A just-right plank sparkles as the friend passes its middle. The walk
ends at the picnic (``ARRIVED``) or gently at the problem (``STOPPED``): at the
edge of an empty span or of a plank that falls short, or in the middle of a
thin plank that bends under a heavy load (``sag``). ``start_return`` then walks
the friend home while the planks swing back up for the next try.

All positions are logical pixels from ``CrossingView``; time advances only
through ``advance(dt)`` so tests and frames see the same run.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
from typing import Final

if __package__:
    from .ponti_layout import BANK_TOP, UNIT, CrossingView, thickness
    from .ponti_model import BridgeState, Failure, Fit, TrialResult
else:
    from ponti_layout import BANK_TOP, UNIT, CrossingView, thickness
    from ponti_model import BridgeState, Failure, Fit, TrialResult

LOWER_SECONDS: Final = 0.75
RAISE_SECONDS: Final = 0.55
WALK_SPEED: Final = 190.0  # logical px per second
RETURN_SPEED: Final = 330.0
SAG_MAX: Final = 22.0
EDGE_STOP: Final = 22  # the friend stops this far before an edge
HOP_HEIGHT: Final = 7.0
HOP_RATE: Final = 7.0


class RunPhase(StrEnum):
    LOWER = "lower"
    WALK = "walk"
    ARRIVED = "arrived"
    STOPPED = "stopped"
    RETURN = "return"
    HOME = "home"


@dataclass(frozen=True, slots=True)
class LaidPlank:
    """A lowered plank as the walk sees it (logical px)."""

    piece: int
    seat_x: int
    tip_x: int
    top: int  # walking surface when straight
    fit: Fit
    bends: bool


class BridgeRun:
    """Timeline of one GO test."""

    def __init__(self, state: BridgeState, view: CrossingView, result: TrialResult | None = None) -> None:
        self.result = result if result is not None else state.evaluate()
        self.view = view
        self.phase = RunPhase.LOWER
        self.elapsed = 0.0
        self.lowered = 0.0
        self.sag = 0.0
        self.x = float(view.home_x)
        self.walked = 0.0
        self.planks: tuple[LaidPlank, ...] = self._lay(state)
        self._passed: set[int] = set()
        self.target_x = float(self._target())

    # -- geometry ----------------------------------------------------------------

    def _lay(self, state: BridgeState) -> tuple[LaidPlank, ...]:
        fits = {r.span.seat: r for r in self.result.results}
        laid = []
        for index, where in enumerate(state.seat_of):
            if where is None or state.is_pillar(index) or where not in state.seats():
                continue
            piece = state.piece(index)
            seat_x = self.view.seat_x(where)
            result = fits.get(where)
            laid.append(
                LaidPlank(
                    piece=index,
                    seat_x=seat_x,
                    tip_x=seat_x + piece.length * UNIT,
                    top=BANK_TOP - thickness(piece.strong),
                    fit=result.fit if result is not None else Fit.JUST_RIGHT,
                    bends=result is not None and not result.holds,
                )
            )
        return tuple(laid)

    def _target(self) -> int:
        result = self.result
        if result.failure is None:
            return self.view.arrive_x
        failed = result.results[result.failed_index or 0]
        edge = self.view.x(failed.span.start)
        if result.failure is Failure.BEND:
            plank = self.plank_for(failed.piece)
            if plank is not None:
                return (plank.seat_x + min(plank.tip_x, self.view.x(failed.span.end))) // 2
        return edge - EDGE_STOP

    def plank_for(self, piece: int | None) -> LaidPlank | None:
        for plank in self.planks:
            if plank.piece == piece:
                return plank
        return None

    @property
    def bending(self) -> LaidPlank | None:
        if self.result.failure is not Failure.BEND:
            return None
        failed = self.result.results[self.result.failed_index or 0]
        return self.plank_for(failed.piece)

    # -- time ----------------------------------------------------------------------

    @property
    def finished(self) -> bool:
        return self.phase in (RunPhase.ARRIVED, RunPhase.STOPPED, RunPhase.HOME)

    def advance(self, dt: float) -> list[str]:
        """Advance ``dt`` seconds; return the moments that happened ("landed", ...)."""

        dt = max(0.0, min(0.1, dt))
        events: list[str] = []
        self.elapsed += dt
        if self.phase is RunPhase.LOWER:
            self.lowered = min(1.0, self.lowered + dt / LOWER_SECONDS)
            if self.lowered >= 1.0:
                self.phase = RunPhase.WALK
                events.append("landed")
            return events
        if self.phase is RunPhase.WALK:
            self.x = min(self.target_x, self.x + WALK_SPEED * dt)
            self.walked += WALK_SPEED * dt
            for plank in self.planks:
                middle = (plank.seat_x + plank.tip_x) / 2
                if plank.piece not in self._passed and self.x >= middle and not plank.bends:
                    self._passed.add(plank.piece)
                    events.append(f"pass:{plank.piece}")
            bending = self.bending
            if bending is not None and self.x > bending.seat_x:
                if self.sag == 0.0:
                    events.append("bend")
                span = max(1.0, self.target_x - bending.seat_x)
                self.sag = SAG_MAX * min(1.0, (self.x - bending.seat_x) / span)
            if self.x >= self.target_x:
                self.phase = RunPhase.ARRIVED if self.result.success else RunPhase.STOPPED
                events.append("arrive" if self.result.success else "stop")
            return events
        if self.phase is RunPhase.RETURN:
            self.x = max(float(self.view.home_x), self.x - RETURN_SPEED * dt)
            self.sag = max(0.0, self.sag - SAG_MAX * dt / 0.25)
            self.lowered = max(0.0, self.lowered - dt / RAISE_SECONDS)
            if self.x <= self.view.home_x and self.lowered <= 0.0:
                self.phase = RunPhase.HOME
                events.append("home")
        return events

    def start_return(self) -> None:
        if self.phase is RunPhase.STOPPED:
            self.phase = RunPhase.RETURN

    # -- what to draw -------------------------------------------------------------

    def angle(self) -> float:
        """Plank angle in degrees: 90 standing up, 0 lying across (eased)."""

        t = self.lowered
        eased = t * t * (3 - 2 * t)
        return 90.0 * (1.0 - eased)

    def sag_at(self, plank: LaidPlank, x: float) -> float:
        if plank is not self.bending or self.sag <= 0.0:
            return 0.0
        length = max(1.0, plank.tip_x - plank.seat_x)
        u = (x - plank.seat_x) / length
        return self.sag * math.sin(math.pi * max(0.0, min(1.0, u)))

    def surface_y(self, x: float) -> float:
        """Where the friend's feet are at ``x`` (bank, plank top, bent plank)."""

        if self.lowered < 1.0 and self.phase is not RunPhase.RETURN:
            return float(BANK_TOP)
        best = float(BANK_TOP)
        on_plank = False
        for plank in self.planks:
            if plank.seat_x - 2 <= x <= plank.tip_x + 2:
                y = plank.top + self.sag_at(plank, x)
                best = y if not on_plank else min(best, y)
                on_plank = True
        return best

    def traveler_midbottom(self) -> tuple[int, int]:
        y = self.surface_y(self.x)
        moving = self.phase in (RunPhase.WALK, RunPhase.RETURN)
        hop = abs(math.sin(self.elapsed * HOP_RATE)) * HOP_HEIGHT if moving else 0.0
        return (int(round(self.x)), int(round(y - hop + 4)))


__all__ = ["BridgeRun", "LaidPlank", "RunPhase", "LOWER_SECONDS", "RAISE_SECONDS"]
