"""Rules of Woodland Hide & Seek (pure, no Pygame).

A round happens in one season scene. Some of the scene's hiding places are
chosen at random; before every request all friends hide again (new places),
so every request is a fresh visual search. The child is asked to find one
named friend and taps a hiding place:

* the asked friend is there -> found (it joins Lilli; the place's position
  word is the reward);
* someone else is there -> that friend shows itself ("not me"), a miss;
* the request never ends in failure: retries are unlimited.

Four finds end the round. The ladder adapts from the misses of the round.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import random

if __package__:
    from .woodland_content import FINDS_PER_ROUND, FRIEND_IDS, LEVELS, MAX_LEVEL, Anchor, Level, Season
else:
    from woodland_content import FINDS_PER_ROUND, FRIEND_IDS, LEVELS, MAX_LEVEL, Anchor, Level, Season


class Pick(StrEnum):
    FOUND = "found"
    WRONG = "wrong"
    IGNORED = "ignored"


@dataclass(frozen=True, slots=True)
class PickOutcome:
    pick: Pick
    spot: int = -1
    friend_id: str | None = None
    task_misses: int = 0


@dataclass(slots=True)
class HideRound:
    """State of one round: places, who hides where, who is asked, who is found."""

    season: Season
    level: int
    rng: random.Random = field(default_factory=random.Random)
    finds_needed: int = FINDS_PER_ROUND
    spots: tuple[Anchor, ...] = ()
    hiding: list[str | None] = field(default_factory=list)
    target: str | None = None
    found: list[str] = field(default_factory=list)
    misses: int = 0
    task_misses: int = 0
    first_try_finds: int = 0

    def __post_init__(self) -> None:
        self.level = max(0, min(MAX_LEVEL, int(self.level)))
        if not self.spots:
            count = min(self.ladder.spots, len(self.season.anchors))
            chosen = self.rng.sample(self.season.anchors, count)
            # Back row first (draw order and keyboard reading order).
            self.spots = tuple(sorted(chosen, key=lambda anchor: (anchor.y, anchor.x)))
        if not self.hiding:
            self.hide_again()

    @property
    def ladder(self) -> Level:
        return LEVELS[self.level]

    @property
    def complete(self) -> bool:
        return len(self.found) >= self.finds_needed

    @property
    def target_spot(self) -> int | None:
        if self.target is None:
            return None
        try:
            return self.hiding.index(self.target)
        except ValueError:
            return None

    def hide_again(self) -> None:
        """Everyone still hiding picks a new place; ask for one of them."""

        if self.complete:
            self.target = None
            self.hiding = [None] * len(self.spots)
            return
        waiting = [friend for friend in FRIEND_IDS if friend not in self.found]
        previous = self.target
        candidates = [friend for friend in waiting if friend != previous] or waiting
        self.target = self.rng.choice(candidates)
        decoys = [friend for friend in waiting if friend != self.target]
        self.rng.shuffle(decoys)
        hiders = [self.target, *decoys[: len(self.spots) - 1]]
        while len(hiders) < len(self.spots):
            hiders.append(None)  # only if the friend list were ever too short
        self.rng.shuffle(hiders)
        self.hiding = hiders
        self.task_misses = 0

    def choose(self, spot: int) -> PickOutcome:
        """The child picked hiding place ``spot``."""

        if self.complete or not 0 <= spot < len(self.spots) or self.target is None:
            return PickOutcome(Pick.IGNORED, spot)
        friend = self.hiding[spot]
        if friend == self.target:
            if self.task_misses == 0:
                self.first_try_finds += 1
            outcome = PickOutcome(Pick.FOUND, spot, friend, self.task_misses)
            self.found.append(friend)
            self.hiding[spot] = None
            self.target = None
            return outcome
        self.misses += 1
        self.task_misses += 1
        return PickOutcome(Pick.WRONG, spot, friend, self.task_misses)


def adapt_level(level: int, misses: int) -> int:
    """Next round's rung: a near-perfect round climbs, a hard one steps back."""

    if misses <= 1:
        return min(MAX_LEVEL, level + 1)
    if misses >= 5:
        return max(0, level - 1)
    return level


__all__ = ["HideRound", "Pick", "PickOutcome", "adapt_level"]
