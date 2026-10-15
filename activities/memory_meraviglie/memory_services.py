"""Greia persistence and event adapters for Wonder Match.

Progress lives under the original key ``memory_meraviglie.progress.v1`` so
existing saves keep loading. Payload schema 2 stores the grid level, the last
album, the collected stickers per album and a short board history. The
pre-rework payload (``theme_idx``/``grid_idx``) is migrated forward on load.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, Sequence

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .memory_content import ALBUM_IDS, MAX_LEVEL, STORAGE_KEY
    from .memory_model import HISTORY_LIMIT, BoardResult, StickerBook
else:
    from memory_content import ALBUM_IDS, MAX_LEVEL, STORAGE_KEY
    from memory_model import HISTORY_LIMIT, BoardResult, StickerBook

SCHEMA_VERSION = 2
# Pre-rework theme order: animals, sweets, vehicles, nature.
_LEGACY_THEMES = ("animals", "food", "vehicles", "nature")


@dataclass(frozen=True, slots=True)
class MemoryProgress:
    level: int = 0
    album_id: str = ALBUM_IDS[0]
    stickers: dict[str, tuple[str, ...]] = field(default_factory=dict)
    history: tuple[BoardResult, ...] = ()


class ProgressPort(Protocol):
    def load(self) -> MemoryProgress: ...
    def save(self, level: int, album_id: str, book: StickerBook, history: Sequence[BoardResult]) -> None: ...


class EventPort(Protocol):
    def pair_found(self, session_id: str, payload: dict[str, Any]) -> None: ...
    def game_completed(self, session_id: str, payload: dict[str, Any]) -> None: ...


def _int(value: object, default: int, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return max(low, min(high, value))


class GreiaMemoryProgress:
    """Map bounded Wonder Match progress onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        if storage is None:
            try:
                storage = get_storage()
            except Exception:
                storage = None
        self._storage = storage

    def load(self) -> MemoryProgress:
        if self._storage is None:
            return MemoryProgress()
        try:
            raw = self._storage.kv_get(STORAGE_KEY)
        except Exception:
            return MemoryProgress()
        if not isinstance(raw, dict):
            return MemoryProgress()
        if raw.get("schema_version") == SCHEMA_VERSION:
            return self._parse_v2(raw)
        return self._migrate_v1(raw)

    def _parse_v2(self, raw: dict) -> MemoryProgress:
        level = _int(raw.get("level"), 0, 0, MAX_LEVEL)
        album_id = raw.get("album") if raw.get("album") in ALBUM_IDS else ALBUM_IDS[0]
        stickers: dict[str, tuple[str, ...]] = {}
        stored = raw.get("stickers")
        if isinstance(stored, dict):
            for key, value in stored.items():
                if key in ALBUM_IDS and isinstance(value, list):
                    stickers[key] = tuple(item for item in value[:16] if isinstance(item, str))
        # StickerBook drops unknown pictures.
        book = StickerBook(stickers)
        stickers = {key: tuple(sorted(book.collected(key))) for key in ALBUM_IDS if book.count(key)}
        history: list[BoardResult] = []
        items = raw.get("history")
        if isinstance(items, list):
            for item in items[-HISTORY_LIMIT:]:
                if not isinstance(item, dict):
                    continue
                pairs = _int(item.get("pairs"), -1, -1, 8)
                if pairs < 1:
                    continue
                history.append(
                    BoardResult(
                        _int(item.get("level"), 0, 0, MAX_LEVEL),
                        pairs,
                        _int(item.get("misses"), 0, 0, 999),
                    )
                )
        return MemoryProgress(level, album_id, stickers, tuple(history))

    def _migrate_v1(self, raw: dict) -> MemoryProgress:
        """Pre-rework save: ``{"theme_idx", "grid_idx", "timestamp"}``."""

        grid = _int(raw.get("grid_idx"), 0, 0, 4)
        theme = _int(raw.get("theme_idx"), 0, 0, len(_LEGACY_THEMES) - 1)
        # The old optional 6x3 board maps to the top rung (4x4).
        return MemoryProgress(min(grid, MAX_LEVEL), _LEGACY_THEMES[theme])

    def save(self, level: int, album_id: str, book: StickerBook, history: Sequence[BoardResult]) -> None:
        if self._storage is None:
            return
        payload = {
            "schema_version": SCHEMA_VERSION,
            "level": max(0, min(MAX_LEVEL, int(level))),
            "album": album_id if album_id in ALBUM_IDS else ALBUM_IDS[0],
            "stickers": book.as_dict(),
            "history": [
                {"level": item.level, "pairs": item.pairs, "misses": item.misses}
                for item in tuple(history)[-HISTORY_LIMIT:]
            ],
        }
        try:
            self._storage.kv_set(STORAGE_KEY, payload)
        except Exception:
            return


class GreiaMemoryEvents:
    """Publish the milestone and completion facts declared by the manifest."""

    def pair_found(self, session_id: str, payload: dict[str, Any]) -> None:
        try:
            emit_activity_event(
                "memory.pair_found",
                payload,
                idempotency_key=f"memory-meraviglie:{session_id}:p{payload.get('pairs', 0)}",
            )
        except Exception:
            return

    def game_completed(self, session_id: str, payload: dict[str, Any]) -> None:
        try:
            emit_activity_event(
                "memory.game_completed",
                payload,
                idempotency_key=f"memory-meraviglie:{session_id}",
            )
        except Exception:
            return


__all__ = [
    "EventPort",
    "GreiaMemoryEvents",
    "GreiaMemoryProgress",
    "MemoryProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
]
