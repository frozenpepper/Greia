"""Domain model and round factory for Leo's Syllable Train (no pygame, no IO).

A round is six picture words. Each word arrives on a train with one wagon per
syllable beat. Three stages of the same loop form the difficulty ladder:

Italian / Spanish (``ReadingMethod.CV_SYLLABLES``)
    clap the beats first, then build each wagon:

    1. the wagon shows its consonant; choose the vowel that makes the
       syllable you hear (L + U → "lu");
    2. choose each wagon's whole syllable tile among near neighbours
       (same consonant / same vowel);
    3. build the word from one shared pool of syllable tiles, in order.

French (staged, ``SYLLABLE_TILES``) uses stages 2–3 only (whole syllables).

English (``BEATS``) never shows letters: the train has N wagons (1 or 2
beats); choose the picture whose word fits (2 pictures, then 3, then 3 without
the pictures being named first), then clap its beats onto the wagons.

Wrong choices are eliminated, retries are unlimited, and only syllables with an
authored recording are ever offered (``clip_exists`` is injected).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import random
from typing import Callable, Final, Sequence, Union

if __package__:
    from .sillabe_content import (
        ReadingMethod,
        TrainWord,
        approved_syllables,
        get_reading_method,
        get_syllable_curriculum,
        syllable_cue,
        train_words,
    )
else:
    from sillabe_content import (
        ReadingMethod,
        TrainWord,
        approved_syllables,
        get_reading_method,
        get_syllable_curriculum,
        syllable_cue,
        train_words,
    )


CHALLENGE_COUNT: Final = 6
HISTORY_LIMIT: Final = 8
MIN_LEVEL: Final = 1
MAX_LEVEL: Final = 3
MAX_CHOICES: Final = 4

Choice = Union[TrainWord, str]


class StepKind(StrEnum):
    VOWEL = "vowel"          # consonant given on the wagon; choose the vowel
    SYLLABLE = "syllable"    # choose the wagon's whole syllable tile
    PICTURE = "picture"      # choose the picture whose word fits the train


class Phase(StrEnum):
    CLAP = "clap"
    CHOOSE = "choose"


@dataclass(frozen=True, slots=True)
class ChoiceStep:
    """One decision.

    ``wagon`` is the wagon the step builds (``None`` for picture steps);
    ``given`` is the consonant already shown on the wagon (vowel steps);
    ``used`` are pool tiles already placed on an earlier wagon (stage 3).
    """

    kind: StepKind
    choices: tuple[Choice, ...]
    correct_index: int
    wagon: int | None = None
    given: str = ""
    used: frozenset[int] = frozenset()

    def __post_init__(self) -> None:
        if not 2 <= len(self.choices) <= MAX_CHOICES:
            raise ValueError("a step offers two to four choices")
        if not 0 <= self.correct_index < len(self.choices):
            raise ValueError("correct_index is out of range")
        if self.correct_index in self.used:
            raise ValueError("the answer cannot be a used tile")
        if len({_choice_key(c) for c in self.choices}) != len(self.choices):
            raise ValueError("choices must be distinct")
        if (self.kind is StepKind.PICTURE) != (self.wagon is None):
            raise ValueError("only picture steps have no wagon")

    @property
    def answer(self) -> Choice:
        return self.choices[self.correct_index]

    def syllable_for(self, index: int) -> str:
        """The syllable a (vowel or syllable) choice would put on the wagon."""

        choice = self.choices[index]
        assert isinstance(choice, str)
        return f"{self.given}{choice}" if self.kind is StepKind.VOWEL else choice

    @property
    def target_syllable(self) -> str:
        return self.syllable_for(self.correct_index)


@dataclass(frozen=True, slots=True)
class TrainChallenge:
    """One word on the train: the clap phase plus one or more choice steps."""

    challenge_id: str
    method: ReadingMethod
    level: int
    word: TrainWord
    steps: tuple[ChoiceStep, ...]

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValueError("a challenge needs at least one step")
        if self.method is ReadingMethod.BEATS:
            if len(self.steps) != 1 or self.steps[0].kind is not StepKind.PICTURE:
                raise ValueError("a beats challenge is one picture step")
            if self.steps[0].answer != self.word:
                raise ValueError("the picture answer must be the train's word")
            beats = [c.beats for c in self.steps[0].choices if isinstance(c, TrainWord)]
            if beats.count(self.word.beats) != 1:
                raise ValueError("exactly one picture may fit the train")
        else:
            if len(self.steps) != self.word.beats:
                raise ValueError("one build step per wagon")
            for index, step in enumerate(self.steps):
                if step.wagon != index or step.target_syllable != self.word.syllables[index]:
                    raise ValueError("a build step must make its wagon's syllable")

    @property
    def wagons(self) -> int:
        return self.word.beats

    @property
    def clap_first(self) -> bool:
        """Builders clap before building; the beats train claps after choosing."""

        return self.method is not ReadingMethod.BEATS


@dataclass(frozen=True, slots=True)
class AttemptSummary:
    """Outcome of one completed word (adaptation input, persisted)."""

    first_attempt_success: bool
    hints_used: int
    used_retry: bool

    def __post_init__(self) -> None:
        if self.hints_used < 0:
            raise ValueError("hints_used must be >= 0")


@dataclass(frozen=True, slots=True)
class AttemptResult:
    correct: bool
    step_completed: bool
    challenge_completed: bool
    session_complete: bool
    errors: int = 0


@dataclass(frozen=True, slots=True)
class ClapResult:
    """One beat clapped onto a wagon (``beat`` is the wagon index)."""

    beat: int
    clap_completed: bool
    challenge_completed: bool
    session_complete: bool


@dataclass(slots=True)
class _ChallengeProgress:
    claps: int = 0
    step: int = 0
    hints: int = 0
    errors: int = 0
    eliminated: set[int] = field(default_factory=set)
    built: list[int] = field(default_factory=list)
    chosen: bool = False


class TrainRoundFactory:
    """Generate six balanced train words for one stage of one language."""

    def __init__(
        self,
        rng: random.Random,
        locale: str = "it",
        *,
        clip_exists: Callable[[str], bool] | None = None,
    ) -> None:
        self._rng = rng
        self.method = get_reading_method(locale)
        self._curriculum = get_syllable_curriculum(locale)
        self._vowels = tuple(self._curriculum.vowels)
        self._consonants = tuple(self._curriculum.consonants)
        has = clip_exists if clip_exists is not None else (lambda _cue: True)
        self._approved = tuple(s for s in approved_syllables(locale) if has(syllable_cue(s)))
        approved = set(self._approved)
        self._words = tuple(
            word for word in train_words(locale)
            if self.method is ReadingMethod.BEATS or all(part in approved for part in word.syllables)
        )
        if self.method is ReadingMethod.BEATS:
            beats = {word.beats for word in self._words}
            if len(beats) < 2:
                raise ValueError("a beats train needs words with different beat counts")
        elif len(self._words) < 3:
            raise ValueError("too few pictured words for a syllable train")
        self._last_slot = -1

    @property
    def words(self) -> tuple[TrainWord, ...]:
        return self._words

    @property
    def approved(self) -> tuple[str, ...]:
        return self._approved

    def build_set(self, level: int, *, count: int = CHALLENGE_COUNT) -> tuple[TrainChallenge, ...]:
        _require_level(level)
        self._last_slot = -1
        words = self._plan(count)
        challenges = []
        for index, word in enumerate(words):
            if self.method is ReadingMethod.BEATS:
                steps = (self._picture_step(word, level),)
            else:
                steps = self._build_steps(word, level)
            challenges.append(
                TrainChallenge(
                    challenge_id=f"L{level}-C{index + 1}-{self._rng.randrange(1_000_000):06d}",
                    method=self.method,
                    level=level,
                    word=word,
                    steps=steps,
                )
            )
        return tuple(challenges)

    # -- planning -----------------------------------------------------------------
    def _plan(self, count: int) -> list[TrainWord]:
        if self.method is ReadingMethod.BEATS:
            # Alternate-ish beat counts so neither train length dominates.
            groups: dict[int, list[TrainWord]] = {}
            for word in self._words:
                groups.setdefault(word.beats, []).append(word)
            beats = sorted(groups)
            pattern = [beats[i % len(beats)] for i in range(count)]
            self._rng.shuffle(pattern)
            plan: list[TrainWord] = []
            pools = {b: [] for b in beats}
            for wanted in pattern:
                if not pools[wanted]:
                    pools[wanted] = list(groups[wanted])
                    self._rng.shuffle(pools[wanted])
                plan.append(pools[wanted].pop())
            return plan
        plan = []
        while len(plan) < count:
            batch = list(self._words)
            self._rng.shuffle(batch)
            if plan and batch[0] == plan[-1]:
                batch.append(batch.pop(0))
            plan.extend(batch)
        return plan[:count]

    # -- beats ----------------------------------------------------------------------
    def _picture_step(self, word: TrainWord, level: int) -> ChoiceStep:
        size = 2 if level == 1 else 3
        others = [w for w in self._words if w.beats != word.beats and w.picture != word.picture]
        self._rng.shuffle(others)
        distractors = others[: size - 1]
        if len(distractors) < size - 1:
            raise ValueError("too few pictures with a different beat count")
        choices, correct = self._place(word, distractors)
        return ChoiceStep(StepKind.PICTURE, choices, correct)

    # -- building -------------------------------------------------------------------
    def _build_steps(self, word: TrainWord, level: int) -> tuple[ChoiceStep, ...]:
        parts = word.syllables
        if level == 3 and len(set(parts)) == len(parts) and len(parts) <= MAX_CHOICES - 2:
            return self._pool_steps(word)
        steps = []
        for wagon, syllable in enumerate(parts):
            step = None
            if level == 1 and self.method is ReadingMethod.CV_SYLLABLES:
                step = self._vowel_step(syllable, wagon)
            if step is None:
                step = self._syllable_step(syllable, wagon, exclude=set(parts) - {syllable})
            steps.append(step)
        return tuple(steps)

    def _split_cv(self, syllable: str) -> tuple[str, str] | None:
        if len(syllable) == 2 and syllable[0] in self._consonants_all and syllable[1] in self._vowels:
            return syllable[0], syllable[1]
        return None

    @property
    def _consonants_all(self) -> set[str]:
        return {s[0] for s in self._approved if len(s) == 2}

    def _vowel_step(self, syllable: str, wagon: int) -> ChoiceStep | None:
        split = self._split_cv(syllable)
        if split is None:
            return None
        consonant, vowel = split
        siblings = [
            v for v in self._vowels
            if v != vowel and f"{consonant}{v}" in self._approved
        ]
        if len(siblings) < 2:
            return None
        distractors = self._rng.sample(siblings, 2)
        choices, correct = self._place(vowel, distractors)
        return ChoiceStep(StepKind.VOWEL, choices, correct, wagon=wagon, given=consonant)

    def _neighbours(self, syllable: str, exclude: set[str], count: int) -> list[str]:
        """Near distractors: same consonant first, then same vowel, then any."""

        pool = [s for s in self._approved if s != syllable and s not in exclude]
        same_start = [s for s in pool if s[:1] == syllable[:1]]
        same_end = [s for s in pool if s[-1:] == syllable[-1:] and s not in same_start]
        rest = [s for s in pool if s not in same_start and s not in same_end]
        picked: list[str] = []
        for group in (same_start, same_end):
            if group and len(picked) < count:
                picked.append(self._rng.choice(group))
        remaining = [s for s in (*same_start, *same_end, *rest) if s not in picked]
        self._rng.shuffle(remaining)
        picked.extend(remaining[: count - len(picked)])
        if len(picked) < count:
            raise ValueError("too few recorded syllables for distractors")
        return picked

    def _syllable_step(self, syllable: str, wagon: int, *, exclude: set[str]) -> ChoiceStep:
        distractors = self._neighbours(syllable, exclude, 2)
        choices, correct = self._place(syllable, distractors)
        return ChoiceStep(StepKind.SYLLABLE, choices, correct, wagon=wagon)

    def _pool_steps(self, word: TrainWord) -> tuple[ChoiceStep, ...]:
        parts = list(word.syllables)
        distractors: list[str] = []
        for part in parts:
            if len(parts) + len(distractors) >= MAX_CHOICES:
                break
            near = self._neighbours(part, set(parts) | set(distractors), 1)
            distractors.extend(near)
        pool = parts + distractors
        self._rng.shuffle(pool)
        steps = []
        used: set[int] = set()
        for wagon, part in enumerate(parts):
            index = pool.index(part)
            steps.append(
                ChoiceStep(StepKind.SYLLABLE, tuple(pool), index, wagon=wagon, used=frozenset(used))
            )
            used.add(index)
        return tuple(steps)

    def _place(self, answer: Choice, distractors: Sequence[Choice]) -> tuple[tuple[Choice, ...], int]:
        size = len(distractors) + 1
        options = [s for s in range(size) if s != self._last_slot] or list(range(size))
        slot = self._rng.choice(options)
        self._last_slot = slot
        ordered = list(distractors)
        ordered.insert(slot, answer)
        return tuple(ordered), slot


def _choice_key(choice: Choice) -> str:
    return choice.word_id if isinstance(choice, TrainWord) else choice


class TrainSession:
    """Own the active round: clap beats, choice steps, attempts, hints, completion."""

    def __init__(
        self,
        challenges: Sequence[TrainChallenge],
        *,
        level: int,
        history: Sequence[AttemptSummary] = (),
    ) -> None:
        _require_level(level)
        if len(challenges) != CHALLENGE_COUNT:
            raise ValueError(f"a syllable-train round has exactly {CHALLENGE_COUNT} words")
        self._challenges = tuple(challenges)
        self.level = level
        self._index = 0
        self._progress = _ChallengeProgress()
        self._history = list(history[-HISTORY_LIMIT:])
        self._completion_consumed = False
        self._pending_milestone: dict[str, int] | None = None

    # -- views ----------------------------------------------------------------------
    @property
    def current_challenge(self) -> TrainChallenge | None:
        return None if self.is_complete else self._challenges[self._index]

    @property
    def previous_challenge(self) -> TrainChallenge | None:
        return self._challenges[self._index - 1] if self._index > 0 else None

    @property
    def phase(self) -> Phase | None:
        challenge = self.current_challenge
        if challenge is None:
            return None
        clap_done = self._progress.claps >= challenge.wagons
        if challenge.clap_first:
            return Phase.CHOOSE if clap_done else Phase.CLAP
        return Phase.CLAP if self._progress.chosen else Phase.CHOOSE

    @property
    def current_step(self) -> ChoiceStep | None:
        challenge = self.current_challenge
        if challenge is None or self.phase is not Phase.CHOOSE:
            return None
        return challenge.steps[self._progress.step]

    @property
    def step_index(self) -> int:
        return self._progress.step

    @property
    def claps(self) -> int:
        return self._progress.claps

    @property
    def built_wagons(self) -> tuple[int, ...]:
        return tuple(self._progress.built)

    @property
    def challenge_index(self) -> int:
        return self._index

    @property
    def is_complete(self) -> bool:
        return self._index >= len(self._challenges)

    @property
    def eliminated(self) -> frozenset[int]:
        """Choice indices tried (wrong) in this step, plus tiles already placed."""

        step = self.current_step
        used = step.used if step is not None else frozenset()
        return frozenset(self._progress.eliminated) | used

    @property
    def errors(self) -> int:
        return self._progress.errors

    @property
    def history(self) -> tuple[AttemptSummary, ...]:
        return tuple(self._history)

    # -- actions ----------------------------------------------------------------------
    def record_hint(self) -> None:
        if not self.is_complete:
            self._progress.hints = min(32, self._progress.hints + 1)

    def clap(self) -> ClapResult | None:
        """Clap one beat onto the next wagon; ``None`` outside the clap phase."""

        challenge = self.current_challenge
        if challenge is None or self.phase is not Phase.CLAP:
            return None
        beat = self._progress.claps
        self._progress.claps += 1
        done = self._progress.claps >= challenge.wagons
        completed = done and not challenge.clap_first
        if completed:
            self._complete(challenge)
        return ClapResult(beat, done, completed, completed and self.is_complete)

    def select_choice(self, index: int) -> AttemptResult:
        challenge = self.current_challenge
        step = self.current_step
        if challenge is None or step is None:
            raise RuntimeError("no choice is open")
        if not 0 <= index < len(step.choices):
            raise IndexError("choice index out of bounds")
        if index in self.eliminated:
            raise ValueError("that choice is no longer available")
        progress = self._progress
        if index != step.correct_index:
            progress.errors += 1
            progress.hints = min(32, progress.hints + 1)
            progress.eliminated.add(index)
            return AttemptResult(False, False, False, False, progress.errors)
        progress.eliminated = set()
        if step.wagon is not None:
            progress.built.append(step.wagon)
        if progress.step + 1 < len(challenge.steps):
            progress.step += 1
            return AttemptResult(True, True, False, False)
        if challenge.clap_first:
            self._complete(challenge)
            return AttemptResult(True, True, True, self.is_complete)
        progress.chosen = True
        return AttemptResult(True, True, False, False)

    def _complete(self, challenge: TrainChallenge) -> None:
        progress = self._progress
        first = progress.errors == 0
        self._history.append(AttemptSummary(first, progress.hints, progress.errors > 0))
        del self._history[:-HISTORY_LIMIT]
        self._pending_milestone = {
            "level": self.level,
            "word_index": self._index + 1,
            "beats": challenge.wagons,
            "first_attempt": int(first),
        }
        self._index += 1
        self._progress = _ChallengeProgress()

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
    """Bounded adaptation for stages 1..3.

    Five strong words (first try, at most one hint) in the last eight move up a
    stage; three hinted misses in a row move down one.
    """

    _require_level(current)
    recent = tuple(history[-HISTORY_LIMIT:])
    if len(recent) >= HISTORY_LIMIT:
        strong = sum(item.first_attempt_success and item.hints_used <= 1 for item in recent)
        if strong >= 5:
            return min(MAX_LEVEL, current + 1)
    if len(recent) >= 3 and all(
        (not item.first_attempt_success) and item.hints_used >= 1 for item in recent[-3:]
    ):
        return max(MIN_LEVEL, current - 1)
    return current


def _require_level(level: int) -> None:
    if not MIN_LEVEL <= level <= MAX_LEVEL:
        raise ValueError("level must be in 1..3")


__all__ = [
    "AttemptResult",
    "AttemptSummary",
    "CHALLENGE_COUNT",
    "ChoiceStep",
    "ClapResult",
    "HISTORY_LIMIT",
    "MAX_CHOICES",
    "Phase",
    "StepKind",
    "TrainChallenge",
    "TrainRoundFactory",
    "TrainSession",
    "adapt_level",
]
