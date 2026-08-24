"""Domain model for La Bottega delle Misure (Measurement Workshop).

Owns comparison, seriation ordering, and repeated non-standard unit measurement invariants,
deterministic challenge generation, bounded adaptation, and milestone/completion facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import random
from typing import Final, Sequence


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
CHALLENGE_COUNT: Final = 5
HISTORY_LIMIT: Final = 8
MAX_UNITS: Final = 8


class Attribute(StrEnum):
    LENGTH = "length"
    HEIGHT = "height"


class MeasureMode(StrEnum):
    COMPARE = "compare"
    ORDER = "order"
    MEASURE = "measure"
    SHELF = "shelf"


@dataclass(frozen=True, slots=True)
class MeasureItem:
    """A parcel or object with an authoritative discrete unit length or height."""

    item_id: str
    units: int
    attribute: Attribute
    color_index: int

    def __post_init__(self) -> None:
        if not self.item_id:
            raise ValueError("item_id must not be empty")
        if not (1 <= self.units <= MAX_UNITS):
            raise ValueError(f"units must be in 1..{MAX_UNITS}")


@dataclass(frozen=True, slots=True)
class MeasureChallenge:
    """One discrete measurement, comparison, or ordering challenge."""

    challenge_id: str
    mode: MeasureMode
    attribute: Attribute
    items: tuple[MeasureItem, ...]
    target_id: str
    target_units: int
    unit_capacity: int
    choice_values: tuple[int, int, int]
    prompt_key: str

    def __post_init__(self) -> None:
        if not self.challenge_id:
            raise ValueError("challenge_id must not be empty")
        if not self.items:
            raise ValueError("items must not be empty")
        if not (0 <= self.unit_capacity <= MAX_UNITS):
            raise ValueError(f"unit_capacity must be in 0..{MAX_UNITS}")
        if self.mode in {MeasureMode.MEASURE, MeasureMode.SHELF}:
            if len(set(self.choice_values)) != 3 or self.target_units not in self.choice_values:
                raise ValueError("choice_values must contain the target_units and be 3 unique values")


@dataclass(frozen=True, slots=True)
class AttemptSummary:
    """Evidence from one completed parcel challenge for adaptation."""

    first_attempt_success: bool
    hints_used: int
    used_retry: bool

    def __post_init__(self) -> None:
        if self.hints_used < 0:
            raise ValueError("hints_used must be >= 0")


@dataclass(frozen=True, slots=True)
class AttemptResult:
    """Result returned by an interactive tap, block drop, or answer selection."""

    correct: bool
    challenge_completed: bool
    session_complete: bool
    first_attempt_success: bool
    hints_used: int
    used_retry: bool


class MeasureRoundFactory:
    """Create deterministic, bounded measurement challenges from an injected RNG."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def build_set(self, level: int, *, count: int = CHALLENGE_COUNT) -> tuple[MeasureChallenge, ...]:
        _require_level(level)
        if count < 1:
            raise ValueError("count must be positive")

        challenges: list[MeasureChallenge] = []
        seen_keys: set[str] = set()

        for index in range(count):
            c = self._generate_unique_challenge(level, index, seen_keys)
            challenges.append(c)
        return tuple(challenges)

    def _generate_unique_challenge(
        self, level: int, index: int, seen: set[str]
    ) -> MeasureChallenge:
        for _ in range(200):
            c = self._sample_level(level, index)
            key = f"{c.mode}:{c.attribute}:{tuple(it.units for it in c.items)}:{c.target_units}"
            if key not in seen:
                seen.add(key)
                return c
        c = self._sample_level(level, index)
        return c

    def _sample_level(self, level: int, index: int) -> MeasureChallenge:
        cid = f"L{level}-P{index + 1}-{self._rng.randrange(1_000_000):06d}"

        if level == 1:
            # L1: Compare 2 items with 1..4 units. Prompt: tap the longest / tallest or shortest
            attr = self._rng.choice([Attribute.LENGTH, Attribute.HEIGHT])
            u1, u2 = self._rng.sample([1, 2, 3, 4], 2)
            find_max = self._rng.choice([True, False])
            target_u = max(u1, u2) if find_max else min(u1, u2)

            items = (
                MeasureItem("item_a", u1, attr, 0),
                MeasureItem("item_b", u2, attr, 1),
            )
            target_id = "item_a" if u1 == target_u else "item_b"
            if attr == Attribute.LENGTH:
                prompt_key = "prompt.compare_longer" if find_max else "prompt.compare_shorter"
            else:
                prompt_key = "prompt.compare_taller" if find_max else "prompt.compare_shorter_h"

            return MeasureChallenge(
                challenge_id=cid,
                mode=MeasureMode.COMPARE,
                attribute=attr,
                items=items,
                target_id=target_id,
                target_units=target_u,
                unit_capacity=0,
                choice_values=(target_u, target_u + 1, target_u + 2),
                prompt_key=prompt_key,
            )

        if level == 2:
            # L2: Order 3 items from 1..5 units
            attr = self._rng.choice([Attribute.LENGTH, Attribute.HEIGHT])
            units_list = self._rng.sample([1, 2, 3, 4, 5], 3)
            # Shuffle display order
            display_units = list(units_list)
            self._rng.shuffle(display_units)

            items = tuple(
                MeasureItem(f"item_{i}", u, attr, i)
                for i, u in enumerate(display_units)
            )
            prompt_key = "prompt.order_length" if attr == Attribute.LENGTH else "prompt.order_height"
            return MeasureChallenge(
                challenge_id=cid,
                mode=MeasureMode.ORDER,
                attribute=attr,
                items=items,
                target_id="ordered",
                target_units=len(items),
                unit_capacity=0,
                choice_values=(1, 2, 3),
                prompt_key=prompt_key,
            )

        if level == 3:
            # L3: Measure one parcel (2..6 units) using unit blocks on a rail
            units = self._rng.randint(2, 6)
            attr = Attribute.LENGTH
            item = MeasureItem("parcel_main", units, attr, 2)
            choices = self._make_choices(units)

            return MeasureChallenge(
                challenge_id=cid,
                mode=MeasureMode.MEASURE,
                attribute=attr,
                items=(item,),
                target_id="parcel_main",
                target_units=units,
                unit_capacity=units,
                choice_values=choices,
                prompt_key="prompt.measure",
            )

        if level == 4:
            # L4: Shelf capacity measurement (2..7 units)
            units = self._rng.randint(2, 7)
            attr = Attribute.LENGTH
            item = MeasureItem("shelf_parcel", units, attr, 3)
            choices = self._make_choices(units)

            return MeasureChallenge(
                challenge_id=cid,
                mode=MeasureMode.SHELF,
                attribute=attr,
                items=(item,),
                target_id="shelf_parcel",
                target_units=units,
                unit_capacity=units,
                choice_values=choices,
                prompt_key="prompt.shelf",
            )

        # L5: Mixed modes (compare, order 4, measure, shelf)
        mode = self._rng.choice([MeasureMode.COMPARE, MeasureMode.ORDER, MeasureMode.MEASURE, MeasureMode.SHELF])
        if mode == MeasureMode.COMPARE:
            attr = self._rng.choice([Attribute.LENGTH, Attribute.HEIGHT])
            u1, u2 = self._rng.sample([2, 3, 4, 5, 6], 2)
            target_u = max(u1, u2)
            items = (MeasureItem("item_a", u1, attr, 0), MeasureItem("item_b", u2, attr, 1))
            return MeasureChallenge(
                challenge_id=cid,
                mode=MeasureMode.COMPARE,
                attribute=attr,
                items=items,
                target_id="item_a" if u1 == target_u else "item_b",
                target_units=target_u,
                unit_capacity=0,
                choice_values=(target_u, target_u + 1, target_u + 2),
                prompt_key="prompt.compare_longer" if attr == Attribute.LENGTH else "prompt.compare_taller",
            )
        if mode == MeasureMode.ORDER:
            attr = self._rng.choice([Attribute.LENGTH, Attribute.HEIGHT])
            units_list = self._rng.sample([1, 2, 3, 4, 5, 6], 3)
            items = tuple(MeasureItem(f"item_{i}", u, attr, i) for i, u in enumerate(units_list))
            return MeasureChallenge(
                challenge_id=cid,
                mode=MeasureMode.ORDER,
                attribute=attr,
                items=items,
                target_id="ordered",
                target_units=3,
                unit_capacity=0,
                choice_values=(1, 2, 3),
                prompt_key="prompt.order_length" if attr == Attribute.LENGTH else "prompt.order_height",
            )
        units = self._rng.randint(3, 8)
        choices = self._make_choices(units)
        return MeasureChallenge(
            challenge_id=cid,
            mode=mode,
            attribute=Attribute.LENGTH,
            items=(MeasureItem("parcel_mixed", units, Attribute.LENGTH, 4),),
            target_id="parcel_mixed",
            target_units=units,
            unit_capacity=units,
            choice_values=choices,
            prompt_key="prompt.measure" if mode == MeasureMode.MEASURE else "prompt.shelf",
        )

    def _make_choices(self, answer: int) -> tuple[int, int, int]:
        distractors = [v for v in range(1, MAX_UNITS + 1) if v != answer]
        picked = self._rng.sample(distractors, 2)
        values = [answer, *picked]
        self._rng.shuffle(values)
        return (values[0], values[1], values[2])


class MeasureSession:
    """Own measurement progression, placed blocks on rail, order selections, and facts."""

    def __init__(
        self,
        challenges: Sequence[MeasureChallenge],
        *,
        level: int,
        history: Sequence[AttemptSummary] = (),
    ) -> None:
        _require_level(level)
        if len(challenges) != CHALLENGE_COUNT:
            raise ValueError(f"a Bottega session requires exactly {CHALLENGE_COUNT} challenges")
        self._challenges = tuple(challenges)
        self.level = level
        self._index = 0
        self._attempts_this_challenge = 0
        self._hints_this_challenge = 0
        self._used_retry_this_challenge = False
        self._history = list(history[-HISTORY_LIMIT:])
        self._completion_consumed = False
        self._pending_milestone: dict[str, int] | None = None

        # Interactive state
        self.placed_blocks = 0
        self.selected_order_ids: list[str] = []

    @property
    def current_challenge(self) -> MeasureChallenge | None:
        if self.is_complete:
            return None
        return self._challenges[self._index]

    @property
    def challenge_index(self) -> int:
        return self._index

    @property
    def is_complete(self) -> bool:
        return self._index >= len(self._challenges)

    @property
    def history(self) -> tuple[AttemptSummary, ...]:
        return tuple(self._history)

    def add_rail_block(self) -> bool:
        current = self.current_challenge
        if current is None or current.unit_capacity == 0:
            return False
        if self.placed_blocks < current.unit_capacity + 2:
            self.placed_blocks += 1
            return True
        return False

    def remove_rail_block(self) -> bool:
        if self.placed_blocks > 0:
            self.placed_blocks -= 1
            return True
        return False

    def select_item(self, item_id: str) -> AttemptResult | None:
        current = self.current_challenge
        if current is None:
            return None

        if current.mode == MeasureMode.COMPARE:
            self._attempts_this_challenge += 1
            correct = item_id == current.target_id
            return self._evaluate_result(correct)

        if current.mode == MeasureMode.ORDER:
            if item_id not in self.selected_order_ids:
                self.selected_order_ids.append(item_id)
                # Check if all items selected in order
                if len(self.selected_order_ids) == len(current.items):
                    self._attempts_this_challenge += 1
                    # Expected order is sorted by units ascending
                    sorted_items = sorted(current.items, key=lambda it: it.units)
                    expected_ids = [it.item_id for it in sorted_items]
                    correct = self.selected_order_ids == expected_ids
                    if not correct:
                        self.selected_order_ids = []
                    return self._evaluate_result(correct)
            return None

        return None

    def select_answer_value(self, value: int) -> AttemptResult:
        current = self.current_challenge
        if current is None:
            raise RuntimeError("cannot answer completed session")
        self._attempts_this_challenge += 1
        correct = value == current.target_units
        return self._evaluate_result(correct)

    def confirm_measure(self) -> AttemptResult:
        current = self.current_challenge
        if current is None or current.mode not in {MeasureMode.MEASURE, MeasureMode.SHELF}:
            raise RuntimeError("confirm is only valid for measurement modes")
        self._attempts_this_challenge += 1
        correct = self.placed_blocks == current.target_units
        return self._evaluate_result(correct)

    def _evaluate_result(self, correct: bool) -> AttemptResult:
        current = self.current_challenge
        assert current is not None

        if not correct:
            self._hints_this_challenge += 1
            self._used_retry_this_challenge = True
            return AttemptResult(
                correct=False,
                challenge_completed=False,
                session_complete=False,
                first_attempt_success=False,
                hints_used=self._hints_this_challenge,
                used_retry=self._used_retry_this_challenge,
            )

        first_attempt = self._attempts_this_challenge == 1 and not self._used_retry_this_challenge
        summary = AttemptSummary(
            first_attempt_success=first_attempt,
            hints_used=self._hints_this_challenge,
            used_retry=self._used_retry_this_challenge,
        )
        self._history.append(summary)
        del self._history[:-HISTORY_LIMIT]

        self._pending_milestone = {
            "level": self.level,
            "challenge_index": self._index + 1,
            "first_attempt": int(first_attempt),
        }

        self._index += 1
        session_complete = self.is_complete
        result = AttemptResult(
            correct=True,
            challenge_completed=True,
            session_complete=session_complete,
            first_attempt_success=first_attempt,
            hints_used=summary.hints_used,
            used_retry=summary.used_retry,
        )
        self._attempts_this_challenge = 0
        self._hints_this_challenge = 0
        self._used_retry_this_challenge = False
        self.placed_blocks = 0
        self.selected_order_ids = []
        return result

    def consume_milestone(self) -> dict[str, int] | None:
        fact = self._pending_milestone
        self._pending_milestone = None
        return fact

    def consume_completion(self) -> dict[str, int] | None:
        if not self.is_complete or self._completion_consumed:
            return None
        self._completion_consumed = True
        recent = self._history[-CHALLENGE_COUNT:]
        return {
            "level": self.level,
            "first_attempt_count": sum(item.first_attempt_success for item in recent),
            "retries": sum(item.used_retry for item in recent),
        }


def adapt_level(current: int, history: Sequence[AttemptSummary]) -> int:
    """Bounded between-set adaptation policy across levels 1..5."""
    _require_level(current)
    recent = tuple(history[-HISTORY_LIMIT:])
    if len(recent) >= HISTORY_LIMIT:
        strong = sum(item.first_attempt_success and item.hints_used <= 1 for item in recent)
        if strong >= 6:
            return min(5, current + 1)

    if len(recent) >= 3:
        last_three = recent[-3:]
        if all((not item.first_attempt_success) and item.hints_used >= 1 for item in last_three):
            return max(1, current - 1)
    return current


def _require_level(level: int) -> None:
    if not (1 <= level <= 5):
        raise ValueError("level must be in 1..5")
