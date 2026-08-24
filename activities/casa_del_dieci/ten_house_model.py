"""Domain model for La Casa del Dieci (Ten House).

Owns mathematical invariants within the 2x5 ten-frame representation,
deterministic challenge generation, bounded adaptation, and milestone/completion facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import random
from typing import Final, Sequence


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
CHALLENGE_COUNT: Final = 6
ROOM_COUNT: Final = 10
HISTORY_LIMIT: Final = 8


class OperationMode(StrEnum):
    COMPOSE = "compose"
    MISSING_PART = "missing_part"
    ADD = "add"
    TAKE_AWAY = "take_away"


@dataclass(frozen=True, slots=True)
class TenHouseChallenge:
    """One concrete mathematical challenge within the 2x5 ten-frame house."""

    challenge_id: str
    mode: OperationMode
    target: int
    starting_lit: int
    delta: int
    answer: int
    choice_values: tuple[int, int, int]

    def __post_init__(self) -> None:
        if not self.challenge_id:
            raise ValueError("challenge_id must not be empty")
        if not (0 <= self.target <= ROOM_COUNT):
            raise ValueError("target must be in 0..10")
        if not (0 <= self.starting_lit <= ROOM_COUNT):
            raise ValueError("starting_lit must be in 0..10")
        if not (0 <= self.delta <= ROOM_COUNT):
            raise ValueError("delta must be in 0..10")
        if not (0 <= self.answer <= ROOM_COUNT):
            raise ValueError("answer must be in 0..10")

        if self.mode == OperationMode.COMPOSE:
            if self.answer != self.target:
                raise ValueError("compose mode answer must equal target")
        elif self.mode == OperationMode.ADD:
            if self.starting_lit + self.delta != self.answer:
                raise ValueError("add mode requires starting_lit + delta == answer")
            if self.answer > ROOM_COUNT:
                raise ValueError("add result cannot exceed 10")
        elif self.mode == OperationMode.TAKE_AWAY:
            if self.starting_lit - self.delta != self.answer:
                raise ValueError("take_away mode requires starting_lit - delta == answer")
            if self.answer < 0:
                raise ValueError("take_away result cannot be negative")
        elif self.mode == OperationMode.MISSING_PART:
            if self.starting_lit + self.answer != self.target:
                raise ValueError("missing_part mode requires starting_lit + answer == target")

        if len(set(self.choice_values)) != 3 or self.answer not in self.choice_values:
            raise ValueError("choice_values must be 3 unique values containing the answer")
        if any(not (0 <= v <= ROOM_COUNT) for v in self.choice_values):
            raise ValueError("choice_values must stay in 0..10")


@dataclass(frozen=True, slots=True)
class AttemptSummary:
    """Bounded evidence from one completed challenge for adaptation."""

    first_attempt_success: bool
    hints_used: int
    used_retry: bool

    def __post_init__(self) -> None:
        if self.hints_used < 0:
            raise ValueError("hints_used must be >= 0")


@dataclass(frozen=True, slots=True)
class AttemptResult:
    """Result returned by a semantic room toggle, confirm, or choice."""

    correct: bool
    challenge_completed: bool
    session_complete: bool
    first_attempt_success: bool
    hints_used: int
    used_retry: bool


class TenHouseRoundFactory:
    """Create deterministic, bounded 10-frame challenges from an injected RNG."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def build_set(self, level: int, *, count: int = CHALLENGE_COUNT) -> tuple[TenHouseChallenge, ...]:
        _require_level(level)
        if count < 1:
            raise ValueError("count must be positive")

        challenges: list[TenHouseChallenge] = []
        seen_tuples: set[tuple[str, int, int, int, int]] = set()

        for index in range(count):
            tuple_data = self._generate_unique_tuple(level, seen_tuples)
            seen_tuples.add(tuple_data)
            mode, target, starting_lit, delta, answer = tuple_data
            choices = self._make_choices(answer)
            challenges.append(
                TenHouseChallenge(
                    challenge_id=f"L{level}-C{index + 1}-{self._rng.randrange(1_000_000):06d}",
                    mode=mode,
                    target=target,
                    starting_lit=starting_lit,
                    delta=delta,
                    answer=answer,
                    choice_values=choices,
                )
            )
        return tuple(challenges)

    def _generate_unique_tuple(
        self, level: int, seen: set[tuple[str, int, int, int, int]]
    ) -> tuple[OperationMode, int, int, int, int]:
        for _ in range(200):
            t = self._sample_level(level)
            if t not in seen:
                return t
        # Fallback if domain is exhausted: construct distinct tuple
        return self._sample_level(level)

    def _sample_level(self, level: int) -> tuple[OperationMode, int, int, int, int]:
        if level == 1:
            # L1: Compose 1..5. Target 1..5 with different initial lit rooms (0..4)
            target = self._rng.randint(1, 5)
            # starting_lit is initial number of turned-on rooms (must not already equal target)
            possible_starts = [s for s in range(0, 6) if s != target]
            starting = self._rng.choice(possible_starts)
            return (OperationMode.COMPOSE, target, starting, 0, target)

        if level == 2:
            # L2: Complete to 5..10 from a nonzero given part
            target = self._rng.randint(5, 10)
            starting = self._rng.randint(1, target - 1)
            answer = target - starting
            return (OperationMode.MISSING_PART, target, starting, 0, answer)

        if level == 3:
            # L3: Add 1..3 to 1..6 with result <= 10
            starting = self._rng.randint(1, 6)
            delta = self._rng.randint(1, min(3, 10 - starting))
            answer = starting + delta
            return (OperationMode.ADD, answer, starting, delta, answer)

        if level == 4:
            # L4: Take-away 1..3 from 3..10 with result >= 0
            starting = self._rng.randint(3, 10)
            delta = self._rng.randint(1, min(3, starting))
            answer = starting - delta
            return (OperationMode.TAKE_AWAY, answer, starting, delta, answer)

        # L5: Mixed modes
        mode = self._rng.choice(
            [OperationMode.ADD, OperationMode.TAKE_AWAY, OperationMode.MISSING_PART, OperationMode.COMPOSE]
        )
        if mode == OperationMode.COMPOSE:
            target = self._rng.randint(2, 10)
            starting = self._rng.choice([s for s in range(0, 11) if s != target])
            return (OperationMode.COMPOSE, target, starting, 0, target)
        if mode == OperationMode.MISSING_PART:
            target = self._rng.randint(5, 10)
            starting = self._rng.randint(1, target - 1)
            return (OperationMode.MISSING_PART, target, starting, 0, target - starting)
        if mode == OperationMode.ADD:
            starting = self._rng.randint(1, 7)
            delta = self._rng.randint(1, min(3, 10 - starting))
            return (OperationMode.ADD, starting + delta, starting, delta, starting + delta)
        # TAKE_AWAY
        starting = self._rng.randint(3, 10)
        delta = self._rng.randint(1, min(3, starting))
        return (OperationMode.TAKE_AWAY, starting - delta, starting, delta, starting - delta)

    def _make_choices(self, answer: int) -> tuple[int, int, int]:
        distractors = [v for v in range(0, 11) if v != answer]
        picked = self._rng.sample(distractors, 2)
        values = [answer, *picked]
        self._rng.shuffle(values)
        return (values[0], values[1], values[2])


class TenHouseSession:
    """Own challenge progression, room state, keyboard focus, and event flags."""

    def __init__(
        self,
        challenges: Sequence[TenHouseChallenge],
        *,
        level: int,
        history: Sequence[AttemptSummary] = (),
    ) -> None:
        _require_level(level)
        if len(challenges) != CHALLENGE_COUNT:
            raise ValueError(f"a Casa del Dieci session requires exactly {CHALLENGE_COUNT} challenges")
        self._challenges = tuple(challenges)
        self.level = level
        self._index = 0
        self._attempts_this_challenge = 0
        self._hints_this_challenge = 0
        self._used_retry_this_challenge = False
        self._history = list(history[-HISTORY_LIMIT:])
        self._completion_consumed = False
        self._pending_milestone: dict[str, int] | None = None

        # Room toggle states (10 bools)
        self.room_states = [False] * ROOM_COUNT
        self._reset_rooms_for_current()

        # Semantic keyboard focus
        self.focused_room = 0
        self.focused_choice = 0
        self.focus_in_choices = False

    @property
    def current_challenge(self) -> TenHouseChallenge | None:
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

    @property
    def lit_count(self) -> int:
        return sum(self.room_states)

    def _reset_rooms_for_current(self) -> None:
        current = self.current_challenge
        if current is None:
            return
        self.room_states = [False] * ROOM_COUNT
        for i in range(min(ROOM_COUNT, current.starting_lit)):
            self.room_states[i] = True

    def toggle_room(self, index: int) -> bool:
        """Toggle one room in COMPOSE mode. Returns True if room state changed."""
        current = self.current_challenge
        if current is None or current.mode != OperationMode.COMPOSE:
            return False
        if not (0 <= index < ROOM_COUNT):
            return False
        self.room_states[index] = not self.room_states[index]
        return True

    def confirm_compose(self) -> AttemptResult:
        """Confirm the current room count in COMPOSE mode."""
        current = self.current_challenge
        if current is None:
            raise RuntimeError("cannot answer a completed session")
        if current.mode != OperationMode.COMPOSE:
            raise RuntimeError("confirm is only valid in COMPOSE mode")

        self._attempts_this_challenge += 1
        correct = self.lit_count == current.target
        return self._evaluate_result(correct)

    def choose(self, value: int) -> AttemptResult:
        """Choose a numeric answer in operation / missing-part modes."""
        current = self.current_challenge
        if current is None:
            raise RuntimeError("cannot answer a completed session")

        self._attempts_this_challenge += 1
        correct = value == current.answer
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
        self._reset_rooms_for_current()
        return result

    def consume_milestone(self) -> dict[str, int] | None:
        """Return and clear pending room milestone fact."""
        fact = self._pending_milestone
        self._pending_milestone = None
        return fact

    def consume_completion(self) -> dict[str, int] | None:
        """Return the terminal factual completion payload once."""
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
