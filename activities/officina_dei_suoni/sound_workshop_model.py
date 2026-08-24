"""Domain model and round factory for Officina dei Suoni."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Final, Sequence

if __package__:
    from .sound_content import (
        SoundUnit,
        WordItem,
        WorkshopMode,
        get_sound_units,
    )
else:
    from sound_content import (
        SoundUnit,
        WordItem,
        WorkshopMode,
        get_sound_units,
    )


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
CHALLENGE_COUNT: Final = 6
HISTORY_LIMIT: Final = 8


@dataclass(frozen=True, slots=True)
class WorkshopChallenge:
    """One phonological sound workshop challenge."""

    challenge_id: str
    mode: WorkshopMode
    target_unit: SoundUnit | None
    target_word: WordItem | None
    choices: tuple[Any, ...]  # WordItem for L1, uppercase letter strings for L2/L3
    correct_index: int

    def __post_init__(self) -> None:
        if not self.challenge_id:
            raise ValueError("challenge_id must not be empty")
        if not (2 <= len(self.choices) <= 4):
            raise ValueError("choices must contain 2 to 4 items")
        if not (0 <= self.correct_index < len(self.choices)):
            raise ValueError("correct_index is out of range")


@dataclass(frozen=True, slots=True)
class AttemptSummary:
    first_attempt_success: bool
    hints_used: int
    used_retry: bool

    def __post_init__(self) -> None:
        if self.hints_used < 0:
            raise ValueError("hints_used must be >= 0")


@dataclass(frozen=True, slots=True)
class AttemptResult:
    correct: bool
    challenge_completed: bool
    session_complete: bool
    first_attempt_success: bool
    hints_used: int
    used_retry: bool


class SoundRoundFactory:
    """Generate 6 balanced, deterministic sound challenges per set."""

    def __init__(self, rng: random.Random, locale: str = "it") -> None:
        self._rng = rng
        self._locale = locale
        self._units = get_sound_units(locale)

    def build_set(self, level: int, *, count: int = CHALLENGE_COUNT) -> tuple[WorkshopChallenge, ...]:
        _require_level(level)
        challenges: list[WorkshopChallenge] = []
        last_slot = -1

        units = list(self._units)
        self._rng.shuffle(units)

        if level == 1:
            # L1: Hear isolated phoneme, choose 1 of 3 pictures whose initial sound matches
            for idx in range(count):
                target_unit = units[idx % len(units)]
                correct_word = self._rng.choice(target_unit.words)

                # Distractor words from other units
                other_units = [u for u in units if u != target_unit]
                distractors = [self._rng.choice(u.words) for u in self._rng.sample(other_units, 2)]

                slot = self._pick_slot(3, last_slot)
                last_slot = slot

                choices: list[WordItem] = list(distractors)
                choices.insert(slot, correct_word)

                cid = f"L1-C{idx + 1}-{self._rng.randrange(1_000_000):06d}"
                challenges.append(
                    WorkshopChallenge(
                        challenge_id=cid,
                        mode=WorkshopMode.FIND_SOUND,
                        target_unit=target_unit,
                        target_word=None,
                        choices=tuple(choices),
                        correct_index=slot,
                    )
                )

        elif level == 2:
            # L2: Hear word/picture, choose initial letter tile (e.g. 'M') from 3 choices
            for idx in range(count):
                target_unit = units[idx % len(units)]
                target_word = self._rng.choice(target_unit.words)
                correct_letter = target_unit.grapheme_upper

                other_units = [u for u in units if u != target_unit]
                distractor_letters = [u.grapheme_upper for u in self._rng.sample(other_units, 2)]

                slot = self._pick_slot(3, last_slot)
                last_slot = slot

                choices_str: list[str] = list(distractor_letters)
                choices_str.insert(slot, correct_letter)

                cid = f"L2-C{idx + 1}-{self._rng.randrange(1_000_000):06d}"
                challenges.append(
                    WorkshopChallenge(
                        challenge_id=cid,
                        mode=WorkshopMode.INITIAL_LETTER,
                        target_unit=target_unit,
                        target_word=target_word,
                        choices=tuple(choices_str),
                        correct_index=slot,
                    )
                )

        else:
            # L3: Word building with visual sound boxes [ _ ][ E ][ L ][ A ]
            for idx in range(count):
                target_unit = units[idx % len(units)]
                target_word = self._rng.choice(target_unit.words)
                correct_letter = target_unit.grapheme_upper

                other_units = [u for u in units if u != target_unit]
                distractor_letters = [u.grapheme_upper for u in self._rng.sample(other_units, 2)]

                slot = self._pick_slot(3, last_slot)
                last_slot = slot

                choices_str = list(distractor_letters)
                choices_str.insert(slot, correct_letter)

                cid = f"L3-C{idx + 1}-{self._rng.randrange(1_000_000):06d}"
                challenges.append(
                    WorkshopChallenge(
                        challenge_id=cid,
                        mode=WorkshopMode.BUILD_WORD,
                        target_unit=target_unit,
                        target_word=target_word,
                        choices=tuple(choices_str),
                        correct_index=slot,
                    )
                )

        return tuple(challenges)

    def _pick_slot(self, num_choices: int, last_slot: int) -> int:
        options = [s for s in range(num_choices) if s != last_slot]
        if not options:
            options = list(range(num_choices))
        return self._rng.choice(options)


class SoundSession:
    """Manage active challenges, attempts, and milestone/completion facts."""

    def __init__(
        self,
        challenges: Sequence[WorkshopChallenge],
        *,
        level: int,
        history: Sequence[AttemptSummary] = (),
    ) -> None:
        _require_level(level)
        if len(challenges) != CHALLENGE_COUNT:
            raise ValueError(f"an Officina dei Suoni session requires exactly {CHALLENGE_COUNT} challenges")
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
    def current_challenge(self) -> WorkshopChallenge | None:
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

        # Correct
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
            "word_index": self._index + 1,
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
    """Bounded adaptation policy for levels 1..3."""
    _require_level(current)
    recent = tuple(history[-HISTORY_LIMIT:])
    if len(recent) >= HISTORY_LIMIT:
        strong = sum(item.first_attempt_success and item.hints_used <= 1 for item in recent)
        if strong >= 5:
            return min(3, current + 1)

    if len(recent) >= 3:
        last_three = recent[-3:]
        if all((not item.first_attempt_success) and item.hints_used >= 1 for item in last_three):
            return max(1, current - 1)
    return current


def _require_level(level: int) -> None:
    if not (1 <= level <= 3):
        raise ValueError("level must be in 1..3")
