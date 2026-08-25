"""Domain model for Luci di Momo.

The model owns challenge truth, bounded adaptation evidence, and one-shot
completion semantics. It deliberately knows nothing about Pygame, storage, or
Greia platform services so the learning loop can be tested independently.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Final, Sequence


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
ROUND_COUNT: Final = 5
HISTORY_LIMIT: Final = 8
MIN_CENTER_SEPARATION: Final = 72.0
PLAYFIELD_LEFT: Final = 300
PLAYFIELD_RIGHT: Final = 860
PLAYFIELD_TOP: Final = 130
PLAYFIELD_BOTTOM: Final = 360

_LEVEL_RULES: Final[dict[int, tuple[int, int, int]]] = {
    1: (1, 3, 1600),
    2: (1, 4, 1400),
    3: (1, 5, 1200),
    4: (1, 5, 1100),
}


@dataclass(frozen=True, slots=True)
class FireflyRound:
    """One immutable quantity challenge shown to the child."""

    round_id: str
    quantity: int
    positions: tuple[tuple[int, int], ...]
    choice_values: tuple[int, int, int]
    reveal_ms: int

    def __post_init__(self) -> None:
        if not self.round_id:
            raise ValueError("round_id must not be empty")
        if not 1 <= self.quantity <= 5:
            raise ValueError("quantity must be in 1..5")
        if len(self.positions) != self.quantity:
            raise ValueError("positions must match quantity")
        if len(set(self.choice_values)) != 3 or self.quantity not in self.choice_values:
            raise ValueError("choice_values must be three unique values including the answer")
        if any(not 1 <= value <= 5 for value in self.choice_values):
            raise ValueError("choice_values must stay in 1..5")
        if self.reveal_ms < 250:
            raise ValueError("reveal_ms is unexpectedly short")
        _validate_positions(self.positions)


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
    """Create deterministic, bounded subitizing rounds from an injected RNG."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def build_set(self, level: int, *, count: int = ROUND_COUNT) -> tuple[FireflyRound, ...]:
        _require_level(level)
        if count < 1:
            raise ValueError("count must be positive")
        low, high, reveal_ms = _LEVEL_RULES[level]
        rounds: list[FireflyRound] = []
        previous_quantity: int | None = None
        for index in range(count):
            candidates = [value for value in range(low, high + 1) if value != previous_quantity]
            if not candidates:
                candidates = list(range(low, high + 1))
            quantity = self._rng.choice(candidates)
            previous_quantity = quantity
            positions = self._positions(level, quantity)
            choices = self._choices(quantity)
            rounds.append(
                FireflyRound(
                    round_id=f"L{level}-R{index + 1}-{self._rng.randrange(1_000_000):06d}",
                    quantity=quantity,
                    positions=positions,
                    choice_values=choices,
                    reveal_ms=reveal_ms,
                )
            )
        return tuple(rounds)

    def _positions(self, level: int, quantity: int) -> tuple[tuple[int, int], ...]:
        if level == 1:
            cx, cy = 590, 245
            layouts = {
                1: ((cx, cy),),
                2: ((cx - 74, cy), (cx + 74, cy)),
                3: ((cx - 82, cy + 48), (cx, cy - 58), (cx + 82, cy + 48)),
            }
            return layouts[quantity]

        points: list[tuple[int, int]] = []
        for _ in range(80):
            candidate = (
                self._rng.randint(PLAYFIELD_LEFT, PLAYFIELD_RIGHT),
                self._rng.randint(PLAYFIELD_TOP, PLAYFIELD_BOTTOM),
            )
            if all(_distance(candidate, other) >= MIN_CENTER_SEPARATION for other in points):
                points.append(candidate)
                if len(points) == quantity:
                    return tuple(points)

        grid = [
            (400, 180), (540, 170), (690, 185),
            (455, 300), (620, 300),
        ]
        self._rng.shuffle(grid)
        return tuple(grid[:quantity])

    def _choices(self, answer: int) -> tuple[int, int, int]:
        distractors = [value for value in range(1, 6) if value != answer]
        picked = self._rng.sample(distractors, 2)
        values = [answer, *picked]
        self._rng.shuffle(values)
        return (values[0], values[1], values[2])


class FireflySession:
    """Own one five-round session and prevent duplicate terminal facts."""

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
        self._history = list(history[-HISTORY_LIMIT:])
        self._completion_consumed = False

    @property
    def current_round(self) -> FireflyRound | None:
        if self.is_complete:
            return None
        return self._rounds[self._index]

    @property
    def rounds(self) -> tuple[FireflyRound, ...]:
        return tuple(self._rounds)

    @property
    def round_index(self) -> int:
        return self._index

    @property
    def is_complete(self) -> bool:
        return self._index >= len(self._rounds)

    @property
    def history(self) -> tuple[AttemptSummary, ...]:
        return tuple(self._history)

    def mark_replay(self) -> None:
        if not self.is_complete:
            self._used_replay_this_round = True

    def choose(self, value: int) -> AttemptResult:
        current = self.current_round
        if current is None:
            raise RuntimeError("cannot answer a completed session")

        self._attempts_this_round += 1
        correct = value == current.quantity
        if not correct:
            self._hints_this_round += 1
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
        session_complete = self.is_complete
        result = AttemptResult(
            correct=True,
            round_completed=True,
            session_complete=session_complete,
            first_attempt_success=first_attempt,
            hints_used=summary.hints_used,
            used_replay=summary.used_replay,
        )
        self._attempts_this_round = 0
        self._hints_this_round = 0
        self._used_replay_this_round = False
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
            return min(4, current + 1)

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
    if level not in _LEVEL_RULES:
        raise ValueError("level must be in 1..4")
