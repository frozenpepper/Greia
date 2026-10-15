"""La Bottega delle Misure — pure domain model (no pygame, no clock).

Numbers ladder, top rung for MEASUREMENT (ages 5-7). Leo's workshop checks
parcels before they are delivered. One delivery is five jobs; each job is one
decision about size, and the jobs climb a fixed teaching order:

1. **Direct comparison** — two parcels lined up against the same start line:
   tap the longer/shorter one (or, standing on the bench, the taller/shorter).
2. **Heavier / lighter** — put both parcels on the toy balance, then tap the
   heavier/lighter one (the balance is the evidence: size can mislead).
3. **Measure with units** — the child takes wooden unit blocks from the crate
   one at a time; they lie end to end from the start line. The child decides
   when the row is exactly as long as the parcel (no gap, no overhang), checks,
   and then says how many blocks long it is. Blocks are never numbered.
4. **Compare measured lengths** — two parcels on boards that start in
   different places: measure both with blocks, then tap the longer/shorter.

Rungs are adaptive stages (never a menu): three clean jobs promote, two
struggling jobs step back. The app owns timing/animation and calls the
explicit transitions below; tests drive them directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import random
from typing import Final

if __package__:
    from .measure_content import BOARD_UNITS, LYING_HEIGHTS, MAX_UNITS, WEIGH_SIZES
else:
    from measure_content import BOARD_UNITS, LYING_HEIGHTS, MAX_UNITS, WEIGH_SIZES

JOBS_PER_DELIVERY: Final[int] = 5
MIN_STAGE: Final[int] = 1
MAX_STAGE: Final[int] = 5
PROMOTE_AFTER_CLEAN: Final[int] = 3
DEMOTE_AFTER_STRUGGLES: Final[int] = 2
PARCEL_COLOURS: Final[int] = 5
MAX_WEIGHT: Final[int] = 5


class TaskKind(StrEnum):
    COMPARE_LENGTH = "compare_length"  # two lying parcels against one start line
    COMPARE_HEIGHT = "compare_height"  # two upright parcels on the bench
    WEIGH = "weigh"  # both on the balance, then pick
    MEASURE = "measure"  # lay unit blocks end to end, then count them
    MEASURE_COMPARE = "measure_compare"  # measure two offset parcels, then pick

    @property
    def rows(self) -> int:
        """Measuring boards in this job's scene."""

        if self in {TaskKind.COMPARE_LENGTH, TaskKind.MEASURE_COMPARE}:
            return 2
        return 1 if self is TaskKind.MEASURE else 0

    @property
    def lays_blocks(self) -> bool:
        return self in {TaskKind.MEASURE, TaskKind.MEASURE_COMPARE}


class Goal(StrEnum):
    MORE = "more"  # longer / taller / heavier
    LESS = "less"  # shorter / lower / lighter


class Phase(StrEnum):
    ARRIVING = "arriving"
    LOADING = "loading"  # WEIGH: parcels go onto the balance
    LAYING = "laying"  # blocks are laid under the parcel(s)
    COUNTING = "counting"  # MEASURE: how many blocks long?
    PICKING = "picking"  # tap the parcel that answers the goal
    DEMONSTRATING = "demonstrating"
    DONE = "done"


class Answer(StrEnum):
    CORRECT = "correct"
    WRONG = "wrong"
    IGNORED = "ignored"


class RowFit(StrEnum):
    EXACT = "exact"
    SHORT = "short"  # a gap is left before the parcel's end
    LONG = "long"  # blocks overhang the parcel's end
    EMPTY = "empty"


@dataclass(frozen=True, slots=True)
class StageSpec:
    """One rung of the adaptive ladder."""

    stage: int
    kinds: tuple[TaskKind, ...]  # weighted by repetition
    units: tuple[int, int]  # parcel lengths/heights, inclusive
    difference: tuple[int, int]  # comparison differences, inclusive
    goals: tuple[Goal, ...]  # weighted by repetition


STAGES: Final[dict[int, StageSpec]] = {
    1: StageSpec(
        1, (TaskKind.COMPARE_LENGTH, TaskKind.COMPARE_HEIGHT), (2, 6), (2, 3), (Goal.MORE, Goal.MORE, Goal.LESS)
    ),
    2: StageSpec(
        2,
        (TaskKind.WEIGH, TaskKind.WEIGH, TaskKind.COMPARE_LENGTH, TaskKind.COMPARE_HEIGHT),
        (2, 6),
        (1, 2),
        (Goal.MORE, Goal.LESS),
    ),
    3: StageSpec(3, (TaskKind.MEASURE,), (2, 5), (0, 0), (Goal.MORE,)),
    4: StageSpec(
        4, (TaskKind.MEASURE, TaskKind.MEASURE, TaskKind.MEASURE_COMPARE), (3, 7), (1, 2), (Goal.MORE, Goal.LESS)
    ),
    5: StageSpec(
        5,
        (TaskKind.MEASURE_COMPARE, TaskKind.MEASURE_COMPARE, TaskKind.MEASURE),
        (3, 8),
        (1, 1),
        (Goal.MORE, Goal.LESS),
    ),
}


def clamp_stage(stage: object) -> int:
    try:
        value = int(stage)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return MIN_STAGE
    return max(MIN_STAGE, min(MAX_STAGE, value))


@dataclass(frozen=True, slots=True)
class Parcel:
    """One parcel. ``units`` is its length (lying) or height (standing) in blocks."""

    parcel_id: int
    units: int
    colour: int
    depth: int = 1  # LYING_HEIGHTS index for lying parcels
    weight: int = 0  # WEIGH only (invisible; the balance shows it)
    size: int = 1  # WEIGH_SIZES index for weighing parcels

    def __post_init__(self) -> None:
        if not 1 <= self.units <= MAX_UNITS:
            raise ValueError(f"units must be in 1..{MAX_UNITS}")
        if not 0 <= self.depth < len(LYING_HEIGHTS):
            raise ValueError("depth out of range")
        if not 0 <= self.size < len(WEIGH_SIZES):
            raise ValueError("size out of range")


@dataclass(slots=True)
class Task:
    """One workshop job: one size decision (plus laying/counting when measuring)."""

    spec: StageSpec
    kind: TaskKind
    goal: Goal
    parcels: tuple[Parcel, ...]
    choices: tuple[int, ...] = ()  # MEASURE: three numerals to count with
    stagger: int = 0  # MEASURE_COMPARE: which board starts further left
    phase: Phase = Phase.ARRIVING
    mistakes: int = 0
    hints: int = 0
    rows: list[int] = field(default_factory=list)  # blocks laid on each board
    on_pan: list[bool] = field(default_factory=list)  # WEIGH: parcel on its pan
    rejected: set[int] = field(default_factory=set)  # rejected count choices
    last_fits: tuple[RowFit, ...] = ()
    _resume: Phase = Phase.PICKING

    def __post_init__(self) -> None:
        if not self.parcels:
            raise ValueError("a job needs at least one parcel")
        if self.kind is TaskKind.MEASURE and len(self.parcels) != 1:
            raise ValueError("a measuring job has exactly one parcel")
        if self.kind is not TaskKind.MEASURE and len(self.parcels) != 2:
            raise ValueError("a comparing job has exactly two parcels")
        if self.kind is TaskKind.MEASURE:
            if len(self.choices) != 3 or self.answer not in self.choices or len(set(self.choices)) != 3:
                raise ValueError("count choices must be three distinct values including the answer")
        if not self.rows:
            self.rows = [0] * max(0, len(self.parcels) if self.kind.lays_blocks else 0)
        if not self.on_pan:
            self.on_pan = [False] * len(self.parcels)

    # -- queries -------------------------------------------------------------

    def value(self, parcel: Parcel) -> int:
        """The compared quantity: weight on the balance, otherwise blocks."""

        return parcel.weight if self.kind is TaskKind.WEIGH else parcel.units

    @property
    def target_id(self) -> int:
        """The parcel that answers the goal (comparison jobs)."""

        pick = max if self.goal is Goal.MORE else min
        return pick(self.parcels, key=self.value).parcel_id

    @property
    def answer(self) -> int:
        """MEASURE: how many blocks long the parcel is."""

        return self.parcels[0].units

    @property
    def clean(self) -> bool:
        """Done right first time with at most one gentle idle hint."""

        return self.mistakes == 0 and self.hints <= 1

    @property
    def resume_phase(self) -> Phase:
        """The interactive phase in play (the one a demonstration returns to)."""

        return self._resume if self.phase is Phase.DEMONSTRATING else self.phase

    @property
    def all_on_pans(self) -> bool:
        return all(self.on_pan)

    def tilt(self) -> int:
        """Balance beam: -1 left pan down, +1 right pan down, 0 level."""

        left = self.parcels[0].weight if self.on_pan[0] else 0
        right = self.parcels[1].weight if self.on_pan[1] else 0
        return (left < right) - (left > right)

    def fit(self, row: int) -> RowFit:
        laid = self.rows[row]
        if laid == 0:
            return RowFit.EMPTY
        units = self.parcels[row].units
        if laid == units:
            return RowFit.EXACT
        return RowFit.SHORT if laid < units else RowFit.LONG

    def missing(self, row: int) -> range:
        """Block places still empty under the parcel (a gap)."""

        return range(self.rows[row], max(self.rows[row], self.parcels[row].units))

    def extra(self, row: int) -> range:
        """Laid blocks that overhang the parcel's end."""

        return range(self.parcels[row].units, max(self.parcels[row].units, self.rows[row]))

    # -- transitions -------------------------------------------------------------

    def arrived(self) -> None:
        if self.phase is not Phase.ARRIVING:
            return
        if self.kind is TaskKind.WEIGH:
            self.phase = Phase.LOADING
        elif self.kind.lays_blocks:
            self.phase = Phase.LAYING
        else:
            self.phase = Phase.PICKING

    def load(self, parcel_id: int) -> bool:
        """WEIGH: put one parcel on its pan; both on → the child may pick."""

        if self.phase is not Phase.LOADING or not 0 <= parcel_id < len(self.parcels) or self.on_pan[parcel_id]:
            return False
        self.on_pan[parcel_id] = True
        if self.all_on_pans:
            self.phase = Phase.PICKING
        return True

    def add_block(self, row: int) -> bool:
        """Lay one more block at the end of ``row`` (never capped at the answer)."""

        if self.phase is not Phase.LAYING or not 0 <= row < len(self.rows) or self.rows[row] >= BOARD_UNITS:
            return False
        self.rows[row] += 1
        return True

    def take_block(self, row: int) -> bool:
        """Put the last block of ``row`` back in the crate."""

        if self.phase is not Phase.LAYING or not 0 <= row < len(self.rows) or self.rows[row] == 0:
            return False
        self.rows[row] -= 1
        return True

    @property
    def can_check(self) -> bool:
        return self.phase is Phase.LAYING and bool(self.rows) and all(count > 0 for count in self.rows)

    def check(self) -> Answer:
        """The child says "the blocks are as long as the parcel"."""

        if not self.can_check:
            return Answer.IGNORED
        self.last_fits = tuple(self.fit(row) for row in range(len(self.rows)))
        if all(fit is RowFit.EXACT for fit in self.last_fits):
            self.phase = Phase.COUNTING if self.kind is TaskKind.MEASURE else Phase.PICKING
            return Answer.CORRECT
        self._wrong(Phase.LAYING)
        return Answer.WRONG

    def choose_count(self, value: int) -> Answer:
        if self.phase is not Phase.COUNTING or value in self.rejected:
            return Answer.IGNORED
        if value == self.answer:
            self.phase = Phase.DONE
            return Answer.CORRECT
        self.rejected.add(value)
        self._wrong(Phase.COUNTING)
        return Answer.WRONG

    def pick(self, parcel_id: int) -> Answer:
        if self.phase is not Phase.PICKING or not 0 <= parcel_id < len(self.parcels):
            return Answer.IGNORED
        if parcel_id == self.target_id:
            self.phase = Phase.DONE
            return Answer.CORRECT
        self._wrong(Phase.PICKING)
        return Answer.WRONG

    def _wrong(self, resume: Phase) -> None:
        self.mistakes += 1
        self._resume = resume
        self.phase = Phase.DEMONSTRATING

    def finish_demonstration(self) -> None:
        if self.phase is Phase.DEMONSTRATING:
            self.phase = self._resume

    def note_hint(self) -> None:
        self.hints += 1


class TaskFactory:
    """Build jobs for a stage from an injected RNG (deterministic in tests)."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    def build(
        self,
        stage: int,
        *,
        previous: TaskKind | None = None,
        kind: TaskKind | None = None,
        goal: Goal | None = None,
    ) -> Task:
        spec = STAGES[clamp_stage(stage)]
        rng = self._rng
        if kind is None:
            options = list(spec.kinds)
            if previous in options and len(set(options)) > 1:
                options.remove(previous)  # gently prefer variety
            kind = rng.choice(options)
        if goal is None:
            goal = rng.choice(spec.goals) if kind is not TaskKind.MEASURE else Goal.MORE
        colours = rng.sample(range(PARCEL_COLOURS), 2)
        if kind is TaskKind.MEASURE:
            units = rng.randint(*spec.units)
            parcel = Parcel(0, units, colours[0], depth=rng.randrange(len(LYING_HEIGHTS)))
            return Task(spec, kind, goal, (parcel,), choices=self._count_choices(units))
        if kind is TaskKind.WEIGH:
            return Task(spec, kind, goal, self._weigh_parcels(colours))
        first, second = self._pair(spec)
        depths = rng.sample(range(len(LYING_HEIGHTS)), 2)
        parcels = (
            Parcel(0, first, colours[0], depth=depths[0]),
            Parcel(1, second, colours[1], depth=depths[1]),
        )
        return Task(spec, kind, goal, parcels, stagger=rng.randrange(2))

    def _pair(self, spec: StageSpec) -> tuple[int, int]:
        """Two different sizes within the stage's range and difference band."""

        low, high = spec.units
        pairs = [
            (a, b)
            for a in range(low, high + 1)
            for b in range(low, high + 1)
            if spec.difference[0] <= abs(a - b) <= spec.difference[1]
        ]
        return self._rng.choice(pairs)

    def _weigh_parcels(self, colours: list[int]) -> tuple[Parcel, Parcel]:
        """Two weights; often the heavier parcel is the *smaller* one."""

        rng = self._rng
        light, heavy = sorted(rng.sample(range(1, MAX_WEIGHT + 1), 2))
        small, big = sorted(rng.sample(range(len(WEIGH_SIZES)), 2))
        surprise = rng.random() < 0.5  # size must not predict weight
        heavy_size, light_size = (small, big) if surprise else (big, small)
        heavy_first = rng.random() < 0.5
        specs = [(heavy, heavy_size), (light, light_size)]
        if not heavy_first:
            specs.reverse()
        return tuple(
            Parcel(index, 1, colours[index], weight=weight, size=size) for index, (weight, size) in enumerate(specs)
        )  # type: ignore[return-value]

    def _count_choices(self, answer: int) -> tuple[int, int, int]:
        """Three consecutive numerals containing the answer, in counting order.

        The window is chosen uniformly among those that fit, so the answer is
        equally likely to be first, middle or last (no position cue) and the
        near misses are always ±1/±2.
        """

        starts = [start for start in (answer - 2, answer - 1, answer) if start >= 1 and start + 2 <= BOARD_UNITS]
        start = self._rng.choice(starts)
        return (start, start + 1, start + 2)


@dataclass(frozen=True, slots=True)
class JobSummary:
    kind: TaskKind
    stage: int
    clean: bool
    mistakes: int


@dataclass(slots=True)
class WorkshopProgress:
    """Bounded, profile-scoped learning state (persisted by the services)."""

    stage: int = MIN_STAGE
    clean_streak: int = 0
    struggle_streak: int = 0
    jobs_completed: int = 0
    deliveries_completed: int = 0

    def record(self, summary: JobSummary) -> None:
        """Adapt: 3 clean jobs -> next stage; 2 struggling ones -> back one."""

        self.jobs_completed += 1
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


class Delivery:
    """Five jobs per visit (1-3 minutes), progress dots and a real ending."""

    def __init__(
        self,
        factory: TaskFactory,
        progress: WorkshopProgress | None = None,
        *,
        jobs: int = JOBS_PER_DELIVERY,
    ) -> None:
        if jobs < 1:
            raise ValueError("a delivery needs at least one job")
        self.factory = factory
        self.progress = progress if progress is not None else WorkshopProgress()
        self.total_jobs = jobs
        self.completed = 0
        self.summaries: list[JobSummary] = []
        self.current = factory.build(self.progress.stage)

    @property
    def complete(self) -> bool:
        return self.completed >= self.total_jobs

    @property
    def stage(self) -> int:
        return self.progress.stage

    def finish_job(self) -> JobSummary:
        """Record the finished job and adapt the stage."""

        task = self.current
        summary = JobSummary(task.kind, task.spec.stage, task.clean, task.mistakes)
        self.summaries.append(summary)
        del self.summaries[:-JOBS_PER_DELIVERY]
        self.completed += 1
        self.progress.record(summary)
        return summary

    def next_job(self) -> Task:
        self.current = self.factory.build(self.progress.stage, previous=self.current.kind)
        return self.current

    def restart(self) -> Task:
        self.completed = 0
        self.summaries.clear()
        return self.next_job()


__all__ = [
    "Answer",
    "Delivery",
    "Goal",
    "JOBS_PER_DELIVERY",
    "JobSummary",
    "MAX_STAGE",
    "MIN_STAGE",
    "PARCEL_COLOURS",
    "Parcel",
    "Phase",
    "RowFit",
    "STAGES",
    "StageSpec",
    "Task",
    "TaskFactory",
    "TaskKind",
    "WorkshopProgress",
    "clamp_stage",
]
