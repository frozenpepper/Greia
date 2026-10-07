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
    def private_card_text_name(self, card_id: str) -> str: ...


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

    @staticmethod
    def _text_name(card_id: str) -> str:
        if (
            not isinstance(card_id, str)
            or not card_id
            or len(card_id) > 80
            or not all(ch.isalnum() or ch == "-" for ch in card_id)
        ):
            raise ValueError("invalid postcard id")
        return f"postcards/{card_id}.txt"

    def private_card_text_name(self, card_id: str) -> str:
        """Return one durable saved-card text source for trusted publication."""
        card = self.load().get(card_id)
        if card is None:
            raise ValueError("postcard is not saved")
        name = self._text_name(card.card_id)
        self._storage.file_write_atomic(name, card.text.encode("utf-8"))
        return name

    def save(self, library: PostcardLibrary) -> bool:
        cards = tuple(library.cards[:MAX_SAVED_CARDS])
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
                for card in cards
            ],
        }

        try:
            previous = self._storage.kv_get(STORAGE_KEY)
        except Exception:
            return False
        old_ids: set[str] = set()
        if previous is None:
            pass
        elif isinstance(previous, dict) and previous.get("schema_version") == 1:
            items = previous.get("cards", [])
            if not isinstance(items, list):
                return False
            for item in items:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    old_ids.add(item["id"])
        else:
            # Never overwrite an unreadable/unknown catalogue during mutation.
            return False

        new_ids = {card.card_id for card in cards}
        created_names: list[str] = []
        try:
            for card in cards:
                name = self._text_name(card.card_id)
                self._storage.file_write_atomic(name, card.text.encode("utf-8"))
                if card.card_id not in old_ids:
                    created_names.append(name)
            self._storage.kv_set(STORAGE_KEY, payload)
        except Exception:
            for name in created_names:
                try:
                    self._storage.file_delete(name)
                except Exception:
                    pass
            return False

        # Index commit is authoritative. Reclaim removed-card source files only
        # after it succeeds, so a failed delete/save never destroys the last
        # committed postcard.
        for card_id in old_ids - new_ids:
            try:
                self._storage.file_delete(self._text_name(card_id))
            except Exception:
                pass
        return True


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
