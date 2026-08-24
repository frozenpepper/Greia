"""Greia persistence and event adapters for Tre Carte Una Storia."""

from __future__ import annotations

from typing import Protocol

from greia_platform.activity_api import emit_activity_event, get_storage
from greia_platform.typography import grapheme_spans

if __package__:
    from .story_cards_content import VALID_SEED_IDS, StorySeed
    from .story_cards_model import MAX_GRAPHEMES, MAX_SAVED_STORIES, SavedStory, StoryLibrary
else:
    from story_cards_content import VALID_SEED_IDS, StorySeed
    from story_cards_model import MAX_GRAPHEMES, MAX_SAVED_STORIES, SavedStory, StoryLibrary


STORAGE_KEY = "tre_carte_una_storia.library.v1"


class StoragePort(Protocol):
    def load(self) -> StoryLibrary: ...
    def save(self, library: StoryLibrary) -> bool: ...


class EventPort(Protocol):
    def sequence_completed(self, seed: StorySeed) -> None: ...
    def story_created(self, story: SavedStory) -> None: ...


class GreiaStoryStorage:
    """Map story collection onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage if storage is not None else get_storage()

    def load(self) -> StoryLibrary:
        try:
            raw = self._storage.kv_get(STORAGE_KEY)
        except Exception:
            return StoryLibrary()

        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            return StoryLibrary()

        items = raw.get("stories", [])
        if not isinstance(items, list):
            return StoryLibrary()

        parsed: list[SavedStory] = []
        seen_ids: set[str] = set()

        for entry in items[:MAX_SAVED_STORIES]:
            if not isinstance(entry, dict):
                continue
            story_id = entry.get("id")
            created_at = entry.get("created_at")
            seed_id = entry.get("seed")
            card_ids = entry.get("cards")
            caption_mode = entry.get("mode")
            caption_text = entry.get("caption", "")

            if (
                isinstance(story_id, str)
                and story_id
                and story_id not in seen_ids
                and isinstance(created_at, int)
                and seed_id in VALID_SEED_IDS
                and isinstance(card_ids, list)
                and len(card_ids) == 3
                and all(isinstance(c, str) for c in card_ids)
                and isinstance(caption_mode, str)
                and isinstance(caption_text, str)
                and len(grapheme_spans(caption_text)) <= MAX_GRAPHEMES
                and not any(ord(c) < 32 and c not in "\n\t" for c in caption_text)
            ):
                seen_ids.add(story_id)
                parsed.append(
                    SavedStory(
                        story_id=story_id,
                        created_at=created_at,
                        seed_id=seed_id,
                        card_ids=tuple(card_ids),  # type: ignore[arg-type]
                        caption_mode=caption_mode,
                        caption_text=caption_text,
                    )
                )

        return StoryLibrary(parsed)

    def save(self, library: StoryLibrary) -> bool:
        payload = {
            "schema_version": 1,
            "stories": [
                {
                    "id": story.story_id,
                    "created_at": story.created_at,
                    "seed": story.seed_id,
                    "cards": list(story.card_ids),
                    "mode": story.caption_mode,
                    "caption": story.caption_text,
                }
                for story in library.stories[:MAX_SAVED_STORIES]
            ],
        }
        try:
            self._storage.kv_set(STORAGE_KEY, payload)
            return True
        except Exception:
            return False


class GreiaStoryEvents:
    """Publish sequence milestone and creation facts declared by manifest without leaking child text."""

    def sequence_completed(self, seed: StorySeed) -> None:
        emit_activity_event(
            "story.sequence_completed",
            {"seed": seed.seed_id},
            idempotency_key=f"tre-carte-una-storia:seq:{seed.seed_id}",
        )

    def story_created(self, story: SavedStory) -> None:
        payload = {
            "seed": story.seed_id,
            "mode": story.caption_mode,
        }
        emit_activity_event(
            "story.created",
            payload,
            idempotency_key=f"tre-carte-una-storia:{story.story_id}",
        )
