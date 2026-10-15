"""Domain model for La Casa del Dieci (The Ten House).

The house is a ten-frame: two rows of five rooms that always fill in reading
order (top row left to right, then the bottom row), so every quantity keeps
its 5-and-10 structure. A glowing room has a firefly living in it.

One visit is six challenges of one loop -- *make the house show the number* --
in four enacted forms:

* ``COMPOSE``: light rooms until the house shows the number on the roof sign,
  optionally starting from a given part ("7 is 5 and 2");
* ``ADD``: guest fireflies wait outside; the child brings each one in, then
  says how many rooms glow in all;
* ``TAKE_AWAY``: some fireflies fly home to the sky, then the child says how
  many rooms still glow;
* ``MISSING_PART``: the sign shows the whole; the child says how many more
  fireflies are needed, then watches the chosen number try to move in.

This module owns the arithmetic invariants, deterministic generation, the
per-challenge phase machine, bounded adaptation and the milestone/completion
facts. It knows nothing about Pygame, timing or art.
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
ROW_LENGTH: Final = 5
HISTORY_LIMIT: Final = 8
MAX_GUESTS: Final = 4
LEVEL_MIN: Final = 1
LEVEL_MAX: Final = 5


class OperationMode(StrEnum):
    COMPOSE = "compose"
    MISSING_PART = "missing_part"
    ADD = "add"
    TAKE_AWAY = "take_away"


class Phase(StrEnum):
    """Where the child is inside one challenge."""

    BUILD = "build"  # light / unlight rooms, then confirm
    ARRIVING = "arriving"  # guests wait outside; each tap brings one in
    LEAVING = "leaving"  # fireflies fly home one by one (paced by the app)
    ASKING = "asking"  # choose how many
    SOLVED = "solved"  # correct; the app celebrates, then calls ``advance``


class RoomState(StrEnum):
    DARK = "dark"
    HOME = "home"  # the given / first part
    GUEST = "guest"  # the part the child added or invited


class RoomChange(StrEnum):
    NONE = "none"
    LIT = "lit"
    UNLIT = "unlit"


@dataclass(frozen=True, slots=True)
class StagePresentation:
    """How much scaffolding a level shows (the dot frames fade out)."""

    sign_dots: bool
    card_frames: bool

    @classmethod
    def for_level(cls, level: int) -> "StagePresentation":
        _require_level(level)
        return cls(sign_dots=level == 1, card_frames=level == 3)


@dataclass(frozen=True, slots=True)
class TenHouseChallenge:
    """One concrete challenge on the ten-frame house."""

    challenge_id: str
    mode: OperationMode
    target: int
    starting_lit: int
    delta: int
    answer: int
    choice_values: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.challenge_id:
            raise ValueError("challenge_id must not be empty")
        for name in ("target", "starting_lit", "delta", "answer"):
            if not 0 <= getattr(self, name) <= ROOM_COUNT:
                raise ValueError(f"{name} must be in 0..{ROOM_COUNT}")

        if self.mode == OperationMode.COMPOSE:
            if self.answer != self.target or self.delta != 0:
                raise ValueError("compose requires answer == target and no delta")
            if not 0 <= self.starting_lit < self.target:
                raise ValueError("compose must leave at least one room for the child to light")
        elif self.mode == OperationMode.ADD:
            if self.starting_lit + self.delta != self.answer or self.target != self.answer:
                raise ValueError("add requires starting_lit + delta == answer == target")
            if not 1 <= self.delta <= MAX_GUESTS:
                raise ValueError(f"add brings 1..{MAX_GUESTS} guests")
        elif self.mode == OperationMode.TAKE_AWAY:
            if self.starting_lit - self.delta != self.answer or self.target != self.answer:
                raise ValueError("take_away requires starting_lit - delta == answer == target")
            if not 1 <= self.delta <= MAX_GUESTS or self.answer < 1:
                raise ValueError(f"take_away sends 1..{MAX_GUESTS} home and keeps at least one")
        elif self.mode == OperationMode.MISSING_PART:
            if self.starting_lit + self.answer != self.target or self.answer < 1 or self.starting_lit < 1:
                raise ValueError("missing_part requires 1 <= starting_lit < target and starting_lit + answer == target")

        if self.mode == OperationMode.COMPOSE:
            if self.choice_values:
                raise ValueError("compose has no answer cards")
            return
        if len(self.choice_values) != 3 or len(set(self.choice_values)) != 3:
            raise ValueError("choice_values must be 3 unique values")
        if self.answer not in self.choice_values:
            raise ValueError("choice_values must contain the answer")
        if any(not (0 <= v <= ROOM_COUNT) or abs(v - self.answer) > 2 for v in self.choice_values):
            raise ValueError("distractors must be near misses (answer +-1 / +-2) within 0..10")

    @property
    def has_choices(self) -> bool:
        return self.mode != OperationMode.COMPOSE


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
    """Result of one confirm or choice."""

    correct: bool
    challenge_completed: bool
    session_complete: bool
    first_attempt_success: bool
    hints_used: int
    used_retry: bool


def near_miss_choices(answer: int, rng: random.Random, *, low: int = 1, high: int = ROOM_COUNT) -> tuple[int, int, int]:
    """Answer plus two distractors at +-1 / +-2 (one of them +-1 when possible)."""

    ones = [answer + d for d in (-1, 1) if low <= answer + d <= high]
    twos = [answer + d for d in (-2, 2) if low <= answer + d <= high]
    picked: list[int] = []
    if ones:
        picked.append(rng.choice(ones))
    pool = [value for value in ones + twos if value not in picked]
    rng.shuffle(pool)
    picked.extend(pool[: 2 - len(picked)])
    values = [answer, *picked]
    rng.shuffle(values)
    return (values[0], values[1], values[2])


class TenHouseRoundFactory:
    """Create deterministic, bounded challenge sets from an injected RNG.

    Levels are stages of the same loop: 1 builds numbers (dot sign), 2 makes
    numbers from a given part, 3 adds arriving guests, 4 adds take-away and
    "how many more to make 10", 5 mixes everything without dot scaffolds.
    """

    _PLANS: Final = {
        1: ("build",) * 6,
        2: ("build", "part", "part", "build", "part", "part"),
        3: ("add", "part", "add", "add", "part", "add"),
        4: ("take", "add", "take", "ten", "take", "add"),
        5: ("ten", "take", "add", "missing", "take", "ten"),
    }

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def build_set(self, level: int, *, count: int = CHALLENGE_COUNT) -> tuple[TenHouseChallenge, ...]:
        _require_level(level)
        if count < 1:
            raise ValueError("count must be positive")
        plan = self._PLANS[level]
        challenges: list[TenHouseChallenge] = []
        seen: set[tuple[OperationMode, int, int, int]] = set()
        for index in range(count):
            kind = plan[index % len(plan)]
            for _ in range(40):
                mode, target, start, delta, answer = self._sample(kind, level)
                key = (mode, target, start, delta)
                if key not in seen:
                    break
            seen.add(key)
            choices = () if mode == OperationMode.COMPOSE else near_miss_choices(answer, self._rng)
            challenges.append(
                TenHouseChallenge(
                    challenge_id=f"L{level}-C{index + 1}-{self._rng.randrange(1_000_000):06d}",
                    mode=mode,
                    target=target,
                    starting_lit=start,
                    delta=delta,
                    answer=answer,
                    choice_values=choices,
                )
            )
        return tuple(challenges)

    def _sample(self, kind: str, level: int) -> tuple[OperationMode, int, int, int, int]:
        rng = self._rng
        if kind == "build":
            target = rng.randint(2, 10) if level == 1 else rng.randint(5, 10)
            return (OperationMode.COMPOSE, target, 0, 0, target)
        if kind == "part":
            target = rng.randint(6, 10)
            # Half the time the given part is a full top row: "5 and some more".
            start = 5 if rng.random() < 0.5 else rng.randint(1, target - 1)
            return (OperationMode.COMPOSE, target, start, 0, target)
        if kind == "add":
            guests = rng.randint(1, 3 if level <= 4 else MAX_GUESTS)
            start = 5 if rng.random() < 0.35 else rng.randint(1, ROOM_COUNT - guests)
            return (OperationMode.ADD, start + guests, start, guests, start + guests)
        if kind == "take":
            leaving = rng.randint(1, 3 if level <= 4 else MAX_GUESTS)
            start = rng.randint(leaving + 1, ROOM_COUNT)
            return (OperationMode.TAKE_AWAY, start - leaving, start, leaving, start - leaving)
        if kind == "ten":
            start = rng.randint(4, 9) if level == 4 else rng.randint(1, 9)
            return (OperationMode.MISSING_PART, ROOM_COUNT, start, 0, ROOM_COUNT - start)
        # "missing": how many more to make a smaller whole
        target = rng.randint(5, 9)
        start = rng.randint(1, target - 1)
        return (OperationMode.MISSING_PART, target, start, 0, target - start)


class TenHouseSession:
    """Own challenge progression, the lit rooms and the attempt evidence."""

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
        self.presentation = StagePresentation.for_level(level)
        self._index = 0
        self._history = list(history[-HISTORY_LIMIT:])
        self._completion_consumed = False
        self._pending_milestone: dict[str, int] | None = None
        self.phase = Phase.BUILD
        self.lit = 0
        self.given = 0
        self.waiting_guests = 0
        self.departed = 0
        self.rejected: set[int] = set()
        self._attempts = 0
        self._hints = 0
        self._used_retry = False
        self._reset_for_current()

    # -- queries ----------------------------------------------------------

    @property
    def current_challenge(self) -> TenHouseChallenge | None:
        if self.is_complete:
            return None
        return self._challenges[self._index]

    @property
    def challenge_index(self) -> int:
        return self._index

    @property
    def completed_count(self) -> int:
        return self._index + (1 if self.phase is Phase.SOLVED else 0)

    @property
    def is_complete(self) -> bool:
        return self._index >= len(self._challenges)

    @property
    def history(self) -> tuple[AttemptSummary, ...]:
        return tuple(self._history)

    @property
    def lit_count(self) -> int:
        return self.lit

    def room_state(self, index: int) -> RoomState:
        if not 0 <= index < ROOM_COUNT or index >= self.lit:
            return RoomState.DARK
        # Building from an empty house shows one colour; otherwise the given
        # part and the added part keep their own colours (part-whole).
        if index < self.given:
            return RoomState.HOME
        current = self.current_challenge
        if self.given == 0 and current is not None and current.mode == OperationMode.COMPOSE:
            return RoomState.HOME
        return RoomState.GUEST

    @property
    def room_states(self) -> tuple[bool, ...]:
        return tuple(index < self.lit for index in range(ROOM_COUNT))

    # -- actions ----------------------------------------------------------

    def tap_room(self, index: int) -> RoomChange:
        """A tap on a window: dark lights the *next* room; lit unlights the *last*.

        Rooms always fill in ten-frame order, so where the child taps never
        breaks the 5-and-10 structure. The given part cannot be switched off.
        """

        if not 0 <= index < ROOM_COUNT:
            return RoomChange.NONE
        if self.phase is not Phase.BUILD:
            return RoomChange.NONE
        if index < self.lit:
            if self.lit > self.given:
                self.lit -= 1
                return RoomChange.UNLIT
            return RoomChange.NONE
        if self.lit < ROOM_COUNT:
            self.lit += 1
            return RoomChange.LIT
        return RoomChange.NONE

    def invite_guest(self) -> bool:
        if self.phase is not Phase.ARRIVING or self.waiting_guests <= 0 or self.lit >= ROOM_COUNT:
            return False
        self.waiting_guests -= 1
        self.lit += 1
        if self.waiting_guests == 0:
            self.phase = Phase.ASKING
        return True

    def depart_one(self) -> bool:
        current = self.current_challenge
        if self.phase is not Phase.LEAVING or current is None or self.departed >= current.delta:
            return False
        self.departed += 1
        self.lit -= 1
        self.given = min(self.given, self.lit)
        if self.departed == current.delta:
            self.phase = Phase.ASKING
        return True

    def confirm(self) -> AttemptResult:
        """Check the built house against the roof sign (COMPOSE)."""

        current = self.current_challenge
        if current is None or self.phase is not Phase.BUILD:
            raise RuntimeError("confirm is only valid while building")
        self._attempts += 1
        return self._evaluate(self.lit == current.target)

    def choose(self, value: int) -> AttemptResult:
        """Answer "how many?" (ADD / TAKE_AWAY / MISSING_PART)."""

        current = self.current_challenge
        if current is None or self.phase is not Phase.ASKING:
            raise RuntimeError("choose is only valid while asking")
        self._attempts += 1
        correct = value == current.answer
        if correct and current.mode == OperationMode.MISSING_PART:
            self.lit = current.target  # the right number of guests move in
        if not correct:
            self.rejected.add(value)
        return self._evaluate(correct)

    def note_hint(self) -> None:
        self._hints += 1

    def advance(self) -> None:
        """Leave a solved challenge and set up the next one."""

        if self.phase is not Phase.SOLVED:
            raise RuntimeError("only a solved challenge can advance")
        self._index += 1
        self._reset_for_current()

    def _evaluate(self, correct: bool) -> AttemptResult:
        if not correct:
            self._hints += 1
            self._used_retry = True
            return AttemptResult(False, False, False, False, self._hints, True)
        first = self._attempts == 1 and not self._used_retry
        summary = AttemptSummary(first, self._hints, self._used_retry)
        self._history.append(summary)
        del self._history[:-HISTORY_LIMIT]
        self._pending_milestone = {
            "level": self.level,
            "challenge_index": self._index + 1,
            "first_attempt": int(first),
        }
        self.phase = Phase.SOLVED
        return AttemptResult(
            correct=True,
            challenge_completed=True,
            session_complete=self._index + 1 >= len(self._challenges),
            first_attempt_success=first,
            hints_used=summary.hints_used,
            used_retry=summary.used_retry,
        )

    def _reset_for_current(self) -> None:
        self._attempts = 0
        self._hints = 0
        self._used_retry = False
        self.rejected = set()
        self.departed = 0
        current = self.current_challenge
        if current is None:
            return
        self.lit = current.starting_lit
        self.given = current.starting_lit
        self.waiting_guests = current.delta if current.mode == OperationMode.ADD else 0
        self.phase = {
            OperationMode.COMPOSE: Phase.BUILD,
            OperationMode.ADD: Phase.ARRIVING,
            OperationMode.TAKE_AWAY: Phase.LEAVING,
            OperationMode.MISSING_PART: Phase.ASKING,
        }[current.mode]

    # -- facts --------------------------------------------------------------

    def consume_milestone(self) -> dict[str, int] | None:
        """Return and clear the pending room milestone fact."""

        fact = self._pending_milestone
        self._pending_milestone = None
        return fact

    def consume_completion(self) -> dict[str, int] | None:
        """Return the terminal factual completion payload once."""

        solved_all = self.is_complete or (
            self._index == len(self._challenges) - 1 and self.phase is Phase.SOLVED
        )
        if not solved_all or self._completion_consumed:
            return None
        self._completion_consumed = True
        recent = self._history[-CHALLENGE_COUNT:]
        return {
            "level": self.level,
            "first_attempt_count": sum(item.first_attempt_success for item in recent),
            "retries": sum(item.used_retry for item in recent),
        }


def adapt_level(current: int, history: Sequence[AttemptSummary]) -> int:
    """Bounded between-visit adaptation policy across levels 1..5."""

    _require_level(current)
    recent = tuple(history[-HISTORY_LIMIT:])
    if len(recent) >= HISTORY_LIMIT:
        strong = sum(item.first_attempt_success and item.hints_used <= 1 for item in recent)
        if strong >= 6:
            return min(LEVEL_MAX, current + 1)
    if len(recent) >= 3:
        last_three = recent[-3:]
        if all((not item.first_attempt_success) and item.hints_used >= 1 for item in last_three):
            return max(LEVEL_MIN, current - 1)
    return current


def room_row_column(index: int) -> tuple[int, int]:
    """Ten-frame position of a room: top row first, left to right."""

    return divmod(index, ROW_LENGTH)


def _require_level(level: int) -> None:
    if not (LEVEL_MIN <= level <= LEVEL_MAX):
        raise ValueError("level must be in 1..5")
