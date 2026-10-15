"""Stelle Incantate — pure domain model (no pygame, no clock).

Numbers ladder rung (ages 4-6): **number order**. Each figure is a set of
numbered stars; the child lights them in counting order and the figure's
picture appears in the sky. Nothing marks the next star: finding it is the
child's decision. The stages of the one loop are an adaptive ladder:

1. 1-5 on small figures;
2. 1-10 on bigger figures;
3. count on: the first star is already lit (for example 4) — keep going;
4. count back: the biggest star is lit — count down to 1;
5. a missing number: one star has lost its numeral; at its turn the child taps
   it and picks the number from three cards;
6. teens: star 10 is lit — continue 11 to 20.

Two clean figures in a row climb a stage; two struggling figures step back.
The app owns timing/animation and calls the explicit transitions below;
tests drive them directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import random
from typing import Final

if __package__:
    from .sky_content import FIGURES_BY_ID, MEDIUM, SMALL, TEEN, Figure
else:
    from sky_content import FIGURES_BY_ID, MEDIUM, SMALL, TEEN, Figure

FIGURES_PER_NIGHT: Final[int] = 4
MIN_STAGE: Final[int] = 1
MAX_STAGE: Final[int] = 6
PROMOTE_AFTER_CLEAN: Final[int] = 2
DEMOTE_AFTER_STRUGGLES: Final[int] = 2
STRUGGLE_MISTAKES: Final[int] = 3
MAX_COUNTER: Final[int] = 10_000_000


class TaskKind(StrEnum):
    ORDER = "order"  # start at 1 and count up
    COUNT_ON = "count_on"  # the first star is given; count up from it
    COUNT_BACK = "count_back"  # the biggest star is given; count down to 1
    MISSING = "missing"  # one star lost its numeral; choose it at its turn


@dataclass(frozen=True, slots=True)
class StageSpec:
    """One rung of the adaptive ladder (never a menu the child chooses)."""

    stage: int
    task: TaskKind
    pool: tuple[str, ...]
    start: tuple[int, int] = (1, 1)  # COUNT_ON: inclusive start range
    top: int = 10  # COUNT_ON: the last number never exceeds this


STAGES: Final[dict[int, StageSpec]] = {
    1: StageSpec(1, TaskKind.ORDER, SMALL),
    2: StageSpec(2, TaskKind.ORDER, MEDIUM),
    3: StageSpec(3, TaskKind.COUNT_ON, SMALL + tuple(f for f in MEDIUM if FIGURES_BY_ID[f].star_count <= 8), (3, 6)),
    4: StageSpec(4, TaskKind.COUNT_BACK, MEDIUM),
    5: StageSpec(5, TaskKind.MISSING, MEDIUM),
    6: StageSpec(6, TaskKind.COUNT_ON, TEEN, (10, 10), top=20),
}


def clamp_stage(stage: object) -> int:
    try:
        value = int(stage)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return MIN_STAGE
    return max(MIN_STAGE, min(MAX_STAGE, value))


class Phase(StrEnum):
    PLAYING = "playing"
    CHOOSING = "choosing"  # the missing-number cards are open
    REVEALED = "revealed"


class TapResult(StrEnum):
    LIT = "lit"  # the right star: it lights
    ASK = "ask"  # the blank star at its turn: choose its number
    AGAIN = "again"  # an already lit star (harmless replay)
    WRONG = "wrong"  # not the next number
    IGNORED = "ignored"


class ChoiceResult(StrEnum):
    CORRECT = "correct"
    WRONG = "wrong"
    IGNORED = "ignored"


@dataclass(slots=True)
class SkyRound:
    """One figure: light its numbered stars in counting order.

    Invariant: lit stars are always a prefix of the counting path, so every
    newly lit star can be drawn attached to an already lit one.
    """

    figure: Figure
    spec: StageSpec
    numbers: tuple[int, ...]  # the true number of each star, in path order
    blank: int | None = None  # MISSING: path index whose numeral is hidden
    choices: tuple[int, ...] = ()
    phase: Phase = Phase.PLAYING
    mistakes: int = 0
    step_mistakes: int = 0
    hints: int = 0
    demonstrated: bool = False
    rejected: set[int] = field(default_factory=set)
    _lit: int = 0
    last_lit: int | None = None

    def __post_init__(self) -> None:
        if self.given is not None:
            self._lit = 1
            self.last_lit = 0

    # -- queries ------------------------------------------------------------

    @property
    def task(self) -> TaskKind:
        return self.spec.task

    @property
    def star_count(self) -> int:
        return self.figure.star_count

    @property
    def given(self) -> int | None:
        """Index of the star lit for the child at the start (count on/back)."""

        return 0 if self.task in (TaskKind.COUNT_ON, TaskKind.COUNT_BACK) else None

    @property
    def lit_count(self) -> int:
        return self._lit

    @property
    def complete(self) -> bool:
        return self._lit >= self.star_count

    @property
    def next_index(self) -> int | None:
        """The star to light next (never drawn; hints and tests only)."""

        return None if self.complete else self._lit

    @property
    def next_number(self) -> int | None:
        index = self.next_index
        return None if index is None else self.numbers[index]

    @property
    def descending(self) -> bool:
        return self.task is TaskKind.COUNT_BACK

    def is_lit(self, index: int) -> bool:
        return 0 <= index < self._lit

    def label(self, index: int) -> int | None:
        """The numeral printed on a star (None while it is the hidden one)."""

        if index == self.blank and not self.is_lit(index):
            return None
        return self.numbers[index]

    def lit_edges(self) -> tuple[tuple[int, int], ...]:
        return tuple(edge for edge in self.figure.edges if self.is_lit(edge[0]) and self.is_lit(edge[1]))

    def edges_to(self, index: int) -> tuple[tuple[int, int], ...]:
        """Edges completed by lighting ``index`` (both ends lit, one of them it)."""

        return tuple(edge for edge in self.lit_edges() if index in edge)

    @property
    def clean(self) -> bool:
        """Right first time with at most one gentle idle hint."""

        return self.mistakes == 0 and self.hints <= 1

    @property
    def struggled(self) -> bool:
        return self.demonstrated or self.mistakes >= STRUGGLE_MISTAKES

    # -- transitions -----------------------------------------------------------

    def tap(self, index: int) -> TapResult:
        if self.phase is not Phase.PLAYING or not 0 <= index < self.star_count:
            return TapResult.IGNORED
        if self.is_lit(index):
            return TapResult.AGAIN
        if index != self._lit:
            self.mistakes += 1
            self.step_mistakes += 1
            return TapResult.WRONG
        if index == self.blank:
            self.phase = Phase.CHOOSING
            return TapResult.ASK
        self._light(index)
        return TapResult.LIT

    def choose(self, value: int) -> ChoiceResult:
        if self.phase is not Phase.CHOOSING or value not in self.choices or value in self.rejected:
            return ChoiceResult.IGNORED
        if value != self.numbers[self._lit]:
            self.rejected.add(value)
            self.mistakes += 1
            self.step_mistakes += 1
            return ChoiceResult.WRONG
        self.phase = Phase.PLAYING
        self._light(self._lit)
        return ChoiceResult.CORRECT

    def note_hint(self) -> None:
        self.hints += 1

    def note_demonstration(self) -> None:
        self.demonstrated = True

    def _light(self, index: int) -> None:
        self._lit = index + 1
        self.last_lit = index
        self.step_mistakes = 0
        if self.complete:
            self.phase = Phase.REVEALED


@dataclass(slots=True)
class SkyProgress:
    """Durable, bounded progress (stage + streaks + revealed figures)."""

    stage: int = MIN_STAGE
    clean_streak: int = 0
    struggle_streak: int = 0
    figures_completed: int = 0
    nights_completed: int = 0
    revealed: set[str] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class FigureSummary:
    figure_id: str
    stage: int
    star_count: int
    mistakes: int
    first_try: bool


class RoundFactory:
    """Build the next figure for a stage (numbers, blank star, choices)."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng if rng is not None else random.Random()

    def build(self, stage: int, *, avoid: set[str] = frozenset(), revealed: set[str] = frozenset()) -> SkyRound:
        spec = STAGES[clamp_stage(stage)]
        figure = FIGURES_BY_ID[self._pick(spec, avoid, revealed)]
        count = figure.star_count
        blank: int | None = None
        choices: tuple[int, ...] = ()
        if spec.task is TaskKind.COUNT_BACK:
            numbers = tuple(range(count, 0, -1))
        elif spec.task is TaskKind.COUNT_ON:
            high = max(spec.start[0], min(spec.start[1], spec.top - count + 1))
            start = self.rng.randint(spec.start[0], high)
            numbers = tuple(range(start, start + count))
        else:
            numbers = tuple(range(1, count + 1))
        if spec.task is TaskKind.MISSING:
            blank = self.rng.randint(3, count - 2)  # never in the goal strip, never last
            choices = self._choices(numbers[blank])
        return SkyRound(figure, spec, numbers, blank=blank, choices=choices)

    def _pick(self, spec: StageSpec, avoid: set[str], revealed: set[str]) -> str:
        pool = [figure for figure in spec.pool if figure not in avoid] or list(spec.pool)
        unseen = [figure for figure in pool if figure not in revealed]
        return self.rng.choice(unseen or pool)

    def _choices(self, value: int) -> tuple[int, ...]:
        """The missing number plus two close look-alikes, shuffled.

        The distractor pair varies so the answer is not always the middle
        value of the three cards.
        """

        pairs = [(value - 1, value + 1), (value + 1, value + 2), (value - 2, value - 1)]
        valid = [pair for pair in pairs if min(pair) >= 1]
        values = [value, *self.rng.choice(valid)]
        self.rng.shuffle(values)
        return tuple(values)


class Night:
    """One play session: four figures, adaptive stage, durable progress."""

    def __init__(self, factory: RoundFactory, progress: SkyProgress | None = None) -> None:
        self.factory = factory
        self.progress = progress if progress is not None else SkyProgress()
        self.progress.stage = clamp_stage(self.progress.stage)
        self.completed = 0
        self.figure_ids: list[str] = []
        self.round: SkyRound = self._new_round()

    @property
    def stage(self) -> int:
        return self.progress.stage

    @property
    def total(self) -> int:
        return FIGURES_PER_NIGHT

    @property
    def complete(self) -> bool:
        return self.completed >= FIGURES_PER_NIGHT

    def finish_figure(self) -> FigureSummary:
        """Record the revealed figure and adapt the stage (once per figure)."""

        current = self.round
        summary = FigureSummary(
            current.figure.figure_id, self.stage, current.star_count, current.mistakes, current.mistakes == 0
        )
        progress = self.progress
        progress.figures_completed = min(MAX_COUNTER, progress.figures_completed + 1)
        progress.revealed.add(current.figure.figure_id)
        if current.clean:
            progress.clean_streak += 1
            progress.struggle_streak = 0
        elif current.struggled:
            progress.struggle_streak += 1
            progress.clean_streak = 0
        else:
            progress.clean_streak = 0
            progress.struggle_streak = 0
        if progress.clean_streak >= PROMOTE_AFTER_CLEAN:
            progress.stage = clamp_stage(progress.stage + 1)
            progress.clean_streak = 0
        elif progress.struggle_streak >= DEMOTE_AFTER_STRUGGLES:
            progress.stage = clamp_stage(progress.stage - 1)
            progress.struggle_streak = 0
        self.completed += 1
        if self.complete:
            progress.nights_completed = min(MAX_COUNTER, progress.nights_completed + 1)
        return summary

    def next_figure(self) -> SkyRound:
        self.round = self._new_round()
        return self.round

    def restart(self) -> SkyRound:
        self.completed = 0
        self.figure_ids.clear()
        self.round = self._new_round()
        return self.round

    def _new_round(self) -> SkyRound:
        round_ = self.factory.build(self.stage, avoid=set(self.figure_ids), revealed=self.progress.revealed)
        self.figure_ids.append(round_.figure.figure_id)
        return round_


__all__ = [
    "ChoiceResult",
    "FIGURES_PER_NIGHT",
    "FigureSummary",
    "MAX_STAGE",
    "MIN_STAGE",
    "Night",
    "Phase",
    "RoundFactory",
    "STAGES",
    "SkyProgress",
    "SkyRound",
    "StageSpec",
    "TapResult",
    "TaskKind",
    "clamp_stage",
]
