"""Storie della Mia Voce — durable per-profile story library.

Each saved story is a record that names the four scene ids and
stores the per-scene audio recordings as separate WAV blobs in
the per-profile Activity store. The library is bounded to the
smallest reasonable cap for a child device.

The Activity never writes global Greia reward state. Stories are
Activity-owned data; the storage key is namespaced to the Activity
id and never collides with another Activity or with the platform
history/reward stores.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Final

from greia_platform.activity_api import emit_activity_event, get_storage

from voice_content import MAX_SAVED_STORIES, SCENE_IDS


STORY_INDEX_KEY: Final = "storie_della_mia_voce.stories.v1"


@dataclass(frozen=True, slots=True)
class SavedStory:
    """One immutable story record."""

    story_id: str
    created_at: int  # unix seconds
    scene_recordings: dict[str, bytes]  # scene_id -> wav bytes
    scene_durations: dict[str, float]  # scene_id -> seconds recorded

    def __post_init__(self) -> None:
        if not self.story_id:
            raise ValueError("story_id must not be empty")
        for scene_id in self.scene_recordings:
            if scene_id not in SCENE_IDS:
                raise ValueError(f"unknown scene id: {scene_id!r}")


@dataclass(slots=True)
class StoryLibrary:
    """Manage a bounded list of saved stories for one profile."""

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
        if self.is_full:
            return False
        if any(s.story_id == story.story_id for s in self._stories):
            return False
        self._stories.insert(0, story)
        return True

    def delete(self, story_id: str) -> bool:
        before = len(self._stories)
        self._stories = [s for s in self._stories if s.story_id != story_id]
        return len(self._stories) < before

    def get(self, story_id: str) -> SavedStory | None:
        for s in self._stories:
            if s.story_id == story_id:
                return s
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
        for item in raw[:MAX_SAVED_STORIES]:
            story = cls._load_story_item(storage, item)
            if story is not None:
                library.add(story)
        return cls(library, storage, True)

    @staticmethod
    def _scene_name(story_id: str, scene_id: str) -> str:
        if not story_id or scene_id not in SCENE_IDS:
            raise ValueError("invalid voice story private filename")
        return f"stories/{story_id}_{scene_id}.wav"

    @classmethod
    def _load_story_item(cls, storage, item: object) -> SavedStory | None:
        if not isinstance(item, dict):
            return None
        story_id = item.get("story_id")
        recordings = item.get("scene_recordings", {})
        durations = item.get("scene_durations", {})
        if (
            not isinstance(story_id, str)
            or not story_id
            or not isinstance(recordings, dict)
            or not isinstance(durations, dict)
        ):
            return None

        loaded_recordings: dict[str, bytes] = {}
        loaded_durations: dict[str, float] = {}
        for scene_id, filename in recordings.items():
            if (
                not isinstance(scene_id, str)
                or scene_id not in SCENE_IDS
                or not isinstance(filename, str)
                or filename != cls._scene_name(story_id, scene_id)
            ):
                continue
            try:
                wav = storage.file_read(filename)
            except Exception:
                continue
            if not isinstance(wav, bytes) or not wav:
                continue
            loaded_recordings[scene_id] = wav
            duration = durations.get(scene_id, 0.0)
            loaded_durations[scene_id] = (
                float(duration) if isinstance(duration, (int, float)) else 0.0
            )

        if not loaded_recordings:
            return None
        try:
            created_at = int(item.get("created_at", 0))
            return SavedStory(
                story_id=story_id,
                created_at=created_at,
                scene_recordings=loaded_recordings,
                scene_durations=loaded_durations,
            )
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _index_payload(stories: tuple[SavedStory, ...]) -> list[dict]:
        result: list[dict] = []
        for story in stories:
            result.append(
                {
                    "story_id": story.story_id,
                    "created_at": story.created_at,
                    "scene_recordings": {
                        scene_id: VoiceStorage._scene_name(
                            story.story_id, scene_id
                        )
                        for scene_id in story.scene_recordings
                    },
                    "scene_durations": dict(story.scene_durations),
                }
            )
        return result

    def save_story(
        self,
        scene_recordings: dict[str, bytes],
        scene_durations: dict[str, float],
    ) -> SavedStory | None:
        if self._library.is_full:
            return None
        if not scene_recordings or self._storage is None:
            return None
        if not self._index_readable:
            raise VoiceStorageError("voice story index is unreadable")

        normalized: dict[str, bytes] = {}
        normalized_durations: dict[str, float] = {}
        for scene_id, wav in scene_recordings.items():
            if scene_id not in SCENE_IDS:
                raise ValueError(f"unknown scene id: {scene_id!r}")
            if not isinstance(wav, bytes) or not wav:
                raise ValueError("voice recording must be non-empty bytes")
            normalized[str(scene_id)] = bytes(wav)
            duration = scene_durations.get(scene_id, 0.0)
            normalized_durations[str(scene_id)] = (
                float(duration) if isinstance(duration, (int, float)) else 0.0
            )

        story_id = uuid.uuid4().hex[:12]
        written: list[str] = []
        try:
            for scene_id, wav in normalized.items():
                filename = self._scene_name(story_id, scene_id)
                self._storage.file_write_atomic(filename, wav)
                written.append(filename)

            story = SavedStory(
                story_id=story_id,
                created_at=int(time.time()),
                scene_recordings=normalized,
                scene_durations=normalized_durations,
            )
            candidate = (story, *self._library.stories)
            self._storage.kv_set(
                STORY_INDEX_KEY,
                self._index_payload(candidate),
            )
        except Exception as exc:
            for filename in written:
                try:
                    self._storage.file_delete(filename)
                except Exception:
                    pass
            raise VoiceStorageError("voice story could not be saved") from exc

        if not self._library.add(story):
            # Defensive: the capacity check above should make this impossible.
            raise VoiceStorageError("voice story library rejected committed story")
        return story

    def delete_story(self, story_id: str) -> bool:
        story = self._library.get(story_id)
        if story is None:
            return False
        if self._storage is None:
            return self._library.delete(story_id)
        if not self._index_readable:
            return False

        remaining = tuple(
            item for item in self._library.stories if item.story_id != story_id
        )
        try:
            self._storage.kv_set(
                STORY_INDEX_KEY,
                self._index_payload(remaining),
            )
        except Exception:
            return False

        deleted = self._library.delete(story_id)
        for scene_id in story.scene_recordings:
            try:
                self._storage.file_delete(
                    self._scene_name(story.story_id, scene_id)
                )
            except Exception:
                pass
        return deleted

    def private_scene_wav_name(
        self,
        story: SavedStory,
        scene_id: str,
    ) -> str:
        current = self._library.get(story.story_id)
        if current is None or scene_id not in current.scene_recordings:
            raise ValueError("voice scene is not a saved private recording")
        return self._scene_name(story.story_id, scene_id)


class VoiceEvents:
    """Typed wrapper around the platform event client."""

    @staticmethod
    def recording_started(scene_id: str) -> None:
        _emit("voice.recording_started", {"scene": scene_id})

    @staticmethod
    def recording_stopped(scene_id: str, duration: float) -> None:
        _emit(
            "voice.recording_stopped",
            {"scene": scene_id, "duration": round(duration, 2)},
        )

    @staticmethod
    def recording_replayed(scene_id: str) -> None:
        _emit("voice.recording_replayed", {"scene": scene_id})

    @staticmethod
    def story_saved(story_id: str, scene_count: int) -> None:
        _emit(
            "voice.story_saved",
            {
                "story_id": story_id,
                "scenes": scene_count,
            },
        )

    @staticmethod
    def first_story_recorded(story_id: str) -> None:
        _emit(
            "voice.first_story_recorded",
            {"story_id": story_id},
        )


def _emit(event_id: str, payload: dict) -> None:
    try:
        emit_activity_event(event_id, payload=payload)
    except Exception:
        pass


__all__ = [
    "SavedStory",
    "StoryLibrary",
    "VoiceStorage",
    "VoiceStorageError",
    "VoiceEvents",
    "STORY_INDEX_KEY",
]
