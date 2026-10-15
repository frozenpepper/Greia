"""Greia persistence and event adapters for Leo's Post.

Storage layout (profile-scoped Greia Storage, never a Linux file workflow):

* KV ``posta_di_leo.library.v1`` — the postbox index. ``schema_version`` 2
  adds the card front and stickers; version-1 indexes (text-only cards) load
  unchanged and are written forward as version 2 on the next save;
* ``postcards/<id>.txt`` — each card's message as plain UTF-8 (the source
  for the reciprocal Writing exchange);
* ``postcards/<id>.front.png`` — the child's own picture when the front came
  from My Creations;
* ``postcards/<id>.png`` — the composed picture, written only when the child
  shares the card to My Creations;
* KV ``posta_di_leo.draft.v1`` + ``postcards/draft.front.png`` — the unsent
  card, kept across Home so a half-made postcard is never lost.

Saves are commit-ordered: files first, then the index; a failed index write
rolls back the files it created, and removed cards' files are reclaimed only
after the new index commits.
"""

from __future__ import annotations

from typing import Mapping, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .postcard_content import (
        MAX_SAVED_CARDS,
        MAX_STICKERS,
        VALID_SCENE_IDS,
        VALID_STAMP_IDS,
        VALID_STICKER_IDS,
        canonical_recipient,
    )
    from .postcard_model import CardFront, PlacedSticker, PostcardDraft, PostcardLibrary, SavedPostcard, clean_message
else:
    from postcard_content import (
        MAX_SAVED_CARDS,
        MAX_STICKERS,
        VALID_SCENE_IDS,
        VALID_STAMP_IDS,
        VALID_STICKER_IDS,
        canonical_recipient,
    )
    from postcard_model import CardFront, PlacedSticker, PostcardDraft, PostcardLibrary, SavedPostcard, clean_message


STORAGE_KEY = "posta_di_leo.library.v1"
DRAFT_KEY = "posta_di_leo.draft.v1"
SCHEMA_VERSION = 2
READABLE_SCHEMAS = frozenset({1, 2})
DRAFT_PICTURE = "postcards/draft.front.png"


class StoragePort(Protocol):
    def load(self) -> PostcardLibrary: ...
    def save(self, library: PostcardLibrary, *, new_pictures: Mapping[str, bytes] | None = None) -> bool: ...
    def load_picture(self, card_id: str) -> bytes: ...
    def private_card_text_name(self, card_id: str) -> str: ...
    def private_card_png_name(self, card_id: str, payload: bytes) -> str: ...
    def save_draft(self, draft: PostcardDraft, picture: bytes | None) -> bool: ...
    def load_draft(self) -> tuple[PostcardDraft, bytes | None] | None: ...
    def clear_draft(self) -> None: ...


class EventPort(Protocol):
    def postcard_created(self, card: SavedPostcard) -> None: ...


def _parse_front(raw: object, stamp_id: str) -> CardFront | None:
    """Return the stored front, ``None`` (legacy default) or raise on garbage."""

    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("front must be an object")
    kind = raw.get("kind")
    if kind == "picture":
        return CardFront.picture()
    if kind == "scene" and raw.get("scene") in VALID_SCENE_IDS:
        return CardFront.scene(raw["scene"])
    raise ValueError("unknown front")


def _parse_stickers(raw: object) -> tuple[PlacedSticker, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError("stickers must be a list")
    stickers: list[PlacedSticker] = []
    for item in raw[:MAX_STICKERS]:
        if (
            isinstance(item, list)
            and len(item) == 3
            and item[0] in VALID_STICKER_IDS
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in item[1:])
        ):
            try:
                stickers.append(PlacedSticker(item[0], float(item[1]), float(item[2])))
            except ValueError:
                continue
    return tuple(stickers)


class GreiaPostcardStorage:
    """Map the postbox and the unsent draft onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage if storage is not None else get_storage()

    # -- postbox -------------------------------------------------------------------

    def load(self) -> PostcardLibrary:
        try:
            raw = self._storage.kv_get(STORAGE_KEY)
        except Exception:
            return PostcardLibrary()
        if not isinstance(raw, dict) or raw.get("schema_version") not in READABLE_SCHEMAS:
            return PostcardLibrary()
        items = raw.get("cards", [])
        if not isinstance(items, list):
            return PostcardLibrary()

        parsed: list[SavedPostcard] = []
        seen: set[str] = set()
        for entry in items[:MAX_SAVED_CARDS]:
            card = self._parse_card(entry, seen)
            if card is not None:
                seen.add(card.card_id)
                parsed.append(card)
        return PostcardLibrary(parsed)

    @staticmethod
    def _parse_card(entry: object, seen: set[str]) -> SavedPostcard | None:
        if not isinstance(entry, dict):
            return None
        card_id = entry.get("id")
        created_at = entry.get("created_at")
        recipient = canonical_recipient(entry.get("recipient"))
        stamp_id = entry.get("stamp")
        text = entry.get("text", "")
        if not (
            isinstance(card_id, str)
            and card_id
            and card_id not in seen
            and len(card_id) <= 80
            and isinstance(created_at, int)
            and not isinstance(created_at, bool)
            and recipient is not None
            and stamp_id in VALID_STAMP_IDS
            and clean_message(text)
        ):
            return None
        try:
            front = _parse_front(entry.get("front"), stamp_id)
            stickers = _parse_stickers(entry.get("stickers"))
            return SavedPostcard(card_id, created_at, recipient, stamp_id, text, front, stickers)
        except ValueError:
            return None

    @staticmethod
    def _text_name(card_id: str) -> str:
        return f"postcards/{_checked_id(card_id)}.txt"

    @staticmethod
    def _picture_name(card_id: str) -> str:
        return f"postcards/{_checked_id(card_id)}.front.png"

    @staticmethod
    def _share_name(card_id: str) -> str:
        return f"postcards/{_checked_id(card_id)}.png"

    def load_picture(self, card_id: str) -> bytes:
        """The child's own front picture of one saved card."""

        payload = self._storage.file_read(self._picture_name(card_id))
        if not isinstance(payload, (bytes, bytearray)) or not payload:
            raise ValueError("postcard picture is missing")
        return bytes(payload)

    def private_card_text_name(self, card_id: str) -> str:
        """Return one durable saved-card text source for trusted publication."""

        card = self.load().get(card_id)
        if card is None:
            raise ValueError("postcard is not saved")
        name = self._text_name(card.card_id)
        self._storage.file_write_atomic(name, card.text.encode("utf-8"))
        return name

    def private_card_png_name(self, card_id: str, payload: bytes) -> str:
        """Write the composed card picture for trusted publication."""

        if self.load().get(card_id) is None:
            raise ValueError("postcard is not saved")
        if not isinstance(payload, bytes) or not payload:
            raise ValueError("postcard picture is empty")
        name = self._share_name(card_id)
        self._storage.file_write_atomic(name, payload)
        return name

    def save(self, library: PostcardLibrary, *, new_pictures: Mapping[str, bytes] | None = None) -> bool:
        cards = tuple(library.cards[:MAX_SAVED_CARDS])
        pictures = dict(new_pictures or {})
        payload = {
            "schema_version": SCHEMA_VERSION,
            "cards": [
                {
                    "id": card.card_id,
                    "created_at": card.created_at,
                    "recipient": card.recipient_id,
                    "stamp": card.stamp_id,
                    "text": card.text,
                    "front": card.front.to_json(),
                    "stickers": [sticker.to_json() for sticker in card.stickers],
                }
                for card in cards
            ],
        }

        try:
            previous = self._storage.kv_get(STORAGE_KEY)
        except Exception:
            return False
        old: dict[str, bool] = {}
        if previous is None:
            pass
        elif isinstance(previous, dict) and previous.get("schema_version") in READABLE_SCHEMAS:
            items = previous.get("cards", [])
            if not isinstance(items, list):
                return False
            for item in items:
                if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"]:
                    front = item.get("front")
                    old[item["id"]] = isinstance(front, dict) and front.get("kind") == "picture"
        else:
            # Never overwrite an unreadable/unknown catalogue during mutation.
            return False

        new_ids = {card.card_id for card in cards}
        created: list[str] = []
        try:
            for card in cards:
                if card.card_id in old:
                    continue
                if card.front.is_picture:
                    picture = pictures.get(card.card_id)
                    if not isinstance(picture, bytes) or not picture:
                        raise ValueError("a new picture postcard needs its picture")
                    name = self._picture_name(card.card_id)
                    self._storage.file_write_atomic(name, picture)
                    created.append(name)
                name = self._text_name(card.card_id)
                self._storage.file_write_atomic(name, card.text.encode("utf-8"))
                created.append(name)
            self._storage.kv_set(STORAGE_KEY, payload)
        except Exception:
            for name in created:
                try:
                    self._storage.file_delete(name)
                except Exception:
                    pass
            return False

        # Index commit is authoritative. Reclaim removed-card files only after
        # it succeeds, so a failed delete/save never destroys a committed card.
        for card_id, had_picture in old.items():
            if card_id in new_ids:
                continue
            names = [self._text_name(card_id), self._share_name(card_id)]
            if had_picture:
                names.append(self._picture_name(card_id))
            for name in names:
                try:
                    self._storage.file_delete(name)
                except Exception:
                    pass
        return True

    # -- unsent draft ------------------------------------------------------------------

    def save_draft(self, draft: PostcardDraft, picture: bytes | None) -> bool:
        """Keep the unsent card (never a blank one) across Home/stop."""

        try:
            if draft.is_blank:
                self.clear_draft()
                return True
            if draft.front is not None and draft.front.is_picture:
                if not picture:
                    return False
                self._storage.file_write_atomic(DRAFT_PICTURE, picture)
            self._storage.kv_set(DRAFT_KEY, {"schema_version": 1, **draft.to_json()})
        except Exception:
            return False
        return True

    def load_draft(self) -> tuple[PostcardDraft, bytes | None] | None:
        try:
            raw = self._storage.kv_get(DRAFT_KEY)
        except Exception:
            return None
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            return None
        text = raw.get("text", "")
        if not clean_message(text):
            text = ""
        try:
            front = _parse_front(raw.get("front"), "heart")
            stickers = _parse_stickers(raw.get("stickers"))
        except ValueError:
            front, stickers = None, ()
        picture: bytes | None = None
        if front is not None and front.is_picture:
            try:
                picture = bytes(self._storage.file_read(DRAFT_PICTURE))
            except Exception:
                front = None
        draft = PostcardDraft(
            recipient_id=canonical_recipient(raw.get("recipient")),
            text=text,
            front=front,
            stickers=stickers,
        )
        return (None if draft.is_blank else (draft, picture))

    def clear_draft(self) -> None:
        try:
            if self._storage.kv_get(DRAFT_KEY) is not None:
                remove = getattr(self._storage, "kv_delete", None)
                if callable(remove):
                    remove(DRAFT_KEY)
                else:
                    self._storage.kv_set(DRAFT_KEY, None)
        except Exception:
            pass
        try:
            self._storage.file_delete(DRAFT_PICTURE)
        except Exception:
            pass


def _valid_id(card_id: str) -> bool:
    return (
        isinstance(card_id, str)
        and 0 < len(card_id) <= 80
        and all((ch.isascii() and ch.isalnum() and not ch.isupper()) or ch == "-" for ch in card_id)
    )


def _checked_id(card_id: str) -> str:
    if not _valid_id(card_id):
        raise ValueError("invalid postcard id")
    return card_id


class GreiaPostcardEvents:
    """Publish the postcard creation fact without leaking message text."""

    def postcard_created(self, card: SavedPostcard) -> None:
        payload = {
            "recipient": card.recipient_id,
            "stamp": card.stamp_id,
        }
        emit_activity_event(
            "postcard.created",
            payload,
            idempotency_key=f"posta-di-leo:{card.card_id}",
        )
