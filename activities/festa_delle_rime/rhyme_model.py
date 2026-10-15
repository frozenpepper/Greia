"""Domain model and round factory for Festa delle Rime.

One core experience: *listen, then find the rhyme*. A festival round has eight
listening challenges; every rhyme found lights one lantern of the festival
string. Four stages of the same loop make the difficulty ladder:

1. match, two pictures (one rhymes);
2. match, three pictures;
3. tricky match, three pictures, where the wrong pictures *start* like the
   target word (``moon`` → ``spoon`` vs ``map``/``mouse``), so the child must
   listen to the end of the word;
4. odd one out, three pictures: two rhyme, find the one that does not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Final, Sequence

if __package__:
    from .rhyme_content import RhymeItem, RhymeMode, get_corpus
else:
    from rhyme_content import RhymeItem, RhymeMode, get_corpus


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
CHALLENGE_COUNT: Final = 8
HISTORY_LIMIT: Final = 8
MIN_LEVEL: Final = 1
MAX_LEVEL: Final = 4


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
        if len({item.item_id for item in self.choices}) != len(self.choices):
            raise ValueError("choices must be distinct words")
        if self.mode is RhymeMode.RHYME_MATCH and self.target_item is None:
            raise ValueError("a rhyme match needs a target word")
        if self.mode is RhymeMode.RHYME_ODD and len(self.choices) != 3:
            raise ValueError("odd one out needs three words")

    @property
    def answer(self) -> RhymeItem:
        return self.choices[self.correct_index]

    @property
    def rhyme_words(self) -> tuple[RhymeItem, ...]:
        """The words that rhyme once the challenge is solved (spoken as praise)."""

        if self.mode is RhymeMode.RHYME_ODD:
            return tuple(item for index, item in enumerate(self.choices) if index != self.correct_index)
        assert self.target_item is not None
        return (self.target_item, self.answer)


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
    errors: int = 0


@dataclass(slots=True)
class _ChallengeProgress:
    attempts: int = 0
    hints: int = 0
    errors: int = 0
    eliminated: set[int] = field(default_factory=set)


class RhymeRoundFactory:
    """Generate eight balanced listening challenges for one stage.

    Distractors always come from *other* rhyme groups, so they never rhyme
    with the target by accident, and no two pictures of one challenge repeat.
    """

    def __init__(self, rng: random.Random, locale: str = "it") -> None:
        self._rng = rng
        self._locale = locale
        self._groups, self._families = get_corpus(locale)

    def build_set(self, level: int, *, count: int = CHALLENGE_COUNT) -> tuple[RhymeChallenge, ...]:
        _require_level(level)
        builders = {1: self._match, 2: self._match, 3: self._tricky_match, 4: self._odd_one_out}
        challenges: list[RhymeChallenge] = []
        last_slot = -1
        plan = self._group_plan(count, eligible=self._tricky_targets() if level == 3 else None)
        for index, (group, target) in enumerate(plan):
            mode, target_item, choices, answer = builders[level](group, target, level)
            slot = self._pick_slot(len(choices) + 1, last_slot)
            last_slot = slot
            ordered = list(choices)
            ordered.insert(slot, answer)
            challenges.append(
                RhymeChallenge(
                    challenge_id=f"L{level}-C{index + 1}-{self._rng.randrange(1_000_000):06d}",
                    mode=mode,
                    target_item=target_item,
                    choices=tuple(ordered),
                    correct_index=slot,
                )
            )
        return tuple(challenges)

    # -- planning --------------------------------------------------------------
    def _group_plan(
        self,
        count: int,
        *,
        eligible: list[tuple[tuple[RhymeItem, ...], RhymeItem]] | None,
    ) -> list[tuple[tuple[RhymeItem, ...], RhymeItem | None]]:
        """Cycle shuffled groups (or tricky targets) without back-to-back repeats."""

        if eligible:
            pool: list[tuple[tuple[RhymeItem, ...], RhymeItem | None]] = list(eligible)
        else:
            pool = [(group, None) for group in self._groups]
        plan: list[tuple[tuple[RhymeItem, ...], RhymeItem | None]] = []
        while len(plan) < count:
            batch = list(pool)
            self._rng.shuffle(batch)
            if plan and len(batch) > 1 and batch[0][0] == plan[-1][0]:
                batch.append(batch.pop(0))
            plan.extend(batch)
        return plan[:count]

    def _tricky_targets(self) -> list[tuple[tuple[RhymeItem, ...], RhymeItem]]:
        """Targets that have a rhyme partner *and* at least one same-start lure."""

        result = []
        for group in self._groups:
            for item in group:
                if self._lures_for(item, group):
                    result.append((group, item))
        return result

    def _lures_for(self, target: RhymeItem, group: tuple[RhymeItem, ...]) -> list[RhymeItem]:
        rhyming = {member.item_id for member in group}
        lures: dict[str, RhymeItem] = {}
        for family in self._families:
            if any(member.item_id == target.item_id for member in family):
                for member in family:
                    if member.item_id not in rhyming:
                        lures.setdefault(member.item_id, member)
        return list(lures.values())

    # -- challenge builders ------------------------------------------------------
    def _match(self, group, target, level):
        target_item, answer = self._target_and_partner(group, target)
        wanted = 1 if level == 1 else 2
        distractors = self._others(group, wanted, exclude=(target_item, answer))
        return RhymeMode.RHYME_MATCH, target_item, distractors, answer

    def _tricky_match(self, group, target, level):
        target_item, answer = self._target_and_partner(group, target)
        lures = self._lures_for(target_item, group)
        self._rng.shuffle(lures)
        lures = _distinct_pictures(lures, exclude=(target_item, answer))[:2]
        if len(lures) < 2:
            lures += self._others(group, 2 - len(lures), exclude=(target_item, answer, *lures))
        return RhymeMode.RHYME_MATCH, target_item, lures, answer

    def _odd_one_out(self, group, target, level):
        pair = self._rng.sample(list(group), 2)
        odd = self._others(group, 1, exclude=tuple(pair))[0]
        # The odd word is the answer; the two rhymers are the "distractors".
        return RhymeMode.RHYME_ODD, None, pair, odd

    def _target_and_partner(self, group, target) -> tuple[RhymeItem, RhymeItem]:
        if target is None:
            target, answer = self._rng.sample(list(group), 2)
            return target, answer
        partners = [member for member in group if member.item_id != target.item_id]
        return target, self._rng.choice(partners)

    def _others(self, group, wanted: int, *, exclude: tuple[RhymeItem, ...]) -> list[RhymeItem]:
        pool = [item for other in self._groups if other != group for item in other]
        self._rng.shuffle(pool)
        picked = _distinct_pictures(pool, exclude=exclude)
        if len(picked) < wanted:
            raise ValueError("rhyme corpus is too small for this stage")
        return picked[:wanted]

    def _pick_slot(self, num_choices: int, last_slot: int) -> int:
        options = [s for s in range(num_choices) if s != last_slot] or list(range(num_choices))
        return self._rng.choice(options)


def _distinct_pictures(items: Sequence[RhymeItem], *, exclude: Sequence[RhymeItem]) -> list[RhymeItem]:
    """Keep items whose word and picture differ from ``exclude`` and each other."""

    words = {item.item_id for item in exclude}
    pictures = {item.picture for item in exclude if item.has_picture}
    picked: list[RhymeItem] = []
    for item in items:
        if item.item_id in words or (item.has_picture and item.picture in pictures):
            continue
        words.add(item.item_id)
        if item.has_picture:
            pictures.add(item.picture)
        picked.append(item)
    return picked


class RhymeSession:
    """Manage active listening challenges, attempts, hints, milestones and completion."""

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
        self._progress = _ChallengeProgress()
        self._history = list(history[-HISTORY_LIMIT:])
        self._found: list[RhymeItem] = []
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
    def previous_challenge(self) -> RhymeChallenge | None:
        """The challenge solved last (shown while its rhyme is celebrated)."""

        return self._challenges[self._index - 1] if self._index > 0 else None

    @property
    def history(self) -> tuple[AttemptSummary, ...]:
        return tuple(self._history)

    @property
    def found(self) -> tuple[RhymeItem, ...]:
        """Answers found so far, one per lit festival lantern."""

        return tuple(self._found)

    @property
    def eliminated(self) -> frozenset[int]:
        """Choice indices already tried (wrong) in the current challenge."""

        return frozenset(self._progress.eliminated)

    @property
    def errors(self) -> int:
        return self._progress.errors

    def record_hint(self) -> None:
        """Count an idle hint for the current challenge (adaptation input)."""

        if not self.is_complete:
            self._progress.hints = min(32, self._progress.hints + 1)

    def select_choice(self, index: int) -> AttemptResult:
        current = self.current_challenge
        if current is None:
            raise RuntimeError("session is already complete")
        if not (0 <= index < len(current.choices)):
            raise IndexError("choice index out of bounds")

        progress = self._progress
        progress.attempts += 1

        if index != current.correct_index:
            progress.errors += 1
            progress.hints = min(32, progress.hints + 1)
            progress.eliminated.add(index)
            return AttemptResult(
                correct=False,
                challenge_completed=False,
                session_complete=False,
                first_attempt_success=False,
                hints_used=progress.hints,
                used_retry=True,
                errors=progress.errors,
            )

        first_attempt = progress.attempts == 1 and progress.errors == 0
        summary = AttemptSummary(
            first_attempt_success=first_attempt,
            hints_used=progress.hints,
            used_retry=progress.errors > 0,
        )
        self._history.append(summary)
        del self._history[:-HISTORY_LIMIT]
        self._found.append(current.answer)

        self._pending_milestone = {
            "level": self.level,
            "challenge_index": self._index + 1,
            "first_attempt": int(first_attempt),
        }

        self._index += 1
        self._progress = _ChallengeProgress()
        return AttemptResult(
            correct=True,
            challenge_completed=True,
            session_complete=self.is_complete,
            first_attempt_success=first_attempt,
            hints_used=summary.hints_used,
            used_retry=summary.used_retry,
            errors=0,
        )

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
    """Bounded adaptation policy for stages 1..4."""
    _require_level(current)
    recent = tuple(history[-HISTORY_LIMIT:])
    if len(recent) >= HISTORY_LIMIT:
        strong = sum(item.first_attempt_success and item.hints_used <= 1 for item in recent)
        if strong >= 6:
            return min(MAX_LEVEL, current + 1)

    if len(recent) >= 3:
        last_three = recent[-3:]
        if all((not item.first_attempt_success) and item.hints_used >= 1 for item in last_three):
            return max(MIN_LEVEL, current - 1)
    return current


def _require_level(level: int) -> None:
    if not (MIN_LEVEL <= level <= MAX_LEVEL):
        raise ValueError("level must be in 1..4")
