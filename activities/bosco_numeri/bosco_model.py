"""Numeral catalogue and forest-walk model for Tito's Number Forest.

One core experience: *meet a numeral, find it, write it, show it*. A forest
walk takes a small teaching group of numerals (two). For each numeral Tito
counts its forest friends into a frame and says the number (MEET); the child
finds the numeral among a few numeral tiles (FIND), traces it stroke by stroke
(TRACE), then picks the frame that holds that many forest things (SHOW) — the
link from the written numeral back to its quantity. Two review finds close the
walk. Numerals are introduced 1–2, 3–4, 5 with 0, 6–7, 8–9, then 10, and the
stages of the same loop get harder:

* groups 1–2: two numeral tiles that look different, two frames far apart;
* groups 3–4: three numeral tiles, two frames closer together;
* group 5 onwards: three tiles with a look-alike decoy (6/9, 1/7, 2/5 …) and
  three frames one or two apart;
* after 10: review walks of the two numerals the child has traced least.

Numerals are language-neutral; only the spoken names come from the
Activity's approved clips. Pure logic: no Pygame import.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import random
from typing import Final, Sequence

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600
REVIEW_FINDS: Final[int] = 2
WALK_NUMERALS: Final[int] = 2
MAX_VALUE: Final[int] = 10


@dataclass(frozen=True, slots=True)
class NumeralItem:
    """One numeral with the forest friend that shows its quantity.

    ``creature`` is a shared visual ID (``creature.woodland.*`` or
    ``prop.nature.*``); ``color`` is a theme accent token for the numeral ink.
    For 0 the creature appears only on the other frames of a SHOW step.
    """

    value: int
    creature: str
    color: str


NUMERALS: Final[tuple[NumeralItem, ...]] = (
    NumeralItem(0, "prop.nature.pinecone", "grape"),
    NumeralItem(1, "creature.woodland.bear", "coral"),
    NumeralItem(2, "creature.woodland.deer", "ocean"),
    NumeralItem(3, "creature.woodland.squirrel", "orange"),
    NumeralItem(4, "creature.woodland.hedgehog", "leaf"),
    NumeralItem(5, "creature.woodland.frog", "raspberry"),
    NumeralItem(6, "creature.woodland.ladybird", "turquoise"),
    NumeralItem(7, "creature.woodland.snail", "grape"),
    NumeralItem(8, "creature.woodland.butterfly", "coral"),
    NumeralItem(9, "prop.nature.mushroom", "ocean"),
    NumeralItem(10, "prop.nature.acorn", "orange"),
)
NUMERAL_BY_VALUE: Final[dict[int, NumeralItem]] = {item.value: item for item in NUMERALS}

# Teaching order: small numbers first, zero once "none" can be contrasted with
# real quantities, ten last (it is written with two digits the child knows).
TEACHING_GROUPS: Final[tuple[tuple[int, ...], ...]] = ((1, 2), (3, 4), (5, 0), (6, 7), (8, 9), (10,))

# Numerals children confuse when reading or writing them.
LOOK_ALIKES: Final[dict[int, tuple[int, ...]]] = {
    0: (6, 8, 9),
    1: (7, 4),
    2: (5, 7),
    3: (8, 5),
    4: (1, 9),
    5: (2, 3, 6),
    6: (9, 0, 5),
    7: (1, 2),
    8: (3, 0),
    9: (6, 4),
    10: (1, 0),
}


@dataclass(frozen=True, slots=True)
class Stage:
    """How hard the finds and frames of one teaching group are."""

    find_tiles: int
    look_alike: bool
    show_cards: int
    min_gap: int
    max_gap: int


def stage_for(group: int) -> Stage:
    if group < 2:
        return Stage(2, False, 2, 2, 4)
    if group < 4:
        return Stage(3, False, 2, 2, 3)
    return Stage(3, True, 3, 1, 2)


class StepKind(StrEnum):
    MEET = "meet"
    FIND = "find"
    TRACE = "trace"
    SHOW = "show"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class ForestStep:
    """One step of a walk.

    FIND/REVIEW ``choices`` are numeral values on tiles; SHOW ``choices`` are
    quantities in frames. ``choices[correct_index]`` is always the numeral.
    """

    kind: StepKind
    numeral: NumeralItem
    choices: tuple[int, ...] = ()
    correct_index: int = 0

    def __post_init__(self) -> None:
        if self.is_choice:
            if not 2 <= len(self.choices) <= 3:
                raise ValueError("a choice step needs two or three options")
            if len(set(self.choices)) != len(self.choices):
                raise ValueError("options must be distinct")
            if any(not 0 <= value <= MAX_VALUE for value in self.choices):
                raise ValueError("options must be numerals 0-10")
            if self.choices[self.correct_index] != self.numeral.value:
                raise ValueError("the correct option must show the numeral")

    @property
    def is_find(self) -> bool:
        return self.kind in {StepKind.FIND, StepKind.REVIEW}

    @property
    def is_choice(self) -> bool:
        return self.kind in {StepKind.FIND, StepKind.REVIEW, StepKind.SHOW}

    @property
    def counts_as_task(self) -> bool:
        return self.kind is not StepKind.MEET


@dataclass(frozen=True, slots=True)
class ChoiceResult:
    correct: bool
    errors: int
    round_complete: bool = False


@dataclass(slots=True)
class _StepProgress:
    errors: int = 0
    hints: int = 0
    eliminated: set[int] = field(default_factory=set)


class WalkPlanner:
    """Build forest walks: which numerals, in which order, with which decoys."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    @property
    def group_count(self) -> int:
        return len(TEACHING_GROUPS)

    def numerals_for(self, group: int, traced: dict[int, int] | None = None) -> tuple[NumeralItem, ...]:
        """Numerals of teaching ``group``; a short group gains a practised one.

        Past the last group, a review walk takes the least-traced numerals.
        """

        counts = traced or {}
        values: list[int] = list(TEACHING_GROUPS[group]) if 0 <= group < len(TEACHING_GROUPS) else []
        if len(values) < WALK_NUMERALS:
            known = self._known_before(group) if values else tuple(NUMERAL_BY_VALUE)
            pool = [value for value in known if value not in values]
            self._rng.shuffle(pool)
            pool.sort(key=lambda value: counts.get(value, 0))  # least practised first (stable)
            values.extend(pool[: WALK_NUMERALS - len(values)])
        return tuple(NUMERAL_BY_VALUE[value] for value in values)

    def build(self, group: int, traced: dict[int, int] | None = None) -> tuple[ForestStep, ...]:
        numerals = self.numerals_for(group, traced)
        stage = stage_for(group)
        # Decoys prefer numerals the child has met (this group, then earlier).
        pool = tuple(item.value for item in numerals) + self._known_before(group)
        steps: list[ForestStep] = []
        last_slot = -1
        for item in numerals:
            steps.append(ForestStep(StepKind.MEET, item))
            find, last_slot = self._find(StepKind.FIND, item, stage, pool, last_slot)
            steps.append(find)
            steps.append(ForestStep(StepKind.TRACE, item))
            show, last_slot = self._show(item, stage, pool, last_slot)
            steps.append(show)
        for target in self._review_targets(numerals):
            review, last_slot = self._find(StepKind.REVIEW, target, stage, pool, last_slot)
            steps.append(review)
        return tuple(steps)

    # -- helpers ---------------------------------------------------------------
    def _known_before(self, group: int) -> tuple[int, ...]:
        upto = max(0, min(group, len(TEACHING_GROUPS)))
        return tuple(value for values in TEACHING_GROUPS[:upto] for value in values)

    def _review_targets(self, numerals: Sequence[NumeralItem]) -> list[NumeralItem]:
        """Review numerals in a new order; never the numeral just written first."""

        order = list(numerals)
        self._rng.shuffle(order)
        if len(order) > 1 and order[0].value == numerals[-1].value:
            order.append(order.pop(0))
        while len(order) < REVIEW_FINDS:
            order.append(self._rng.choice(list(numerals)))
        return order[:REVIEW_FINDS]

    def _place(self, target: int, decoys: Sequence[int], last_slot: int) -> tuple[tuple[int, ...], int]:
        """Insert the answer at a random slot, never the previous answer's slot."""

        options = [slot for slot in range(len(decoys) + 1) if slot != last_slot] or [0]
        slot = self._rng.choice(options)
        ordered = list(decoys)
        ordered.insert(slot, target)
        return tuple(ordered), slot

    def _find(
        self, kind: StepKind, target: NumeralItem, stage: Stage, pool: Sequence[int], last_slot: int
    ) -> tuple[ForestStep, int]:
        decoys = self._find_decoys(target.value, stage.find_tiles - 1, stage.look_alike, pool)
        choices, slot = self._place(target.value, decoys, last_slot)
        return ForestStep(kind, target, choices, slot), slot

    def _find_decoys(self, target: int, wanted: int, look_alike: bool, pool: Sequence[int]) -> list[int]:
        similar = [value for value in LOOK_ALIKES.get(target, ()) if value != target]
        picked: list[int] = []
        if look_alike and similar:
            picked.append(self._rng.choice(similar))
        preferred = [value for value in dict.fromkeys(pool) if value != target and value not in picked]
        self._rng.shuffle(preferred)
        others = [value for value in NUMERAL_BY_VALUE if value != target and value not in picked and value not in preferred]
        self._rng.shuffle(others)
        if not look_alike:
            # Early stages: decoys must look clearly different from the target.
            preferred = [value for value in preferred if value not in similar]
            others = [value for value in others if value not in similar]
        for value in preferred + others:
            if len(picked) >= wanted:
                break
            if value not in picked:
                picked.append(value)
        return picked[:wanted]

    def _show(self, target: NumeralItem, stage: Stage, pool: Sequence[int], last_slot: int) -> tuple[ForestStep, int]:
        allow_zero = 0 in pool and target.value != 0
        candidates = [
            value
            for value in range(MAX_VALUE + 1)
            if value != target.value
            and stage.min_gap <= abs(value - target.value) <= stage.max_gap
            and (value != 0 or allow_zero)
        ]
        if len(candidates) < stage.show_cards - 1:
            # Near the ends of 0–10 widen the gap rather than repeat a frame.
            candidates = [
                value
                for value in range(MAX_VALUE + 1)
                if value != target.value and abs(value - target.value) >= stage.min_gap and (value != 0 or allow_zero)
            ]
            candidates.sort(key=lambda value: abs(value - target.value))
            candidates = candidates[: max(stage.show_cards - 1, 3)]
        self._rng.shuffle(candidates)
        decoys = candidates[: stage.show_cards - 1]
        choices, slot = self._place(target.value, decoys, last_slot)
        return ForestStep(StepKind.SHOW, target, choices, slot), slot


class ForestWalk:
    """State of one walk: steps, tries, hints, written numerals, completion."""

    def __init__(self, steps: Sequence[ForestStep], *, group: int) -> None:
        if not steps:
            raise ValueError("a forest walk needs steps")
        self._steps = tuple(steps)
        self.group = int(group)
        self._index = 0
        self._progress = _StepProgress()
        self._written: list[NumeralItem] = []
        self.choice_errors = 0
        self.hints = 0
        self.first_try_choices = 0
        self._completion_consumed = False

    # -- queries -----------------------------------------------------------------
    @property
    def steps(self) -> tuple[ForestStep, ...]:
        return self._steps

    @property
    def step(self) -> ForestStep | None:
        return None if self.is_complete else self._steps[self._index]

    @property
    def step_index(self) -> int:
        return self._index

    @property
    def is_complete(self) -> bool:
        return self._index >= len(self._steps)

    @property
    def numerals(self) -> tuple[NumeralItem, ...]:
        return tuple(step.numeral for step in self._steps if step.kind is StepKind.MEET)

    @property
    def written(self) -> tuple[NumeralItem, ...]:
        """Numerals traced this walk, in order (the signposts along the path)."""

        return tuple(self._written)

    @property
    def task_total(self) -> int:
        return sum(step.counts_as_task for step in self._steps)

    @property
    def tasks_done(self) -> int:
        return sum(step.counts_as_task for step in self._steps[: self._index])

    @property
    def eliminated(self) -> frozenset[int]:
        return frozenset(self._progress.eliminated)

    @property
    def errors(self) -> int:
        return self._progress.errors

    # -- actions -----------------------------------------------------------------
    def record_hint(self) -> None:
        if not self.is_complete:
            self._progress.hints = min(32, self._progress.hints + 1)
            self.hints = min(999, self.hints + 1)

    def finish_meet(self) -> None:
        self._require(StepKind.MEET)
        self._advance()

    def select(self, index: int) -> ChoiceResult:
        step = self.step
        if step is None or not step.is_choice:
            raise RuntimeError("no options to choose from")
        if not 0 <= index < len(step.choices):
            raise IndexError("option index out of range")
        progress = self._progress
        if index in progress.eliminated:
            return ChoiceResult(False, progress.errors)
        if index != step.correct_index:
            progress.errors += 1
            progress.eliminated.add(index)
            self.choice_errors += 1
            return ChoiceResult(False, progress.errors)
        if progress.errors == 0:
            self.first_try_choices += 1
        self._advance()
        return ChoiceResult(True, 0, self.is_complete)

    def finish_trace(self) -> bool:
        """Put the written numeral on the path; True when the walk is complete."""

        step = self._require(StepKind.TRACE)
        self._written.append(step.numeral)
        self._advance()
        return self.is_complete

    def consume_completion(self) -> dict[str, int] | None:
        if not self.is_complete or self._completion_consumed:
            return None
        self._completion_consumed = True
        return {
            "group": self.group + 1,
            "numerals": len(self._written),
            "first_try": self.first_try_choices,
            "retries": self.choice_errors,
        }

    def _require(self, kind: StepKind) -> ForestStep:
        step = self.step
        if step is None or step.kind is not kind:
            raise RuntimeError(f"current step is not {kind.value}")
        return step

    def _advance(self) -> None:
        self._index += 1
        self._progress = _StepProgress()


def next_group(current: int, walk: ForestWalk, group_count: int) -> int:
    """Bounded adaptation: repeat a group the child found hard, else move on.

    Past the last teaching group the child stays in review walks
    (``group_count``), which pick the least-practised numerals.
    """

    if walk.choice_errors >= 3:
        return max(0, min(current, group_count))
    return min(group_count, current + 1)


__all__ = [
    "ChoiceResult",
    "ForestStep",
    "ForestWalk",
    "LOOK_ALIKES",
    "MAX_VALUE",
    "NUMERALS",
    "NUMERAL_BY_VALUE",
    "NumeralItem",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "REVIEW_FINDS",
    "Stage",
    "StepKind",
    "TEACHING_GROUPS",
    "WalkPlanner",
    "next_group",
    "stage_for",
]
