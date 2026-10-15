"""Domain model and round factory for Officina dei Suoni.

One core experience: *listen, then feed the Sound Machine the right thing*.
A workshop round has six challenges; three stages of the same loop make the
difficulty ladder (sound first, letters later — letter **names** belong to
Leo's Letter Garden, never to this Activity):

1. **first sound** — the machine plays an isolated sound (/m/); the child feeds
   it the picture whose word starts with that sound. No letter is visible
   until the answer is found;
2. **sound to letter** — the machine shows and says a word; the child feeds it
   the capital letter of the word's first sound;
3. **build a word** — the machine shows the word's letters with sound slots;
   the child fills the first sound and then one later sound (reviewed per
   word in ``sound_content``), hearing each sound as it lands.

Each decision offers three choices; wrong choices are eliminated, so a child
who struggles narrows the task by playing. Retries are unlimited.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Final, Sequence, Union

if __package__:
    from .sound_content import (
        SoundUnit,
        WordItem,
        WorkshopMode,
        get_build_slots,
        get_sound_units,
        pictures_conflict,
    )
else:
    from sound_content import (
        SoundUnit,
        WordItem,
        WorkshopMode,
        get_build_slots,
        get_sound_units,
        pictures_conflict,
    )


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
CHALLENGE_COUNT: Final = 6
CHOICE_COUNT: Final = 3
HISTORY_LIMIT: Final = 8
MIN_LEVEL: Final = 1
MAX_LEVEL: Final = 3

Choice = Union[WordItem, str]


@dataclass(frozen=True, slots=True)
class ChoiceStep:
    """One decision: pick the right picture (stage 1) or capital letter (2–3).

    ``unit`` is the sound the step is about; ``slot`` is the letter position
    in the target word that the step fills (``None`` for picture steps).
    """

    choices: tuple[Choice, ...]
    correct_index: int
    unit: SoundUnit
    slot: int | None = None

    def __post_init__(self) -> None:
        if len(self.choices) != CHOICE_COUNT:
            raise ValueError(f"a step offers exactly {CHOICE_COUNT} choices")
        if not (0 <= self.correct_index < len(self.choices)):
            raise ValueError("correct_index is out of range")
        if len(set(_choice_key(c) for c in self.choices)) != len(self.choices):
            raise ValueError("choices must be distinct")

    @property
    def answer(self) -> Choice:
        return self.choices[self.correct_index]

    @property
    def is_letter(self) -> bool:
        return isinstance(self.answer, str)


@dataclass(frozen=True, slots=True)
class WorkshopChallenge:
    """One Sound Machine task made of one (stages 1–2) or two (stage 3) steps."""

    challenge_id: str
    mode: WorkshopMode
    target_unit: SoundUnit
    target_word: WordItem | None
    steps: tuple[ChoiceStep, ...]

    def __post_init__(self) -> None:
        if not self.challenge_id:
            raise ValueError("challenge_id must not be empty")
        if not self.steps:
            raise ValueError("a challenge needs at least one step")
        if self.mode is WorkshopMode.FIND_SOUND:
            if self.target_word is not None or len(self.steps) != 1 or self.steps[0].is_letter:
                raise ValueError("a first-sound task is one picture step without a shown word")
        else:
            if self.target_word is None:
                raise ValueError("letter tasks need a target word")
            for step in self.steps:
                if not step.is_letter or step.slot is None:
                    raise ValueError("letter tasks fill letter slots")
                if self.target_word.label[step.slot] != step.answer:
                    raise ValueError("a slot answer must be the word's letter at that slot")

    @property
    def choices(self) -> tuple[Choice, ...]:
        """Choices of the first step (stable compatibility view)."""

        return self.steps[0].choices

    @property
    def correct_index(self) -> int:
        return self.steps[0].correct_index

    @property
    def answer_word(self) -> WordItem:
        """The word the machine ends up holding once the task is solved."""

        if self.target_word is not None:
            return self.target_word
        answer = self.steps[0].answer
        assert isinstance(answer, WordItem)
        return answer

    @property
    def slots(self) -> tuple[int, ...]:
        return tuple(step.slot for step in self.steps if step.slot is not None)


@dataclass(frozen=True, slots=True)
class AttemptSummary:
    """Outcome of one completed challenge (adaptation input, persisted)."""

    first_attempt_success: bool
    hints_used: int
    used_retry: bool

    def __post_init__(self) -> None:
        if self.hints_used < 0:
            raise ValueError("hints_used must be >= 0")


@dataclass(frozen=True, slots=True)
class AttemptResult:
    """Result of one choice."""

    correct: bool
    step_completed: bool
    challenge_completed: bool
    session_complete: bool
    first_attempt_success: bool
    hints_used: int
    used_retry: bool
    errors: int = 0


@dataclass(slots=True)
class _ChallengeProgress:
    step: int = 0
    attempts: int = 0
    hints: int = 0
    errors: int = 0
    eliminated: set[int] = field(default_factory=set)
    filled: list[int] = field(default_factory=list)


class SoundRoundFactory:
    """Generate six balanced challenges for one stage.

    Targets cycle through shuffled sound units without back-to-back repeats,
    no word is the answer twice in a round, distractors come from *other*
    sounds, and pictures that could be named alike never share a task.
    """

    def __init__(self, rng: random.Random, locale: str = "it") -> None:
        self._rng = rng
        self._locale = locale
        self._units = get_sound_units(locale)
        self._build_slots = get_build_slots(locale)
        self._unit_by_letter = {unit.grapheme_upper: unit for unit in self._units}
        self._last_slot = -1
        self._used_words: set[str] = set()

    def unit_for_letter(self, letter: str) -> SoundUnit | None:
        """The sound taught for one capital letter in this language (or None)."""

        return self._unit_by_letter.get(letter)

    def build_set(self, level: int, *, count: int = CHALLENGE_COUNT) -> tuple[WorkshopChallenge, ...]:
        _require_level(level)
        builder = {1: self._first_sound, 2: self._first_letter, 3: self._build_word}[level]
        challenges: list[WorkshopChallenge] = []
        self._last_slot = -1
        self._used_words: set[str] = set()
        for index, item in enumerate(self._plan(level, count)):
            mode, unit, word, steps = builder(item)
            challenges.append(
                WorkshopChallenge(
                    challenge_id=f"L{level}-C{index + 1}-{self._rng.randrange(1_000_000):06d}",
                    mode=mode,
                    target_unit=unit,
                    target_word=word,
                    steps=steps,
                )
            )
        return tuple(challenges)

    # -- planning ----------------------------------------------------------------
    def _plan(self, level: int, count: int) -> list:
        if level == 3:
            pool: list = self._build_pool()
        else:
            pool = list(self._units)
        plan: list = []
        while len(plan) < count:
            batch = list(pool)
            self._rng.shuffle(batch)
            if plan and len(batch) > 1 and batch[0] == plan[-1]:
                batch.append(batch.pop(0))
            plan.extend(batch)
        return plan[:count]

    def _build_pool(self) -> list[tuple[WordItem, tuple[int, ...]]]:
        """Reviewed build lessons with a picture, else first-sound-only lessons."""

        words = {word.word_id: word for unit in self._units for word in unit.words}
        pool = [
            (words[word_id], slots)
            for word_id, slots in self._build_slots.items()
            if word_id in words and words[word_id].has_picture
        ]
        if not pool:
            pool = [(word, (0,)) for unit in self._units for word in _usable(unit.words)]
        return pool

    # -- builders ----------------------------------------------------------------------
    def _first_sound(self, unit: SoundUnit):
        answer = self._pick_word(unit)
        distractors: list[WordItem] = []
        others = [other for other in self._units if other is not unit]
        self._rng.shuffle(others)
        for other in others:
            if len(distractors) == CHOICE_COUNT - 1:
                break
            candidates = [
                word
                for word in _usable(other.words)
                if not any(pictures_conflict(word.picture, taken.picture) for taken in (answer, *distractors))
            ]
            if candidates:
                distractors.append(self._rng.choice(candidates))
        if len(distractors) < CHOICE_COUNT - 1:
            raise ValueError("sound corpus is too small for a first-sound task")
        choices, correct = self._place(answer, distractors)
        step = ChoiceStep(choices, correct, unit)
        return WorkshopMode.FIND_SOUND, unit, None, (step,)

    def _first_letter(self, unit: SoundUnit):
        word = self._pick_word(unit)
        step = self._letter_step(word, 0)
        return WorkshopMode.INITIAL_LETTER, unit, word, (step,)

    def _build_word(self, lesson: tuple[WordItem, tuple[int, ...]]):
        word, slots = lesson
        self._used_words.add(word.word_id)
        steps = tuple(self._letter_step(word, slot) for slot in slots)
        return WorkshopMode.BUILD_WORD, steps[0].unit, word, steps

    # -- helpers ---------------------------------------------------------------------------
    def _pick_word(self, unit: SoundUnit) -> WordItem:
        usable = _usable(unit.words)
        fresh = [word for word in usable if word.word_id not in self._used_words] or usable
        word = self._rng.choice(fresh)
        self._used_words.add(word.word_id)
        return word

    def _letter_step(self, word: WordItem, slot: int) -> ChoiceStep:
        letter = word.label[slot]
        unit = self._unit_by_letter.get(letter)
        if unit is None:
            raise ValueError(f"{word.word_id!r} slot {slot} has no taught sound")
        others = [other.grapheme_upper for other in self._units if other.grapheme_upper != letter]
        distractors = self._rng.sample(others, CHOICE_COUNT - 1)
        choices, correct = self._place(letter, distractors)
        return ChoiceStep(choices, correct, unit, slot)

    def _place(self, answer: Choice, distractors: Sequence[Choice]) -> tuple[tuple[Choice, ...], int]:
        options = [s for s in range(CHOICE_COUNT) if s != self._last_slot] or list(range(CHOICE_COUNT))
        slot = self._rng.choice(options)
        self._last_slot = slot
        ordered = list(distractors)
        ordered.insert(slot, answer)
        return tuple(ordered), slot


def _usable(words: Sequence[WordItem]) -> tuple[WordItem, ...]:
    """Pictured words; staged languages without pictures fall back to all words."""

    pictured = tuple(word for word in words if word.has_picture)
    return pictured or tuple(words)


def _choice_key(choice: Choice) -> str:
    return choice.word_id if isinstance(choice, WordItem) else choice


class SoundSession:
    """Manage the active challenges, steps, attempts, hints, milestones and completion."""

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
        self._progress = _ChallengeProgress()
        self._history = list(history[-HISTORY_LIMIT:])
        self._made: list[WorkshopChallenge] = []
        self._completion_consumed = False
        self._pending_milestone: dict[str, int] | None = None

    # -- read-only views ------------------------------------------------------------
    @property
    def current_challenge(self) -> WorkshopChallenge | None:
        if self.is_complete:
            return None
        return self._challenges[self._index]

    @property
    def current_step(self) -> ChoiceStep | None:
        challenge = self.current_challenge
        if challenge is None:
            return None
        return challenge.steps[self._progress.step]

    @property
    def step_index(self) -> int:
        return self._progress.step

    @property
    def challenge_index(self) -> int:
        return self._index

    @property
    def is_complete(self) -> bool:
        return self._index >= len(self._challenges)

    @property
    def previous_challenge(self) -> WorkshopChallenge | None:
        """The challenge solved last (shown while it is celebrated)."""

        return self._challenges[self._index - 1] if self._index > 0 else None

    @property
    def history(self) -> tuple[AttemptSummary, ...]:
        return tuple(self._history)

    @property
    def made(self) -> tuple[WorkshopChallenge, ...]:
        """Challenges solved this round, one per filled progress dot."""

        return tuple(self._made)

    @property
    def eliminated(self) -> frozenset[int]:
        """Choice indices already tried (wrong) in the current step."""

        return frozenset(self._progress.eliminated)

    @property
    def filled_slots(self) -> tuple[int, ...]:
        """Letter slots of the current challenge filled so far."""

        return tuple(self._progress.filled)

    @property
    def errors(self) -> int:
        return self._progress.errors

    # -- actions -----------------------------------------------------------------------
    def record_hint(self) -> None:
        """Count an idle hint for the current challenge (adaptation input)."""

        if not self.is_complete:
            self._progress.hints = min(32, self._progress.hints + 1)

    def select_choice(self, index: int) -> AttemptResult:
        challenge = self.current_challenge
        step = self.current_step
        if challenge is None or step is None:
            raise RuntimeError("session is already complete")
        if not (0 <= index < len(step.choices)):
            raise IndexError("choice index out of bounds")

        progress = self._progress
        progress.attempts += 1

        if index != step.correct_index:
            progress.errors += 1
            progress.hints = min(32, progress.hints + 1)
            progress.eliminated.add(index)
            return AttemptResult(
                correct=False,
                step_completed=False,
                challenge_completed=False,
                session_complete=False,
                first_attempt_success=False,
                hints_used=progress.hints,
                used_retry=True,
                errors=progress.errors,
            )

        if step.slot is not None:
            progress.filled.append(step.slot)
        if progress.step + 1 < len(challenge.steps):
            progress.step += 1
            progress.eliminated = set()
            return AttemptResult(
                correct=True,
                step_completed=True,
                challenge_completed=False,
                session_complete=False,
                first_attempt_success=False,
                hints_used=progress.hints,
                used_retry=progress.errors > 0,
                errors=0,
            )

        first_attempt = progress.errors == 0
        summary = AttemptSummary(
            first_attempt_success=first_attempt,
            hints_used=progress.hints,
            used_retry=progress.errors > 0,
        )
        self._history.append(summary)
        del self._history[:-HISTORY_LIMIT]
        self._made.append(challenge)
        self._pending_milestone = {
            "level": self.level,
            "word_index": self._index + 1,
            "first_attempt": int(first_attempt),
        }
        self._index += 1
        self._progress = _ChallengeProgress()
        return AttemptResult(
            correct=True,
            step_completed=True,
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
    """Bounded adaptation policy for stages 1..3.

    Five strong answers (first try, at most one hint) in the last eight move
    up a stage; three hinted misses in a row move down one.
    """

    _require_level(current)
    recent = tuple(history[-HISTORY_LIMIT:])
    if len(recent) >= HISTORY_LIMIT:
        strong = sum(item.first_attempt_success and item.hints_used <= 1 for item in recent)
        if strong >= 5:
            return min(MAX_LEVEL, current + 1)

    if len(recent) >= 3:
        last_three = recent[-3:]
        if all((not item.first_attempt_success) and item.hints_used >= 1 for item in last_three):
            return max(MIN_LEVEL, current - 1)
    return current


def _require_level(level: int) -> None:
    if not (MIN_LEVEL <= level <= MAX_LEVEL):
        raise ValueError("level must be in 1..3")
