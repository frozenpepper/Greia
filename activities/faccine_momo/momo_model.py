"""Renderer-independent rules for Momo's Happy Faces.

A *visit* is ``TASKS_PER_VISIT`` tasks in three stages of one loop:

* **recognise** - Momo shows a feeling; the child picks the friend who feels
  the same (other cast faces, so it is never picture matching);
* **explain** - a picture story happens to Momo (hidden behind a ``?``
  silhouette); the child picks the face that fits;
* **help** - Momo shows a feeling in a story; the child picks the kind thing
  that would help (hug, teddy, umbrella, ...).

Wrong picks are never final: the pick is set aside and the child retries
(unlimited). The ladder (``LEVELS``) adapts between visits from first-try
answers. The optional mirror warm-up is the free face play that opens the
first visit of a session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import random

if __package__:
    from .momo_content import (
        ALL_EMOTIONS,
        FRIEND_CHARACTERS,
        HELP_PLANS,
        LEVELS,
        MAX_LEVEL,
        STORIES_BY_ID,
        TASKS_PER_VISIT,
        WARMUP_READY_FACES,
        Emotion,
        LevelPlan,
        Stage,
        stories_for,
    )
else:
    from momo_content import (
        ALL_EMOTIONS,
        FRIEND_CHARACTERS,
        HELP_PLANS,
        LEVELS,
        MAX_LEVEL,
        STORIES_BY_ID,
        TASKS_PER_VISIT,
        WARMUP_READY_FACES,
        Emotion,
        LevelPlan,
        Stage,
        stories_for,
    )


@dataclass(frozen=True, slots=True)
class Choice:
    """One answer tile: a feeling (shown by ``character``) or a help item."""

    key: str
    character: str | None = None


@dataclass(frozen=True, slots=True)
class Task:
    """One decision. ``feeling`` is what Momo feels in this task."""

    stage: Stage
    feeling: Emotion
    answer: str
    choices: tuple[Choice, ...]
    story_id: str | None = None

    @property
    def answer_index(self) -> int:
        return next(index for index, choice in enumerate(self.choices) if choice.key == self.answer)

    @property
    def emotion_answer(self) -> Emotion | None:
        return Emotion(self.answer) if self.stage is not Stage.HELP else None


class Outcome(StrEnum):
    CORRECT = "correct"
    TRY_AGAIN = "try_again"
    IGNORED = "ignored"


class TaskFactory:
    """Build a varied visit for one ladder rung (seeded ``random.Random``)."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng
        self._last_story_ids: tuple[str, ...] = ()

    def build_visit(self, level: int) -> tuple[Task, ...]:
        plan = LEVELS[max(0, min(MAX_LEVEL, level))]
        used_stories: set[str] = set()
        used_feelings: list[Emotion] = []
        tasks: list[Task] = []
        for stage in plan.stages:
            if stage is Stage.RECOGNISE:
                task = self._recognise(plan, used_feelings)
            elif stage is Stage.EXPLAIN:
                task = self._explain(plan, used_stories)
            else:
                task = self._help(plan, used_stories)
            if task.story_id is not None:
                used_stories.add(task.story_id)
            used_feelings.append(task.feeling)
            tasks.append(task)
        self._last_story_ids = tuple(used_stories)
        return tuple(tasks)

    # -- stages ----------------------------------------------------------------

    def _recognise(self, plan: LevelPlan, used: list[Emotion]) -> Task:
        fresh = [emotion for emotion in plan.pool if emotion not in used] or list(plan.pool)
        target = self._rng.choice(fresh)
        others = [emotion for emotion in plan.pool if emotion is not target]
        picks = [target, *self._rng.sample(others, plan.recognise_choices - 1)]
        self._rng.shuffle(picks)
        friends = self._rng.sample(list(FRIEND_CHARACTERS), len(picks))
        choices = tuple(Choice(emotion.value, friend) for emotion, friend in zip(picks, friends))
        return Task(Stage.RECOGNISE, target, target.value, choices)

    def _explain(self, plan: LevelPlan, used_stories: set[str]) -> Task:
        candidates = [story for story in stories_for(plan.pool) if story.story_id not in used_stories]
        fresh = [story for story in candidates if story.story_id not in self._last_story_ids]
        story = self._rng.choice(fresh or candidates)
        wrong = [emotion for emotion in plan.pool if emotion is not story.emotion and emotion not in story.also_fits]
        picks = [story.emotion, *self._rng.sample(wrong, plan.explain_choices - 1)]
        self._rng.shuffle(picks)
        choices = tuple(Choice(emotion.value, "momo") for emotion in picks)
        return Task(Stage.EXPLAIN, story.emotion, story.emotion.value, choices, story.story_id)

    def _help(self, plan: LevelPlan, used_stories: set[str]) -> Task:
        candidates = [help_plan for help_plan in HELP_PLANS if help_plan.story_id not in used_stories]
        fresh = [help_plan for help_plan in candidates if help_plan.story_id not in self._last_story_ids]
        help_plan = self._rng.choice(fresh or candidates or list(HELP_PLANS))
        story = STORIES_BY_ID[help_plan.story_id]
        picks = [help_plan.helper, *self._rng.sample(list(help_plan.distractors), plan.help_choices - 1)]
        self._rng.shuffle(picks)
        return Task(Stage.HELP, story.emotion, help_plan.helper, tuple(Choice(key) for key in picks), story.story_id)


@dataclass(slots=True)
class TaskRecord:
    first_try: bool = True
    misses: int = 0
    hints: int = 0


class MomoVisit:
    """Progress through one visit: picks, kind retries, first-try tally."""

    def __init__(self, tasks: tuple[Task, ...], *, level: int = 0) -> None:
        if not tasks:
            raise ValueError("a visit needs at least one task")
        self.tasks = tasks
        self.level = max(0, min(MAX_LEVEL, int(level)))
        self.index = 0
        self.rejected: set[int] = set()
        self.solved = False
        self.records: list[TaskRecord] = [TaskRecord() for _ in tasks]

    @property
    def task(self) -> Task:
        return self.tasks[self.index]

    @property
    def completed_count(self) -> int:
        return self.index + (1 if self.solved else 0)

    @property
    def is_last(self) -> bool:
        return self.index >= len(self.tasks) - 1

    @property
    def first_try_count(self) -> int:
        return sum(1 for record in self.records[: self.completed_count] if record.first_try)

    def choose(self, index: int) -> Outcome:
        if self.solved or index in self.rejected or not 0 <= index < len(self.task.choices):
            return Outcome.IGNORED
        if self.task.choices[index].key == self.task.answer:
            self.solved = True
            return Outcome.CORRECT
        self.rejected.add(index)
        record = self.records[self.index]
        record.first_try = False
        record.misses += 1
        return Outcome.TRY_AGAIN

    def note_hint(self) -> None:
        self.records[self.index].hints += 1

    def advance(self) -> bool:
        """Move to the next task; return False when the visit is over."""

        if not self.solved:
            return True
        if self.is_last:
            return False
        self.index += 1
        self.rejected = set()
        self.solved = False
        return True

    @property
    def finished(self) -> bool:
        return self.solved and self.is_last


def adapt_level(level: int, first_try: int, total: int = TASKS_PER_VISIT) -> int:
    """Next rung: up after a near-perfect visit, down after a hard one."""

    if first_try >= total - 1:
        return min(MAX_LEVEL, level + 1)
    if first_try <= total // 3:
        return max(0, level - 1)
    return max(0, min(MAX_LEVEL, level))


class MirrorWarmup:
    """Free face play before the first visit: Momo mirrors any chosen face."""

    def __init__(self) -> None:
        self.emotion: Emotion = Emotion.HAPPY
        self.tried: set[Emotion] = set()
        self.comforted = False

    def show(self, emotion: Emotion) -> None:
        self.emotion = emotion
        self.tried.add(emotion)
        self.comforted = False

    def comfort(self) -> bool:
        """A cuddle helps sad Momo feel better (once per sad face)."""

        if self.emotion is Emotion.SAD and not self.comforted:
            self.comforted = True
            self.emotion = Emotion.HAPPY
            return True
        return False

    @property
    def ready(self) -> bool:
        return len(self.tried) >= WARMUP_READY_FACES


@dataclass(slots=True)
class FeelingsLog:
    """Profile-wide feelings the child has recognised (for milestone events)."""

    known: set[Emotion] = field(default_factory=set)

    def learn(self, emotion: Emotion) -> bool:
        if emotion in self.known:
            return False
        self.known.add(emotion)
        return True

    def ordered(self) -> tuple[str, ...]:
        return tuple(emotion.value for emotion in ALL_EMOTIONS if emotion in self.known)


__all__ = [
    "Choice",
    "FeelingsLog",
    "MirrorWarmup",
    "MomoVisit",
    "Outcome",
    "Task",
    "TaskFactory",
    "TaskRecord",
    "adapt_level",
]
