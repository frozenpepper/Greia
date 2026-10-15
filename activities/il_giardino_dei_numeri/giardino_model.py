"""Domain model for Il Giardino dei Numeri (The Number Garden).

The first rung of the Greia numbers ladder (ages 2-5): the child touches each
garden object once, hears the counting word, and watches the object hop into
Dani's crate (one-to-one correspondence with a stable number order). When the
set is counted, the *last* number tells how many (cardinality): from stage 2 the
child answers "how many?" by choosing a numeral + dot card, which introduces
numeral-quantity pairing gently.

This module is pure (no Pygame, no clock). The app owns timing/animation and
calls the explicit transitions below; tests drive them directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import random
from typing import Final

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600

ROUNDS_PER_SESSION: Final[int] = 5
MIN_STAGE: Final[int] = 1
MAX_STAGE: Final[int] = 4
PROMOTE_AFTER_CLEAN: Final[int] = 3
DEMOTE_AFTER_STRUGGLES: Final[int] = 2
MAX_COUNT: Final[int] = 10

# -- scene geometry (reference 1024x600 logical pixels) ---------------------

CRATE_SIZE: Final[tuple[int, int]] = (416, 150)
CRATE_LEFT: Final[int] = 600
CRATE_TOP_FIVE: Final[int] = 444
CRATE_ROW_STEP: Final[int] = 80
WELL_PITCH: Final[int] = 76
WELL_FIRST_X: Final[int] = 56  # crate-local x of well 0
WELL_FLOOR_Y: Final[int] = 96  # crate-local y where an item rests
CRATE_RIM: Final[int] = 12  # transparent margin above the crate's back wall

DANI_MIDBOTTOM: Final[tuple[int, int]] = (128, 588)
DANI_HEIGHT: Final[int] = 214
DANI_RECT: Final[tuple[int, int, int, int]] = (0, 370, 235, 230)

FIELD_LEFT: Final[int] = 240
FIELD_TOP: Final[int] = 235
FIELD_RIGHT: Final[int] = 1010
FIELD_BOTTOM: Final[int] = 590
CELL_WIDTH: Final[int] = 118
CELL_HEIGHT: Final[int] = 105
CELL_JITTER: Final[int] = 10
ITEM_SIZE: Final[int] = 116
POP_ITEM_SIZE: Final[int] = 134
ITEM_HIT_RADIUS: Final[float] = 64.0
LINE_Y: Final[int] = 330
LINE_CENTER_X: Final[int] = 600
LINE_SPACING: Final[int] = 160


class Layout(StrEnum):
    LINE = "line"
    SCATTER = "scatter"


@dataclass(frozen=True, slots=True)
class StageSpec:
    """One rung of the adaptive ladder (never a menu the child chooses)."""

    stage: int
    counts: tuple[int, ...]
    layout: Layout
    choices: int  # 0 = no "how many?" question (cardinality is shown, not asked)
    wells: int  # 5 = five-frame crate, 10 = two crate rows (ten-frame)


STAGES: Final[dict[int, StageSpec]] = {
    1: StageSpec(1, (2, 3, 4), Layout.LINE, 0, 5),
    2: StageSpec(2, (2, 3, 4, 5), Layout.SCATTER, 2, 5),
    3: StageSpec(3, (3, 4, 5), Layout.SCATTER, 3, 5),
    4: StageSpec(4, (6, 7, 8, 9, 10), Layout.SCATTER, 3, 10),
}


def clamp_stage(stage: object) -> int:
    try:
        value = int(stage)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return MIN_STAGE
    return max(MIN_STAGE, min(MAX_STAGE, value))


class ItemKind(StrEnum):
    """Garden objects; each is one shared-library visual (no emoji content)."""

    APPLE = "apple"
    STRAWBERRY = "strawberry"
    CARROT = "carrot"
    FLOWER = "flower"
    MUSHROOM = "mushroom"
    ACORN = "acorn"
    LADYBIRD = "ladybird"
    BUTTERFLY = "butterfly"
    SNAIL = "snail"

    @property
    def asset_id(self) -> str:
        return _ASSET_IDS[self]


_ASSET_IDS: Final[dict[ItemKind, str]] = {
    ItemKind.APPLE: "prop.food.apple",
    ItemKind.STRAWBERRY: "prop.food.strawberry",
    ItemKind.CARROT: "prop.food.carrot",
    ItemKind.FLOWER: "prop.nature.flower",
    ItemKind.MUSHROOM: "prop.nature.mushroom",
    ItemKind.ACORN: "prop.nature.acorn",
    ItemKind.LADYBIRD: "creature.woodland.ladybird",
    ItemKind.BUTTERFLY: "creature.woodland.butterfly",
    ItemKind.SNAIL: "creature.woodland.snail",
}


def crate_rows(wells: int) -> int:
    return 2 if wells > 5 else 1


def crate_origin(row: int, wells: int) -> tuple[int, int]:
    """Top-left of one crate row; the ten-frame stacks a second row in front."""

    rows = crate_rows(wells)
    top = CRATE_TOP_FIVE - CRATE_ROW_STEP * (rows - 1) + CRATE_ROW_STEP * row
    return (CRATE_LEFT, top)


def well_position(index: int, wells: int) -> tuple[int, int]:
    """Mid-bottom resting point of well ``index`` (0-based, row-major)."""

    if not 0 <= index < wells:
        raise ValueError("well index out of range")
    row, column = divmod(index, 5)
    left, top = crate_origin(row, wells)
    return (left + WELL_FIRST_X + WELL_PITCH * column, top + WELL_FLOOR_Y)


def crate_rect(wells: int) -> tuple[int, int, int, int]:
    left, top = crate_origin(0, wells)
    rows = crate_rows(wells)
    return (left, top, CRATE_SIZE[0], CRATE_SIZE[1] + CRATE_ROW_STEP * (rows - 1))


def _overlaps(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def field_cells(wells: int) -> list[tuple[int, int]]:
    """Grid cell centres on the grass that keep clear of Dani and the crate."""

    # Prop art keeps ~15% transparent padding, so the visible body is smaller
    # than ITEM_SIZE; jitter stays inside that padding.
    half = ITEM_SIZE * 0.425
    left, top, width, height = crate_rect(wells)
    blocked = ((left, top + CRATE_RIM, width, height - CRATE_RIM), DANI_RECT)
    cells: list[tuple[int, int]] = []
    columns = (FIELD_RIGHT - FIELD_LEFT) // CELL_WIDTH
    rows = (FIELD_BOTTOM - FIELD_TOP) // CELL_HEIGHT
    for row in range(rows):
        for column in range(columns):
            cx = FIELD_LEFT + CELL_WIDTH // 2 + CELL_WIDTH * column
            cy = FIELD_TOP + CELL_HEIGHT // 2 + CELL_HEIGHT * row
            box = (cx - half, cy - half, 2 * half, 2 * half)
            if not any(_overlaps(box, tuple(map(float, other))) for other in blocked):
                cells.append((cx, cy))
    return cells


@dataclass(slots=True)
class GardenItem:
    """One countable object; ``order`` is 0 until the child counts it."""

    item_id: int
    kind: ItemKind
    x: float
    y: float
    order: int = 0

    @property
    def counted(self) -> bool:
        return self.order > 0

    def hit_test(self, px: float, py: float) -> bool:
        # Generous touch area for small fingers (well beyond the 64 px floor).
        return (px - self.x) ** 2 + (py - self.y) ** 2 <= ITEM_HIT_RADIUS**2


class Phase(StrEnum):
    COUNTING = "counting"
    ASKING = "asking"
    DEMONSTRATING = "demonstrating"
    CLOSING = "closing"
    DONE = "done"


class TapResult(StrEnum):
    COUNTED = "counted"
    ALREADY_COUNTED = "already_counted"
    IGNORED = "ignored"


class ChoiceResult(StrEnum):
    CORRECT = "correct"
    TRY_AGAIN = "try_again"
    IGNORED = "ignored"


@dataclass(frozen=True, slots=True)
class TapOutcome:
    result: TapResult
    number: int = 0
    finished_counting: bool = False


@dataclass(slots=True)
class GardenRound:
    """One basket: count every object once, then (stage >= 2) say how many."""

    spec: StageSpec
    kind: ItemKind
    items: list[GardenItem]
    choices: tuple[int, ...] = ()
    phase: Phase = Phase.COUNTING
    counted: int = 0
    mistakes: int = 0
    hints: int = 0
    rejected: set[int] = field(default_factory=set)

    @property
    def target(self) -> int:
        return len(self.items)

    @property
    def asks_question(self) -> bool:
        return bool(self.choices)

    @property
    def clean(self) -> bool:
        """First-try answer with at most one gentle idle hint."""

        return self.mistakes == 0 and self.hints <= 1

    def item(self, item_id: int) -> GardenItem:
        return self.items[item_id]

    def uncounted(self) -> list[GardenItem]:
        return [item for item in self.items if not item.counted]

    def next_uncounted(self) -> GardenItem | None:
        """Leftmost waiting object: the one a hint points at."""

        waiting = self.uncounted()
        return min(waiting, key=lambda it: (it.x, it.y)) if waiting else None

    def item_at(self, px: float, py: float) -> GardenItem | None:
        for item in reversed(self.items):
            if not item.counted and item.hit_test(px, py):
                return item
        return None

    def tap_item(self, item_id: int) -> TapOutcome:
        if self.phase is not Phase.COUNTING or not 0 <= item_id < len(self.items):
            return TapOutcome(TapResult.IGNORED)
        item = self.items[item_id]
        if item.counted:
            return TapOutcome(TapResult.ALREADY_COUNTED, item.order)
        self.counted += 1
        item.order = self.counted
        finished = self.counted >= self.target
        return TapOutcome(TapResult.COUNTED, item.order, finished)

    def finish_counting(self) -> None:
        """Counting is over: ask "how many?" or go straight to the close."""

        if self.phase is Phase.COUNTING and self.counted >= self.target:
            self.phase = Phase.ASKING if self.asks_question else Phase.CLOSING

    def choose(self, value: int) -> ChoiceResult:
        if self.phase is not Phase.ASKING or value not in self.choices or value in self.rejected:
            return ChoiceResult.IGNORED
        if value == self.target:
            self.phase = Phase.CLOSING
            return ChoiceResult.CORRECT
        self.mistakes += 1
        self.rejected.add(value)
        self.phase = Phase.DEMONSTRATING
        return ChoiceResult.TRY_AGAIN

    def finish_demonstration(self) -> None:
        if self.phase is Phase.DEMONSTRATING:
            self.phase = Phase.ASKING

    def note_hint(self) -> None:
        self.hints += 1

    def finish_close(self) -> None:
        if self.phase is Phase.CLOSING:
            self.phase = Phase.DONE


class RoundFactory:
    """Build rounds for a stage from an injected RNG (deterministic in tests)."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    def build(
        self,
        stage: int,
        *,
        previous_count: int | None = None,
        previous_kind: ItemKind | None = None,
        count: int | None = None,
    ) -> GardenRound:
        spec = STAGES[clamp_stage(stage)]
        if count is None:
            options = [value for value in spec.counts if value != previous_count] or list(spec.counts)
            count = self._rng.choice(options)
        count = max(1, min(MAX_COUNT, int(count)))
        kinds = [kind for kind in ItemKind if kind is not previous_kind]
        kind = self._rng.choice(kinds)
        positions = self._positions(spec, count)
        items = [GardenItem(index, kind, float(x), float(y)) for index, (x, y) in enumerate(positions)]
        choices = self._choices(count, spec.choices)
        return GardenRound(spec=spec, kind=kind, items=items, choices=choices)

    def _positions(self, spec: StageSpec, count: int) -> list[tuple[float, float]]:
        if spec.layout is Layout.LINE:
            start = LINE_CENTER_X - LINE_SPACING * (count - 1) / 2
            return [(start + LINE_SPACING * index, float(LINE_Y)) for index in range(count)]
        cells = field_cells(spec.wells)
        if len(cells) < count:  # defensive: geometry guarantees >= 10 cells
            raise ValueError("garden field cannot hold that many objects")
        chosen = self._rng.sample(cells, count)
        jitter = CELL_JITTER
        return [
            (cx + self._rng.uniform(-jitter, jitter), cy + self._rng.uniform(-jitter, jitter))
            for cx, cy in chosen
        ]

    def _choices(self, count: int, size: int) -> tuple[int, ...]:
        """The answer plus close distractors (+/-1 first, then +/-2)."""

        if size <= 0:
            return ()
        near = [count - 1, count + 1, count - 2, count + 2]
        near = [value for value in near if 1 <= value <= MAX_COUNT]
        first = near[:2]
        self._rng.shuffle(first)
        distractors = (first + near[2:])[: size - 1]
        values = [count, *distractors]
        self._rng.shuffle(values)
        return tuple(values)


@dataclass(frozen=True, slots=True)
class RoundSummary:
    count: int
    stage: int
    clean: bool
    mistakes: int


@dataclass(slots=True)
class GardenProgress:
    """Bounded, profile-scoped learning state (persisted by the services)."""

    stage: int = MIN_STAGE
    clean_streak: int = 0
    struggle_streak: int = 0
    total_counted: int = 0
    baskets_filled: int = 0
    sessions_completed: int = 0
    highest_count: int = 0

    def record(self, summary: RoundSummary) -> None:
        """Adapt: 3 clean baskets -> next stage; 2 struggling ones -> back one."""

        self.total_counted += summary.count
        self.baskets_filled += 1
        self.highest_count = max(self.highest_count, summary.count)
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


class GardenSession:
    """Five baskets per visit (1-3 minutes), progress dots and a real ending."""

    def __init__(
        self,
        factory: RoundFactory,
        progress: GardenProgress | None = None,
        *,
        rounds: int = ROUNDS_PER_SESSION,
    ) -> None:
        if rounds < 1:
            raise ValueError("a session needs at least one round")
        self.factory = factory
        self.progress = progress if progress is not None else GardenProgress()
        self.total_rounds = rounds
        self.completed_rounds = 0
        self.summaries: list[RoundSummary] = []
        self.current = factory.build(self.progress.stage)

    @property
    def complete(self) -> bool:
        return self.completed_rounds >= self.total_rounds

    @property
    def stage(self) -> int:
        return self.progress.stage

    def finish_round(self) -> RoundSummary:
        """Record the finished basket and adapt the stage (idempotent per round)."""

        current = self.current
        current.finish_close()
        summary = RoundSummary(current.target, current.spec.stage, current.clean, current.mistakes)
        self.summaries.append(summary)
        del self.summaries[:-ROUNDS_PER_SESSION]
        self.completed_rounds += 1
        self.progress.record(summary)
        return summary

    def next_round(self) -> GardenRound:
        previous = self.current
        self.current = self.factory.build(
            self.progress.stage,
            previous_count=previous.target,
            previous_kind=previous.kind,
        )
        return self.current

    def restart(self) -> GardenRound:
        self.completed_rounds = 0
        self.summaries.clear()
        return self.next_round()


__all__ = [
    "CRATE_SIZE",
    "ChoiceResult",
    "DANI_HEIGHT",
    "DANI_MIDBOTTOM",
    "GardenItem",
    "GardenProgress",
    "GardenRound",
    "GardenSession",
    "ITEM_SIZE",
    "POP_ITEM_SIZE",
    "ItemKind",
    "Layout",
    "MAX_STAGE",
    "MIN_STAGE",
    "Phase",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "ROUNDS_PER_SESSION",
    "RoundFactory",
    "RoundSummary",
    "STAGES",
    "StageSpec",
    "TapOutcome",
    "TapResult",
    "clamp_stage",
    "crate_origin",
    "crate_rect",
    "crate_rows",
    "field_cells",
    "well_position",
]
