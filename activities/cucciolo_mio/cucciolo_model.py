"""Pure care-day rules for My Cute Pet (no pygame, no Greia IO).

A ``CareDay`` is one finite day of care. Needs come one at a time
(``emerge``); the child reads the pet's body language and offers a care
(``offer``). The right care starts it (``act`` once per child action until
the care is done, then ``settle``); any other care is a kind "not now" that
changes nothing - needs never get worse, nothing decays and nothing is lost.
The last need of every day is bedtime.

``plan_day`` draws the daytime needs from the level's pool with a gentle
"what comes next" logic, never the same need twice in a row, so every
choice is a real reading of the pet rather than elimination.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import random

if __package__:
    from .cucciolo_content import CARE_FOR_NEED, CARES, FIRST_NEEDS, LEVELS, MAX_LEVEL, NEXT_NEEDS, Care, Need
else:
    from cucciolo_content import CARE_FOR_NEED, CARES, FIRST_NEEDS, LEVELS, MAX_LEVEL, NEXT_NEEDS, Care, Need  # type: ignore[no-redef]


class Phase(StrEnum):
    CALM = "calm"  # the pet is content; the next need has not shown yet
    NEED = "need"  # a need is showing; waiting for the child's choice
    CARE = "care"  # the right care is being done
    DONE = "done"  # bedtime care finished: the day is over


class Offer(StrEnum):
    RIGHT = "right"
    NOT_NOW = "not_now"
    IGNORED = "ignored"


@dataclass(frozen=True, slots=True)
class OfferOutcome:
    offer: Offer
    need: Need | None
    misses: int  # wrong offers for the current need so far


def _weighted(rng: random.Random, weights: dict[Need, int]) -> Need:
    items = sorted(weights.items(), key=lambda item: item[0].value)
    total = sum(weight for _, weight in items)
    pick = rng.uniform(0.0, total)
    for need, weight in items:
        pick -= weight
        if pick <= 0.0:
            return need
    return items[-1][0]


def plan_day(level: int, rng: random.Random) -> tuple[Need, ...]:
    """Daytime needs for ``level`` followed by bedtime."""

    rung = LEVELS[max(0, min(MAX_LEVEL, level))]
    pool = set(rung.pool)
    needs: list[Need] = []
    previous: Need | None = None
    for slot in range(rung.daytime_needs):
        source = FIRST_NEEDS if previous is None else NEXT_NEEDS[previous]
        # Needs not seen yet today are three times as likely, and every need
        # of the pool shows up at least once a day when there is room for it.
        unseen = pool - set(needs)
        must = unseen if len(unseen) >= rung.daytime_needs - slot else set(pool)
        weights = {
            need: w * (1 if need in needs else 3)
            for need, w in source.items()
            if need in must and need is not previous
        }
        if not weights:
            weights = {need: 1 for need in must if need is not previous} or {
                need: 1 for need in pool if need is not previous
            }
        previous = _weighted(rng, weights)
        needs.append(previous)
    needs.append(Need.SLEEPY)
    return tuple(needs)


def adapt_level(level: int, misses: int) -> int:
    """Next day's rung: up after a calm day, down after a hard one."""

    if misses <= 1:
        return min(MAX_LEVEL, level + 1)
    if misses >= 5:
        return max(0, level - 1)
    return max(0, min(MAX_LEVEL, level))


class CareDay:
    """State of one day of care (see module docstring)."""

    def __init__(self, needs: tuple[Need, ...], level: int = 0) -> None:
        if not needs or needs[-1] is not Need.SLEEPY:
            raise ValueError("a care day must end with bedtime")
        self.needs = tuple(needs)
        self.level = max(0, min(MAX_LEVEL, int(level)))
        self.index = 0
        self.phase = Phase.CALM
        self.steps_done = 0
        self.misses = 0  # whole day
        self.need_misses = 0  # current need
        self.first_try = 0
        self.cared: list[Need] = []

    @classmethod
    def planned(cls, level: int, rng: random.Random) -> "CareDay":
        return cls(plan_day(level, rng), level)

    # -- queries -----------------------------------------------------------

    @property
    def total(self) -> int:
        return len(self.needs)

    @property
    def tray(self) -> tuple[Care, ...]:
        return LEVELS[self.level].tray

    @property
    def current_need(self) -> Need | None:
        if self.phase in (Phase.NEED, Phase.CARE):
            return self.needs[self.index]
        return None

    @property
    def next_need(self) -> Need | None:
        return self.needs[self.index] if self.index < len(self.needs) else None

    @property
    def right_care(self) -> Care | None:
        need = self.current_need
        return CARE_FOR_NEED[need] if need is not None else None

    @property
    def steps(self) -> int:
        care = self.right_care
        return CARES[care].steps if care is not None else 0

    @property
    def care_finished(self) -> bool:
        return self.phase is Phase.CARE and self.steps_done >= self.steps

    @property
    def done(self) -> bool:
        return self.phase is Phase.DONE

    @property
    def is_bedtime(self) -> bool:
        return self.index == len(self.needs) - 1

    # -- transitions ---------------------------------------------------------

    def emerge(self) -> Need | None:
        """Let the next need show (CALM -> NEED)."""

        if self.phase is not Phase.CALM or self.index >= len(self.needs):
            return None
        self.phase = Phase.NEED
        self.need_misses = 0
        self.steps_done = 0
        return self.needs[self.index]

    def offer(self, care: Care) -> OfferOutcome:
        """The child offers ``care``; only NEED accepts offers."""

        need = self.current_need
        if self.phase is not Phase.NEED or need is None:
            return OfferOutcome(Offer.IGNORED, need, self.need_misses)
        if care is CARE_FOR_NEED[need]:
            if self.need_misses == 0:
                self.first_try += 1
            self.phase = Phase.CARE
            self.steps_done = 0
            return OfferOutcome(Offer.RIGHT, need, self.need_misses)
        self.need_misses += 1
        self.misses += 1
        return OfferOutcome(Offer.NOT_NOW, need, self.need_misses)

    def act(self) -> bool:
        """One child action while caring; returns True when it counted."""

        if self.phase is not Phase.CARE or self.care_finished:
            return False
        self.steps_done += 1
        return True

    def settle(self) -> Need | None:
        """Finish the current care (CARE -> CALM, or DONE after bedtime)."""

        if not self.care_finished:
            return None
        need = self.needs[self.index]
        self.cared.append(need)
        self.index += 1
        self.phase = Phase.DONE if self.index >= len(self.needs) else Phase.CALM
        return need


__all__ = ["CareDay", "Offer", "OfferOutcome", "Phase", "adapt_level", "plan_day"]
