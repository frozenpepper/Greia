"""Wonder Match rules: one pairs board, the sticker book and adaptation.

Pure Python (no Pygame): the board owns card states and the classic two-flip
rule, the sticker book owns which album pictures a child has collected across
visits, and ``adapt_level`` moves the grid ladder (two clean boards up, one
long board down). Nothing here can fail a child: a miss only turns the two
cards back over.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
import random

if __package__:
    from .memory_content import ALBUM_IDS, ALBUMS, LEVELS, MAX_LEVEL, Album, album_by_id
else:
    from memory_content import ALBUM_IDS, ALBUMS, LEVELS, MAX_LEVEL, Album, album_by_id

HISTORY_LIMIT = 6


class CardState(StrEnum):
    DOWN = "down"
    UP = "up"
    MATCHED = "matched"


class FlipResult(StrEnum):
    IGNORED = "ignored"
    FIRST = "first"
    MATCH = "match"
    MISS = "miss"


@dataclass(slots=True)
class Card:
    subject_id: str
    state: CardState = CardState.DOWN
    seen: bool = False


@dataclass(frozen=True, slots=True)
class FlipOutcome:
    result: FlipResult
    first: int | None = None
    second: int | None = None
    subject_id: str | None = None


class MemoryBoard:
    """One shuffled board of face-down pairs and the two-flip rule.

    While two different cards are up (``pending_miss``) no other card can be
    flipped; the Activity turns them back with ``cover_miss`` after the child
    has had a moment to look.
    """

    def __init__(self, subject_ids: Sequence[str], rng: random.Random) -> None:
        if not subject_ids or len(set(subject_ids)) != len(subject_ids):
            raise ValueError("a board needs distinct subjects")
        deck = [subject for subject in subject_ids for _ in range(2)]
        rng.shuffle(deck)
        self.cards: list[Card] = [Card(subject) for subject in deck]
        self.pairs = len(subject_ids)
        self.open_index: int | None = None
        self.pending_miss: tuple[int, int] | None = None
        self.matched = 0
        self.misses = 0
        self.miss_streak = 0

    @property
    def complete(self) -> bool:
        return self.matched >= self.pairs

    def can_flip(self, index: int) -> bool:
        return (
            0 <= index < len(self.cards)
            and self.pending_miss is None
            and self.cards[index].state is CardState.DOWN
        )

    def flip(self, index: int) -> FlipOutcome:
        if not self.can_flip(index):
            return FlipOutcome(FlipResult.IGNORED)
        card = self.cards[index]
        card.state = CardState.UP
        if self.open_index is None:
            self.open_index = index
            card.seen = True
            return FlipOutcome(FlipResult.FIRST, index, None, card.subject_id)
        first = self.open_index
        self.open_index = None
        other = self.cards[first]
        if other.subject_id == card.subject_id:
            other.state = card.state = CardState.MATCHED
            card.seen = True
            self.matched += 1
            self.miss_streak = 0
            return FlipOutcome(FlipResult.MATCH, first, index, card.subject_id)
        card.seen = True
        self.pending_miss = (first, index)
        self.misses += 1
        self.miss_streak += 1
        return FlipOutcome(FlipResult.MISS, first, index, card.subject_id)

    def cover_miss(self) -> tuple[int, ...]:
        """Turn the two missed cards face down again; returns their indices."""

        if self.pending_miss is None:
            return ()
        covered = self.pending_miss
        for index in covered:
            if self.cards[index].state is CardState.UP:
                self.cards[index].state = CardState.DOWN
        self.pending_miss = None
        return covered

    def partner(self, index: int) -> int | None:
        subject = self.cards[index].subject_id
        for other, card in enumerate(self.cards):
            if other != index and card.subject_id == subject:
                return other
        return None

    def peek_pair(self, rng: random.Random) -> tuple[int, int] | None:
        """Choose an unfound pair for Lilli's peek (prefer pictures already seen)."""

        if self.pending_miss is not None:
            return None
        candidates: dict[str, list[int]] = {}
        for index, card in enumerate(self.cards):
            if card.state is CardState.DOWN:
                candidates.setdefault(card.subject_id, []).append(index)
        pairs = [tuple(indices) for indices in candidates.values() if len(indices) == 2]
        if not pairs:
            return None
        seen = [pair for pair in pairs if any(self.cards[i].seen for i in pair)]
        pool = seen or pairs
        first, second = rng.choice(pool)
        return first, second

    def reset_streak(self) -> None:
        self.miss_streak = 0


def peek_threshold(pairs: int) -> int:
    """Misses in a row before Lilli peeks a pair (more room on bigger boards)."""

    if pairs <= 3:
        return 3
    if pairs <= 6:
        return 4
    return 5


@dataclass(frozen=True, slots=True)
class BoardResult:
    level: int
    pairs: int
    misses: int

    @property
    def clean(self) -> bool:
        return self.misses <= self.pairs

    @property
    def long(self) -> bool:
        return self.misses >= 3 * self.pairs


def adapt_level(level: int, history: Sequence[BoardResult]) -> int:
    """Two clean boards in a row at this level -> up; one long board -> down."""

    level = max(0, min(MAX_LEVEL, int(level)))
    if not history:
        return level
    last = history[-1]
    if last.level == level and last.long and level > 0:
        return level - 1
    recent = list(history[-2:])
    if len(recent) == 2 and all(item.level == level and item.clean for item in recent) and level < MAX_LEVEL:
        return level + 1
    return level


class StickerBook:
    """Which album pictures this child has collected (fills across visits)."""

    def __init__(self, collected: Mapping[str, Iterable[str]] | None = None) -> None:
        self._collected: dict[str, set[str]] = {album_id: set() for album_id in ALBUM_IDS}
        for album_id, subjects in (collected or {}).items():
            if album_id not in self._collected:
                continue
            valid = set(album_by_id(album_id).subject_ids)
            self._collected[album_id].update(subject for subject in subjects if subject in valid)

    def collected(self, album_id: str) -> frozenset[str]:
        return frozenset(self._collected.get(album_id, ()))

    def count(self, album_id: str) -> int:
        return len(self._collected.get(album_id, ()))

    def has(self, album_id: str, subject_id: str) -> bool:
        return subject_id in self._collected.get(album_id, ())

    def add(self, album_id: str, subject_id: str) -> bool:
        """Stick a picture in; returns True when it is new to the album."""

        bucket = self._collected.get(album_id)
        if bucket is None or subject_id in bucket or subject_id not in album_by_id(album_id).subject_ids:
            return False
        bucket.add(subject_id)
        return True

    def as_dict(self) -> dict[str, list[str]]:
        order = {album.album_id: album.subject_ids for album in ALBUMS}
        return {
            album_id: [subject for subject in order[album_id] if subject in subjects]
            for album_id, subjects in self._collected.items()
            if subjects
        }


def choose_subjects(album: Album, pairs: int, book: StickerBook, rng: random.Random) -> list[str]:
    """Pick the board's pictures, preferring ones still missing from the album."""

    missing = [s for s in album.subject_ids if not book.has(album.album_id, s)]
    owned = [s for s in album.subject_ids if book.has(album.album_id, s)]
    rng.shuffle(missing)
    rng.shuffle(owned)
    return (missing + owned)[: max(1, min(pairs, len(album.subjects)))]


def pairs_for_level(level: int) -> int:
    return LEVELS[max(0, min(MAX_LEVEL, level))].pairs


__all__ = [
    "BoardResult",
    "Card",
    "CardState",
    "FlipOutcome",
    "FlipResult",
    "HISTORY_LIMIT",
    "MemoryBoard",
    "StickerBook",
    "adapt_level",
    "choose_subjects",
    "pairs_for_level",
    "peek_threshold",
]
