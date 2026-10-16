"""Rules of The Big Seasons Tree (pure, no Pygame).

A round dresses one season's scene. Its missions come from
``tree_content.plan_missions``; each mission shows picture cards and exactly
one belongs to the season. The child picks a card:

* the right card -> it is placed in the scene and the round moves on;
* a card that does not belong -> it is tried in the scene, comes back and
  stays greyed; retries are unlimited and the round never fails.

The ladder adapts from the misses of a finished round.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import random

if __package__:
    from .tree_content import ITEMS, MAX_LEVEL, Mission, Season, Slot, plan_missions
else:
    from tree_content import ITEMS, MAX_LEVEL, Mission, Season, Slot, plan_missions


class Pick(StrEnum):
    RIGHT = "right"
    WRONG = "wrong"
    IGNORED = "ignored"


@dataclass(frozen=True, slots=True)
class PickOutcome:
    pick: Pick
    item_id: str = ""
    slot: Slot | None = None
    task_misses: int = 0


@dataclass(slots=True)
class DressRound:
    """State of one round: the season, its missions, what is placed, misses."""

    season: Season
    level: int
    rng: random.Random = field(default_factory=random.Random)
    missions: tuple[Mission, ...] = ()
    index: int = 0
    placed: dict[Slot, str] = field(default_factory=dict)
    tried: set[str] = field(default_factory=set)
    misses: int = 0
    task_misses: int = 0
    first_try: int = 0

    def __post_init__(self) -> None:
        self.level = max(0, min(MAX_LEVEL, int(self.level)))
        if not self.missions:
            self.missions = plan_missions(self.season, self.level, self.rng)

    @property
    def complete(self) -> bool:
        return self.index >= len(self.missions)

    @property
    def mission(self) -> Mission | None:
        return None if self.complete else self.missions[self.index]

    @property
    def total(self) -> int:
        return len(self.missions)

    def choose(self, item_id: str) -> PickOutcome:
        """The child picked card ``item_id`` for the current mission."""

        mission = self.mission
        if mission is None or item_id not in mission.options or item_id in self.tried:
            return PickOutcome(Pick.IGNORED, item_id)
        if item_id == mission.answer:
            if self.task_misses == 0:
                self.first_try += 1
            outcome = PickOutcome(Pick.RIGHT, item_id, mission.slot, self.task_misses)
            self.placed[mission.slot] = item_id
            self.index += 1
            self.tried.clear()
            self.task_misses = 0
            return outcome
        self.tried.add(item_id)
        self.misses += 1
        self.task_misses += 1
        return PickOutcome(Pick.WRONG, item_id, mission.slot, self.task_misses)

    def placed_item(self, slot: Slot):
        item_id = self.placed.get(slot)
        return ITEMS[item_id] if item_id is not None else None


def adapt_level(level: int, misses: int) -> int:
    """Next round's rung: a near-perfect round climbs, a hard one steps back."""

    if misses <= 1:
        return min(MAX_LEVEL, level + 1)
    if misses >= 4:
        return max(0, level - 1)
    return level


__all__ = ["DressRound", "Pick", "PickOutcome", "adapt_level"]
