"""Greia persistence and event adapters for L'Alfabeto di Leo.

Progress stays under the original storage key. Version 1 saves (from the old
explore/guess game) held only ``discovered_letters`` and ``rounds_completed``;
they load unchanged and are carried forward, so no child data is lost. Version
2 adds the next teaching group per lesson language and how often each letter
has been traced (bounded to the alphabet).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Mapping, Protocol

from greia_platform.activity_api import emit_activity_event, get_storage

STORAGE_KEY: Final[str] = "alfabeto_leo.progress.v1"
SCHEMA_VERSION: Final[int] = 2
MAX_TRACE_COUNT: Final[int] = 999
MAX_GROUP: Final[int] = 64
_LANGUAGES: Final = ("it", "en", "es", "fr")


def _letter_key(value: object) -> str | None:
    if isinstance(value, str) and len(value) == 1 and value.isalpha() and value.isupper():
        return value
    return None


@dataclass
class AlfabetoProgress:
    """Bounded, profile-scoped garden progress (all fields JSON-safe)."""

    discovered_letters: set[str] = field(default_factory=set)
    rounds_completed: int = 0
    groups: dict[str, int] = field(default_factory=dict)
    traced: dict[str, int] = field(default_factory=dict)

    def group_for(self, language: str) -> int:
        return self.groups.get(language, 0)

    def record_trace(self, char: str) -> bool:
        """Count one traced letter; True the first time this letter is learned."""

        first = self.traced.get(char, 0) == 0
        self.traced[char] = min(MAX_TRACE_COUNT, self.traced.get(char, 0) + 1)
        self.discovered_letters.add(char)
        return first

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "discovered_letters": sorted(self.discovered_letters),
            "rounds_completed": max(0, int(self.rounds_completed)),
            "groups": {lang: int(group) for lang, group in sorted(self.groups.items())},
            "traced": {char: int(count) for char, count in sorted(self.traced.items())},
        }

    @classmethod
    def from_payload(cls, raw: object) -> "AlfabetoProgress":
        """Parse v1 or v2 payloads defensively; malformed parts are dropped."""

        if not isinstance(raw, Mapping):
            return cls()
        letters = raw.get("discovered_letters", [])
        discovered = {key for key in (_letter_key(x) for x in letters) if key} if isinstance(letters, list) else set()
        rounds = raw.get("rounds_completed", 0)
        rounds = rounds if isinstance(rounds, int) and not isinstance(rounds, bool) and rounds >= 0 else 0
        groups: dict[str, int] = {}
        raw_groups = raw.get("groups", {})
        if isinstance(raw_groups, Mapping):
            for lang, value in raw_groups.items():
                if lang in _LANGUAGES and isinstance(value, int) and not isinstance(value, bool):
                    groups[lang] = max(0, min(MAX_GROUP, value))
        traced: dict[str, int] = {}
        raw_traced = raw.get("traced", {})
        if isinstance(raw_traced, Mapping):
            for char, value in list(raw_traced.items())[:40]:
                key = _letter_key(char)
                if key and isinstance(value, int) and not isinstance(value, bool) and value > 0:
                    traced[key] = min(MAX_TRACE_COUNT, value)
        return cls(discovered, min(rounds, 1_000_000), groups, traced)


class ProgressPort(Protocol):
    def load(self) -> AlfabetoProgress: ...
    def save(self, progress: AlfabetoProgress) -> None: ...


class EventPort(Protocol):
    def letter_learned(self, session_id: str, char: str) -> None: ...
    def garden_completed(self, session_id: str, payload: dict[str, int]) -> None: ...
    def alphabet_completed(self, session_id: str, letters: int) -> None: ...


class GreiaAlfabetoProgress:
    """Map garden progress onto profile-scoped Greia Storage."""

    def __init__(self, storage=None) -> None:
        self._storage = storage

    def _store(self):
        return self._storage if self._storage is not None else get_storage()

    def load(self) -> AlfabetoProgress:
        try:
            raw = self._store().kv_get(STORAGE_KEY, {})
        except Exception:
            return AlfabetoProgress()
        return AlfabetoProgress.from_payload(raw)

    def save(self, progress: AlfabetoProgress) -> None:
        try:
            self._store().kv_set(STORAGE_KEY, progress.to_payload())
        except Exception:
            return


class GreiaAlfabetoEvents:
    """Publish the milestone and completion facts declared by the manifest."""

    def letter_learned(self, session_id: str, char: str) -> None:
        emit_activity_event(
            "letter.discovered",
            {"letter": char},
            idempotency_key=f"alfabeto-leo:{session_id}:{char}",
        )

    def garden_completed(self, session_id: str, payload: dict[str, int]) -> None:
        emit_activity_event(
            "alphabet.garden_completed",
            payload,
            idempotency_key=f"alfabeto-leo:{session_id}",
        )

    def alphabet_completed(self, session_id: str, letters: int) -> None:
        emit_activity_event(
            "alphabet.parade_completed",
            {"letters": letters},
            idempotency_key=f"alfabeto-leo:{session_id}:alphabet",
        )


__all__ = [
    "AlfabetoProgress",
    "EventPort",
    "GreiaAlfabetoEvents",
    "GreiaAlfabetoProgress",
    "ProgressPort",
    "SCHEMA_VERSION",
    "STORAGE_KEY",
]
