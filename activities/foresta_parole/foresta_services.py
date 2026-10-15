"""Greia persistence and event adapters for The Word Forest.

Progress stays under the original storage key. Earlier saves held only
``score``, ``stars`` and ``words_completed`` (sometimes ``vocab_idx`` /
``matches_current``); those counters load unchanged and are carried forward,
so no child data is lost. Schema 3 adds the stage reached per lesson language
and how often each letter was caught (bounded to single capital letters).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Mapping, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

if __package__:
    from .foresta_content import STAGES, STORAGE_KEY
else:
    from foresta_content import STAGES, STORAGE_KEY  # type: ignore[no-redef]

SCHEMA_VERSION: Final[int] = 3
MAX_COUNTER: Final[int] = 1_000_000
MAX_LETTER_COUNT: Final[int] = 9_999
_LANGUAGES: Final = ("it", "en", "es", "fr")


def _count(value: object, limit: int = MAX_COUNTER) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, min(limit, value))


def _letter(value: object) -> str | None:
    if isinstance(value, str) and len(value) == 1 and value.isalpha() and value.isupper():
        return value
    return None


@dataclass
class ForestProgress:
    """Bounded, profile-scoped Word Forest progress (all fields JSON-safe)."""

    score: int = 0
    stars: int = 0
    words_completed: int = 0
    rounds_completed: int = 0
    stages: dict[str, int] = field(default_factory=dict)
    caught: dict[str, dict[str, int]] = field(default_factory=dict)

    def stage_for(self, language: str) -> int:
        return self.stages.get(language, 1)

    def caught_for(self, language: str) -> dict[str, int]:
        return self.caught.setdefault(language, {})

    def record_catch(self, language: str, letter: str) -> None:
        letters = self.caught_for(language)
        letters[letter] = min(MAX_LETTER_COUNT, letters.get(letter, 0) + 1)
        self.words_completed = min(MAX_COUNTER, self.words_completed + 1)
        self.stars = min(MAX_COUNTER, self.stars + 1)
        self.score = min(MAX_COUNTER, self.score + 10)

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "score": int(self.score),
            "stars": int(self.stars),
            "words_completed": int(self.words_completed),
            "rounds_completed": int(self.rounds_completed),
            "stages": {lang: int(stage) for lang, stage in sorted(self.stages.items())},
            "caught": {
                lang: {char: int(n) for char, n in sorted(letters.items())}
                for lang, letters in sorted(self.caught.items())
            },
        }

    @classmethod
    def from_payload(cls, raw: object) -> "ForestProgress":
        """Parse v2 (legacy counters) or v3 payloads; malformed parts are dropped."""

        if not isinstance(raw, Mapping):
            return cls()
        stages: dict[str, int] = {}
        raw_stages = raw.get("stages", {})
        if isinstance(raw_stages, Mapping):
            for lang, value in raw_stages.items():
                if lang in _LANGUAGES and isinstance(value, int) and not isinstance(value, bool):
                    stages[lang] = max(1, min(len(STAGES), value))
        caught: dict[str, dict[str, int]] = {}
        raw_caught = raw.get("caught", {})
        if isinstance(raw_caught, Mapping):
            for lang, letters in raw_caught.items():
                if lang not in _LANGUAGES or not isinstance(letters, Mapping):
                    continue
                parsed = {}
                for char, value in list(letters.items())[:40]:
                    key = _letter(char)
                    count = _count(value, MAX_LETTER_COUNT)
                    if key and count:
                        parsed[key] = count
                caught[lang] = parsed
        return cls(
            score=_count(raw.get("score", 0)),
            stars=_count(raw.get("stars", 0)),
            words_completed=_count(raw.get("words_completed", 0)),
            rounds_completed=_count(raw.get("rounds_completed", 0)),
            stages=stages,
            caught=caught,
        )


class ProgressPort(Protocol):
    def load(self) -> ForestProgress: ...
    def save(self, progress: ForestProgress) -> None: ...


class EventPort(Protocol):
    def letter_caught(self, session_id: str, index: int, letter: str, word: str) -> None: ...
    def round_completed(self, session_id: str, payload: dict[str, int]) -> None: ...


class GreiaForestProgress:
    """Map Word Forest progress onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage

    def _store(self):
        return self._storage if self._storage is not None else get_storage()

    def load(self) -> ForestProgress:
        try:
            raw = self._store().kv_get(STORAGE_KEY, {})
        except Exception:
            return ForestProgress()
        return ForestProgress.from_payload(raw)

    def save(self, progress: ForestProgress) -> None:
        try:
            self._store().kv_set(STORAGE_KEY, progress.to_payload())
        except Exception:
            return


class GreiaForestEvents:
    """Publish the milestone and completion facts declared by the manifest."""

    def letter_caught(self, session_id: str, index: int, letter: str, word: str) -> None:
        try:
            emit_activity_event(
                "letter.matched",
                {"letter": letter, "word": word},
                idempotency_key=f"foresta-parole:{session_id}:{index}",
            )
        except Exception:
            return

    def round_completed(self, session_id: str, payload: dict[str, int]) -> None:
        try:
            emit_activity_event(
                "forest.round_completed",
                payload,
                idempotency_key=f"foresta-parole:{session_id}",
            )
        except Exception:
            return


__all__ = [
    "EventPort",
    "ForestProgress",
    "GreiaForestEvents",
    "GreiaForestProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
]
