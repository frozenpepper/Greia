"""Stories of My Voice — durable per-profile story shelf, progress and events.

A saved story names its picture-story template, the card order and one WAV
recording per told card. Recordings are separate private files in the
per-profile Activity store; a single KV index lists the stories. The shelf is
bounded (``MAX_SAVED_STORIES``) and **never evicts**: a full shelf refuses the
save so the child can choose what to remove. Deleting is deliberate (see
``DeleteConfirmation``) and commits the index before removing files.

Schema (key ``storie_della_mia_voce.stories.v1``) is additive: entries written
before the Story Cards rework have no ``story`` field and load as the legacy
four-scene story, so no child recording is lost.

The Activity never writes global Greia reward state; events are facts only.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import time
import uuid
from typing import Final

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .voice_content import ALL_TEMPLATES, LEGACY_SCENES, LEGACY_STORY_ID, MAX_SAVED_STORIES, is_valid_card_id
else:
    from voice_content import ALL_TEMPLATES, LEGACY_SCENES, LEGACY_STORY_ID, MAX_SAVED_STORIES, is_valid_card_id


STORY_INDEX_KEY: Final = "storie_della_mia_voce.stories.v1"
PROGRESS_KEY: Final = "storie_della_mia_voce.progress.v1"


@dataclass(frozen=True, slots=True)
class SavedStory:
    """One immutable saved story (recordings keyed by card id)."""

    story_id: str
    created_at: int  # unix seconds
    recordings: dict[str, bytes]
    durations: dict[str, float]
    template_id: str = LEGACY_STORY_ID
    order: tuple[str, ...] = ()
    shared: bool = False

    def __post_init__(self) -> None:
        if not _safe_story_id(self.story_id):
            raise ValueError("story_id must be a short safe identifier")
        if not self.recordings:
            raise ValueError("a saved story needs at least one recording")
        for card_id, wav in self.recordings.items():
            if not is_valid_card_id(card_id):
                raise ValueError(f"invalid card id: {card_id!r}")
            if not isinstance(wav, bytes) or not wav:
                raise ValueError("recordings must be non-empty bytes")
        if not self.order:
            object.__setattr__(self, "order", _default_order(self.template_id, self.recordings))
        missing = [card for card in self.recordings if card not in self.order]
        if missing:
            object.__setattr__(self, "order", (*self.order, *missing))
        if any(not is_valid_card_id(card) for card in self.order):
            raise ValueError("invalid card id in story order")

    @property
    def total_seconds(self) -> float:
        return sum(self.durations.values())

    @property
    def cover_card(self) -> str:
        return self.order[0]


def _safe_story_id(value: object) -> bool:
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-")
    return isinstance(value, str) and 0 < len(value) <= 40 and all(c in allowed for c in value)


def _default_order(template_id: str, recordings: dict[str, bytes]) -> tuple[str, ...]:
    template = ALL_TEMPLATES.get(template_id)
    if template is LEGACY_SCENES:
        # Old free-scene stories only show the scenes the child recorded.
        return tuple(card for card in template.card_ids if card in recordings)
    if template is not None:
        return template.card_ids
    return tuple(recordings)


@dataclass(slots=True)
class StoryLibrary:
    """A bounded list of saved stories for one profile (newest first)."""

    _stories: list[SavedStory] = field(default_factory=list)

    @property
    def stories(self) -> tuple[SavedStory, ...]:
        return tuple(self._stories)

    @property
    def count(self) -> int:
        return len(self._stories)

    @property
    def is_full(self) -> bool:
        return self.count >= MAX_SAVED_STORIES

    def add(self, story: SavedStory) -> bool:
        if self.is_full or any(s.story_id == story.story_id for s in self._stories):
            return False
        self._stories.insert(0, story)
        return True

    def replace(self, story: SavedStory) -> None:
        self._stories = [story if s.story_id == story.story_id else s for s in self._stories]

    def delete(self, story_id: str) -> bool:
        before = len(self._stories)
        self._stories = [s for s in self._stories if s.story_id != story_id]
        return len(self._stories) < before

    def get(self, story_id: str) -> SavedStory | None:
        return next((s for s in self._stories if s.story_id == story_id), None)


class DeleteConfirmation:
    """Pure state for the deliberate "delete this story?" step.

    The dialog always opens with the safe choice (keep) focused, so a stray
    Space/Enter or controller south-button press never deletes. The destructive
    choice only works after a short arming delay, which also absorbs a
    double-tap that opened and then immediately confirmed the dialog. Teatrino
    uses the same behaviour so both Activities feel identical.
    """

    KEEP = "keep"
    DELETE = "delete"
    ARM_SECONDS = 0.6

    def __init__(self, target_id: str, opened_at: float) -> None:
        self.target_id = target_id
        self.opened_at = float(opened_at)
        self.focus = self.KEEP

    def move_focus(self) -> None:
        self.focus = self.DELETE if self.focus == self.KEEP else self.KEEP

    def armed(self, now: float) -> bool:
        return (float(now) - self.opened_at) >= self.ARM_SECONDS

    def resolve(self, choice: str, now: float) -> str | None:
        """Return ``keep``/``delete`` when the choice takes effect, else ``None``."""

        if choice == self.KEEP:
            return self.KEEP
        if choice == self.DELETE and self.armed(now):
            return self.DELETE
        return None


class VoiceStorageError(RuntimeError):
    """A private voice-story mutation could not be committed."""


@dataclass(frozen=True, slots=True)
class VoiceStorage:
    """Authoritative private story storage with rollback on failed commits."""

    _library: StoryLibrary
    _storage: object | None = None
    _index_readable: bool = True

    @classmethod
    def load(cls, storage=None) -> "VoiceStorage":
        if storage is None:
            try:
                storage = get_storage()
            except Exception:
                storage = None
        if storage is None:
            return cls(StoryLibrary(), None)
        try:
            raw = storage.kv_get(STORY_INDEX_KEY, [])
        except Exception:
            return cls(StoryLibrary(), storage, False)
        if not isinstance(raw, list):
            return cls(StoryLibrary(), storage, False)
        library = StoryLibrary()
        loaded = [story for story in (cls._load_story_item(storage, item) for item in raw[:MAX_SAVED_STORIES]) if story]
        # The index is newest first; ``add`` prepends, so add oldest first.
        for story in reversed(loaded):
            library.add(story)
        return cls(library, storage, True)

    # -- queries --
    @property
    def library(self) -> StoryLibrary:
        return self._library

    @property
    def stories(self) -> tuple[SavedStory, ...]:
        return self._library.stories

    @property
    def is_full(self) -> bool:
        return self._library.is_full

    @property
    def available(self) -> bool:
        return self._storage is not None and self._index_readable

    # -- file names --
    @staticmethod
    def _card_name(story_id: str, card_id: str) -> str:
        if not _safe_story_id(story_id) or not is_valid_card_id(card_id):
            raise ValueError("invalid voice story private filename")
        return f"stories/{story_id}_{card_id}.wav"

    def private_card_wav_name(self, story: SavedStory, card_id: str) -> str:
        current = self._library.get(story.story_id)
        if current is None or card_id not in current.recordings:
            raise ValueError("voice card is not a saved private recording")
        return self._card_name(story.story_id, card_id)

    # -- loading --
    @classmethod
    def _load_story_item(cls, storage, item: object) -> SavedStory | None:
        if not isinstance(item, dict):
            return None
        story_id = item.get("story_id")
        recordings = item.get("scene_recordings", {})
        durations = item.get("scene_durations", {})
        if not _safe_story_id(story_id) or not isinstance(recordings, dict) or not isinstance(durations, dict):
            return None
        template_id = item.get("story", LEGACY_STORY_ID)
        if not isinstance(template_id, str) or not is_valid_card_id(template_id):
            template_id = LEGACY_STORY_ID
        loaded: dict[str, bytes] = {}
        loaded_durations: dict[str, float] = {}
        for card_id, filename in recordings.items():
            try:
                expected = cls._card_name(story_id, card_id)
            except ValueError:
                continue
            if filename != expected:
                continue
            try:
                wav = storage.file_read(filename)
            except Exception:
                continue
            if not isinstance(wav, bytes) or not wav:
                continue
            loaded[card_id] = wav
            duration = durations.get(card_id, 0.0)
            loaded_durations[card_id] = float(duration) if isinstance(duration, (int, float)) else 0.0
        if not loaded:
            return None
        raw_order = item.get("cards")
        order: tuple[str, ...] = ()
        if isinstance(raw_order, list):
            order = tuple(card for card in raw_order if is_valid_card_id(card))
            if len(set(order)) != len(order):
                order = ()
        try:
            return SavedStory(
                story_id=story_id,
                created_at=int(item.get("created_at", 0)),
                recordings=loaded,
                durations=loaded_durations,
                template_id=template_id,
                order=order,
                shared=item.get("shared") is True,
            )
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _index_payload(stories: tuple[SavedStory, ...]) -> list[dict]:
        payload: list[dict] = []
        for story in stories:
            entry = {
                "story_id": story.story_id,
                "created_at": story.created_at,
                "scene_recordings": {
                    card_id: VoiceStorage._card_name(story.story_id, card_id) for card_id in story.recordings
                },
                "scene_durations": dict(story.durations),
                "story": story.template_id,
                "cards": list(story.order),
            }
            if story.shared:
                entry["shared"] = True
            payload.append(entry)
        return payload

    # -- mutations --
    def save_story(
        self,
        template_id: str,
        order: tuple[str, ...],
        recordings: dict[str, bytes],
        durations: dict[str, float],
    ) -> SavedStory | None:
        """Commit all recording files plus the index, or roll back.

        Returns ``None`` (nothing written) when the shelf is full or there is
        no store; raises ``VoiceStorageError`` when a commit fails.
        """

        if self._library.is_full or not recordings or self._storage is None:
            return None
        if not self._index_readable:
            raise VoiceStorageError("voice story index is unreadable")
        normalized: dict[str, bytes] = {}
        normalized_durations: dict[str, float] = {}
        for card_id, wav in recordings.items():
            if not is_valid_card_id(card_id) or card_id not in order:
                raise ValueError(f"unknown card id: {card_id!r}")
            if not isinstance(wav, bytes) or not wav:
                raise ValueError("voice recording must be non-empty bytes")
            normalized[card_id] = bytes(wav)
            duration = durations.get(card_id, 0.0)
            normalized_durations[card_id] = float(duration) if isinstance(duration, (int, float)) else 0.0
        story_id = uuid.uuid4().hex[:12]
        story = SavedStory(
            story_id=story_id,
            created_at=int(time.time()),
            recordings=normalized,
            durations=normalized_durations,
            template_id=template_id,
            order=tuple(order),
        )
        written: list[str] = []
        try:
            for card_id, wav in normalized.items():
                filename = self._card_name(story_id, card_id)
                self._storage.file_write_atomic(filename, wav)
                written.append(filename)
            self._storage.kv_set(STORY_INDEX_KEY, self._index_payload((story, *self._library.stories)))
        except Exception as exc:
            for filename in written:
                try:
                    self._storage.file_delete(filename)
                except Exception:
                    pass
            raise VoiceStorageError("voice story could not be saved") from exc
        if not self._library.add(story):
            raise VoiceStorageError("voice story library rejected committed story")
        return story

    def mark_shared(self, story_id: str) -> SavedStory | None:
        """Remember that a story's voices are in My Creations (best effort)."""

        story = self._library.get(story_id)
        if story is None or story.shared:
            return story
        updated = replace(story, shared=True)
        candidate = tuple(updated if s.story_id == story_id else s for s in self._library.stories)
        if self._storage is not None and self._index_readable:
            try:
                self._storage.kv_set(STORY_INDEX_KEY, self._index_payload(candidate))
            except Exception:
                pass  # the session still remembers it; nothing is lost
        self._library.replace(updated)
        return updated

    def delete_story(self, story_id: str) -> bool:
        story = self._library.get(story_id)
        if story is None:
            return False
        if self._storage is None:
            return self._library.delete(story_id)
        if not self._index_readable:
            return False
        remaining = tuple(item for item in self._library.stories if item.story_id != story_id)
        try:
            self._storage.kv_set(STORY_INDEX_KEY, self._index_payload(remaining))
        except Exception:
            return False
        deleted = self._library.delete(story_id)
        for card_id in story.recordings:
            try:
                self._storage.file_delete(self._card_name(story.story_id, card_id))
            except Exception:
                pass
        return deleted


class StoryProgress:
    """Which picture stories the child has finished (a star on the picker)."""

    def __init__(self, storage: object | None = None) -> None:
        self._storage = storage
        self.done: set[str] = set()

    @classmethod
    def load(cls, storage: object | None) -> "StoryProgress":
        progress = cls(storage)
        if storage is None:
            return progress
        try:
            raw = storage.kv_get(PROGRESS_KEY, {})
        except Exception:
            return progress
        if isinstance(raw, dict) and isinstance(raw.get("done"), list):
            progress.done = {item for item in raw["done"] if isinstance(item, str) and item in ALL_TEMPLATES}
        return progress

    def mark_done(self, story_id: str) -> None:
        if story_id not in ALL_TEMPLATES or story_id in self.done:
            return
        self.done.add(story_id)
        if self._storage is None:
            return
        try:
            self._storage.kv_set(PROGRESS_KEY, {"done": sorted(self.done)})
        except Exception:
            pass


class VoiceEvents:
    """Typed wrapper around the platform event client (facts only)."""

    @staticmethod
    def cards_ordered(story: str, mistakes: int) -> None:
        _emit("story.cards_ordered", {"story": story, "mistakes": int(mistakes)})

    @staticmethod
    def recording_started(card_id: str) -> None:
        _emit("voice.recording_started", {"card": card_id})

    @staticmethod
    def recording_stopped(card_id: str, duration: float) -> None:
        _emit("voice.recording_stopped", {"card": card_id, "duration": round(duration, 2)})

    @staticmethod
    def recording_replayed(card_id: str) -> None:
        _emit("voice.recording_replayed", {"card": card_id})

    @staticmethod
    def story_saved(story_id: str, card_count: int) -> None:
        _emit("voice.story_saved", {"story_id": story_id, "cards": card_count})

    @staticmethod
    def first_story_recorded(story_id: str) -> None:
        _emit("voice.first_story_recorded", {"story_id": story_id})


def _emit(event_id: str, payload: dict) -> None:
    try:
        emit_activity_event(event_id, payload=payload)
    except Exception:
        pass


__all__ = [
    "DeleteConfirmation",
    "PROGRESS_KEY",
    "STORY_INDEX_KEY",
    "SavedStory",
    "StoryLibrary",
    "StoryProgress",
    "VoiceEvents",
    "VoiceStorage",
    "VoiceStorageError",
]
