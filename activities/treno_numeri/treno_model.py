"""Treno Numeri — pure domain model (no pygame, no clock).

Numbers ladder rung 2 (ages 4-5): **count out / make N**. The station board
orders N cargo (numeral + dot card at first, numeral alone later); the child
loads cargo into the wagons one at a time and decides when to send the train.
Nothing stops the child at N — loading more is always possible — so stopping
at the right number is the child's decision. Later stages compare two wagons:
the first wagon arrives already loaded and the child makes the second one the
*same* (from empty, then from a wagon that has more or fewer).

Ten wagon slots form a ten-frame: slots 0-4 are the first (orange) wagon,
5-9 the second (green) wagon. The app owns timing/animation and calls the
explicit transitions below; tests drive them directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import random
from typing import Final

if __package__:
    from .treno_content import FIELD_JITTER, WAGON_WELLS, CargoKind, field_cells
else:
    from treno_content import FIELD_JITTER, WAGON_WELLS, CargoKind, field_cells

STATIONS_PER_JOURNEY: Final[int] = 5
MIN_STAGE: Final[int] = 1
MAX_STAGE: Final[int] = 5
PROMOTE_AFTER_CLEAN: Final[int] = 3
DEMOTE_AFTER_STRUGGLES: Final[int] = 2
SLOTS: Final[int] = 2 * WAGON_WELLS
FIELD_SIZE: Final[int] = len(field_cells())


class TaskKind(StrEnum):
    COUNT_OUT = "count_out"  # the board shows N: load exactly N
    SAME = "same"  # the first wagon shows the order: make the second the same


@dataclass(frozen=True, slots=True)
class StageSpec:
    """One rung of the adaptive ladder (never a menu the child chooses)."""

    stage: int
    task: TaskKind
    orders: tuple[int, ...]
    pile: int  # cargo waiting on the platform at arrival
    sign_dots: bool  # the board shows a dot card under the numeral
    preload: bool = False  # SAME: the second wagon arrives with more/fewer


STAGES: Final[dict[int, StageSpec]] = {
    1: StageSpec(1, TaskKind.COUNT_OUT, (1, 2, 3), 5, True),
    2: StageSpec(2, TaskKind.COUNT_OUT, (2, 3, 4, 5), 7, False),
    3: StageSpec(3, TaskKind.COUNT_OUT, (6, 7, 8, 9), 10, False),
    4: StageSpec(4, TaskKind.SAME, (2, 3, 4), 6, False),
    5: StageSpec(5, TaskKind.SAME, (2, 3, 4), 5, False, preload=True),
}


def clamp_stage(stage: object) -> int:
    try:
        value = int(stage)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return MIN_STAGE
    return max(MIN_STAGE, min(MAX_STAGE, value))


@dataclass(slots=True)
class Cargo:
    """One cargo item: on the platform (``slot is None``) or in a wagon slot."""

    item_id: int
    home: int  # platform cell it returns to when unloaded
    x: float
    y: float
    slot: int | None = None
    locked: bool = False  # the SAME order wagon's sample cargo

    @property
    def on_platform(self) -> bool:
        return self.slot is None


class Phase(StrEnum):
    ARRIVING = "arriving"
    LOADING = "loading"
    DEMONSTRATING = "demonstrating"
    DEPARTING = "departing"
    DONE = "done"


class MoveResult(StrEnum):
    MOVED = "moved"
    FULL = "full"
    IGNORED = "ignored"


class GoResult(StrEnum):
    CORRECT = "correct"
    TOO_FEW = "too_few"
    TOO_MANY = "too_many"
    IGNORED = "ignored"


@dataclass(frozen=True, slots=True)
class MoveOutcome:
    result: MoveResult
    item_id: int = -1
    slot: int = -1
    count: int = 0  # cargo in the child's wagon(s) after the move


@dataclass(slots=True)
class Station:
    """One station: read the order, load cargo, decide when to send the train."""

    spec: StageSpec
    kind: CargoKind
    order: int
    items: list[Cargo]
    phase: Phase = Phase.ARRIVING
    mistakes: int = 0
    hints: int = 0
    last_result: GoResult | None = None
    _slots: list[int | None] = field(default_factory=lambda: [None] * SLOTS)

    def __post_init__(self) -> None:
        for item in self.items:
            if item.slot is not None:
                self._slots[item.slot] = item.item_id

    # -- queries ------------------------------------------------------------

    @property
    def task(self) -> TaskKind:
        return self.spec.task

    @property
    def child_slots(self) -> range:
        """Slots the child fills: the whole train, or only the second wagon."""

        return range(SLOTS) if self.task is TaskKind.COUNT_OUT else range(WAGON_WELLS, SLOTS)

    @property
    def child_wagons(self) -> tuple[int, ...]:
        return (0, 1) if self.task is TaskKind.COUNT_OUT else (1,)

    @property
    def loaded(self) -> int:
        return sum(1 for slot in self.child_slots if self._slots[slot] is not None)

    @property
    def clean(self) -> bool:
        """Sent right first time with at most one gentle idle hint."""

        return self.mistakes == 0 and self.hints <= 1

    def item(self, item_id: int) -> Cargo:
        return self.items[item_id]

    def item_in_slot(self, slot: int) -> Cargo | None:
        item_id = self._slots[slot]
        return None if item_id is None else self.items[item_id]

    def platform_items(self) -> list[Cargo]:
        return [item for item in self.items if item.on_platform]

    def next_platform_item(self) -> Cargo | None:
        """Leftmost waiting cargo: the one a hint points at."""

        waiting = self.platform_items()
        return min(waiting, key=lambda it: (it.x, it.y)) if waiting else None

    def filled_slots(self) -> list[int]:
        """Child-wagon slots holding cargo, in reading (counting) order."""

        return [slot for slot in self.child_slots if self._slots[slot] is not None]

    def sample_slots(self) -> list[int]:
        """The SAME task's order: the first wagon's locked cargo slots."""

        return [slot for slot in range(WAGON_WELLS) if (it := self.item_in_slot(slot)) and it.locked]

    def free_slots(self) -> list[int]:
        return [slot for slot in self.child_slots if self._slots[slot] is None]

    def extra_slots(self) -> list[int]:
        """Cargo beyond the order, in counting order (empty unless too many)."""

        return self.filled_slots()[self.order:]

    def missing_slots(self) -> list[int]:
        """Where the missing cargo would go (empty unless too few)."""

        return self.free_slots()[: max(0, self.order - self.loaded)]

    def wagon_has_cargo(self, wagon: int) -> bool:
        if wagon not in self.child_wagons:
            return False
        bays = range(wagon * WAGON_WELLS, (wagon + 1) * WAGON_WELLS)
        return any((it := self.item_in_slot(slot)) is not None and not it.locked for slot in bays)

    # -- transitions ----------------------------------------------------------

    def arrived(self) -> None:
        if self.phase is Phase.ARRIVING:
            self.phase = Phase.LOADING

    def load(self, item_id: int) -> MoveOutcome:
        """Move one platform cargo into the first free slot (never capped at N)."""

        if self.phase is not Phase.LOADING or not 0 <= item_id < len(self.items):
            return MoveOutcome(MoveResult.IGNORED)
        item = self.items[item_id]
        if not item.on_platform:
            return MoveOutcome(MoveResult.IGNORED)
        free = self.free_slots()
        if not free:
            return MoveOutcome(MoveResult.FULL, item_id)
        slot = free[0]
        item.slot = slot
        self._slots[slot] = item_id
        return MoveOutcome(MoveResult.MOVED, item_id, slot, self.loaded)

    def unload(self, wagon: int) -> MoveOutcome:
        """Send the last cargo of ``wagon`` back to its platform spot."""

        if self.phase is not Phase.LOADING or not self.wagon_has_cargo(wagon):
            return MoveOutcome(MoveResult.IGNORED)
        for slot in reversed(range(wagon * WAGON_WELLS, (wagon + 1) * WAGON_WELLS)):
            item = self.item_in_slot(slot)
            if item is not None and not item.locked:
                self._slots[slot] = None
                item.slot = None
                return MoveOutcome(MoveResult.MOVED, item.item_id, slot, self.loaded)
        return MoveOutcome(MoveResult.IGNORED)

    def go(self) -> GoResult:
        """The child sends the train: right amount departs, otherwise demonstrate."""

        if self.phase is not Phase.LOADING or self.loaded == 0:
            return GoResult.IGNORED
        if self.loaded == self.order:
            self.phase = Phase.DEPARTING
            result = GoResult.CORRECT
        else:
            self.mistakes += 1
            self.phase = Phase.DEMONSTRATING
            result = GoResult.TOO_MANY if self.loaded > self.order else GoResult.TOO_FEW
        self.last_result = result
        return result

    def finish_demonstration(self) -> None:
        if self.phase is Phase.DEMONSTRATING:
            self.phase = Phase.LOADING

    def note_hint(self) -> None:
        self.hints += 1

    def departed(self) -> None:
        if self.phase is Phase.DEPARTING:
            self.phase = Phase.DONE


class StationFactory:
    """Build stations for a stage from an injected RNG (deterministic in tests)."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    def build(
        self,
        stage: int,
        *,
        previous_order: int | None = None,
        previous_kind: CargoKind | None = None,
        order: int | None = None,
        preload: int | None = None,
    ) -> Station:
        spec = STAGES[clamp_stage(stage)]
        if order is None:
            options = [value for value in spec.orders if value != previous_order] or list(spec.orders)
            order = self._rng.choice(options)
        order = max(1, min(SLOTS - 1, int(order)))
        kind = self._rng.choice([kind for kind in CargoKind if kind is not previous_kind])
        cells = field_cells()
        items: list[Cargo] = []
        if spec.task is TaskKind.SAME:
            # The order wagon's sample cargo: locked, never on the platform.
            for slot in range(min(order, WAGON_WELLS)):
                items.append(Cargo(len(items), -1, 0.0, 0.0, slot=slot, locked=True))
        preloaded = 0
        if spec.preload:
            preloaded = preload if preload is not None else self._preload(order)
            preloaded = max(1, min(WAGON_WELLS, preloaded))
        pile = max(spec.pile, order + 2 - preloaded)
        homes = self._rng.sample(range(len(cells)), min(len(cells), pile + preloaded))
        for index, home in enumerate(homes):
            cx, cy = cells[home]
            x = cx + self._rng.uniform(-FIELD_JITTER, FIELD_JITTER)
            y = cy + self._rng.uniform(-FIELD_JITTER / 2, FIELD_JITTER / 2)
            slot = WAGON_WELLS + index if index < preloaded else None
            items.append(Cargo(len(items), home, x, y, slot=slot))
        return Station(spec=spec, kind=kind, order=order, items=items)

    def _preload(self, order: int) -> int:
        """More or fewer than the order (never the same), within one wagon."""

        options = [order + delta for delta in (-2, -1, 1, 2) if 1 <= order + delta <= WAGON_WELLS]
        return self._rng.choice(options)


@dataclass(frozen=True, slots=True)
class StationSummary:
    order: int
    stage: int
    clean: bool
    mistakes: int


@dataclass(slots=True)
class TrainProgress:
    """Bounded, profile-scoped learning state (persisted by the services)."""

    stage: int = MIN_STAGE
    clean_streak: int = 0
    struggle_streak: int = 0
    stations_completed: int = 0
    journeys_completed: int = 0
    highest_order: int = 0

    def record(self, summary: StationSummary) -> None:
        """Adapt: 3 clean stations -> next stage; 2 struggling ones -> back one."""

        self.stations_completed += 1
        self.highest_order = max(self.highest_order, summary.order)
        if summary.clean:
            self.clean_streak += 1
            self.struggle_streak = 0
        else:
            self.clean_streak = 0
            if summary.mistakes > 0:
                self.struggle_streak += 1
        if self.clean_streak >= PROMOTE_AFTER_CLEAN and self.stage < MAX_STAGE:
            self.stage += 1
            self.clean_streak = 0
            self.struggle_streak = 0
        elif self.struggle_streak >= DEMOTE_AFTER_STRUGGLES and self.stage > MIN_STAGE:
            self.stage -= 1
            self.clean_streak = 0
            self.struggle_streak = 0


class Journey:
    """Five stations per visit (1-3 minutes), progress dots and a real ending."""

    def __init__(
        self,
        factory: StationFactory,
        progress: TrainProgress | None = None,
        *,
        stations: int = STATIONS_PER_JOURNEY,
    ) -> None:
        if stations < 1:
            raise ValueError("a journey needs at least one station")
        self.factory = factory
        self.progress = progress if progress is not None else TrainProgress()
        self.total_stations = stations
        self.completed = 0
        self.summaries: list[StationSummary] = []
        self.current = factory.build(self.progress.stage)

    @property
    def complete(self) -> bool:
        return self.completed >= self.total_stations

    @property
    def stage(self) -> int:
        return self.progress.stage

    def finish_station(self) -> StationSummary:
        """Record the departed station and adapt the stage."""

        station = self.current
        station.departed()
        summary = StationSummary(station.order, station.spec.stage, station.clean, station.mistakes)
        self.summaries.append(summary)
        del self.summaries[:-STATIONS_PER_JOURNEY]
        self.completed += 1
        self.progress.record(summary)
        return summary

    def next_station(self) -> Station:
        previous = self.current
        self.current = self.factory.build(
            self.progress.stage,
            previous_order=previous.order,
            previous_kind=previous.kind,
        )
        return self.current

    def restart(self) -> Station:
        self.completed = 0
        self.summaries.clear()
        return self.next_station()


__all__ = [
    "Cargo",
    "GoResult",
    "Journey",
    "MAX_STAGE",
    "MIN_STAGE",
    "MoveOutcome",
    "MoveResult",
    "Phase",
    "SLOTS",
    "STAGES",
    "STATIONS_PER_JOURNEY",
    "StageSpec",
    "Station",
    "StationFactory",
    "StationSummary",
    "TaskKind",
    "TrainProgress",
    "clamp_stage",
]
