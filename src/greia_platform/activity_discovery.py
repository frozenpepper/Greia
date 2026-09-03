from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence

from .activities import ActivityManifest


class ActivityDiscoveryError(ValueError):
    """Stored or requested Activity discovery policy is invalid."""


class ChallengePreference(str, Enum):
    AUTOMATIC = "automatic"
    EASIER = "easier"
    STANDARD = "standard"
    HARDER = "harder"


class ActivityVisibilityMode(str, Enum):
    SHOW_ALL = "show_all"
    AGE_AND_EASIER = "age_and_easier"
    RECOMMENDED_ONLY = "recommended_only"
    CUSTOM = "custom"

    # Compatibility input only. ActivityDiscoveryPolicy normalizes this old
    # persisted/API value immediately so all new writes use AGE_AND_EASIER.
    HIDE_TOO_SIMPLE = "hide_too_simple"


class ActivityVisibilityOverride(str, Enum):
    ALWAYS_SHOW = "always_show"
    ALWAYS_HIDE = "always_hide"


@dataclass(frozen=True, slots=True)
class ActivityDiscoveryPolicy:
    """Parent-owned visibility policy plus platform-owned adaptive UI state.

    ``difficulty_min`` and ``difficulty_max`` are optional inclusive bounds on
    Activities the child can discover. Fixed-difficulty Activities are compared
    directly; adaptive Activities are visible when their declared achievable
    range overlaps the requested range. Explicit per-Activity overrides always
    take precedence over age and difficulty automation.

    ``overrides`` is stored as an ordered tuple rather than a mutable mapping so
    one policy value can be compared, cached and passed across presentation
    boundaries safely. ``subdivided_collections`` is not Parent intent: it is a
    bounded platform-owned hysteresis memory used to keep child navigation from
    changing shape after one small catalogue fluctuation.
    """

    visibility_mode: ActivityVisibilityMode = ActivityVisibilityMode.SHOW_ALL
    difficulty_min: int | None = None
    difficulty_max: int | None = None
    overrides: tuple[tuple[str, ActivityVisibilityOverride], ...] = ()
    subdivided_collections: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.visibility_mode is ActivityVisibilityMode.HIDE_TOO_SIMPLE:
            object.__setattr__(
                self,
                "visibility_mode",
                ActivityVisibilityMode.AGE_AND_EASIER,
            )
        _validate_difficulty_range(self.difficulty_min, self.difficulty_max)

    def override_for(self, activity_id: str) -> ActivityVisibilityOverride | None:
        for candidate, value in self.overrides:
            if candidate == activity_id:
                return value
        return None

    def with_override(
        self,
        activity_id: str,
        value: ActivityVisibilityOverride | None,
    ) -> "ActivityDiscoveryPolicy":
        _validate_activity_id(activity_id)
        mapping = dict(self.overrides)
        if value is None:
            mapping.pop(activity_id, None)
        else:
            mapping[activity_id] = value
        return ActivityDiscoveryPolicy(
            visibility_mode=self.visibility_mode,
            difficulty_min=self.difficulty_min,
            difficulty_max=self.difficulty_max,
            overrides=tuple(sorted(mapping.items())),
            subdivided_collections=self.subdivided_collections,
        )

    def with_visibility_mode(
        self, mode: ActivityVisibilityMode
    ) -> "ActivityDiscoveryPolicy":
        return ActivityDiscoveryPolicy(
            visibility_mode=mode,
            difficulty_min=self.difficulty_min,
            difficulty_max=self.difficulty_max,
            overrides=self.overrides,
            subdivided_collections=self.subdivided_collections,
        )

    def with_difficulty_range(
        self,
        minimum: int | None,
        maximum: int | None,
    ) -> "ActivityDiscoveryPolicy":
        _validate_difficulty_range(minimum, maximum)
        return ActivityDiscoveryPolicy(
            visibility_mode=self.visibility_mode,
            difficulty_min=minimum,
            difficulty_max=maximum,
            overrides=self.overrides,
            subdivided_collections=self.subdivided_collections,
        )

    def with_subdivision_state(
        self, collection_id: str, subdivided: bool
    ) -> "ActivityDiscoveryPolicy":
        _validate_collection_id(collection_id)
        state = set(self.subdivided_collections)
        if subdivided:
            state.add(collection_id)
        else:
            state.discard(collection_id)
        return ActivityDiscoveryPolicy(
            visibility_mode=self.visibility_mode,
            difficulty_min=self.difficulty_min,
            difficulty_max=self.difficulty_max,
            overrides=self.overrides,
            subdivided_collections=tuple(sorted(state)),
        )


class ActivityDiscoveryPolicyStore:
    """Small atomic JSON store scoped to one child profile.

    The file is intentionally separate from the profile identity registry. A
    malformed policy must fail closed as invalid policy data rather than mutate
    profile identity, while a missing file simply means the safe default policy.

    Profile data is shared between the child Shell and the constrained Parent
    service through the same managed group boundary as the profile registry, so
    policy files deliberately use group-readable/writable ``0660`` mode rather
    than a private owner-only mode.
    """

    SCHEMA_VERSION = 1
    MAX_BYTES = 64 * 1024
    MAX_OVERRIDES = 512
    MAX_SUBDIVIDED_COLLECTIONS = 16

    def __init__(self, path: Path):
        self.path = path

    def read(self) -> ActivityDiscoveryPolicy:
        try:
            if self.path.is_symlink():
                raise ActivityDiscoveryError("Activity discovery policy may not be a symlink")
            raw_bytes = self.path.read_bytes()
        except FileNotFoundError:
            return ActivityDiscoveryPolicy()
        except OSError as exc:
            raise ActivityDiscoveryError(f"cannot read Activity discovery policy: {exc}") from exc
        if len(raw_bytes) > self.MAX_BYTES:
            raise ActivityDiscoveryError("Activity discovery policy exceeds its size bound")
        try:
            raw = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ActivityDiscoveryError("Activity discovery policy is invalid JSON") from exc
        return self._parse(raw)

    def write(self, policy: ActivityDiscoveryPolicy) -> None:
        payload = self._payload(policy)
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded) > self.MAX_BYTES:
            raise ActivityDiscoveryError("Activity discovery policy exceeds its size bound")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.is_symlink():
            raise ActivityDiscoveryError("Activity discovery policy may not be a symlink")
        fd, temporary = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            dir=str(self.path.parent),
        )
        temp_path = Path(temporary)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_path, 0o660)
            os.replace(temp_path, self.path)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    def update_visibility_mode(
        self, mode: ActivityVisibilityMode
    ) -> ActivityDiscoveryPolicy:
        updated = self.read().with_visibility_mode(mode)
        self.write(updated)
        return updated

    def update_difficulty_range(
        self, minimum: int | None, maximum: int | None
    ) -> ActivityDiscoveryPolicy:
        updated = self.read().with_difficulty_range(minimum, maximum)
        self.write(updated)
        return updated

    def update_override(
        self,
        activity_id: str,
        value: ActivityVisibilityOverride | None,
    ) -> ActivityDiscoveryPolicy:
        updated = self.read().with_override(activity_id, value)
        if len(updated.overrides) > self.MAX_OVERRIDES:
            raise ActivityDiscoveryError("too many per-Activity visibility overrides")
        self.write(updated)
        return updated

    def update_subdivision_state(
        self, collection_id: str, subdivided: bool
    ) -> ActivityDiscoveryPolicy:
        updated = self.read().with_subdivision_state(collection_id, subdivided)
        if len(updated.subdivided_collections) > self.MAX_SUBDIVIDED_COLLECTIONS:
            raise ActivityDiscoveryError("too many adaptive Collection state entries")
        self.write(updated)
        return updated

    def _parse(self, raw: object) -> ActivityDiscoveryPolicy:
        if not isinstance(raw, dict) or raw.get("schema_version") != self.SCHEMA_VERSION:
            raise ActivityDiscoveryError("unsupported Activity discovery policy schema")
        try:
            mode = ActivityVisibilityMode(raw.get("visibility_mode", "show_all"))
        except (TypeError, ValueError) as exc:
            raise ActivityDiscoveryError("invalid Activity visibility mode") from exc

        difficulty_min = _optional_difficulty(raw.get("difficulty_min"))
        difficulty_max = _optional_difficulty(raw.get("difficulty_max"))
        _validate_difficulty_range(difficulty_min, difficulty_max)

        raw_overrides = raw.get("overrides", {})
        if not isinstance(raw_overrides, dict) or len(raw_overrides) > self.MAX_OVERRIDES:
            raise ActivityDiscoveryError("invalid per-Activity visibility overrides")
        overrides: list[tuple[str, ActivityVisibilityOverride]] = []
        for activity_id, raw_value in raw_overrides.items():
            if not isinstance(activity_id, str):
                raise ActivityDiscoveryError("Activity override identifier must be text")
            _validate_activity_id(activity_id)
            try:
                value = ActivityVisibilityOverride(raw_value)
            except (TypeError, ValueError) as exc:
                raise ActivityDiscoveryError("invalid per-Activity visibility override") from exc
            overrides.append((activity_id, value))

        raw_subdivided = raw.get("subdivided_collections", [])
        if (
            not isinstance(raw_subdivided, list)
            or len(raw_subdivided) > self.MAX_SUBDIVIDED_COLLECTIONS
            or not all(isinstance(item, str) for item in raw_subdivided)
        ):
            raise ActivityDiscoveryError("invalid adaptive Collection state")
        subdivided = tuple(raw_subdivided)
        if len(set(subdivided)) != len(subdivided):
            raise ActivityDiscoveryError("adaptive Collection state contains duplicates")
        for collection_id in subdivided:
            _validate_collection_id(collection_id)

        return ActivityDiscoveryPolicy(
            visibility_mode=mode,
            difficulty_min=difficulty_min,
            difficulty_max=difficulty_max,
            overrides=tuple(sorted(overrides)),
            subdivided_collections=tuple(sorted(subdivided)),
        )

    @classmethod
    def _payload(cls, policy: ActivityDiscoveryPolicy) -> dict[str, object]:
        if len(policy.overrides) > cls.MAX_OVERRIDES:
            raise ActivityDiscoveryError("too many per-Activity visibility overrides")
        if len(policy.subdivided_collections) > cls.MAX_SUBDIVIDED_COLLECTIONS:
            raise ActivityDiscoveryError("too many adaptive Collection state entries")
        _validate_difficulty_range(policy.difficulty_min, policy.difficulty_max)
        for activity_id, _ in policy.overrides:
            _validate_activity_id(activity_id)
        for collection_id in policy.subdivided_collections:
            _validate_collection_id(collection_id)
        return {
            "schema_version": cls.SCHEMA_VERSION,
            "visibility_mode": policy.visibility_mode.value,
            "difficulty_min": policy.difficulty_min,
            "difficulty_max": policy.difficulty_max,
            "overrides": {
                activity_id: value.value for activity_id, value in policy.overrides
            },
            "subdivided_collections": list(policy.subdivided_collections),
        }


class ActivityDiscoveryService:
    """Compute the effective child-visible Activity set without package authority.

    This service never changes registry trust, permissions, Activity identity or
    save state. Unknown audience metadata remains usable in unrestricted views,
    but restrictive Parent age presets only auto-include Activities with declared
    audience metadata. Parent explicit overrides are evaluated before automatic
    age/difficulty policy.
    """

    def effective_activities(
        self,
        activities: Iterable[ActivityManifest],
        *,
        approximate_age: int | None,
        challenge_preference: ChallengePreference,
        policy: ActivityDiscoveryPolicy,
    ) -> tuple[ActivityManifest, ...]:
        if approximate_age is not None and not 1 <= approximate_age <= 18:
            raise ActivityDiscoveryError("approximate child age is outside 1..18")
        ordered = tuple(activities)
        visible = tuple(
            activity
            for activity in ordered
            if self._visible(activity, approximate_age=approximate_age, policy=policy)
        )
        if challenge_preference in {
            ChallengePreference.AUTOMATIC,
            ChallengePreference.STANDARD,
        }:
            return tuple(
                activity
                for _, activity in sorted(
                    enumerate(visible),
                    key=lambda pair: (
                        self._age_rank(pair[1], approximate_age),
                        pair[0],
                    ),
                )
            )

        difficulty_sign = 1 if challenge_preference is ChallengePreference.EASIER else -1
        return tuple(
            activity
            for _, activity in sorted(
                enumerate(visible),
                key=lambda pair: (
                    self._age_rank(pair[1], approximate_age),
                    difficulty_sign * pair[1].difficulty,
                    pair[0],
                ),
            )
        )

    @staticmethod
    def _visible(
        activity: ActivityManifest,
        *,
        approximate_age: int | None,
        policy: ActivityDiscoveryPolicy,
    ) -> bool:
        override = policy.override_for(activity.activity_id)
        if override is ActivityVisibilityOverride.ALWAYS_HIDE:
            return False
        if override is ActivityVisibilityOverride.ALWAYS_SHOW:
            return True

        age_visible = True
        if policy.visibility_mode not in {
            ActivityVisibilityMode.SHOW_ALL,
            ActivityVisibilityMode.CUSTOM,
        } and approximate_age is not None:
            if policy.visibility_mode is ActivityVisibilityMode.AGE_AND_EASIER:
                minimum = activity.recommended_age_min
                maximum = activity.recommended_age_max
                age_visible = (minimum is not None or maximum is not None) and (
                    minimum is None or minimum <= approximate_age
                )
            elif policy.visibility_mode is ActivityVisibilityMode.RECOMMENDED_ONLY:
                age_visible = _age_within_declared_range(activity, approximate_age)

        return age_visible and _difficulty_ranges_overlap(activity, policy)

    @staticmethod
    def _age_rank(activity: ActivityManifest, approximate_age: int | None) -> int:
        if approximate_age is None:
            return 0
        minimum = activity.recommended_age_min
        maximum = activity.recommended_age_max
        if minimum is None and maximum is None:
            return 1
        if (minimum is None or approximate_age >= minimum) and (
            maximum is None or approximate_age <= maximum
        ):
            return 0
        return 2


@dataclass(frozen=True, slots=True)
class AdaptiveActivityGroup:
    group_id: str
    activities: tuple[ActivityManifest, ...]


@dataclass(frozen=True, slots=True)
class AdaptiveCollectionPlan:
    collection_id: str
    activities: tuple[ActivityManifest, ...]
    groups: tuple[AdaptiveActivityGroup, ...] = ()

    @property
    def subdivided(self) -> bool:
        return bool(self.groups)


class AdaptiveCollectionPlanner:
    """Deterministically choose direct Activities or one semantic group layer."""

    def __init__(
        self,
        *,
        enter_threshold: int = 10,
        collapse_threshold: int = 8,
        minimum_groups: int = 2,
        maximum_groups: int = 5,
    ):
        if not 1 <= collapse_threshold <= enter_threshold:
            raise ActivityDiscoveryError("invalid adaptive Collection thresholds")
        if not 2 <= minimum_groups <= maximum_groups <= 8:
            raise ActivityDiscoveryError("invalid adaptive Collection group bounds")
        self.enter_threshold = enter_threshold
        self.collapse_threshold = collapse_threshold
        self.minimum_groups = minimum_groups
        self.maximum_groups = maximum_groups

    def plan(
        self,
        collection_id: str,
        activities: Sequence[ActivityManifest],
        *,
        allowed_group_ids: Iterable[str],
        previously_subdivided: bool = False,
    ) -> AdaptiveCollectionPlan:
        _validate_collection_id(collection_id)
        items = tuple(activities)
        count = len(items)
        if count <= self.collapse_threshold:
            return AdaptiveCollectionPlan(collection_id, items)
        if count <= self.enter_threshold and not previously_subdivided:
            return AdaptiveCollectionPlan(collection_id, items)

        allowed = frozenset(allowed_group_ids)
        frequencies: dict[str, int] = {}
        for activity in items:
            seen: set[str] = set()
            for tag in activity.discovery_tags:
                if tag not in allowed or tag in seen:
                    continue
                seen.add(tag)
                frequencies[tag] = frequencies.get(tag, 0) + 1

        candidates = tuple(
            tag
            for tag, frequency in sorted(
                frequencies.items(), key=lambda pair: (-pair[1], pair[0])
            )
            if frequency >= 2
        )
        if len(candidates) < self.minimum_groups:
            return AdaptiveCollectionPlan(collection_id, items)

        selected_tags = candidates[: self.maximum_groups]
        buckets: dict[str, list[ActivityManifest]] = {tag: [] for tag in selected_tags}
        unassigned: list[ActivityManifest] = []
        for activity in items:
            chosen = next((tag for tag in selected_tags if tag in activity.discovery_tags), None)
            if chosen is None:
                unassigned.append(activity)
            else:
                buckets[chosen].append(activity)

        nonempty = tuple(
            (tag, tuple(bucket))
            for tag, bucket in buckets.items()
            if len(bucket) >= 2
        )
        assigned_ids = {
            activity.activity_id
            for _, bucket in nonempty
            for activity in bucket
        }
        if unassigned or len(assigned_ids) != len(items):
            return AdaptiveCollectionPlan(collection_id, items)
        if not self.minimum_groups <= len(nonempty) <= self.maximum_groups:
            return AdaptiveCollectionPlan(collection_id, items)
        if any(len(bucket) > count - 2 for _, bucket in nonempty):
            return AdaptiveCollectionPlan(collection_id, items)

        groups = tuple(
            AdaptiveActivityGroup(group_id=tag, activities=bucket)
            for tag, bucket in nonempty
        )
        return AdaptiveCollectionPlan(collection_id, items, groups)


def _age_within_declared_range(activity: ActivityManifest, age: int) -> bool:
    minimum = activity.recommended_age_min
    maximum = activity.recommended_age_max
    if minimum is None and maximum is None:
        return False
    return (minimum is None or age >= minimum) and (maximum is None or age <= maximum)


def _difficulty_ranges_overlap(
    activity: ActivityManifest, policy: ActivityDiscoveryPolicy
) -> bool:
    requested_min = policy.difficulty_min
    requested_max = policy.difficulty_max
    if requested_min is None and requested_max is None:
        return True
    if activity.adaptive_difficulty:
        activity_min = activity.difficulty_min or activity.difficulty
        activity_max = activity.difficulty_max or activity.difficulty
    else:
        activity_min = activity.difficulty
        activity_max = activity.difficulty
    return (requested_min is None or activity_max >= requested_min) and (
        requested_max is None or activity_min <= requested_max
    )


def _optional_difficulty(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 10:
        raise ActivityDiscoveryError("Activity difficulty bound must be an integer from 1 through 10 or null")
    return value


def _validate_difficulty_range(minimum: int | None, maximum: int | None) -> None:
    for value in (minimum, maximum):
        if value is not None and (
            not isinstance(value, int)
            or isinstance(value, bool)
            or not 1 <= value <= 10
        ):
            raise ActivityDiscoveryError(
                "Activity difficulty bound must be an integer from 1 through 10 or null"
            )
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ActivityDiscoveryError(
            "Activity difficulty minimum must not exceed maximum"
        )


def _validate_activity_id(value: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 160
        or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for character in value)
    ):
        raise ActivityDiscoveryError("invalid Activity identifier in discovery policy")


def _validate_collection_id(value: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 64
        or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for character in value)
    ):
        raise ActivityDiscoveryError("invalid Collection identifier in discovery policy")