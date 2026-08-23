from __future__ import annotations

import json
import math
import os
import shutil
import tempfile
import threading
import time
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, Mapping

from .activities import ActivityManifest
from .history import HistorySummary, PlatformHistoryService
from .profiles import ProfileContext


_STATE_SCHEMA_VERSION = 1
_ALLOWED_TIERS = frozenset({"bronze", "silver", "gold", "special"})
_ALLOWED_CRITERIA = frozenset({"event_count", "best_score", "reward_balance"})
_ALLOWED_COMPARISONS = frozenset({"at_least", "at_most"})


class AchievementError(RuntimeError):
    """Achievement policy/state could not be safely interpreted."""


class AchievementPolicyError(AchievementError):
    """Platform achievement definitions are invalid."""


@dataclass(frozen=True, slots=True)
class LocalizedAchievementText:
    """Small locale map with deterministic language/base-language fallback."""

    values: tuple[tuple[str, str], ...]
    default_locale: str

    def resolve(self, locale: str | None) -> str:
        mapping = dict(self.values)
        requested = (locale or "").strip().replace("_", "-").casefold()
        if requested in mapping:
            return mapping[requested]
        base = requested.split("-", 1)[0]
        if base in mapping:
            return mapping[base]
        if self.default_locale in mapping:
            return mapping[self.default_locale]
        return next(iter(mapping.values()))


@dataclass(frozen=True, slots=True)
class AchievementCriterion:
    """One typed trusted-history predicate; multiple criteria are all-of."""

    kind: str
    threshold: float
    comparison: str = "at_least"
    activity_id: str | None = None
    event_id: str | None = None
    reward_id: str | None = None

    def is_met(self, summary: HistorySummary) -> bool:
        if self.kind == "event_count":
            assert self.activity_id is not None and self.event_id is not None
            actual = float(
                dict(summary.event_counts).get(
                    f"{self.activity_id}:{self.event_id}", 0
                )
            )
        elif self.kind == "best_score":
            assert self.activity_id is not None and self.event_id is not None
            raw = dict(summary.best_scores).get(
                f"{self.activity_id}:{self.event_id}"
            )
            if raw is None:
                return False
            actual = float(raw)
        elif self.kind == "reward_balance":
            assert self.reward_id is not None
            actual = float(dict(summary.reward_balances).get(self.reward_id, 0))
        else:  # Policy loading prevents this; keep runtime fail-closed.
            return False
        if self.comparison == "at_most":
            return actual <= self.threshold
        return actual >= self.threshold


@dataclass(frozen=True, slots=True)
class AchievementDefinition:
    """Platform-owned immutable meaning and presentation metadata for one badge."""

    achievement_id: str
    category: str
    tier: str
    icon_id: str
    secret: bool
    title: LocalizedAchievementText
    description: LocalizedAchievementText
    locked_hint: LocalizedAchievementText
    criteria: tuple[AchievementCriterion, ...]


@dataclass(frozen=True, slots=True)
class AchievementPolicy:
    schema_version: int
    default_locale: str
    achievements: tuple[AchievementDefinition, ...]

    @classmethod
    def load(
        cls,
        path: Path,
        activities: Iterable[ActivityManifest],
    ) -> "AchievementPolicy":
        try:
            with path.resolve(strict=True).open("rb") as handle:
                raw = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise AchievementPolicyError(f"invalid achievement policy {path}: {exc}") from exc
        if not isinstance(raw, dict):
            raise AchievementPolicyError("achievement policy must be a TOML table")
        schema_version = _required_int(raw, "schema_version", minimum=1, maximum=1)
        default_locale = _locale_id(raw.get("default_locale", "en"), "default_locale")
        raw_defs = raw.get("achievements", [])
        if not isinstance(raw_defs, list) or not all(isinstance(item, dict) for item in raw_defs):
            raise AchievementPolicyError("achievements must be an array of tables")

        manifests = {item.activity_id: item for item in activities}
        definitions: list[AchievementDefinition] = []
        seen: set[str] = set()
        for raw_def in raw_defs:
            assert isinstance(raw_def, dict)
            achievement_id = _bounded_id(raw_def.get("id"), "achievement id")
            if achievement_id in seen:
                raise AchievementPolicyError(f"duplicate achievement id: {achievement_id}")
            seen.add(achievement_id)
            category = _bounded_id(raw_def.get("category"), "achievement category")
            tier = str(raw_def.get("tier", "bronze")).strip().casefold()
            if tier not in _ALLOWED_TIERS:
                raise AchievementPolicyError(
                    f"achievement {achievement_id!r} has unsupported tier {tier!r}"
                )
            icon_id = _bounded_id(raw_def.get("icon_id", "yellow_star"), "achievement icon_id")
            secret = raw_def.get("secret", False)
            if not isinstance(secret, bool):
                raise AchievementPolicyError(
                    f"achievement {achievement_id!r} secret must be boolean"
                )
            title = _localized_text(raw_def.get("title"), default_locale, "title")
            description = _localized_text(
                raw_def.get("description"), default_locale, "description"
            )
            locked_hint = _localized_text(
                raw_def.get("locked_hint", raw_def.get("description")),
                default_locale,
                "locked_hint",
            )
            raw_criteria = raw_def.get("criteria", [])
            if not isinstance(raw_criteria, list) or not raw_criteria:
                raise AchievementPolicyError(
                    f"achievement {achievement_id!r} requires at least one criterion"
                )
            criteria = tuple(
                _criterion(item, manifests, achievement_id)
                for item in raw_criteria
                if isinstance(item, dict)
            )
            if len(criteria) != len(raw_criteria):
                raise AchievementPolicyError(
                    f"achievement {achievement_id!r} criteria must be tables"
                )
            definitions.append(
                AchievementDefinition(
                    achievement_id=achievement_id,
                    category=category,
                    tier=tier,
                    icon_id=icon_id,
                    secret=secret,
                    title=title,
                    description=description,
                    locked_hint=locked_hint,
                    criteria=criteria,
                )
            )
        return cls(schema_version, default_locale, tuple(definitions))

    def get(self, achievement_id: str) -> AchievementDefinition:
        for definition in self.achievements:
            if definition.achievement_id == achievement_id:
                return definition
        raise KeyError(achievement_id)


@dataclass(frozen=True, slots=True)
class AchievementRecord:
    unlocked_at: float
    announced_at: float | None = None
    seen_at: float | None = None


@dataclass(frozen=True, slots=True)
class AchievementEntry:
    definition: AchievementDefinition
    unlocked_at: float | None
    announced_at: float | None
    seen_at: float | None

    @property
    def unlocked(self) -> bool:
        return self.unlocked_at is not None

    @property
    def is_new(self) -> bool:
        return self.unlocked and self.seen_at is None

    @property
    def visible(self) -> bool:
        return self.unlocked or not self.definition.secret


@dataclass(frozen=True, slots=True)
class AchievementSnapshot:
    entries: tuple[AchievementEntry, ...]
    newly_unlocked: tuple[AchievementEntry, ...] = ()

    @property
    def unlocked_count(self) -> int:
        return sum(1 for entry in self.entries if entry.unlocked)

    @property
    def visible_entries(self) -> tuple[AchievementEntry, ...]:
        return tuple(entry for entry in self.entries if entry.visible)

    @property
    def pending_announcements(self) -> tuple[AchievementEntry, ...]:
        return tuple(
            entry
            for entry in self.entries
            if entry.unlocked and entry.announced_at is None
        )


class ProfileAchievementService:
    """Evaluate platform milestones from trusted history and persist unlock metadata.

    Activity packages never receive this service and never write achievement state.
    Achievement truth is derived from ``PlatformHistoryService`` aggregates; the
    profile-local JSON file stores only first-unlock and presentation timestamps.
    The service serializes metadata mutations because the event broker can process
    more than one request thread for the same profile.
    """

    STATE_NAME = "achievements.json"
    BACKUP_NAME = "achievements.backup.json"

    def __init__(
        self,
        policy: AchievementPolicy,
        history_service: PlatformHistoryService,
        *,
        clock=time.time,
    ) -> None:
        self.policy = policy
        self.history_service = history_service
        self._clock = clock
        self._state_lock = threading.RLock()
        self._known_ids = frozenset(
            definition.achievement_id for definition in self.policy.achievements
        )

    @classmethod
    def load(
        cls,
        path: Path,
        activities: Iterable[ActivityManifest],
        history_service: PlatformHistoryService,
    ) -> "ProfileAchievementService":
        return cls(AchievementPolicy.load(path, activities), history_service)

    def refresh(self, profile: ProfileContext) -> AchievementSnapshot:
        summary = self.history_service.open(profile).summary()
        with self._state_lock:
            state = self._read_state(profile)
            now = _timestamp(self._clock())
            changed = False
            newly_ids: list[str] = []
            for definition in self.policy.achievements:
                if definition.achievement_id in state:
                    continue
                if all(criterion.is_met(summary) for criterion in definition.criteria):
                    state[definition.achievement_id] = AchievementRecord(unlocked_at=now)
                    newly_ids.append(definition.achievement_id)
                    changed = True
            if changed:
                self._write_state(profile, state)
            entries = self._entries(state)
        newly = tuple(
            entry for entry in entries if entry.definition.achievement_id in newly_ids
        )
        return AchievementSnapshot(entries, newly)

    def snapshot(self, profile: ProfileContext) -> AchievementSnapshot:
        return self.refresh(profile)

    def mark_announced(self, profile: ProfileContext, achievement_id: str) -> None:
        with self._state_lock:
            self._update_timestamp(profile, achievement_id, announced=True)

    def mark_seen(self, profile: ProfileContext, achievement_ids: Iterable[str]) -> None:
        wanted = set(achievement_ids)
        if not wanted:
            return
        with self._state_lock:
            state = self._read_state(profile)
            now = _timestamp(self._clock())
            changed = False
            for achievement_id in wanted:
                record = state.get(achievement_id)
                if record is None or record.seen_at is not None:
                    continue
                state[achievement_id] = replace(record, seen_at=now)
                changed = True
            if changed:
                self._write_state(profile, state)

    def _update_timestamp(
        self,
        profile: ProfileContext,
        achievement_id: str,
        *,
        announced: bool,
    ) -> None:
        self.policy.get(achievement_id)
        state = self._read_state(profile)
        record = state.get(achievement_id)
        if record is None:
            return
        if announced and record.announced_at is not None:
            return
        now = _timestamp(self._clock())
        state[achievement_id] = replace(record, announced_at=now)
        self._write_state(profile, state)

    def _entries(
        self, state: Mapping[str, AchievementRecord]
    ) -> tuple[AchievementEntry, ...]:
        entries: list[AchievementEntry] = []
        for definition in self.policy.achievements:
            record = state.get(definition.achievement_id)
            entries.append(
                AchievementEntry(
                    definition=definition,
                    unlocked_at=None if record is None else record.unlocked_at,
                    announced_at=None if record is None else record.announced_at,
                    seen_at=None if record is None else record.seen_at,
                )
            )
        return tuple(entries)

    def _state_paths(self, profile: ProfileContext) -> tuple[Path, Path]:
        root = profile.progress_dir
        try:
            root.relative_to(profile.root)
        except ValueError as exc:
            raise AchievementError("achievement state escaped profile root") from exc
        root.mkdir(parents=True, exist_ok=True)
        os.chmod(root, 0o2770)
        return root / self.STATE_NAME, root / self.BACKUP_NAME

    def _read_state(self, profile: ProfileContext) -> dict[str, AchievementRecord]:
        state_path, backup_path = self._state_paths(profile)
        for path in (state_path, backup_path):
            if not path.is_file():
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                return _decode_state(raw)
            except (OSError, ValueError, TypeError, AchievementError):
                continue
        return {}

    def _valid_state_file(self, path: Path) -> bool:
        if not path.is_file():
            return False
        try:
            _decode_state(json.loads(path.read_text(encoding="utf-8")))
            return True
        except (OSError, ValueError, TypeError, AchievementError):
            return False

    def _write_state(
        self,
        profile: ProfileContext,
        state: Mapping[str, AchievementRecord],
    ) -> None:
        state_path, backup_path = self._state_paths(profile)
        payload = {
            "schema_version": _STATE_SCHEMA_VERSION,
            "unlocks": {
                achievement_id: {
                    "unlocked_at": record.unlocked_at,
                    "announced_at": record.announced_at,
                    "seen_at": record.seen_at,
                }
                for achievement_id, record in sorted(state.items())
                if achievement_id in self._known_ids
            },
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ) + "\n"

        # Preserve only a known-good primary as rollback material. A corrupt
        # primary must never overwrite a valid backup before atomic replacement.
        if self._valid_state_file(state_path):
            try:
                shutil.copy2(state_path, backup_path)
                os.chmod(backup_path, 0o660)
            except OSError:
                pass

        fd, temp_name = tempfile.mkstemp(
            prefix=".achievements-", dir=str(state_path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_name, 0o660)
            os.replace(temp_name, state_path)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise


def _decode_state(raw: object) -> dict[str, AchievementRecord]:
    if not isinstance(raw, dict) or raw.get("schema_version") != _STATE_SCHEMA_VERSION:
        raise AchievementError("unsupported achievement state schema")
    unlocks = raw.get("unlocks", {})
    if not isinstance(unlocks, dict):
        raise AchievementError("achievement unlock state must be an object")
    result: dict[str, AchievementRecord] = {}
    for achievement_id, item in unlocks.items():
        if not isinstance(achievement_id, str) or not isinstance(item, dict):
            raise AchievementError("invalid achievement unlock record")
        result[achievement_id] = AchievementRecord(
            unlocked_at=_timestamp(item.get("unlocked_at")),
            announced_at=_optional_timestamp(item.get("announced_at")),
            seen_at=_optional_timestamp(item.get("seen_at")),
        )
    return result


def _criterion(
    raw: Mapping[str, object],
    manifests: Mapping[str, ActivityManifest],
    achievement_id: str,
) -> AchievementCriterion:
    kind = str(raw.get("type", "")).strip().casefold()
    if kind not in _ALLOWED_CRITERIA:
        raise AchievementPolicyError(
            f"achievement {achievement_id!r} has unsupported criterion {kind!r}"
        )
    threshold_raw = raw.get("threshold")
    if isinstance(threshold_raw, bool) or not isinstance(threshold_raw, (int, float)):
        raise AchievementPolicyError(
            f"achievement {achievement_id!r} criterion threshold must be numeric"
        )
    threshold = float(threshold_raw)
    if not math.isfinite(threshold):
        raise AchievementPolicyError("achievement criterion threshold must be finite")
    comparison = str(raw.get("comparison", "at_least")).strip().casefold()
    if comparison not in _ALLOWED_COMPARISONS:
        raise AchievementPolicyError(
            f"achievement {achievement_id!r} has invalid criterion comparison"
        )

    if kind in {"event_count", "best_score"}:
        activity_id = _bounded_id(raw.get("activity_id"), "criterion activity_id")
        event_id = _bounded_id(raw.get("event_id"), "criterion event_id")
        manifest = manifests.get(activity_id)
        if manifest is None:
            raise AchievementPolicyError(
                f"achievement {achievement_id!r} references unknown Activity {activity_id!r}"
            )
        event = next((item for item in manifest.events if item.event_id == event_id), None)
        if event is None:
            raise AchievementPolicyError(
                f"achievement {achievement_id!r} references undeclared event {event_id!r}"
            )
        if kind == "event_count" and (threshold < 1 or not threshold.is_integer()):
            raise AchievementPolicyError("event_count threshold must be a positive integer")
        if kind == "best_score" and event.kind != "score":
            raise AchievementPolicyError(
                f"achievement {achievement_id!r} best_score criterion requires a score event"
            )
        return AchievementCriterion(
            kind=kind,
            threshold=threshold,
            comparison=comparison,
            activity_id=activity_id,
            event_id=event_id,
        )

    reward_id = _bounded_id(raw.get("reward_id"), "criterion reward_id")
    return AchievementCriterion(
        kind=kind,
        threshold=threshold,
        comparison=comparison,
        reward_id=reward_id,
    )


def _localized_text(
    raw: object,
    default_locale: str,
    label: str,
) -> LocalizedAchievementText:
    if not isinstance(raw, dict) or not raw:
        raise AchievementPolicyError(f"achievement {label} must be a locale table")
    values: list[tuple[str, str]] = []
    for locale, text in raw.items():
        locale_id = _locale_id(locale, f"{label} locale")
        if not isinstance(text, str) or not text.strip():
            raise AchievementPolicyError(f"achievement {label} text must be non-empty")
        values.append((locale_id, text.strip()))
    if default_locale not in dict(values):
        raise AchievementPolicyError(
            f"achievement {label} must include default locale {default_locale!r}"
        )
    return LocalizedAchievementText(tuple(values), default_locale)


def _locale_id(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise AchievementPolicyError(f"{label} must be text")
    normalized = value.strip().replace("_", "-").casefold()
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-")
    if not normalized or any(char not in allowed for char in normalized):
        raise AchievementPolicyError(f"{label} is invalid")
    return normalized


def _bounded_id(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise AchievementPolicyError(f"{label} must be text")
    normalized = value.strip().casefold()
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    if (
        not normalized
        or len(normalized) > 160
        or not normalized[0].isalnum()
        or not normalized[-1].isalnum()
        or any(char not in allowed for char in normalized)
    ):
        raise AchievementPolicyError(f"{label} must be a bounded lower-case identifier")
    return normalized


def _required_int(
    raw: Mapping[str, object], key: str, *, minimum: int, maximum: int
) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise AchievementPolicyError(f"{key} must be an integer")
    if not minimum <= value <= maximum:
        raise AchievementPolicyError(f"{key} is outside its allowed range")
    return value


def _timestamp(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AchievementError("achievement timestamp must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise AchievementError("achievement timestamp must be finite and non-negative")
    return result


def _optional_timestamp(value: object) -> float | None:
    return None if value is None else _timestamp(value)


__all__ = [
    "AchievementCriterion",
    "AchievementDefinition",
    "AchievementEntry",
    "AchievementError",
    "AchievementPolicy",
    "AchievementPolicyError",
    "AchievementRecord",
    "AchievementSnapshot",
    "LocalizedAchievementText",
    "ProfileAchievementService",
]
