"""Greia persistence and event adapters for Posta di Leo."""

from __future__ import annotations

from typing import Protocol

from greia_platform.activity_api import emit_activity_event, get_storage
from greia_platform.typography import grapheme_spans

if __package__:
    from .postcard_content import VALID_RECIPIENT_IDS, VALID_STAMP_IDS
    from .postcard_model import MAX_GRAPHEMES, MAX_SAVED_CARDS, PostcardLibrary, SavedPostcard
else:
    from postcard_content import VALID_RECIPIENT_IDS, VALID_STAMP_IDS
    from postcard_model import MAX_GRAPHEMES, MAX_SAVED_CARDS, PostcardLibrary, SavedPostcard


STORAGE_KEY = "posta_di_leo.library.v1"


class StoragePort(Protocol):
    def load(self) -> PostcardLibrary: ...
    def save(self, library: PostcardLibrary) -> bool: ...


class EventPort(Protocol):
    def postcard_created(self, card: SavedPostcard) -> None: ...


class GreiaPostcardStorage:
    """Map postcard library onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage if storage is not None else get_storage()

    def load(self) -> PostcardLibrary:
        try:
            raw = self._storage.kv_get(STORAGE_KEY)
        except Exception:
            return PostcardLibrary()

        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            return PostcardLibrary()

        items = raw.get("cards", [])
        if not isinstance(items, list):
            return PostcardLibrary()

        parsed: list[SavedPostcard] = []
        seen_ids: set[str] = set()

        for entry in items[:MAX_SAVED_CARDS]:
            if not isinstance(entry, dict):
                continue
            card_id = entry.get("id")
            created_at = entry.get("created_at")
            recipient_id = entry.get("recipient")
            stamp_id = entry.get("stamp")
            text = entry.get("text", "")

            if (
                isinstance(card_id, str)
                and card_id
                and card_id not in seen_ids
                and isinstance(created_at, int)
                and recipient_id in VALID_RECIPIENT_IDS
                and stamp_id in VALID_STAMP_IDS
                and isinstance(text, str)
                and len(grapheme_spans(text)) <= MAX_GRAPHEMES
                and not any(ord(c) < 32 and c not in "\n\t" for c in text)
            ):
                seen_ids.add(card_id)
                parsed.append(
                    SavedPostcard(
                        card_id=card_id,
                        created_at=created_at,
                        recipient_id=recipient_id,
                        stamp_id=stamp_id,
                        text=text,
                    )
                )

        return PostcardLibrary(parsed)

    def save(self, library: PostcardLibrary) -> bool:
        payload = {
            "schema_version": 1,
            "cards": [
                {
                    "id": card.card_id,
                    "created_at": card.created_at,
                    "recipient": card.recipient_id,
                    "stamp": card.stamp_id,
                    "text": card.text,
                }
                for card in library.cards[:MAX_SAVED_CARDS]
            ],
        }
        try:
            self._storage.kv_set(STORAGE_KEY, payload)
            return True
        except Exception:
            return False


class GreiaPostcardEvents:
    """Publish postcard creation fact declared by manifest without leaking message text."""

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
