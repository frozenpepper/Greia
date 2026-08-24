"""Domain model and round factory for Festa delle Rime."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Final, Sequence

if __package__:
    from .rhyme_content import (
        RhymeItem,
        RhymeMode,
        get_corpus,
    )
else:
    from rhyme_content import (
        RhymeItem,
        RhymeMode,
        get_corpus,
    )


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
CHALLENGE_COUNT: Final = 8
HISTORY_LIMIT: Final = 8


@dataclass(frozen=True, slots=True)
class RhymeChallenge:
    """One audio-first listening challenge."""

    challenge_id: str
    mode: RhymeMode
    target_item: RhymeItem | None
    choices: tuple[RhymeItem, ...]
    correct_index: int

    def __post_init__(self) -> None:
        if not self.challenge_id:
            raise ValueError("challenge_id must not be empty")
        if not (2 <= len(self.choices) <= 3):
            raise ValueError("choices must contain 2 or 3 items")
        if not (0 <= self.correct_index < len(self.choices)):
            raise ValueError("correct_index is out of range")


@dataclass(frozen=True, slots=True)
class AttemptSummary:
    """Outcome of one completed listening challenge."""

    first_attempt_success: bool
    hints_used: int
    used_retry: bool

    def __post_init__(self) -> None:
        if self.hints_used < 0:
            raise ValueError("hints_used must be >= 0")


@dataclass(frozen=True, slots=True)
class AttemptResult:
    """Result of a choice selection."""

    correct: bool
    challenge_completed: bool
    session_complete: bool
    first_attempt_success: bool
    hints_used: int
    used_retry: bool


class RhymeRoundFactory:
    """Generate 8 balanced, deterministic listening challenges per set."""

    def __init__(self, rng: random.Random, locale: str = "it") -> None:
        self._rng = rng
        self._locale = locale
        self._rhyme_pairs, self._alliteration_families = get_corpus(locale)

    def build_set(self, level: int, *, count: int = CHALLENGE_COUNT) -> tuple[RhymeChallenge, ...]:
        _require_level(level)
        challenges: list[RhymeChallenge] = []
        last_slot = -1

        if level in {1, 2}:
            # Rhyme Matching (L1 = 2 choices, L2 = 3 choices)
            num_choices = 2 if level == 1 else 3
            # Shuffled rhyme pairs
            pairs = list(self._rhyme_pairs)
            self._rng.shuffle(pairs)

            for idx in range(count):
                pair = pairs[idx % len(pairs)]
                target, match = (pair[0], pair[1]) if self._rng.random() < 0.5 else (pair[1], pair[0])

                # Pick distractors from other pairs
                other_items = [
                    item for p in pairs if p != pair for item in p
                ]
                distractors = self._rng.sample(other_items, num_choices - 1)

                # Pick correct answer slot
                slot = self._pick_slot(num_choices, last_slot)
                last_slot = slot

                choices = list(distractors)
                choices.insert(slot, match)

                cid = f"L{level}-C{idx + 1}-{self._rng.randrange(1_000_000):06d}"
                challenges.append(
                    RhymeChallenge(
                        challenge_id=cid,
                        mode=RhymeMode.RHYME_MATCH,
                        target_item=target,
                        choices=tuple(choices),
                        correct_index=slot,
                    )
                )

        elif level == 3:
            # Rhyme Odd-One-Out (3 choices: 2 rhyme, 1 doesn't)
            pairs = list(self._rhyme_pairs)
            self._rng.shuffle(pairs)

            for idx in range(count):
                rhyme_pair = pairs[idx % len(pairs)]
                other_items = [item for p in pairs if p != rhyme_pair for item in p]
                odd_item = self._rng.choice(other_items)

                slot = self._pick_slot(3, last_slot)
                last_slot = slot

                choices = [rhyme_pair[0], rhyme_pair[1]]
                choices.insert(slot, odd_item)

                cid = f"L3-C{idx + 1}-{self._rng.randrange(1_000_000):06d}"
                challenges.append(
                    RhymeChallenge(
                        challenge_id=cid,
                        mode=RhymeMode.RHYME_ODD,
                        target_item=None,
                        choices=tuple(choices),
                        correct_index=slot,
                    )
                )

        else:
            # Level 4: Alliteration (3 choices: 1 target, 1 matches initial sound, 2 from other families)
            families = list(self._alliteration_families)
            self._rng.shuffle(families)

            for idx in range(count):
                family = families[idx % len(families)]
                target, match = self._rng.sample(family, 2)

                other_items = [item for f in families if f != family for item in f]
                distractors = self._rng.sample(other_items, 2)

                slot = self._pick_slot(3, last_slot)
                last_slot = slot

                choices = list(distractors)
                choices.insert(slot, match)

                cid = f"L4-C{idx + 1}-{self._rng.randrange(1_000_000):06d}"
                challenges.append(
                    RhymeChallenge(
                        challenge_id=cid,
                        mode=RhymeMode.ALLITERATION,
                        target_item=target,
                        choices=tuple(choices),
                        correct_index=slot,
                    )
                )

        return tuple(challenges)

    def _pick_slot(self, num_choices: int, last_slot: int) -> int:
        options = [s for s in range(num_choices) if s != last_slot]
        if not options:
            options = list(range(num_choices))
        return self._rng.choice(options)


class RhymeSession:
    """Manage active listening challenges, attempts, milestones, and completion facts."""

    def __init__(
        self,
        challenges: Sequence[RhymeChallenge],
        *,
        level: int,
        history: Sequence[AttemptSummary] = (),
    ) -> None:
        _require_level(level)
        if len(challenges) != CHALLENGE_COUNT:
            raise ValueError(f"a Festa delle Rime session requires exactly {CHALLENGE_COUNT} challenges")
        self._challenges = tuple(challenges)
        self.level = level
        self._index = 0
        self._attempts_this_challenge = 0
        self._hints_this_challenge = 0
        self._used_retry_this_challenge = False
        self._history = list(history[-HISTORY_LIMIT:])
        self._completion_consumed = False
        self._pending_milestone: dict[str, int] | None = None

    @property
    def current_challenge(self) -> RhymeChallenge | None:
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

    def select_choice(self, index: int) -> AttemptResult:
        current = self.current_challenge
        if current is None:
            raise RuntimeError("session is already complete")
        if not (0 <= index < len(current.choices)):
            raise IndexError("choice index out of bounds")

        self._attempts_this_challenge += 1

        if index != current.correct_index:
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

        # Correct!
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
    """Bounded adaptation policy for levels 1..4."""
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


def _require_level(level: int) -> None:
    if not (1 <= level <= 4):
        raise ValueError("level must be in 1..4")
