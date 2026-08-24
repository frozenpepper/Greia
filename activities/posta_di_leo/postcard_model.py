"""Domain model and grapheme-safe postcard text editor for Posta di Leo."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Final, Sequence

from greia_platform.typography import (
    grapheme_spans,
    next_grapheme_boundary,
    previous_grapheme_boundary,
    snap_grapheme_boundary,
)

if __package__:
    from .postcard_content import VALID_RECIPIENT_IDS, VALID_STAMP_IDS
else:
    from postcard_content import VALID_RECIPIENT_IDS, VALID_STAMP_IDS


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600
MAX_GRAPHEMES: Final = 80
MAX_SAVED_CARDS: Final = 20


@dataclass(frozen=True, slots=True)
class SavedPostcard:
    """One immutable saved postcard record."""

    card_id: str
    created_at: int
    recipient_id: str
    stamp_id: str
    text: str

    def __post_init__(self) -> None:
        if not self.card_id:
            raise ValueError("card_id must not be empty")
        if self.recipient_id not in VALID_RECIPIENT_IDS:
            raise ValueError(f"unknown recipient_id: {self.recipient_id!r}")
        if self.stamp_id not in VALID_STAMP_IDS:
            raise ValueError(f"unknown stamp_id: {self.stamp_id!r}")
        if len(grapheme_spans(self.text)) > MAX_GRAPHEMES:
            raise ValueError(f"postcard text exceeds {MAX_GRAPHEMES} graphemes")


class PostcardDraft:
    """Active mutable postcard draft with grapheme-safe cursor editing."""

    def __init__(
        self,
        *,
        recipient_id: str = "leo",
        stamp_id: str = "heart",
        text: str = "",
    ) -> None:
        self.recipient_id = recipient_id if recipient_id in VALID_RECIPIENT_IDS else "leo"
        self.stamp_id = stamp_id if stamp_id in VALID_STAMP_IDS else "heart"
        self._text = text
        self._cursor = len(text)

    @property
    def text(self) -> str:
        return self._text

    @property
    def cursor(self) -> int:
        return self._cursor

    @property
    def grapheme_count(self) -> int:
        return len(grapheme_spans(self._text))

    def set_recipient(self, recipient_id: str) -> None:
        if recipient_id in VALID_RECIPIENT_IDS:
            self.recipient_id = recipient_id

    def set_stamp(self, stamp_id: str) -> None:
        if stamp_id in VALID_STAMP_IDS:
            self.stamp_id = stamp_id

    def insert(self, segment: str) -> bool:
        if not segment or any(ord(c) < 32 and c not in "\n\t" for c in segment):
            return False

        # Filter out control characters
        clean = "".join(c for c in segment if ord(c) >= 32 or c in " ")
        if not clean:
            return False

        self._cursor = snap_grapheme_boundary(self._text, self._cursor)
        new_text = self._text[:self._cursor] + clean + self._text[self._cursor:]
        if len(grapheme_spans(new_text)) > MAX_GRAPHEMES:
            return False

        self._text = new_text
        self._cursor += len(clean)
        self._cursor = snap_grapheme_boundary(self._text, self._cursor)
        return True

    def backspace(self) -> bool:
        if not self._text or self._cursor <= 0:
            return False
        self._cursor = snap_grapheme_boundary(self._text, self._cursor)
        prev_bound = previous_grapheme_boundary(self._text, self._cursor)
        self._text = self._text[:prev_bound] + self._text[self._cursor:]
        self._cursor = prev_bound
        return True

    def delete_forward(self) -> bool:
        if not self._text or self._cursor >= len(self._text):
            return False
        self._cursor = snap_grapheme_boundary(self._text, self._cursor)
        nxt_bound = next_grapheme_boundary(self._text, self._cursor)
        self._text = self._text[:self._cursor] + self._text[nxt_bound:]
        return True

    def move_left(self) -> bool:
        if self._cursor <= 0:
            return False
        self._cursor = previous_grapheme_boundary(self._text, self._cursor)
        return True

    def move_right(self) -> bool:
        if self._cursor >= len(self._text):
            return False
        self._cursor = next_grapheme_boundary(self._text, self._cursor)
        return True

    def clear(self) -> None:
        self._text = ""
        self._cursor = 0


class PostcardLibrary:
    """Manage collection of up to 20 saved postcards."""

    def __init__(self, cards: Sequence[SavedPostcard] = ()) -> None:
        self._cards: list[SavedPostcard] = list(cards[:MAX_SAVED_CARDS])

    @property
    def cards(self) -> tuple[SavedPostcard, ...]:
        return tuple(self._cards)

    @property
    def count(self) -> int:
        return len(self._cards)

    @property
    def is_full(self) -> bool:
        return len(self._cards) >= MAX_SAVED_CARDS

    def add(self, card: SavedPostcard) -> bool:
        if self.is_full:
            return False
        if any(c.card_id == card.card_id for c in self._cards):
            return False
        self._cards.insert(0, card)  # Newest first
        return True

    def delete(self, card_id: str) -> bool:
        initial_len = len(self._cards)
        self._cards = [c for c in self._cards if c.card_id != card_id]
        return len(self._cards) < initial_len

    def get(self, card_id: str) -> SavedPostcard | None:
        for c in self._cards:
            if c.card_id == card_id:
                return c
        return None
