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


@dataclass(frozen=True, slots=True)
class VoiceStorage:
    """Per-profile saved stories wrapper around the platform Activity storage."""

    _library: StoryLibrary

    @classmethod
    def load(cls) -> "VoiceStorage":
        storage = get_storage()
        if storage is None:
            return cls(StoryLibrary())
        try:
            raw = storage.kv_get(STORY_INDEX_KEY, [])
        except Exception:
            return cls(StoryLibrary())
        if not isinstance(raw, list):
            return cls(StoryLibrary())
        library = StoryLibrary()
        for item in raw[:MAX_SAVED_STORIES]:
            if not isinstance(item, dict):
                continue
            sid = item.get("story_id")
            if not isinstance(sid, str) or not sid:
                continue
            recs_meta = item.get("scene_recordings", {})
            durs_meta = item.get("scene_durations", {})
            if not isinstance(recs_meta, dict):
                continue
            scene_recordings: dict[str, bytes] = {}
            scene_durations: dict[str, float] = {}
            for scene_id, fname in recs_meta.items():
                if not isinstance(scene_id, str) or scene_id not in SCENE_IDS:
                    continue
                if not isinstance(fname, str) or not fname:
                    continue
                try:
                    wav = storage.file_read(fname)
                except Exception:
                    wav = b""
                if not wav:
                    continue
                scene_recordings[scene_id] = wav
                d = durs_meta.get(scene_id, 0.0)
                scene_durations[scene_id] = float(d) if isinstance(d, (int, float)) else 0.0
            if not scene_recordings:
                continue
            try:
                created_at = int(item.get("created_at", 0))
            except Exception:
                created_at = 0
            library.add(
                SavedStory(
                    story_id=sid,
                    created_at=created_at,
                    scene_recordings=scene_recordings,
                    scene_durations=scene_durations,
                )
            )
        return cls(library)

    def save_story(self, scene_recordings: dict[str, bytes],
                   scene_durations: dict[str, float]) -> SavedStory | None:
        if self._library.is_full:
            return None
        # Validate
        if not scene_recordings:
            return None
        storage = get_storage()
        if storage is None:
            return None
        story_id = uuid.uuid4().hex[:12]
        stored_filenames: dict[str, str] = {}
        for scene_id, wav in scene_recordings.items():
            if scene_id not in SCENE_IDS:
                continue
            fname = f"stories/{story_id}_{scene_id}.wav"
            try:
                storage.file_write_atomic(fname, wav)
            except Exception:
                continue
            stored_filenames[scene_id] = fname
        if not stored_filenames:
            return None
        story = SavedStory(
            story_id=story_id,
            created_at=int(time.time()),
            scene_recordings={
                sid: scene_recordings[sid] for sid in stored_filenames
            },
            scene_durations={
                sid: scene_durations.get(sid, 0.0) for sid in stored_filenames
            },
        )
        self._library.add(story)
        # Persist index
        self._persist_index()
        return story

    def delete_story(self, story_id: str) -> bool:
        storage = get_storage()
        story = self._library.get(story_id)
        if story is None:
            return False
        if storage is not None:
            for scene_id, fname in story.scene_recordings.items():
                try:
                    storage.file_delete(fname)
                except Exception:
                    pass
        deleted = self._library.delete(story_id)
        self._persist_index()
        return deleted

    def _persist_index(self) -> None:
        storage = get_storage()
        if storage is None:
            return
        try:
            index_items: list[dict] = []
            for s in self._library.stories:
                index_items.append({
                    "story_id": s.story_id,
                    "created_at": s.created_at,
                    "scene_recordings": {
                        sid: f"stories/{s.story_id}_{sid}.wav"
                        for sid in s.scene_recordings
                    },
                    "scene_durations": dict(s.scene_durations),
                })
            storage.kv_set(STORY_INDEX_KEY, index_items)
        except Exception:
            pass


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
