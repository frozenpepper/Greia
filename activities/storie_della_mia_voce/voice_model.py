"""Pure rules for Story Cards: ordering, telling and the slideshow.

No Pygame, no IO: the app drives these objects and the renderer reads them.

* ``OrderingBoard`` — shuffled cards in a tray, numbered slots, place/return/
  swap, a whole-story check that locks the cards already in the right place
  and sends the others home (never a penalty), and graduated hint targets.
* ``TellingSession`` — which card is being told and the child's recordings.
* ``Slideshow`` — the timing of the watch-back (voice length or a picture
  hold for cards without a voice).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import random
from typing import Final

SILENT_HOLD_SECONDS: Final = 2.6
VOICE_TAIL_SECONDS: Final = 0.7
MAX_VOICE_HOLD_SECONDS: Final = 32.0


@dataclass(frozen=True, slots=True)
class CheckResult:
    correct: bool
    returned: tuple[str, ...] = ()
    locked: tuple[int, ...] = ()


class OrderingBoard:
    """Cards of one story: tray positions, numbered slots and the right order."""

    def __init__(self, order: tuple[str, ...], tray: tuple[str, ...]) -> None:
        if len(order) < 2 or sorted(order) != sorted(tray) or len(set(order)) != len(order):
            raise ValueError("tray must be a permutation of at least two unique cards")
        self.order = tuple(order)
        self._home = {card: index for index, card in enumerate(tray)}
        self.tray: list[str | None] = list(tray)
        self.slots: list[str | None] = [None] * len(order)
        self.locked: set[int] = set()
        self.mistakes = 0
        self.checks = 0

    @classmethod
    def shuffled(cls, order: tuple[str, ...], rng: random.Random) -> "OrderingBoard":
        """A tray that is never already in story order (nothing to do)."""

        tray = list(order)
        for _ in range(12):
            rng.shuffle(tray)
            if tuple(tray) != tuple(order):
                break
        if tuple(tray) == tuple(order):
            tray = tray[1:] + tray[:1]
        return cls(tuple(order), tuple(tray))

    # -- queries --
    @property
    def size(self) -> int:
        return len(self.order)

    @property
    def full(self) -> bool:
        return all(card is not None for card in self.slots)

    @property
    def solved(self) -> bool:
        return tuple(self.slots) == self.order

    def slot_of(self, card: str) -> int | None:
        return next((index for index, item in enumerate(self.slots) if item == card), None)

    def tray_index(self, card: str) -> int:
        return self._home[card]

    def in_tray(self, card: str) -> bool:
        return self.tray[self._home[card]] == card

    def first_open_slot(self) -> int | None:
        return next((index for index, card in enumerate(self.slots) if card is None), None)

    def movable(self, slot: int) -> bool:
        return 0 <= slot < self.size and slot not in self.locked and self.slots[slot] is not None

    # -- moves --
    def place(self, card: str, slot: int | None = None) -> int | None:
        """Put ``card`` into ``slot`` (default: the first open one).

        A card already in a slot moves; an unlocked occupant of the target
        slot swaps places with it (or goes home to the tray). Returns the slot
        used, or ``None`` when nothing changed.
        """

        if card not in self._home:
            return None
        target = self.first_open_slot() if slot is None else slot
        if target is None or not 0 <= target < self.size or target in self.locked:
            return None
        source = self.slot_of(card)
        if source is not None and source in self.locked:
            return None
        if source == target:
            return target
        occupant = self.slots[target]
        if source is not None:
            self.slots[source] = occupant  # swap (or leave the old place open)
        else:
            self.tray[self._home[card]] = None
            if occupant is not None:
                self.tray[self._home[occupant]] = occupant
        self.slots[target] = card
        return target

    def take_back(self, slot: int) -> str | None:
        """Return the (unlocked) card in ``slot`` to its tray place."""

        if not self.movable(slot):
            return None
        card = self.slots[slot]
        assert card is not None
        self.slots[slot] = None
        self.tray[self._home[card]] = card
        return card

    def check(self) -> CheckResult:
        """Judge a full row: right cards lock, the others go home gently."""

        if not self.full:
            raise ValueError("check needs every slot filled")
        self.checks += 1
        if self.solved:
            self.locked = set(range(self.size))
            return CheckResult(True, locked=tuple(range(self.size)))
        self.mistakes += 1
        returned = []
        newly_locked = []
        for index, card in enumerate(self.slots):
            if card == self.order[index]:
                if index not in self.locked:
                    newly_locked.append(index)
                self.locked.add(index)
            elif card is not None:
                returned.append(card)
                self.slots[index] = None
                self.tray[self._home[card]] = card
        return CheckResult(False, tuple(returned), tuple(newly_locked))

    def hint(self) -> tuple[int, str] | None:
        """The first slot still to fill and the card that belongs there."""

        for index, card in enumerate(self.slots):
            if index in self.locked:
                continue
            if card != self.order[index]:
                return index, self.order[index]
        return None


class RecordState(StrEnum):
    IDLE = "idle"
    COUNTDOWN = "countdown"
    RECORDING = "recording"


@dataclass
class TellingSession:
    """The child telling each card in story order (recordings stay in memory)."""

    order: tuple[str, ...]
    index: int = 0
    recordings: dict[str, bytes] = field(default_factory=dict)
    durations: dict[str, float] = field(default_factory=dict)

    @property
    def card(self) -> str:
        return self.order[self.index]

    @property
    def last(self) -> bool:
        return self.index >= len(self.order) - 1

    @property
    def told(self) -> int:
        return sum(1 for card in self.order if card in self.recordings)

    def has(self, card: str | None = None) -> bool:
        return (card or self.card) in self.recordings

    def keep(self, wav: bytes, seconds: float) -> None:
        if not isinstance(wav, bytes) or not wav:
            raise ValueError("a recording must be non-empty WAV bytes")
        self.recordings[self.card] = wav
        self.durations[self.card] = max(0.0, float(seconds))

    def forget(self) -> None:
        self.recordings.pop(self.card, None)
        self.durations.pop(self.card, None)

    def advance(self) -> bool:
        if self.last:
            return False
        self.index += 1
        return True

    def back(self) -> bool:
        if self.index == 0:
            return False
        self.index -= 1
        return True


@dataclass(frozen=True, slots=True)
class Slide:
    card_id: str
    hold: float
    voiced: bool


class Slideshow:
    """Timing of the watch-back; the app plays each slide's voice itself."""

    def __init__(self, order: tuple[str, ...], durations: dict[str, float], voiced: set[str]) -> None:
        if not order:
            raise ValueError("a slideshow needs at least one card")
        self.slides = tuple(
            Slide(
                card,
                min(MAX_VOICE_HOLD_SECONDS, max(1.0, float(durations.get(card, 0.0))) + VOICE_TAIL_SECONDS)
                if card in voiced
                else SILENT_HOLD_SECONDS,
                card in voiced,
            )
            for card in order
        )
        self.index = 0
        self.started_at = 0.0
        self.finished = False

    @property
    def current(self) -> Slide:
        return self.slides[self.index]

    def start(self, now: float) -> None:
        self.index = 0
        self.started_at = now
        self.finished = False

    def due(self, now: float, *, voice_busy: bool | None) -> bool:
        """True when the current slide has been shown long enough.

        ``voice_busy`` is the live playback state of this slide's voice, or
        ``None`` when it could not be played (then the recorded length is used,
        so a silent device still shows each picture for a sensible time).
        """

        if self.finished:
            return False
        elapsed = now - self.started_at
        if self.current.voiced and voice_busy is not None:
            # Follow the real playback; the hold is a safety net only.
            return elapsed >= self.current.hold or (elapsed >= 1.0 and not voice_busy)
        return elapsed >= max(self.current.hold, SILENT_HOLD_SECONDS if not self.current.voiced else 1.0)

    def next(self, now: float) -> bool:
        """Move on; returns False (and finishes) after the last slide."""

        if self.index + 1 >= len(self.slides):
            self.finished = True
            return False
        self.index += 1
        self.started_at = now
        return True


__all__ = [
    "CheckResult",
    "OrderingBoard",
    "RecordState",
    "SILENT_HOLD_SECONDS",
    "Slide",
    "Slideshow",
    "TellingSession",
]
