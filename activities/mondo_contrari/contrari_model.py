"""Domain model for Mondo Contrari ("Flash's Opposite Game").

One visit is a short sequence of opposite *pairs* (up/down, big/small,
in/out, open/closed, fast/slow). For every pair the child hears one concept
word and makes it happen (or finds it), then hears the opposite word and does
that too. Level 3 adds a third, unpredictable ask so the answer is never just
"the other one". There are no modes: all five pairs are stages of the same
listen -> decide -> see it happen loop.

The model is pure Python (no Pygame) so it is cheap to test: it owns the
round plan, which pole sits on which side, correctness, retry/hint evidence
and the bounded adaptive level. Presentation lives in ``contrari_scenes``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import random
from typing import Final, Sequence

REFERENCE_WIDTH: Final[int] = 1024
REFERENCE_HEIGHT: Final[int] = 600

MIN_LEVEL: Final[int] = 1
MAX_LEVEL: Final[int] = 3
HISTORY_LIMIT: Final[int] = 10


class OppositeCategory(StrEnum):
    """One opposite pair; the value is also the progression event payload."""

    UP_DOWN = "up_down"
    BIG_SMALL = "big_small"
    IN_OUT = "in_out"
    OPEN_CLOSED = "open_closed"
    FAST_SLOW = "fast_slow"


class Pole(StrEnum):
    """One concept word. The value is the speech cue id and the text key suffix."""

    UP = "up"
    DOWN = "down"
    BIG = "big"
    SMALL = "small"
    IN = "in"
    OUT = "out"
    OPEN = "open"
    CLOSED = "closed"
    FAST = "fast"
    SLOW = "slow"

    @property
    def text_key(self) -> str:
        return f"opposite.{self.value}"


class TaskKind(StrEnum):
    """How the child answers: move the thing there, or pick the right picture."""

    MAKE = "make"
    FIND = "find"


PAIR_POLES: Final[dict[OppositeCategory, tuple[Pole, Pole]]] = {
    OppositeCategory.UP_DOWN: (Pole.UP, Pole.DOWN),
    OppositeCategory.BIG_SMALL: (Pole.BIG, Pole.SMALL),
    OppositeCategory.IN_OUT: (Pole.IN, Pole.OUT),
    OppositeCategory.OPEN_CLOSED: (Pole.OPEN, Pole.CLOSED),
    OppositeCategory.FAST_SLOW: (Pole.FAST, Pole.SLOW),
}
PAIR_KIND: Final[dict[OppositeCategory, TaskKind]] = {
    OppositeCategory.UP_DOWN: TaskKind.MAKE,
    OppositeCategory.BIG_SMALL: TaskKind.FIND,
    OppositeCategory.IN_OUT: TaskKind.MAKE,
    OppositeCategory.OPEN_CLOSED: TaskKind.FIND,
    OppositeCategory.FAST_SLOW: TaskKind.FIND,
}
_POLE_PAIR: Final[dict[Pole, OppositeCategory]] = {
    pole: category for category, poles in PAIR_POLES.items() for pole in poles
}

# Picture variety for the "find" pairs: the SAME picture appears twice so the
# only difference between the two choices is the concept being taught.
SIZE_SUBJECTS: Final[tuple[str, ...]] = (
    "prop.vocab.elephant",
    "prop.everyday.ball",
    "prop.vocab.bear",
    "prop.vocab.cake",
    "prop.food.apple",
    "creature.woodland.duck",
)
RACERS: Final[tuple[str, ...]] = (
    "creature.woodland.snail",
    "prop.vocab.car",
    "creature.woodland.ladybird",
    "prop.vocab.train",
    "creature.woodland.mouse",
)


def opposite(pole: Pole) -> Pole:
    first, second = PAIR_POLES[category_of(pole)]
    return second if pole is first else first


def category_of(pole: Pole) -> OppositeCategory:
    return _POLE_PAIR[pole]


@dataclass(frozen=True, slots=True)
class Ask:
    """One spoken word to act on.

    ``sides`` names the pole shown at choice 0 and choice 1. "Make" pairs keep
    a fixed geometry (sky above, grass below; the box on one side), "find"
    pairs may swap the two pictures between asks so the child must look again.
    """

    pole: Pole
    sides: tuple[Pole, Pole]

    def __post_init__(self) -> None:
        if set(self.sides) != set(PAIR_POLES[category_of(self.pole)]):
            raise ValueError("an ask must offer exactly the two poles of its pair")

    def index_of(self, pole: Pole) -> int:
        return self.sides.index(pole)


@dataclass(frozen=True, slots=True)
class PairRound:
    """One opposite pair inside a visit (one progress dot)."""

    category: OppositeCategory
    asks: tuple[Ask, ...]
    subject: str | None = None  # picture used by big/small and fast/slow

    def __post_init__(self) -> None:
        if not 2 <= len(self.asks) <= 3:
            raise ValueError("a pair round has two or three asks")
        if any(category_of(ask.pole) is not self.category for ask in self.asks):
            raise ValueError("every ask must belong to the round's pair")
        if self.asks[1].pole is not opposite(self.asks[0].pole):
            raise ValueError("the second ask is always the opposite of the first")
        if PAIR_KIND[self.category] is TaskKind.MAKE and len({ask.sides for ask in self.asks}) != 1:
            raise ValueError("make pairs keep one fixed geometry")

    @property
    def kind(self) -> TaskKind:
        return PAIR_KIND[self.category]


@dataclass(frozen=True, slots=True)
class AttemptSummary:
    """Evidence for one pair: used to adapt the next visit (bounded history)."""

    first_attempt_success: bool
    hints_used: int
    used_retry: bool


class Phase(StrEnum):
    ASKING = "asking"
    SOLVED = "solved"
    DONE = "done"


@dataclass(frozen=True, slots=True)
class ChoiceResult:
    correct: bool
    round_complete: bool = False
    visit_complete: bool = False


def visit_size(level: int) -> tuple[int, int]:
    """(pairs per visit, asks per pair) for a level."""

    level = clamp_level(level)
    if level == 1:
        return (4, 2)
    if level == 2:
        return (5, 2)
    return (5, 3)


def clamp_level(level: int) -> int:
    return max(MIN_LEVEL, min(MAX_LEVEL, int(level)))


class ContrariRoundFactory:
    """Build one visit's plan for a level (seedable for tests)."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    def build_visit(self, level: int) -> tuple[PairRound, ...]:
        level = clamp_level(level)
        pairs, asks = visit_size(level)
        rng = self._rng
        rest = [category for category in OppositeCategory if category is not OppositeCategory.UP_DOWN]
        rng.shuffle(rest)
        # The balloon is the warm-up: everyone knows how to send it up.
        order = [OppositeCategory.UP_DOWN, *rest][:pairs]
        subjects = list(SIZE_SUBJECTS)
        racers = list(RACERS)
        rng.shuffle(subjects)
        rng.shuffle(racers)
        return tuple(self._round(category, level, asks, subjects, racers) for category in order)

    def _round(
        self,
        category: OppositeCategory,
        level: int,
        count: int,
        subjects: list[str],
        racers: list[str],
    ) -> PairRound:
        rng = self._rng
        poles = PAIR_POLES[category]
        first = rng.choice(poles)
        words = [first, opposite(first)]
        if count == 3:
            words.append(rng.choice(poles))
        kind = PAIR_KIND[category]
        if category is OppositeCategory.UP_DOWN:
            fixed: tuple[Pole, Pole] = (Pole.UP, Pole.DOWN)  # sky is always above
            sides = [fixed] * count
        elif kind is TaskKind.MAKE:
            fixed = poles if rng.random() < 0.5 else (poles[1], poles[0])
            sides = [fixed] * count
        else:
            current = poles if rng.random() < 0.5 else (poles[1], poles[0])
            sides = []
            for index in range(count):
                if index > 0 and level >= 2 and (index == 2 or rng.random() < 0.5):
                    current = (current[1], current[0])
                sides.append(current)
        subject: str | None = None
        if category is OppositeCategory.BIG_SMALL:
            subject = subjects[0]
        elif category is OppositeCategory.FAST_SLOW:
            subject = racers[0]
        return PairRound(
            category,
            tuple(Ask(pole, side) for pole, side in zip(words, sides)),
            subject,
        )


class ContrariSession:
    """Track one visit: current pair/ask, correctness and evidence."""

    def __init__(
        self,
        rounds: Sequence[PairRound],
        *,
        level: int = 1,
        history: Sequence[AttemptSummary] = (),
    ) -> None:
        if not rounds:
            raise ValueError("a visit needs at least one pair")
        self.rounds = tuple(rounds)
        self.level = clamp_level(level)
        self.history: list[AttemptSummary] = list(history)[-HISTORY_LIMIT:]
        self.round_index = 0
        self.ask_index = 0
        self.phase = Phase.ASKING
        self.rejected: set[Pole] = set()
        self.completed_rounds = 0
        self._round_errors = 0
        self._round_hints = 0
        self._milestone: OppositeCategory | None = None
        self._completion_pending = False
        self._first_try_rounds = 0

    # -- state ---------------------------------------------------------------

    @property
    def current_round(self) -> PairRound | None:
        if self.phase is Phase.DONE:
            return None
        return self.rounds[self.round_index]

    @property
    def current_ask(self) -> Ask | None:
        current = self.current_round
        if current is None:
            return None
        return current.asks[self.ask_index]

    @property
    def is_last_ask_of_round(self) -> bool:
        current = self.current_round
        return current is not None and self.ask_index == len(current.asks) - 1

    # -- answers -------------------------------------------------------------

    def choose(self, pole: Pole) -> ChoiceResult:
        ask = self.current_ask
        if ask is None or self.phase is not Phase.ASKING:
            return ChoiceResult(False)
        if pole is not ask.pole:
            self.rejected.add(pole)
            self._round_errors += 1
            return ChoiceResult(False)
        self.phase = Phase.SOLVED
        if not self.is_last_ask_of_round:
            return ChoiceResult(True)
        current = self.current_round
        assert current is not None
        self.completed_rounds += 1
        first_try = self._round_errors == 0
        if first_try:
            self._first_try_rounds += 1
        self.history.append(AttemptSummary(first_try, self._round_hints, not first_try))
        del self.history[:-HISTORY_LIMIT]
        self._milestone = current.category
        visit_done = self.round_index == len(self.rounds) - 1
        if visit_done:
            self._completion_pending = True
        return ChoiceResult(True, round_complete=True, visit_complete=visit_done)

    def note_hint(self) -> None:
        self._round_hints = min(32, self._round_hints + 1)

    def advance(self) -> bool:
        """Move to the next ask/pair after a solved ask; False when the visit is over."""

        if self.phase is not Phase.SOLVED:
            return self.phase is Phase.ASKING
        self.rejected.clear()
        if not self.is_last_ask_of_round:
            self.ask_index += 1
            self.phase = Phase.ASKING
            return True
        if self.round_index >= len(self.rounds) - 1:
            self.phase = Phase.DONE
            return False
        self.round_index += 1
        self.ask_index = 0
        self._round_errors = 0
        self._round_hints = 0
        self.phase = Phase.ASKING
        return True

    def consume_milestone(self) -> OppositeCategory | None:
        milestone, self._milestone = self._milestone, None
        return milestone

    def consume_completion(self) -> dict[str, int] | None:
        if not self._completion_pending:
            return None
        self._completion_pending = False
        return {
            "pairs": len(self.rounds),
            "level": self.level,
            "first_try_pairs": self._first_try_rounds,
        }


def adapt_level(level: int, history: Sequence[AttemptSummary]) -> int:
    """Raise after four clean pairs in a row; lower when retries pile up."""

    level = clamp_level(level)
    recent = list(history)[-4:]
    if len(recent) == 4 and all(item.first_attempt_success and item.hints_used == 0 for item in recent):
        return clamp_level(level + 1)
    last_three = list(history)[-3:]
    if len(last_three) == 3 and sum(item.used_retry for item in last_three) >= 2:
        return clamp_level(level - 1)
    return level


__all__ = [
    "Ask",
    "AttemptSummary",
    "ChoiceResult",
    "ContrariRoundFactory",
    "ContrariSession",
    "HISTORY_LIMIT",
    "MAX_LEVEL",
    "MIN_LEVEL",
    "OppositeCategory",
    "PAIR_KIND",
    "PAIR_POLES",
    "PairRound",
    "Phase",
    "Pole",
    "RACERS",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "SIZE_SUBJECTS",
    "TaskKind",
    "adapt_level",
    "category_of",
    "clamp_level",
    "opposite",
    "visit_size",
]
