"""Bridge Builders -- bridge state, the crossing test, hints and the visit (no Pygame).

``BridgeState`` is what the child edits: which tray plank stands on which
*seat* (the near edge of a span: the left bank, an island or a pillar) and
which rock holds a pillar. Planks are hinged drawbridges: during building they
stand upright on their seat and the GO test lowers them, so the result of a
choice is only revealed by the test, never marked beforehand.

``BridgeState.evaluate`` is the whole physics: walking from the left bank, the
friend stops at the first span that is empty, whose plank is too short, or
whose thin wooden plank bends under a heavy load. ``HintPlanner`` compares the
bridge with the closest working arrangement (planks of the same length and
material are interchangeable) and names the single next helpful step.
``Visit`` walks one set of four crossings; ``PontiProgress`` is the save.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
import itertools
from typing import Final

if __package__:
    from .ponti_content import CROSSING_SETS, CROSSINGS_PER_SET, Crossing, CrossingSet, PieceKind
else:
    from ponti_content import CROSSING_SETS, CROSSINGS_PER_SET, Crossing, CrossingSet, PieceKind

SNAP_AFTER_MISSES: Final = 3  # from the third miss on a crossing, the demonstration also does the step
BANK: Final = "bank"


def island_seat(index: int) -> str:
    return f"island{index}"


def spot_seat(index: int) -> str:
    return f"spot{index}"


class Fit(StrEnum):
    """How one plank meets its span (only revealed by the test)."""

    JUST_RIGHT = "just_right"
    LONG = "long"  # reaches and sticks out onto the far side
    SHORT = "short"
    EMPTY = "empty"


class Failure(StrEnum):
    EMPTY = "empty"  # no plank: the friend stops at the edge
    SHORT = "short"  # the plank does not reach: the friend stops at the edge
    BEND = "bend"  # thin wood under a heavy load: it bends, the friend steps back


@dataclass(frozen=True, slots=True)
class Span:
    """One stretch of water between two supports (units from the left edge)."""

    seat: str
    start: float  # right edge of the near support
    end: float  # left edge of the far support

    @property
    def width(self) -> float:
        return self.end - self.start


@dataclass(frozen=True, slots=True)
class SpanResult:
    span: Span
    piece: int | None
    fit: Fit
    holds: bool  # False when a thin plank bends under a heavy friend


@dataclass(frozen=True, slots=True)
class TrialResult:
    """What the GO test reveals, span by span, up to the first problem."""

    results: tuple[SpanResult, ...]
    failure: Failure | None
    failed_index: int | None

    @property
    def success(self) -> bool:
        return self.failure is None


@dataclass(frozen=True, slots=True)
class Arrangement:
    """A comparable bridge: pillar rocks used + seat -> plank signature."""

    pillars: frozenset[int]
    planks: tuple[tuple[str, tuple[str, int, bool]], ...]

    def seat_map(self) -> dict[str, tuple[str, int, bool]]:
        return dict(self.planks)


class HintAction(StrEnum):
    PLACE_PLANK = "place_plank"
    PLACE_PILLAR = "place_pillar"
    REMOVE_PILLAR = "remove_pillar"
    GO = "go"


@dataclass(frozen=True, slots=True)
class HintStep:
    action: HintAction
    seat: str | None = None
    spot: int | None = None
    signature: tuple[str, int, bool] | None = None  # the plank to use


@dataclass(slots=True)
class CrossingSummary:
    tests: int = 0
    misses: int = 0
    hints: int = 0


class BridgeState:
    """The child's planks and pillars on one crossing."""

    def __init__(self, crossing: Crossing) -> None:
        self.crossing = crossing
        count = len(crossing.pieces)
        self.seat_of: list[str | None] = [None] * count  # plank -> seat, pillar -> spot seat
        self.selected: int | None = 0 if count else None
        self.summary = CrossingSummary()
        self.revision = 0

    # -- queries ---------------------------------------------------------------

    def piece(self, index: int):
        return self.crossing.pieces[index]

    def is_pillar(self, index: int) -> bool:
        return self.piece(index).kind is PieceKind.PILLAR

    def in_tray(self, index: int) -> bool:
        return self.seat_of[index] is None

    def tray_pieces(self) -> list[int]:
        return [index for index, where in enumerate(self.seat_of) if where is None]

    def occupant(self, seat: str) -> int | None:
        for index, where in enumerate(self.seat_of):
            if where == seat and not self.is_pillar(index):
                return index
        return None

    def pillar_at(self, spot: int) -> int | None:
        seat = spot_seat(spot)
        for index, where in enumerate(self.seat_of):
            if where == seat and self.is_pillar(index):
                return index
        return None

    def pillar_spots(self) -> list[int]:
        return [spot for spot in range(len(self.crossing.spots)) if self.pillar_at(spot) is not None]

    def spans(self) -> tuple[Span, ...]:
        """Current spans, left to right, given the islands and placed pillars."""

        crossing = self.crossing
        supports: list[tuple[float, float, str]] = [
            (start, start + width, island_seat(index)) for index, (start, width) in enumerate(crossing.islands)
        ]
        supports += [(crossing.spots[spot], crossing.spots[spot] + 1, spot_seat(spot)) for spot in self.pillar_spots()]
        supports.sort()
        result: list[Span] = []
        edge, seat = 0.0, BANK
        for start, end, support_seat in supports:
            if start > edge:
                result.append(Span(seat, edge, start))
            edge, seat = max(edge, end), support_seat
        if crossing.gap > edge:
            result.append(Span(seat, edge, float(crossing.gap)))
        return tuple(result)

    def seats(self) -> tuple[str, ...]:
        return tuple(span.seat for span in self.spans())

    def evaluate(self) -> TrialResult:
        heavy = self.crossing.heavy
        results: list[SpanResult] = []
        for index, span in enumerate(self.spans()):
            piece = self.occupant(span.seat)
            if piece is None:
                results.append(SpanResult(span, None, Fit.EMPTY, False))
                return TrialResult(tuple(results), Failure.EMPTY, index)
            plank = self.piece(piece)
            if plank.length < span.width:
                results.append(SpanResult(span, piece, Fit.SHORT, False))
                return TrialResult(tuple(results), Failure.SHORT, index)
            fit = Fit.JUST_RIGHT if plank.length == span.width else Fit.LONG
            holds = plank.strong or not heavy
            results.append(SpanResult(span, piece, fit, holds))
            if not holds:
                return TrialResult(tuple(results), Failure.BEND, index)
        return TrialResult(tuple(results), None, None)

    def arrangement(self) -> Arrangement:
        seats = set(self.seats())
        planks = tuple(
            sorted(
                (where, self.piece(index).signature)
                for index, where in enumerate(self.seat_of)
                if where is not None and not self.is_pillar(index) and where in seats
            )
        )
        return Arrangement(frozenset(self.pillar_spots()), planks)

    # -- edits -----------------------------------------------------------------

    def select(self, index: int) -> bool:
        if not (0 <= index < len(self.seat_of)) or not self.in_tray(index):
            return False
        self.selected = index
        return True

    def tray_choice(self, *, pillar: bool) -> int | None:
        """The selected tray piece when it is of the wanted kind, else the first one."""

        selected = self.selected
        if selected is not None and self.in_tray(selected) and self.is_pillar(selected) == pillar:
            return selected
        for index in self.tray_pieces():
            if self.is_pillar(index) == pillar:
                return index
        return None

    def place_plank(self, index: int, seat: str) -> int | None:
        """Stand plank ``index`` on ``seat``; a plank already there goes back to the tray."""

        if self.is_pillar(index) or seat not in self.seats():
            raise ValueError("planks stand on seats")
        displaced = self.occupant(seat)
        if displaced == index:
            return None
        if displaced is not None:
            self.seat_of[displaced] = None
        self.seat_of[index] = seat
        self._reselect(prefer=displaced)
        self.revision += 1
        return displaced

    def place_pillar(self, index: int, spot: int) -> bool:
        if not self.is_pillar(index) or not (0 <= spot < len(self.crossing.spots)):
            raise ValueError("pillars stand on rocks")
        if self.pillar_at(spot) is not None or self._blocked(spot):
            return False
        self.seat_of[index] = spot_seat(spot)
        self._drop_orphans()
        self._reselect()
        self.revision += 1
        return True

    def remove(self, index: int) -> bool:
        """Send a piece back to the tray (a pillar takes its plank back too)."""

        if self.seat_of[index] is None:
            return False
        self.seat_of[index] = None
        self._drop_orphans()
        self.selected = index
        self.revision += 1
        return True

    def clear(self) -> None:
        self.seat_of = [None] * len(self.seat_of)
        self.selected = 0 if self.seat_of else None
        self.revision += 1

    def _blocked(self, spot: int) -> bool:
        """A rock is unusable when another pillar's unit overlaps it."""

        start = self.crossing.spots[spot]
        return any(abs(self.crossing.spots[other] - start) < 1 for other in self.pillar_spots() if other != spot)

    def _drop_orphans(self) -> None:
        seats = set(self.seats())
        for index, where in enumerate(self.seat_of):
            if where is not None and not self.is_pillar(index) and where not in seats:
                self.seat_of[index] = None

    def _reselect(self, prefer: int | None = None) -> None:
        if prefer is not None and self.in_tray(prefer):
            self.selected = prefer
            return
        tray = self.tray_pieces()
        if self.selected is not None and self.selected in tray:
            return
        self.selected = tray[0] if tray else None

    # -- working arrangements ---------------------------------------------------

    @property
    def solutions(self) -> tuple[Arrangement, ...]:
        """Every arrangement that gets the friend across (cached per crossing)."""

        return solve(self.crossing)


@lru_cache(maxsize=32)
def solve(crossing: Crossing) -> tuple[Arrangement, ...]:
    pillars = [index for index, piece in enumerate(crossing.pieces) if piece.kind is PieceKind.PILLAR]
    planks = [index for index, piece in enumerate(crossing.pieces) if piece.kind is PieceKind.PLANK]
    found: dict[Arrangement, None] = {}
    spot_ids = range(len(crossing.spots))
    for count in range(len(pillars) + 1):
        for spots in itertools.combinations(spot_ids, count):
            probe = BridgeState(crossing)
            ok = all(probe.place_pillar(pillar, spot) for pillar, spot in zip(pillars, spots))
            if not ok:
                continue
            seats = probe.seats()
            for chosen in itertools.permutations(planks, len(seats)):
                trial = BridgeState(crossing)
                for pillar, spot in zip(pillars, spots):
                    trial.place_pillar(pillar, spot)
                for plank, seat in zip(chosen, seats):
                    trial.place_plank(plank, seat)
                if trial.evaluate().success:
                    found[trial.arrangement()] = None
    return tuple(found)


def _exact_fits(crossing: Crossing, arrangement: Arrangement) -> int:
    probe = BridgeState(crossing)
    pillars = [i for i, piece in enumerate(crossing.pieces) if piece.kind is PieceKind.PILLAR]
    for pillar, spot in zip(pillars, sorted(arrangement.pillars)):
        probe.place_pillar(pillar, spot)
    widths = {span.seat: span.width for span in probe.spans()}
    return sum(1 for seat, signature in arrangement.planks if widths.get(seat) == signature[1])


class HintPlanner:
    """Name the single next step from the child's bridge towards one that works."""

    @staticmethod
    def closest(state: BridgeState) -> Arrangement | None:
        solutions = state.solutions
        if not solutions:
            return None
        current = state.arrangement()
        here = current.seat_map()

        def score(solution: Arrangement) -> tuple[int, int]:
            wanted = solution.seat_map()
            matches = len(current.pillars & solution.pillars) * 2
            matches -= len(current.pillars - solution.pillars) * 2
            matches += sum(1 for seat, signature in wanted.items() if here.get(seat) == signature)
            return (matches, _exact_fits(state.crossing, solution))

        return max(solutions, key=score)

    @classmethod
    def next_step(cls, state: BridgeState) -> HintStep:
        if state.evaluate().success:
            return HintStep(HintAction.GO)
        target = cls.closest(state)
        if target is None:
            return HintStep(HintAction.GO)
        current = state.arrangement()
        for spot in sorted(current.pillars - target.pillars):
            return HintStep(HintAction.REMOVE_PILLAR, spot=spot)
        for spot in sorted(target.pillars - current.pillars):
            return HintStep(HintAction.PLACE_PILLAR, spot=spot)
        here = current.seat_map()
        order = {seat: index for index, seat in enumerate(state.seats())}
        for seat, signature in sorted(target.seat_map().items(), key=lambda item: order.get(item[0], 99)):
            if here.get(seat) != signature:
                return HintStep(HintAction.PLACE_PLANK, seat=seat, signature=signature)
        return HintStep(HintAction.GO)

    @classmethod
    def piece_for(cls, state: BridgeState, step: HintStep) -> int | None:
        """The tray (or misplaced) piece that carries out ``step``."""

        if step.action is HintAction.PLACE_PILLAR:
            return state.tray_choice(pillar=True)
        if step.action is HintAction.REMOVE_PILLAR and step.spot is not None:
            return state.pillar_at(step.spot)
        if step.action is not HintAction.PLACE_PLANK or step.signature is None:
            return None
        matching = [i for i in state.tray_pieces() if state.piece(i).signature == step.signature]
        if matching:
            return matching[0]
        target = cls.closest(state)
        wanted = target.seat_map() if target is not None else {}
        for index, where in enumerate(state.seat_of):
            if where is None or state.is_pillar(index) or state.piece(index).signature != step.signature:
                continue
            if wanted.get(where) != step.signature:
                return index
        return None

    @classmethod
    def apply(cls, state: BridgeState, step: HintStep) -> bool:
        piece = cls.piece_for(state, step)
        if piece is None:
            return False
        if step.action is HintAction.REMOVE_PILLAR:
            return state.remove(piece)
        if step.action is HintAction.PLACE_PILLAR and step.spot is not None:
            return state.place_pillar(piece, step.spot)
        if step.action is HintAction.PLACE_PLANK and step.seat is not None:
            state.place_plank(piece, step.seat)
            return True
        return False


# -- progress + visit ------------------------------------------------------------


@dataclass(slots=True)
class PontiProgress:
    """Profile-scoped save: which set comes next and simple lifetime counters.

    ``legacy_stars`` keeps the first release's star count untouched (child data
    is never dropped by a migration).
    """

    next_set: int = 0
    crossings_solved: int = 0
    sets_completed: int = 0
    legacy_stars: int = 0


class Visit:
    """One set of four crossings, played to the shared completion scene."""

    def __init__(self, progress: PontiProgress, sets: tuple[CrossingSet, ...] = CROSSING_SETS) -> None:
        self.progress = progress
        self._sets = sets
        self.set_index = progress.next_set % len(sets)
        self.index = 0
        self.state = BridgeState(self.crossing_set.crossings[0])

    @property
    def crossing_set(self) -> CrossingSet:
        return self._sets[self.set_index]

    @property
    def crossing(self) -> Crossing:
        return self.state.crossing

    @property
    def total(self) -> int:
        return CROSSINGS_PER_SET

    @property
    def completed(self) -> int:
        return self.index

    @property
    def complete(self) -> bool:
        return self.index >= self.total

    def finish_crossing(self) -> None:
        self.progress.crossings_solved += 1
        self.index += 1

    def next_crossing(self) -> None:
        if not self.complete:
            self.state = BridgeState(self.crossing_set.crossings[self.index])

    def finish_set(self) -> None:
        self.progress.sets_completed += 1
        self.progress.next_set = (self.set_index + 1) % len(self._sets)

    def start_next_set(self) -> None:
        self.set_index = self.progress.next_set % len(self._sets)
        self.index = 0
        self.state = BridgeState(self.crossing_set.crossings[0])


__all__ = [
    "Arrangement",
    "BANK",
    "BridgeState",
    "CrossingSummary",
    "Failure",
    "Fit",
    "HintAction",
    "HintPlanner",
    "HintStep",
    "PontiProgress",
    "SNAP_AFTER_MISSES",
    "Span",
    "SpanResult",
    "TrialResult",
    "Visit",
    "island_seat",
    "solve",
    "spot_seat",
]
