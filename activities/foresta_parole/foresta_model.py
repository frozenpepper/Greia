"""The Word Forest — pure domain model (catalogue, round, falling letters).

One core experience: *hear the word, catch its letter*. A round has six
picture words. For each, letters drop from the canopy in calm lanes; the child
steers a basket under the letter that starts the word and lets the others
fall past. Catching another letter is a kind try-again (it bounces out);
missing a letter just lets it float away. Stages of the same loop get harder
(faster drops, more decoy letters, then look-alike decoys) and adapt to how
the last round went.

Nothing here touches pygame, audio, storage or the clock: the app feeds
``dt`` and the basket position and receives :class:`FieldEvent` facts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
import random
from typing import Final, Mapping, Sequence

if __package__:
    from .foresta_content import (
        AVOIDED_EXAMPLES,
        LETTER_TOKENS,
        LOOKALIKE_PAIRS,
        PHONICS_DATA,
        PICTURE_PENDING,
        STAGES,
        TARGETS_PER_ROUND,
        StageSpec,
    )
else:
    from foresta_content import (  # type: ignore[no-redef]
        AVOIDED_EXAMPLES,
        LETTER_TOKENS,
        LOOKALIKE_PAIRS,
        PHONICS_DATA,
        PICTURE_PENDING,
        STAGES,
        TARGETS_PER_ROUND,
        StageSpec,
    )

SUPPORTED_LANGUAGES: Final[tuple[str, ...]] = ("it", "en", "es", "fr")
FALLBACK_LANGUAGE: Final = "en"


def lesson_language(locale: str) -> str:
    """Base language with a real recorded lesson set (English otherwise)."""

    language = (locale or "").replace("_", "-").split("-", 1)[0].lower()
    return language if language in SUPPORTED_LANGUAGES else FALLBACK_LANGUAGE


@dataclass(frozen=True, slots=True)
class WordCard:
    """One picture word whose first letter is the target."""

    letter: str
    word: str
    picture: str
    prompt_cue: str   # "B as Boat"
    letter_cue: str   # "B"
    word_cue: str     # "Boat"
    color: str = "coral"


def catch_catalogue(language: str) -> tuple[WordCard, ...]:
    """Playable cards: recorded, pictured and not pedagogically misleading."""

    language = lesson_language(language)
    cards: list[WordCard] = []
    for index, (letter, letter_stem, prompt_stem, word, picture, word_stem) in enumerate(PHONICS_DATA[language]):
        if picture == PICTURE_PENDING or (language, letter) in AVOIDED_EXAMPLES:
            continue
        color = LETTER_TOKENS[index % len(LETTER_TOKENS)]
        cards.append(WordCard(letter, word, picture, prompt_stem, letter_stem, word_stem, color))
    return tuple(cards)


def lookalikes(letter: str, alphabet: Sequence[str]) -> tuple[str, ...]:
    pool = set(alphabet)
    found = [b if a == letter else a for a, b in LOOKALIKE_PAIRS if letter in (a, b)]
    return tuple(sorted(item for item in found if item in pool and item != letter))


def stage_spec(stage: int) -> StageSpec:
    return STAGES[max(1, min(len(STAGES), int(stage))) - 1]


# --------------------------------------------------------------------------
# Round: six words, each with its decoy letters.
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Target:
    card: WordCard
    decoys: tuple[str, ...]


@dataclass
class CatchRound:
    """Progress through one round's targets (errors are counted, never punished)."""

    targets: tuple[Target, ...]
    stage: int = 1
    index: int = 0
    errors: int = 0              # wrong catches this round
    target_errors: int = 0       # wrong catches on the current word
    target_misses: int = 0       # times the right letter fell past
    hints: int = 0
    caught: list[WordCard] = field(default_factory=list)
    _completion_consumed: bool = False

    @property
    def total(self) -> int:
        return len(self.targets)

    @property
    def current(self) -> Target | None:
        return self.targets[self.index] if self.index < len(self.targets) else None

    @property
    def done(self) -> int:
        return len(self.caught)

    @property
    def is_complete(self) -> bool:
        return self.index >= len(self.targets)

    def record_wrong(self) -> int:
        self.errors += 1
        self.target_errors += 1
        return self.target_errors

    def record_miss(self) -> int:
        self.target_misses += 1
        return self.target_misses

    def record_hint(self) -> None:
        self.hints += 1

    def record_caught(self) -> WordCard:
        target = self.current
        if target is None:
            raise RuntimeError("round already complete")
        self.caught.append(target.card)
        return target.card

    def advance(self) -> None:
        self.index += 1
        self.target_errors = 0
        self.target_misses = 0

    @property
    def needs_guide(self) -> bool:
        """Two wrong catches or two misses on one word → demonstrate."""

        return self.target_errors >= 2 or self.target_misses >= 2

    def consume_completion(self) -> dict[str, int] | None:
        if not self.is_complete or self._completion_consumed:
            return None
        self._completion_consumed = True
        return {"words": self.total, "stage": self.stage, "wrong_catches": self.errors, "hints": self.hints}


class RoundPlanner:
    """Choose a round's words (least-caught first) and their decoys."""

    def __init__(self, rng: random.Random, *, language: str) -> None:
        self._rng = rng
        self.language = lesson_language(language)
        self.cards = catch_catalogue(self.language)
        if len(self.cards) < 4:
            raise ValueError(f"not enough playable words for {self.language}")

    @property
    def alphabet(self) -> tuple[str, ...]:
        return tuple(card.letter for card in self.cards)

    def build(self, stage: int, caught: Mapping[str, int] | None = None) -> CatchRound:
        caught = caught or {}
        spec = stage_spec(stage)
        cards = list(self.cards)
        self._rng.shuffle(cards)
        # Least-practised letters first; the shuffle breaks ties.
        cards.sort(key=lambda card: min(int(caught.get(card.letter, 0)), 50))
        chosen = cards[: min(TARGETS_PER_ROUND, len(cards))]
        self._rng.shuffle(chosen)
        targets = tuple(Target(card, self._decoys(card.letter, spec)) for card in chosen)
        return CatchRound(targets, stage=spec.number)

    def _decoys(self, letter: str, spec: StageSpec) -> tuple[str, ...]:
        alphabet = [item for item in self.alphabet if item != letter]
        similar = list(lookalikes(letter, self.alphabet))
        picks: list[str] = []
        if spec.lookalikes and similar:
            picks.append(self._rng.choice(similar))
        # Early stages keep decoys visually distinct from the target.
        distinct = [item for item in alphabet if item not in similar and item not in picks]
        pool = distinct if not spec.lookalikes else [item for item in alphabet if item not in picks]
        self._rng.shuffle(pool)
        picks.extend(pool[: max(0, spec.decoy_kinds - len(picks))])
        return tuple(picks[: spec.decoy_kinds])


def next_stage(round_: CatchRound, stage_count: int = len(STAGES)) -> int:
    """Adapt the next round: smooth rounds climb, bumpy rounds step back."""

    stage = round_.stage
    if round_.errors <= 1 and round_.hints <= 1:
        return min(stage_count, stage + 1)
    if round_.errors >= 5:
        return max(1, stage - 1)
    return stage


# --------------------------------------------------------------------------
# Falling letters
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FieldGeometry:
    """Logical play-field geometry (1024×600 reference canvas)."""

    lanes: tuple[int, ...] = (340, 495, 650, 805, 960)
    spawn_y: float = 92.0
    mouth_y: float = 488.0
    ground_y: float = 566.0
    token: int = 104
    basket_half: int = 96
    basket_min_x: int = 300
    basket_max_x: int = 972
    sway: float = 9.0


class FallState(StrEnum):
    FALLING = "falling"
    CAUGHT = "caught"     # sliding into the basket
    BOUNCED = "bounced"   # a wrong letter hopping out of the basket
    LANDED = "landed"     # fell past; floats away


FALL_STATE_SECONDS: Final[dict[FallState, float]] = {
    FallState.CAUGHT: 0.35,
    FallState.BOUNCED: 0.9,
    FallState.LANDED: 0.8,
}


@dataclass
class FallingLetter:
    uid: int
    char: str
    is_target: bool
    lane: int
    x: float
    y: float
    speed: float
    phase: float
    color: str
    glow: bool = False
    state: FallState = FallState.FALLING
    state_age: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    passed: bool = False

    @property
    def fade(self) -> float:
        """1 → 0 while the letter leaves (caught/bounced/landed)."""

        limit = FALL_STATE_SECONDS.get(self.state)
        if limit is None:
            return 1.0
        return max(0.0, 1.0 - self.state_age / limit)


class FieldEventKind(StrEnum):
    CAUGHT_TARGET = "caught_target"
    CAUGHT_DECOY = "caught_decoy"
    MISSED_TARGET = "missed_target"


@dataclass(frozen=True, slots=True)
class FieldEvent:
    kind: FieldEventKind
    letter: FallingLetter


class ForestField:
    """Spawn, move and resolve falling letters against the basket.

    Drops use separate lanes and a minimum vertical gap, so letters never
    overlap. ``guide`` (after repeated trouble) slows the drops and sends the
    right letter next, glowing, in the lane nearest the basket.
    """

    MAX_LETTERS: Final = 8

    def __init__(self, rng: random.Random, geometry: FieldGeometry | None = None) -> None:
        self._rng = rng
        self.geometry = geometry or FieldGeometry()
        self.letters: list[FallingLetter] = []
        self.spec: StageSpec = stage_spec(1)
        self.target: str | None = None
        self.decoys: tuple[str, ...] = ()
        self.active = False
        self.guide = False
        self._uid = 0
        self._timer = 0.0
        self._last_lane: int | None = None
        self._last_decoy: str | None = None
        self._last_color: str | None = None
        self._drops = 0
        self._decoys_since_target = 0
        self._opening: list[bool] = []
        self.time = 0.0

    # -- control --------------------------------------------------------------
    def start(self, target: Target, spec: StageSpec) -> None:
        """Begin dropping for a new word (earlier letters float away)."""

        self.release_all()
        self.spec = spec
        self.target = target.card.letter
        self.decoys = target.decoys or ()
        self.active = True
        self.guide = False
        self._drops = 0
        self._decoys_since_target = 0
        self._timer = 0.15
        # The first two drops are one right letter and one other, so a choice
        # is on screen from the start.
        opening = [True, False] if self.decoys else [True]
        self._rng.shuffle(opening)
        self._opening = opening

    def stop(self) -> None:
        self.active = False

    def release_all(self) -> None:
        """Let every letter still in the air float away."""

        for letter in self.letters:
            if letter.state is FallState.FALLING:
                letter.state = FallState.LANDED
                letter.state_age = 0.0

    def set_guide(self, value: bool) -> None:
        if value and not self.guide:
            self._timer = min(self._timer, 0.6)
        self.guide = value
        for letter in self.letters:
            letter.glow = value and letter.is_target and letter.state is FallState.FALLING

    @property
    def falling(self) -> list[FallingLetter]:
        return [letter for letter in self.letters if letter.state is FallState.FALLING]

    def falling_target(self) -> FallingLetter | None:
        """The right letter in the air closest to the basket line (hints)."""

        candidates = [l for l in self.falling if l.is_target and not l.passed]
        return max(candidates, key=lambda l: l.y) if candidates else None

    # -- simulation ---------------------------------------------------------------
    def update(self, dt: float, basket_x: float) -> list[FieldEvent]:
        dt = max(0.0, min(0.1, float(dt)))
        self.time += dt
        events: list[FieldEvent] = []
        if self.active:
            self._timer -= dt
            if self._timer <= 0.0 and self._can_spawn():
                self._spawn(basket_x)
        geo = self.geometry
        speed_factor = 0.75 if self.guide else 1.0
        for letter in self.letters:
            if letter.state is FallState.FALLING:
                letter.y += letter.speed * speed_factor * dt
                lane_x = geo.lanes[letter.lane]
                letter.x = lane_x + math.sin(letter.phase + self.time * 1.6) * geo.sway
                if not letter.passed and self._in_mouth(letter, basket_x):
                    if letter.is_target:
                        letter.state = FallState.CAUGHT
                        events.append(FieldEvent(FieldEventKind.CAUGHT_TARGET, letter))
                    else:
                        letter.state = FallState.BOUNCED
                        letter.vx = 150.0 if letter.x >= basket_x else -150.0
                        letter.vy = -260.0
                        events.append(FieldEvent(FieldEventKind.CAUGHT_DECOY, letter))
                    letter.state_age = 0.0
                    continue
                if not letter.passed and letter.y > geo.mouth_y + geo.token * 0.3:
                    letter.passed = True
                    if letter.is_target:
                        events.append(FieldEvent(FieldEventKind.MISSED_TARGET, letter))
                if letter.y >= geo.ground_y:
                    letter.y = geo.ground_y
                    letter.state = FallState.LANDED
                    letter.state_age = 0.0
            else:
                letter.state_age += dt
                if letter.state is FallState.BOUNCED:
                    letter.vy += 520.0 * dt
                    letter.x += letter.vx * dt
                    letter.y += letter.vy * dt
                elif letter.state is FallState.LANDED:
                    letter.y -= 22.0 * dt   # drifts up a little as it fades
                elif letter.state is FallState.CAUGHT:
                    letter.x += (basket_x - letter.x) * min(1.0, dt * 12.0)
                    letter.y += 120.0 * dt
        self.letters = [
            letter for letter in self.letters
            if letter.state is FallState.FALLING or letter.state_age < FALL_STATE_SECONDS[letter.state]
        ]
        return events

    def _in_mouth(self, letter: FallingLetter, basket_x: float) -> bool:
        geo = self.geometry
        if not (geo.mouth_y - geo.token * 0.15 <= letter.y <= geo.mouth_y + geo.token * 0.3):
            return False
        return abs(letter.x - basket_x) <= geo.basket_half - geo.token * 0.12

    def _can_spawn(self) -> bool:
        if self.target is None or len(self.letters) >= self.MAX_LETTERS:
            return False
        return len(self.falling) < self.spec.max_falling and bool(self._free_lanes())

    def _free_lanes(self) -> list[int]:
        geo = self.geometry
        busy = {
            letter.lane for letter in self.falling
            if letter.y < geo.spawn_y + geo.token * 1.8
        }
        return [index for index in range(len(geo.lanes)) if index not in busy]

    def _choose_target(self) -> bool:
        if self.guide:
            self._opening.clear()
            return True
        if self._opening:
            return self._opening.pop(0)
        if not self.decoys:
            return True
        if any(letter.is_target for letter in self.falling):
            return False
        # Never more than two other letters in a row; otherwise about half.
        return self._decoys_since_target >= 2 or self._rng.random() < 0.5

    def _spawn(self, basket_x: float) -> None:
        assert self.target is not None
        geo = self.geometry
        lanes = self._free_lanes()
        is_target = self._choose_target()
        if self.guide and is_target:
            lane = min(lanes, key=lambda i: abs(geo.lanes[i] - basket_x))
        else:
            options = [lane for lane in lanes if lane != self._last_lane] or lanes
            lane = self._rng.choice(options)
        if is_target:
            char = self.target
            self._decoys_since_target = 0
        else:
            options = [d for d in self.decoys if d != self._last_decoy] or list(self.decoys)
            char = self._rng.choice(options)
            self._last_decoy = char
            self._decoys_since_target += 1
        # Each drop gets a fresh ink colour, so colour never gives the answer away.
        color = self._rng.choice([token for token in LETTER_TOKENS if token != self._last_color])
        self._last_color = color
        self._uid += 1
        self._drops += 1
        self._last_lane = lane
        speed = self.spec.fall_speed * self._rng.uniform(0.92, 1.08)
        self.letters.append(
            FallingLetter(
                uid=self._uid,
                char=char,
                is_target=is_target,
                lane=lane,
                x=float(geo.lanes[lane]),
                y=geo.spawn_y,
                speed=speed,
                phase=self._rng.uniform(0.0, math.tau),
                color=color,
                glow=self.guide and is_target,
            )
        )
        quick = bool(self._opening)
        base = 0.9 if quick else self.spec.spawn_interval
        self._timer = base * self._rng.uniform(0.85, 1.15)


class Basket:
    """The child's basket on the forest floor (logical x, clamped to the track)."""

    def __init__(self, geometry: FieldGeometry | None = None) -> None:
        self.geometry = geometry or FieldGeometry()
        self.x = float((self.geometry.basket_min_x + self.geometry.basket_max_x) // 2)
        self.goal: float | None = None   # pointer/touch destination

    def clamp(self, x: float) -> float:
        return max(float(self.geometry.basket_min_x), min(float(self.geometry.basket_max_x), float(x)))

    def nudge(self, dx: float) -> bool:
        before = self.x
        self.x = self.clamp(self.x + dx)
        return self.x != before

    def follow(self, dt: float, max_speed: float = 1500.0) -> bool:
        """Glide toward the pointer goal (fast, but never a teleport)."""

        if self.goal is None:
            return False
        goal = self.clamp(self.goal)
        delta = goal - self.x
        if abs(delta) < 0.5:
            self.goal = None
            return False
        step = max(-max_speed * dt, min(max_speed * dt, delta * min(1.0, dt * 14.0) if abs(delta) > 6 else delta))
        return self.nudge(step)


__all__ = [
    "Basket",
    "CatchRound",
    "FallState",
    "FallingLetter",
    "FieldEvent",
    "FieldEventKind",
    "FieldGeometry",
    "ForestField",
    "RoundPlanner",
    "Target",
    "WordCard",
    "catch_catalogue",
    "lesson_language",
    "lookalikes",
    "next_stage",
    "stage_spec",
]
