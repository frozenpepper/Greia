"""Domain model for Luci di Momo (Momo's Lights): a subitizing ladder.

Momo's fireflies glow all at once for a moment and go dark; the child says how
many they saw by choosing one of three number cards. The stages climb the
early-number ladder (P7 §3):

1. dice patterns of 1-5 (canonical arrangements are subitized first);
2. 2-6 as dice or free scatter (the same amount in an unfamiliar shape);
3. 4-8 as two small groups (see the parts, then the whole);
4. 6-10 in a firefly ten-frame (a full row of five and a bit more).

Distractors are always near misses (answer +-1, +-2). The model owns challenge
truth, the per-round attempt record, bounded adaptation evidence and one-shot
completion. It knows nothing about Pygame, storage or Greia services.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
import random
from typing import Final, Sequence


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
ROUND_COUNT: Final = 6
HISTORY_LIMIT: Final = 8
MAX_QUANTITY: Final = 10
CHOICE_COUNT: Final = 3
MIN_CENTER_SEPARATION: Final = 68.0

# The night meadow the fireflies glow in (logical pixels, right of Momo).
PLAYFIELD_LEFT: Final = 420
PLAYFIELD_RIGHT: Final = 880
PLAYFIELD_TOP: Final = 112
PLAYFIELD_BOTTOM: Final = 348
FIELD_CENTER: Final[tuple[int, int]] = (628, 236)

DICE_PITCH: Final = 100
# Two compact groups far apart, so the parts read as parts before the whole.
GROUP_PITCH: Final = 50
GROUP_CENTERS: Final[tuple[tuple[int, int], tuple[int, int]]] = ((500, 236), (790, 236))
SCATTER_SEPARATION: Final = 94.0
FRAME_CELL: Final = 88
FRAME_COLUMNS: Final = 5
FRAME_ROWS: Final = 2


class Arrangement(StrEnum):
    """How the fireflies are laid out for one glimpse."""

    DICE = "dice"
    SCATTER = "scatter"
    GROUPS = "groups"
    TEN_FRAME = "ten_frame"


@dataclass(frozen=True, slots=True)
class StageRule:
    """One rung of the ladder: amounts, arrangements, glimpse time, card faces."""

    low: int
    high: int
    arrangements: tuple[Arrangement, ...]
    reveal_ms: int
    card_dots: bool


_STAGES: Final[dict[int, StageRule]] = {
    1: StageRule(1, 5, (Arrangement.DICE,), 1500, True),
    2: StageRule(2, 6, (Arrangement.DICE, Arrangement.SCATTER), 1300, True),
    3: StageRule(4, 8, (Arrangement.GROUPS,), 1400, True),
    4: StageRule(6, 10, (Arrangement.TEN_FRAME,), 1500, False),
}

# Canonical dice faces as unit offsets (x, y) from the pattern centre.
_DICE: Final[dict[int, tuple[tuple[float, float], ...]]] = {
    1: ((0, 0),),
    2: ((-1, -1), (1, 1)),
    3: ((-1, -1), (0, 0), (1, 1)),
    4: ((-1, -1), (1, -1), (-1, 1), (1, 1)),
    5: ((-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)),
    6: ((-0.6, -1), (0.6, -1), (-0.6, 0), (0.6, 0), (-0.6, 1), (0.6, 1)),
}


def stage_rule(level: int) -> StageRule:
    _require_level(level)
    return _STAGES[level]


def frame_cell_center(index: int) -> tuple[int, int]:
    """Centre of ten-frame cell ``index`` (reading order, 5 per row)."""

    row, column = divmod(index, FRAME_COLUMNS)
    left = FIELD_CENTER[0] - (FRAME_COLUMNS * FRAME_CELL) // 2
    top = FIELD_CENTER[1] - (FRAME_ROWS * FRAME_CELL) // 2
    return (left + column * FRAME_CELL + FRAME_CELL // 2, top + row * FRAME_CELL + FRAME_CELL // 2)


def dice_positions(quantity: int, center: tuple[int, int], pitch: int) -> tuple[tuple[int, int], ...]:
    if quantity not in _DICE:
        raise ValueError("dice patterns cover 1..6")
    cx, cy = center
    return tuple((int(round(cx + dx * pitch)), int(round(cy + dy * pitch))) for dx, dy in _DICE[quantity])


@dataclass(frozen=True, slots=True)
class FireflyRound:
    """One immutable glimpse: where the fireflies glow and the answer cards.

    ``groups`` lists the part sizes in display order (one part for dice and
    scatter, two for grouped or ten-frame glimpses); ``positions`` follow the
    same order so a demonstration can name a part and then count on.
    """

    round_id: str
    quantity: int
    positions: tuple[tuple[int, int], ...]
    choice_values: tuple[int, ...]
    reveal_ms: int
    arrangement: Arrangement = Arrangement.DICE
    groups: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.round_id:
            raise ValueError("round_id must not be empty")
        if not 1 <= self.quantity <= MAX_QUANTITY:
            raise ValueError(f"quantity must be in 1..{MAX_QUANTITY}")
        if len(self.positions) != self.quantity:
            raise ValueError("positions must match quantity")
        if len(self.choice_values) != CHOICE_COUNT or len(set(self.choice_values)) != CHOICE_COUNT:
            raise ValueError("choice_values must be three unique values")
        if self.quantity not in self.choice_values:
            raise ValueError("choice_values must include the answer")
        if any(not 1 <= value <= MAX_QUANTITY for value in self.choice_values):
            raise ValueError(f"choice_values must stay in 1..{MAX_QUANTITY}")
        if any(abs(value - self.quantity) > 2 for value in self.choice_values):
            raise ValueError("distractors must be near misses (+-1, +-2)")
        if self.reveal_ms < 250:
            raise ValueError("reveal_ms is unexpectedly short")
        groups = self.groups or (self.quantity,)
        if sum(groups) != self.quantity or any(size < 1 for size in groups):
            raise ValueError("groups must partition the quantity")
        object.__setattr__(self, "groups", tuple(groups))
        _validate_positions(self.positions)

    @property
    def lead_group(self) -> int:
        """Size of the part a demonstration names at once (0 = count all)."""

        if self.arrangement in {Arrangement.GROUPS, Arrangement.TEN_FRAME} and len(self.groups) > 1:
            return self.groups[0]
        return 0


@dataclass(frozen=True, slots=True)
class AttemptSummary:
    """Bounded evidence from one completed round for between-set adaptation."""

    first_attempt_success: bool
    hints_used: int
    used_replay: bool

    def __post_init__(self) -> None:
        if self.hints_used < 0:
            raise ValueError("hints_used must be >= 0")


@dataclass(frozen=True, slots=True)
class AttemptResult:
    """Result returned by a semantic numeral choice."""

    correct: bool
    round_completed: bool
    session_complete: bool
    first_attempt_success: bool
    hints_used: int
    used_replay: bool


class FireflyRoundFactory:
    """Create bounded subitizing rounds for one stage from an injected RNG."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def build_set(self, level: int, *, count: int = ROUND_COUNT) -> tuple[FireflyRound, ...]:
        rule = stage_rule(level)
        if count < 1:
            raise ValueError("count must be positive")
        rounds: list[FireflyRound] = []
        previous: int | None = None
        for index in range(count):
            candidates = [value for value in range(rule.low, rule.high + 1) if value != previous]
            quantity = self._rng.choice(candidates)
            previous = quantity
            arrangement = rule.arrangements[index % len(rule.arrangements)]
            if len(rule.arrangements) > 1 and self._rng.random() < 0.5:
                arrangement = self._rng.choice(rule.arrangements)
            positions, groups = self._layout(arrangement, quantity)
            rounds.append(
                FireflyRound(
                    round_id=f"L{level}-R{index + 1}-{self._rng.randrange(1_000_000):06d}",
                    quantity=quantity,
                    positions=positions,
                    choice_values=self._choices(quantity),
                    reveal_ms=rule.reveal_ms,
                    arrangement=arrangement,
                    groups=groups,
                )
            )
        return tuple(rounds)

    # -- layouts --------------------------------------------------------------

    def _layout(
        self, arrangement: Arrangement, quantity: int
    ) -> tuple[tuple[tuple[int, int], ...], tuple[int, ...]]:
        if arrangement is Arrangement.DICE:
            return dice_positions(quantity, FIELD_CENTER, DICE_PITCH), (quantity,)
        if arrangement is Arrangement.SCATTER:
            return self._scatter(quantity), (quantity,)
        if arrangement is Arrangement.GROUPS:
            first = self._rng.randint(max(1, quantity - 5), min(5, quantity - 1))
            second = quantity - first
            positions = (
                *dice_positions(first, GROUP_CENTERS[0], GROUP_PITCH),
                *dice_positions(second, GROUP_CENTERS[1], GROUP_PITCH),
            )
            return positions, (first, second)
        # Ten-frame: the top row fills first, then the rest in reading order.
        positions = tuple(frame_cell_center(index) for index in range(quantity))
        groups = (5, quantity - 5) if quantity > 5 else (quantity,)
        return positions, groups

    def _scatter(self, quantity: int) -> tuple[tuple[int, int], ...]:
        margin = 40
        points: list[tuple[int, int]] = []
        for _ in range(400):
            candidate = (
                self._rng.randint(PLAYFIELD_LEFT + margin, PLAYFIELD_RIGHT - margin),
                self._rng.randint(PLAYFIELD_TOP + margin, PLAYFIELD_BOTTOM - margin),
            )
            if all(_distance(candidate, other) >= SCATTER_SEPARATION for other in points):
                points.append(candidate)
                if len(points) == quantity:
                    # Reading order (top band first, left to right), so a
                    # counting demonstration sweeps instead of jumping around.
                    return tuple(sorted(points, key=lambda p: (p[1] // 80, p[0])))
        # Deterministic fallback: a loose two-row zigzag.
        return tuple(
            (PLAYFIELD_LEFT + 70 + index * 64, FIELD_CENTER[1] + (-56 if index % 2 else 56))
            for index in range(quantity)
        )

    def _choices(self, answer: int) -> tuple[int, ...]:
        """Answer plus two near misses: one is always +-1."""

        near = [value for value in (answer - 1, answer + 1) if 1 <= value <= MAX_QUANTITY]
        far = [value for value in (answer - 2, answer + 2) if 1 <= value <= MAX_QUANTITY]
        first = self._rng.choice(near)
        rest = [value for value in (*near, *far) if value != first]
        second = self._rng.choice(rest)
        values = [answer, first, second]
        self._rng.shuffle(values)
        return tuple(values)


class FireflySession:
    """Own one set of rounds, rejected answers and one-shot completion."""

    def __init__(
        self,
        rounds: Sequence[FireflyRound],
        *,
        level: int,
        history: Sequence[AttemptSummary] = (),
    ) -> None:
        _require_level(level)
        if len(rounds) != ROUND_COUNT:
            raise ValueError(f"a Luci di Momo session requires exactly {ROUND_COUNT} rounds")
        self._rounds = tuple(rounds)
        self.level = level
        self._index = 0
        self._attempts_this_round = 0
        self._hints_this_round = 0
        self._used_replay_this_round = False
        self._rejected: set[int] = set()
        self._history = list(history[-HISTORY_LIMIT:])
        self._completion_consumed = False

    @property
    def current_round(self) -> FireflyRound | None:
        if self.is_complete:
            return None
        return self._rounds[self._index]

    @property
    def rounds(self) -> tuple[FireflyRound, ...]:
        return self._rounds

    @property
    def round_index(self) -> int:
        return self._index

    @property
    def is_complete(self) -> bool:
        return self._index >= len(self._rounds)

    @property
    def history(self) -> tuple[AttemptSummary, ...]:
        return tuple(self._history)

    @property
    def rejected(self) -> frozenset[int]:
        """Answers already tried (and kindly declined) in the current round."""

        return frozenset(self._rejected)

    @property
    def replay_used(self) -> bool:
        return self._used_replay_this_round

    @property
    def missed(self) -> bool:
        """True once the current round had a wrong answer (fireflies stay lit)."""

        return bool(self._rejected)

    def mark_replay(self) -> None:
        if not self.is_complete:
            self._used_replay_this_round = True

    def note_hint(self) -> None:
        """Record an idle hint (Momo points) as scaffolding for adaptation."""

        if not self.is_complete:
            self._hints_this_round += 1

    def choose(self, value: int) -> AttemptResult:
        current = self.current_round
        if current is None:
            raise RuntimeError("cannot answer a completed session")

        self._attempts_this_round += 1
        if value != current.quantity:
            self._hints_this_round += 1
            self._rejected.add(value)
            return AttemptResult(
                correct=False,
                round_completed=False,
                session_complete=False,
                first_attempt_success=False,
                hints_used=self._hints_this_round,
                used_replay=self._used_replay_this_round,
            )

        first_attempt = self._attempts_this_round == 1 and not self._used_replay_this_round
        summary = AttemptSummary(
            first_attempt_success=first_attempt,
            hints_used=self._hints_this_round,
            used_replay=self._used_replay_this_round,
        )
        self._history.append(summary)
        del self._history[:-HISTORY_LIMIT]

        self._index += 1
        result = AttemptResult(
            correct=True,
            round_completed=True,
            session_complete=self.is_complete,
            first_attempt_success=first_attempt,
            hints_used=summary.hints_used,
            used_replay=summary.used_replay,
        )
        self._attempts_this_round = 0
        self._hints_this_round = 0
        self._used_replay_this_round = False
        self._rejected.clear()
        return result

    def consume_completion(self) -> dict[str, int] | None:
        """Return the terminal factual payload once, then permanently None."""
        if not self.is_complete or self._completion_consumed:
            return None
        self._completion_consumed = True
        recent = self._history[-ROUND_COUNT:]
        return {
            "level": self.level,
            "first_attempt_count": sum(item.first_attempt_success for item in recent),
            "replays": sum(item.used_replay for item in recent),
        }


def adapt_level(current: int, history: Sequence[AttemptSummary]) -> int:
    """Apply the portfolio's bounded between-set adaptation policy."""
    _require_level(current)
    recent = tuple(history[-HISTORY_LIMIT:])
    if len(recent) >= HISTORY_LIMIT:
        strong = sum(item.first_attempt_success and item.hints_used <= 1 for item in recent)
        if strong >= 6:
            return min(len(_STAGES), current + 1)

    if len(recent) >= 3:
        last_three = recent[-3:]
        if all((not item.first_attempt_success) and item.hints_used >= 1 for item in last_three):
            return max(1, current - 1)
    return current


def _validate_positions(positions: Sequence[tuple[int, int]]) -> None:
    for x, y in positions:
        if not (PLAYFIELD_LEFT <= x <= PLAYFIELD_RIGHT):
            raise ValueError("firefly x position escapes playfield")
        if not (PLAYFIELD_TOP <= y <= PLAYFIELD_BOTTOM):
            raise ValueError("firefly y position escapes playfield")
    for index, point in enumerate(positions):
        for other in positions[index + 1:]:
            if _distance(point, other) < MIN_CENTER_SEPARATION:
                raise ValueError("firefly positions are too close")


def _distance(a: tuple[int, int], b: tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _require_level(level: int) -> None:
    if level not in _STAGES:
        raise ValueError(f"level must be in 1..{len(_STAGES)}")
