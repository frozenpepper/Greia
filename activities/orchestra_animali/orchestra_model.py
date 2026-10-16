"""Orchestra Animali — pure band/echo domain (no pygame, IO or clock).

Free play is the heart of the Activity; inside the same screen a musician
now and then invites the child to "copy my rhythm". This module owns the
musical rules of that invitation:

* ``EchoPattern`` — the beats a musician plays (who plays, and when, in beats);
* ``judge_echo`` — whether the child's taps echo the pattern (same players in
  the same order; for uneven patterns the same long/short rhythm, judged
  relative to the child's own tempo so fast and slow players both succeed);
* ``PatternFactory`` — the stage ladder (2 even beats → 3 even beats → two
  players → long/short rhythm → two players with rhythm);
* ``ConcertSession`` — one finite concert of ``SESSION_ECHOES`` invitations
  with cheap adaptive staging;
* ``ConcertProgress`` — the saved state, migrated forward from the legacy
  ``{"stars": n}`` payload without losing anything.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
import random
from typing import Final

if __package__:
    from .orchestra_content import BAND, LEVEL_MAX, LEVEL_MIN, SESSION_ECHOES
else:  # pragma: no cover - runtime/script fallback
    from orchestra_content import BAND, LEVEL_MAX, LEVEL_MIN, SESSION_ECHOES


# Any rainbow-xylophone bar counts as this "voice" inside an echo attempt.
XYLOPHONE_VOICE: Final = len(BAND)
# An interval counts as "long" when it is at least this many times the
# shortest interval of the same performance (between 1:1 and 2:1).
LONG_RATIO: Final = 1.45
# Taps closer than this are treated as this far apart (double-tap jitter).
MIN_INTERVAL_SECONDS: Final = 0.06


@dataclass(frozen=True, slots=True)
class Beat:
    """One note of a pattern: the band member playing it and its onset in beats."""

    voice: int
    at: float


@dataclass(frozen=True, slots=True)
class EchoPattern:
    """A short call the child echoes; onsets are in beats (tempo-free)."""

    beats: tuple[Beat, ...]
    level: int

    def __post_init__(self) -> None:
        if len(self.beats) < 2:
            raise ValueError("an echo pattern needs at least two beats")
        onsets = [beat.at for beat in self.beats]
        if onsets != sorted(onsets) or len(set(onsets)) != len(onsets):
            raise ValueError("pattern onsets must strictly increase")
        if any(not 0 <= beat.voice < len(BAND) for beat in self.beats):
            raise ValueError("pattern voices must be band members")

    @property
    def length(self) -> int:
        return len(self.beats)

    @property
    def voices(self) -> tuple[int, ...]:
        """Distinct players in order of first appearance."""

        return tuple(dict.fromkeys(beat.voice for beat in self.beats))

    @property
    def span(self) -> float:
        return self.beats[-1].at - self.beats[0].at

    def long_flags(self) -> tuple[bool, ...] | None:
        """Long/short shape of the gaps, or ``None`` for an even pattern."""

        return rhythm_flags([beat.at for beat in self.beats])


def rhythm_flags(onsets: Sequence[float]) -> tuple[bool, ...] | None:
    """Classify each inter-onset gap as long (True) or short.

    Returns ``None`` when every gap is "short", i.e. the performance is even.
    """

    if len(onsets) < 2:
        return None
    gaps = [max(MIN_INTERVAL_SECONDS, b - a) for a, b in zip(onsets, onsets[1:])]
    shortest = min(gaps)
    flags = tuple(gap >= LONG_RATIO * shortest for gap in gaps)
    return flags if any(flags) else None


class EchoVerdict(StrEnum):
    MATCH = "match"
    TOO_FEW = "too_few"
    WRONG_PLAYER = "wrong_player"
    WRONG_RHYTHM = "wrong_rhythm"


def judge_echo(pattern: EchoPattern, attempt: Sequence[tuple[int, float]]) -> EchoVerdict:
    """Judge ``attempt`` = ``[(voice, seconds), ...]`` against ``pattern``."""

    if len(attempt) < pattern.length:
        return EchoVerdict.TOO_FEW
    taps = list(attempt[: pattern.length])
    if [voice for voice, _ in taps] != [beat.voice for beat in pattern.beats]:
        return EchoVerdict.WRONG_PLAYER
    expected = pattern.long_flags()
    if expected is not None:
        played = rhythm_flags([at for _, at in taps]) or (False,) * (pattern.length - 1)
        if played != expected:
            return EchoVerdict.WRONG_RHYTHM
    return EchoVerdict.MATCH


# -- the stage ladder ---------------------------------------------------------

_EVEN: Final = {2: (0.0, 1.0), 3: (0.0, 1.0, 2.0)}
_RHYTHMS: Final = (
    (0.0, 1.0, 1.5),        # taa  ti
    (0.0, 0.5, 1.5),        # ti   taa
    (0.0, 1.0, 2.0, 2.5),   # taa  taa  ti
    (0.0, 0.5, 1.0, 2.0),   # ti   ti   taa
)
# A = the inviting musician, B = the neighbour who joins in.
_ORDERS: Final = {
    3: ((0, 0, 1), (0, 1, 0), (0, 1, 1)),
    4: ((0, 0, 1, 1), (0, 1, 1, 0), (0, 0, 0, 1), (0, 1, 0, 1)),
}


def level_uses_partner(level: int) -> bool:
    return level in (3, 5)


class PatternFactory:
    """Build the call for one invitation at a given stage.

    1: two even beats · 2: three even beats · 3: two players, three even
    beats · 4: one player with a long/short rhythm · 5: two players with a
    long/short rhythm.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng if rng is not None else random.Random()

    def build(self, level: int, lead: int, partner: int | None = None) -> EchoPattern:
        level = max(LEVEL_MIN, min(LEVEL_MAX, int(level)))
        if level == 1:
            onsets = _EVEN[2]
        elif level in (2, 3):
            onsets = _EVEN[3]
        else:
            onsets = self._rng.choice(_RHYTHMS)
        if level_uses_partner(level) and partner is not None and partner != lead:
            order = self._rng.choice(_ORDERS[len(onsets)])
            voices = [lead if slot == 0 else partner for slot in order]
        else:
            voices = [lead] * len(onsets)
        return EchoPattern(tuple(Beat(v, at) for v, at in zip(voices, onsets)), level)


# -- one concert ----------------------------------------------------------------


@dataclass(slots=True)
class Invitation:
    """One "copy my rhythm" moment inside free play."""

    index: int
    lead: int
    partner: int | None
    pattern: EchoPattern
    attempts: int = 0
    hints: int = 0
    matched: bool = False


class ConcertSession:
    """A finite concert: ``total`` echo invitations between free play.

    Adaptive staging is deliberately cheap: two clean first-try echoes in a
    row step the stage up; an invitation that needed three or more tries
    steps it down for the next one.
    """

    def __init__(
        self,
        factory: PatternFactory,
        *,
        level: int = LEVEL_MIN,
        total: int = SESSION_ECHOES,
        rng: random.Random | None = None,
    ) -> None:
        if total < 1:
            raise ValueError("a concert needs at least one invitation")
        self._factory = factory
        self._rng = rng if rng is not None else random.Random()
        self.level = max(LEVEL_MIN, min(LEVEL_MAX, int(level)))
        self.total = int(total)
        self.completed = 0
        self.current: Invitation | None = None
        self._streak = 0
        self._last_lead: int | None = None

    @property
    def finished(self) -> bool:
        return self.completed >= self.total

    def invite(self) -> Invitation:
        """Open the next invitation (a different musician than last time)."""

        if self.finished:
            raise RuntimeError("the concert is already complete")
        choices = [index for index in range(len(BAND)) if index != self._last_lead]
        lead = self._rng.choice(choices)
        neighbours = [n for n in (lead - 1, lead + 1) if 0 <= n < len(BAND)]
        partner = self._rng.choice(neighbours) if level_uses_partner(self.level) else None
        pattern = self._factory.build(self.level, lead, partner)
        self._last_lead = lead
        self.current = Invitation(self.completed, lead, partner, pattern)
        return self.current

    def note_hint(self) -> None:
        if self.current is not None:
            self.current.hints += 1

    def answer(self, attempt: Sequence[tuple[int, float]]) -> EchoVerdict:
        invitation = self.current
        if invitation is None or invitation.matched:
            raise RuntimeError("no open invitation")
        invitation.attempts += 1
        verdict = judge_echo(invitation.pattern, attempt)
        if verdict is EchoVerdict.MATCH:
            invitation.matched = True
            self.completed += 1
            self._adapt(invitation)
        return verdict

    def close(self) -> None:
        """Forget the matched invitation (back to free play)."""

        self.current = None

    def _adapt(self, invitation: Invitation) -> None:
        if invitation.attempts == 1 and invitation.hints == 0:
            self._streak += 1
            if self._streak >= 2:
                self.level = min(LEVEL_MAX, self.level + 1)
                self._streak = 0
        elif invitation.attempts >= 3:
            self.level = max(LEVEL_MIN, self.level - 1)
            self._streak = 0
        else:
            self._streak = 0


# -- saved state ------------------------------------------------------------------

PROGRESS_SCHEMA: Final = 2


@dataclass(frozen=True, slots=True)
class ConcertProgress:
    """Profile-scoped Orchestra progress (schema 2 of ``STORAGE_KEY``).

    ``stars`` carries the legacy counter forward and grows by one per echo;
    ``concerts`` counts finished concerts; ``level`` is the next stage.
    """

    level: int = LEVEL_MIN
    stars: int = 0
    concerts: int = 0

    @classmethod
    def from_raw(cls, raw: object) -> "ConcertProgress":
        if not isinstance(raw, Mapping):
            return cls()
        return cls(
            level=_bounded(raw.get("level"), LEVEL_MIN, LEVEL_MAX, LEVEL_MIN),
            stars=_bounded(raw.get("stars"), 0, 10_000_000, 0),
            concerts=_bounded(raw.get("concerts"), 0, 1_000_000, 0),
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "schema_version": PROGRESS_SCHEMA,
            "level": self.level,
            "stars": self.stars,
            "concerts": self.concerts,
        }


def _bounded(value: object, low: int, high: int, default: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return max(low, min(high, int(value)))


__all__ = [
    "Beat",
    "ConcertProgress",
    "ConcertSession",
    "PROGRESS_SCHEMA",
    "EchoPattern",
    "EchoVerdict",
    "Invitation",
    "LONG_RATIO",
    "PatternFactory",
    "XYLOPHONE_VOICE",
    "judge_echo",
    "level_uses_partner",
    "rhythm_flags",
]
