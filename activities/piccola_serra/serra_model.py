"""Piccola Serra -- pure greenhouse rules (no pygame, storage or audio).

* ``GrowCycle`` -- one plant from seed to harvest: every stage has one need,
  the right care cures it and the plant grows; a wrong care changes nothing
  (it is counted for hints/adaptation, never punished).
* ``SequenceTask`` -- after the harvest: put the plant's stage pictures in
  order (tap the card that comes next).
* ``Visit`` -- three plants: choose a seed -> grow -> order the pictures,
  then the shared completion scene; the rung adapts between visits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import random

if __package__:
    from .serra_content import (
        CURE,
        MAX_LEVEL,
        MIN_LEVEL,
        PLANTS_BY_ID,
        PLANTS_PER_VISIT,
        Care,
        Need,
        PlantSpec,
        Rung,
        Stage,
        rung_for,
        sequence_stages,
    )
else:
    from serra_content import (
        CURE,
        MAX_LEVEL,
        MIN_LEVEL,
        PLANTS_BY_ID,
        PLANTS_PER_VISIT,
        Care,
        Need,
        PlantSpec,
        Rung,
        Stage,
        rung_for,
        sequence_stages,
    )

LEVEL_UP_MAX_MISSES = 1
LEVEL_DOWN_MIN_MISSES = 7


class Verdict(StrEnum):
    GREW = "grew"            # right care: the plant grows to the next stage
    HARVESTED = "harvested"  # right care at the fruit stage
    NOT_YET = "not_yet"      # this care does not help this need
    IGNORED = "ignored"      # nothing to care for (already harvested)


@dataclass(frozen=True, slots=True)
class CareResult:
    verdict: Verdict
    care: Care
    need: Need | None
    stage: Stage          # stage after the care
    previous: Stage       # stage before the care
    misses: int = 0       # misses on this need so far


def plan_needs(plant: PlantSpec, pool: tuple[Need, ...], rng: random.Random) -> tuple[Need, ...]:
    """One need per stage: seeds are thirsty, the fruit is ripe, the stages in
    between draw from ``pool`` without an immediate repeat and use every
    symptom of the pool at least once when there is room."""

    middle = len(plant.stages) - 2
    picks: list[Need] = []
    bag: list[Need] = []
    previous = Need.THIRSTY
    for _ in range(middle):
        if not bag:
            bag = list(pool)
            rng.shuffle(bag)
        choice = next((need for need in bag if need is not previous), bag[0])
        bag.remove(choice)
        picks.append(choice)
        previous = choice
    return (Need.THIRSTY, *picks, Need.RIPE)


class GrowCycle:
    """One plant growing in the pot."""

    def __init__(self, plant: PlantSpec, pool: tuple[Need, ...], rng: random.Random) -> None:
        self.plant = plant
        self.needs = plan_needs(plant, pool, rng)
        self.index = 0
        self.misses = 0
        self.need_misses = 0
        self.harvested = False

    @property
    def stage(self) -> Stage:
        return self.plant.stages[self.index]

    @property
    def need(self) -> Need | None:
        return None if self.harvested else self.needs[self.index]

    @property
    def right_care(self) -> Care | None:
        need = self.need
        return CURE[need] if need is not None else None

    def apply(self, care: Care) -> CareResult:
        previous = self.stage
        need = self.need
        if need is None:
            return CareResult(Verdict.IGNORED, care, None, previous, previous, self.need_misses)
        if CURE[need] is not care:
            self.misses += 1
            self.need_misses += 1
            return CareResult(Verdict.NOT_YET, care, need, previous, previous, self.need_misses)
        self.need_misses = 0
        if need is Need.RIPE:
            self.harvested = True
            return CareResult(Verdict.HARVESTED, care, need, previous, previous)
        self.index += 1
        return CareResult(Verdict.GREW, care, need, self.stage, previous)


class Place(StrEnum):
    PLACED = "placed"
    NOT_NEXT = "not_next"
    IGNORED = "ignored"


class SequenceTask:
    """Order the stage pictures: the child taps the card that comes next."""

    def __init__(self, stages: tuple[Stage, ...], rng: random.Random) -> None:
        if len(stages) < 2:
            raise ValueError("a sequence needs at least two pictures")
        self.order = tuple(stages)
        deck = list(stages)
        # Never deal the cards already in order (there would be nothing to do).
        for _ in range(8):
            rng.shuffle(deck)
            if tuple(deck) != self.order:
                break
        if tuple(deck) == self.order:
            deck.reverse()
        self.deck = tuple(deck)
        self.placed: list[Stage] = []
        self.misses = 0
        self.slot_misses = 0

    @property
    def expected(self) -> Stage | None:
        return None if self.complete else self.order[len(self.placed)]

    @property
    def complete(self) -> bool:
        return len(self.placed) == len(self.order)

    def is_placed(self, stage: Stage) -> bool:
        return stage in self.placed

    def place(self, stage: Stage) -> Place:
        if self.complete or stage in self.placed or stage not in self.order:
            return Place.IGNORED
        if stage is not self.expected:
            self.misses += 1
            self.slot_misses += 1
            return Place.NOT_NEXT
        self.placed.append(stage)
        self.slot_misses = 0
        return Place.PLACED


class Phase(StrEnum):
    CHOOSE = "choose"      # pick a seed packet
    GROW = "grow"          # read the plant, choose the care
    SEQUENCE = "sequence"  # order the stage pictures
    DONE = "done"          # every plant of the visit is finished


@dataclass(slots=True)
class SerraProgress:
    """Bounded, profile-scoped progress (persisted by ``serra_services``)."""

    level: int = MIN_LEVEL
    harvests: int = 0
    visits: int = 0
    plants: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PlantSummary:
    plant_id: str
    level: int
    care_misses: int
    order_misses: int
    cards: int


class Visit:
    """Three plants, then the completion scene; adapts the rung per visit."""

    def __init__(self, progress: SerraProgress, rng: random.Random, *, total: int = PLANTS_PER_VISIT) -> None:
        self.progress = progress
        self.rng = rng
        self.total = int(total)
        self.rung: Rung = rung_for(progress.level)
        self.completed = 0
        self.phase = Phase.CHOOSE
        self.cycle: GrowCycle | None = None
        self.sequence: SequenceTask | None = None
        self.harvested: list[str] = []
        self.misses = 0

    @property
    def complete(self) -> bool:
        return self.phase is Phase.DONE

    # -- choose -------------------------------------------------------------

    def choose(self, plant_id: str) -> GrowCycle | None:
        plant = PLANTS_BY_ID.get(plant_id)
        if self.phase is not Phase.CHOOSE or plant is None:
            return None
        self.cycle = GrowCycle(plant, self.rung.needs, self.rng)
        self.phase = Phase.GROW
        return self.cycle

    # -- grow ---------------------------------------------------------------

    def care(self, care: Care) -> CareResult | None:
        cycle = self.cycle
        if self.phase is not Phase.GROW or cycle is None:
            return None
        if care not in self.rung.cares:
            return None
        result = cycle.apply(care)
        if result.verdict is Verdict.HARVESTED:
            plant_id = cycle.plant.plant_id
            self.harvested.append(plant_id)
            self.progress.harvests = min(1_000_000, self.progress.harvests + 1)
            self.progress.plants[plant_id] = min(1_000_000, self.progress.plants.get(plant_id, 0) + 1)
            self.sequence = SequenceTask(sequence_stages(cycle.plant, self.rung.cards), self.rng)
            self.phase = Phase.SEQUENCE
        return result

    # -- sequence -----------------------------------------------------------

    def place(self, stage: Stage) -> Place:
        if self.phase is not Phase.SEQUENCE or self.sequence is None:
            return Place.IGNORED
        return self.sequence.place(stage)

    def finish_plant(self) -> PlantSummary | None:
        """Close the current plant once its pictures are in order."""

        cycle, sequence = self.cycle, self.sequence
        if self.phase is not Phase.SEQUENCE or cycle is None or sequence is None or not sequence.complete:
            return None
        summary = PlantSummary(cycle.plant.plant_id, self.rung.level, cycle.misses, sequence.misses, len(sequence.order))
        self.misses += cycle.misses + sequence.misses
        self.completed += 1
        self.cycle = None
        self.sequence = None
        if self.completed >= self.total:
            self.phase = Phase.DONE
            self._adapt()
        else:
            self.phase = Phase.CHOOSE
        return summary

    def _adapt(self) -> None:
        progress = self.progress
        progress.visits = min(1_000_000, progress.visits + 1)
        if self.misses <= LEVEL_UP_MAX_MISSES:
            progress.level = min(MAX_LEVEL, progress.level + 1)
        elif self.misses >= LEVEL_DOWN_MIN_MISSES:
            progress.level = max(MIN_LEVEL, progress.level - 1)

    def restart(self) -> None:
        self.rung = rung_for(self.progress.level)
        self.completed = 0
        self.phase = Phase.CHOOSE
        self.cycle = None
        self.sequence = None
        self.harvested = []
        self.misses = 0


__all__ = [
    "CareResult",
    "GrowCycle",
    "LEVEL_DOWN_MIN_MISSES",
    "LEVEL_UP_MAX_MISSES",
    "Phase",
    "Place",
    "PlantSummary",
    "SequenceTask",
    "SerraProgress",
    "Verdict",
    "Visit",
    "plan_needs",
]
