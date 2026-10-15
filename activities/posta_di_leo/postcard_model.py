"""Domain model for Leo's Post: postcard draft, saved cards and the postbox.

Pure rules, no pygame: a draft is a friend + a card front (shared scene or a
picture from My Creations) + up to eight stickers + an optional short message
edited grapheme-safely (emoji/accents are never split). Saved postcards are
immutable records; the postbox is bounded and never evicts old cards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Sequence

from greia_platform.typography import (
    grapheme_spans,
    next_grapheme_boundary,
    previous_grapheme_boundary,
    snap_grapheme_boundary,
    truncate_grapheme_safe,
)

if __package__:
    from .postcard_content import (
        LEGACY_STAMP_SCENES,
        MAX_GRAPHEMES,
        MAX_SAVED_CARDS,
        MAX_STICKERS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STICKER_SPOTS,
        VALID_RECIPIENT_IDS,
        VALID_SCENE_IDS,
        VALID_STAMP_IDS,
        VALID_STICKER_IDS,
        friend,
    )
else:
    from postcard_content import (
        LEGACY_STAMP_SCENES,
        MAX_GRAPHEMES,
        MAX_SAVED_CARDS,
        MAX_STICKERS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        STICKER_SPOTS,
        VALID_RECIPIENT_IDS,
        VALID_SCENE_IDS,
        VALID_STAMP_IDS,
        VALID_STICKER_IDS,
        friend,
    )

__all__ = [
    "MAX_GRAPHEMES",
    "MAX_SAVED_CARDS",
    "REFERENCE_HEIGHT",
    "REFERENCE_WIDTH",
    "CardFront",
    "PlacedSticker",
    "PostcardDraft",
    "PostcardLibrary",
    "SavedPostcard",
    "clean_message",
]

FRONT_SCENE: Final = "scene"
FRONT_PICTURE: Final = "picture"


def clean_message(text: str) -> bool:
    """True when ``text`` is a storable message (bounded, no control bytes)."""

    return (
        isinstance(text, str)
        and len(grapheme_spans(text)) <= MAX_GRAPHEMES
        and not any(ord(c) < 32 and c not in "\n\t" for c in text)
    )


@dataclass(frozen=True, slots=True)
class CardFront:
    """What the front of a postcard shows: a shared scene or the child's picture."""

    kind: str
    scene_id: str | None = None

    def __post_init__(self) -> None:
        if self.kind == FRONT_SCENE:
            if self.scene_id not in VALID_SCENE_IDS:
                raise ValueError(f"unknown scene_id: {self.scene_id!r}")
        elif self.kind == FRONT_PICTURE:
            if self.scene_id is not None:
                raise ValueError("a picture front has no scene")
        else:
            raise ValueError(f"unknown front kind: {self.kind!r}")

    @classmethod
    def scene(cls, scene_id: str) -> "CardFront":
        return cls(FRONT_SCENE, scene_id)

    @classmethod
    def picture(cls) -> "CardFront":
        return cls(FRONT_PICTURE)

    @property
    def is_picture(self) -> bool:
        return self.kind == FRONT_PICTURE

    def to_json(self) -> dict[str, str]:
        return {"kind": self.kind, "scene": self.scene_id} if self.scene_id else {"kind": self.kind}


@dataclass(frozen=True, slots=True)
class PlacedSticker:
    """One sticker on a card front, centred at normalised ``(x, y)``."""

    sticker_id: str
    x: float
    y: float

    def __post_init__(self) -> None:
        if self.sticker_id not in VALID_STICKER_IDS:
            raise ValueError(f"unknown sticker_id: {self.sticker_id!r}")
        for value in (self.x, self.y):
            if not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
                raise ValueError("sticker position must be normalised to 0..1")

    def moved(self, x: float, y: float) -> "PlacedSticker":
        return PlacedSticker(self.sticker_id, _unit(x), _unit(y))

    def to_json(self) -> list:
        return [self.sticker_id, round(float(self.x), 3), round(float(self.y), 3)]


def _unit(value: float) -> float:
    return round(min(1.0, max(0.0, float(value))), 3)


@dataclass(frozen=True, slots=True)
class SavedPostcard:
    """One immutable sent postcard.

    The first five fields keep the version-1 record shape. A version-1 card
    (no picture) gets the scene that matches its stamp, so it still has a
    front; its message text is never altered.
    """

    card_id: str
    created_at: int
    recipient_id: str
    stamp_id: str
    text: str
    front: CardFront | None = None
    stickers: tuple[PlacedSticker, ...] = field(default=())

    def __post_init__(self) -> None:
        if not self.card_id:
            raise ValueError("card_id must not be empty")
        if self.recipient_id not in VALID_RECIPIENT_IDS:
            raise ValueError(f"unknown recipient_id: {self.recipient_id!r}")
        if self.stamp_id not in VALID_STAMP_IDS:
            raise ValueError(f"unknown stamp_id: {self.stamp_id!r}")
        if len(grapheme_spans(self.text)) > MAX_GRAPHEMES:
            raise ValueError(f"postcard text exceeds {MAX_GRAPHEMES} graphemes")
        if len(self.stickers) > MAX_STICKERS:
            raise ValueError(f"postcard has more than {MAX_STICKERS} stickers")
        if self.front is None:
            object.__setattr__(self, "front", CardFront.scene(LEGACY_STAMP_SCENES[self.stamp_id]))
        object.__setattr__(self, "stickers", tuple(self.stickers))


class PostcardDraft:
    """The postcard being made: friend, front, stickers and a short message.

    Text editing is grapheme-safe (an emoji or accented cluster is inserted,
    deleted and stepped over as one unit) and bounded to 80 graphemes. The
    draft is *ready to send* once it has a friend and a front; stickers and
    the message are optional so pre-readers can send a picture card.
    """

    def __init__(
        self,
        *,
        recipient_id: str | None = None,
        stamp_id: str | None = None,
        text: str = "",
        front: CardFront | None = None,
        stickers: Sequence[PlacedSticker] = (),
    ) -> None:
        self.recipient_id: str | None = recipient_id if recipient_id in VALID_RECIPIENT_IDS else None
        self._stamp_id = stamp_id if stamp_id in VALID_STAMP_IDS else None
        self.front: CardFront | None = front
        self._stickers: list[PlacedSticker] = list(stickers[:MAX_STICKERS])
        self._text = text if clean_message(text) else ""
        self._cursor = len(self._text)
        self.revision = 0

    # -- friend / stamp / front -----------------------------------------------

    @property
    def stamp_id(self) -> str:
        """The friend's own stamp (an explicit legacy stamp wins)."""

        if self._stamp_id is not None:
            return self._stamp_id
        if self.recipient_id is not None:
            return friend(self.recipient_id).stamp_id
        return "heart"

    def set_recipient(self, recipient_id: str) -> bool:
        if recipient_id not in VALID_RECIPIENT_IDS or recipient_id == self.recipient_id:
            return False
        self.recipient_id = recipient_id
        self._stamp_id = None
        self._touch()
        return True

    def set_stamp(self, stamp_id: str) -> None:
        if stamp_id in VALID_STAMP_IDS:
            self._stamp_id = stamp_id
            self._touch()

    def set_front(self, front: CardFront) -> bool:
        if front == self.front:
            return False
        self.front = front
        self._touch()
        return True

    @property
    def ready(self) -> bool:
        """A friend and a front are chosen: the card can be sent."""

        return self.recipient_id is not None and self.front is not None

    @property
    def is_blank(self) -> bool:
        return self.recipient_id is None and self.front is None and not self._stickers and not self._text

    # -- stickers ---------------------------------------------------------------

    @property
    def stickers(self) -> tuple[PlacedSticker, ...]:
        return tuple(self._stickers)

    @property
    def stickers_full(self) -> bool:
        return len(self._stickers) >= MAX_STICKERS

    def add_sticker(self, sticker_id: str) -> int | None:
        """Place a sticker on the first free spot; return its index."""

        if sticker_id not in VALID_STICKER_IDS or self.stickers_full:
            return None
        x, y = self._free_spot()
        self._stickers.append(PlacedSticker(sticker_id, x, y))
        self._touch()
        return len(self._stickers) - 1

    def move_sticker(self, index: int, x: float, y: float) -> bool:
        if not 0 <= index < len(self._stickers):
            return False
        self._stickers[index] = self._stickers[index].moved(x, y)
        self._touch()
        return True

    def remove_sticker(self, index: int) -> bool:
        if not 0 <= index < len(self._stickers):
            return False
        del self._stickers[index]
        self._touch()
        return True

    def pop_sticker(self) -> bool:
        return self.remove_sticker(len(self._stickers) - 1)

    def _free_spot(self) -> tuple[float, float]:
        taken = [(s.x, s.y) for s in self._stickers]
        for spot in STICKER_SPOTS:
            if all((spot[0] - x) ** 2 + (spot[1] - y) ** 2 > 0.02 for x, y in taken):
                return spot
        # Every spot is used: offset the first spot by the sticker count.
        nudge = 0.04 * (len(self._stickers) % 5)
        return (_unit(0.3 + nudge), _unit(0.5 + nudge))

    # -- message ---------------------------------------------------------------

    @property
    def text(self) -> str:
        return self._text

    @property
    def cursor(self) -> int:
        return self._cursor

    @property
    def grapheme_count(self) -> int:
        return len(grapheme_spans(self._text))

    def insert(self, segment: str) -> bool:
        if not segment or any(ord(c) < 32 and c not in "\n\t" for c in segment):
            return False
        clean = "".join(c for c in segment if ord(c) >= 32 or c in " ")
        if not clean:
            return False
        self._cursor = snap_grapheme_boundary(self._text, self._cursor)
        new_text = self._text[: self._cursor] + clean + self._text[self._cursor :]
        if len(grapheme_spans(new_text)) > MAX_GRAPHEMES:
            return False
        self._text = new_text
        self._cursor = snap_grapheme_boundary(self._text, self._cursor + len(clean))
        self._touch()
        return True

    def replace_text(self, text: str) -> bool:
        """Replace the message with a safe postcard-length plain-text snapshot."""

        if not isinstance(text, str):
            raise TypeError("postcard text must be a string")
        # Postcards are a compact single-message surface. Imported document
        # paragraph/tab structure becomes ordinary spaces; control bytes never
        # enter the draft.
        compact = " ".join(text.replace("\x00", "").split())
        normalized = truncate_grapheme_safe(compact, MAX_GRAPHEMES)
        changed = normalized != self._text
        self._text = normalized
        self._cursor = len(normalized)
        if changed:
            self._touch()
        return changed

    def backspace(self) -> bool:
        if not self._text or self._cursor <= 0:
            return False
        self._cursor = snap_grapheme_boundary(self._text, self._cursor)
        previous = previous_grapheme_boundary(self._text, self._cursor)
        self._text = self._text[:previous] + self._text[self._cursor :]
        self._cursor = previous
        self._touch()
        return True

    def delete_forward(self) -> bool:
        if not self._text or self._cursor >= len(self._text):
            return False
        self._cursor = snap_grapheme_boundary(self._text, self._cursor)
        following = next_grapheme_boundary(self._text, self._cursor)
        self._text = self._text[: self._cursor] + self._text[following:]
        self._touch()
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

    def move_home(self) -> None:
        self._cursor = 0

    def move_end(self) -> None:
        self._cursor = len(self._text)

    def clear(self) -> None:
        """Forget the message only (friend, front and stickers stay)."""

        self._text = ""
        self._cursor = 0
        self._touch()

    def reset(self) -> None:
        """Start a brand-new postcard."""

        self.recipient_id = None
        self._stamp_id = None
        self.front = None
        self._stickers.clear()
        self._text = ""
        self._cursor = 0
        self._touch()

    def _touch(self) -> None:
        self.revision += 1

    # -- persistence -------------------------------------------------------------

    def to_json(self) -> dict:
        return {
            "recipient": self.recipient_id,
            "front": self.front.to_json() if self.front is not None else None,
            "stickers": [s.to_json() for s in self._stickers],
            "text": self._text,
        }


class PostcardLibrary:
    """The postbox: up to 20 sent postcards, newest first, never evicting."""

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
        if self.is_full or any(c.card_id == card.card_id for c in self._cards):
            return False
        self._cards.insert(0, card)
        return True

    def delete(self, card_id: str) -> bool:
        before = len(self._cards)
        self._cards = [c for c in self._cards if c.card_id != card_id]
        return len(self._cards) < before

    def get(self, card_id: str) -> SavedPostcard | None:
        for card in self._cards:
            if card.card_id == card_id:
                return card
        return None

    def index_of(self, card_id: str) -> int | None:
        for index, card in enumerate(self._cards):
            if card.card_id == card_id:
                return index
        return None
