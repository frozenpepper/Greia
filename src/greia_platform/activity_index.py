"""Versioned Activity index model and runtime loader.

The index is a build-time snapshot of already-validated Activity
registrations for one configured :class:`ActivitySource`. The authoritative
validation lives in :mod:`greia_platform.activities`
(``ActivityRegistry.validate_registration``); trust comes only from the
configured source in :mod:`greia_platform.trust`. This module deliberately
does not duplicate that validator and never re-reads package trees: the
loader reconstructs :class:`ActivityRegistration` values from stored fields
and binds them to the configured source root.

Missing, corrupt or incompatible built-in index data raises
:class:`ActivityIndexError`, a controlled failure for the launcher
maintenance/error path. The loader never performs a silent full rescan and
never recomputes per-boot package digests for image content.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from .activities import (
    ActivityEventDefinition,
    ActivityManifest,
    ActivityRegistration,
    RuntimeCatalogue,
    SkillContribution,
)
from .trust import ActivitySource, PackageTrust

SCHEMA_VERSION = 1

_MAX_INDEX_BYTES = 8 * 1024 * 1024


class ActivityIndexError(ValueError):
    """Stored Activity index data is missing, corrupt or incompatible."""


@dataclass(frozen=True, slots=True)
class ActivityIndexEntry:
    """Already-validated data for one Activity package.

    ``package_relpath`` is the canonical package root relative to the
    configured source root, stored as POSIX text. ``package_digest`` is the
    validation-time package digest recorded by the generator; the loader
    carries it through without recomputation.
    """

    activity_id: str
    package_relpath: str
    package_digest: str
    title_key: str
    version: str
    runtime_type: str
    api_version: str
    entrypoint: str
    icon_id: str
    categories: tuple[str, ...] = ()
    skills: tuple[SkillContribution, ...] = ()
    events: tuple[ActivityEventDefinition, ...] = ()
    difficulty: int = 1
    languages: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    optional_capabilities: tuple[str, ...] = ()
    requested_permissions: tuple[str, ...] = ()
    storage_schema_version: int = 1
    input_profile: str = "hybrid"
    launcher_categories: tuple[str, ...] = ()
    discovery_tags: tuple[str, ...] = ()
    legacy_ids: tuple[str, ...] = ()
    recommended_age_min: int | None = None
    recommended_age_max: int | None = None
    difficulty_min: int | None = None
    difficulty_max: int | None = None
    adaptive_difficulty: bool = False


@dataclass(frozen=True, slots=True)
class ActivityIndex:
    """Immutable versioned snapshot of validated registrations for one source."""

    schema_version: int = SCHEMA_VERSION
    platform_activity_api_version: str = ""
    source_id: str = ""
    package_trust: PackageTrust = PackageTrust.DEVELOPER_UNSIGNED
    generated_from_policy_version: str = ""
    generated_from_policy_hash: str = ""
    registrations: tuple[ActivityIndexEntry, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-compatible mapping (sorted registrations)."""
        ordered = tuple(sorted(self.registrations, key=lambda item: item.activity_id))
        return {
            "generated_from_policy_hash": self.generated_from_policy_hash,
            "generated_from_policy_version": self.generated_from_policy_version,
            "package_trust": self.package_trust.value,
            "platform_activity_api_version": self.platform_activity_api_version,
            "registrations": [_entry_to_dict(item) for item in ordered],
            "schema_version": self.schema_version,
            "source_id": self.source_id,
        }

    def dumps(self) -> str:
        """Serialize deterministically: sorted keys, UTF-8 text, newline terminated."""
        return (
            json.dumps(
                self.to_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )

    def dump_bytes(self) -> bytes:
        return self.dumps().encode("utf-8")

    def write_file(self, path: Path) -> None:
        """Write the deterministic index payload to *path* atomically."""
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = self.dump_bytes()
        temporary = destination.with_name(destination.name + ".tmp")
        temporary.write_bytes(payload)
        temporary.replace(destination)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ActivityIndex":
        """Parse one index mapping, raising :class:`ActivityIndexError` if invalid."""
        if not isinstance(raw, Mapping):
            raise ActivityIndexError("Activity index must be a JSON object")
        schema_version = raw.get("schema_version")
        if schema_version != SCHEMA_VERSION:
            raise ActivityIndexError(
                f"unsupported Activity index schema: {schema_version!r}"
            )
        try:
            trust = PackageTrust(str(raw.get("package_trust")))
        except ValueError as exc:
            raise ActivityIndexError(
                f"unknown Activity index trust: {raw.get('package_trust')!r}"
            ) from exc
        raw_registrations = raw.get("registrations")
        if not isinstance(raw_registrations, list):
            raise ActivityIndexError("Activity index registrations must be a list")
        entries = tuple(_entry_from_dict(item) for item in raw_registrations)
        for key in (
            "platform_activity_api_version",
            "source_id",
            "generated_from_policy_version",
            "generated_from_policy_hash",
        ):
            value = raw.get(key)
            if not isinstance(value, str) or not value.strip():
                raise ActivityIndexError(f"Activity index {key} must be non-empty text")
        return cls(
            schema_version=SCHEMA_VERSION,
            platform_activity_api_version=str(raw["platform_activity_api_version"]),
            source_id=str(raw["source_id"]),
            package_trust=trust,
            generated_from_policy_version=str(raw["generated_from_policy_version"]),
            generated_from_policy_hash=str(raw["generated_from_policy_hash"]),
            registrations=entries,
        )

    @classmethod
    def loads(cls, payload: bytes | str) -> "ActivityIndex":
        """Parse one index payload, raising :class:`ActivityIndexError` if invalid."""
        if isinstance(payload, bytes):
            try:
                text = payload.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ActivityIndexError("Activity index is not UTF-8") from exc
        elif isinstance(payload, str):
            text = payload
        else:
            raise ActivityIndexError("Activity index payload must be bytes or text")
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ActivityIndexError("Activity index is not valid JSON") from exc
        return cls.from_dict(raw)

    @classmethod
    def load_file(cls, path: Path) -> "ActivityIndex":
        """Read one index file, raising :class:`ActivityIndexError` if unusable."""
        candidate = Path(path)
        try:
            metadata = candidate.stat()
        except FileNotFoundError as exc:
            raise ActivityIndexError(
                f"Activity index is missing: {candidate}"
            ) from exc
        except OSError as exc:
            raise ActivityIndexError(
                f"cannot read Activity index {candidate}: {exc}"
            ) from exc
        if not candidate.is_file() or metadata.st_size > _MAX_INDEX_BYTES:
            raise ActivityIndexError(f"Activity index is unusable: {candidate}")
        try:
            payload = candidate.read_bytes()
        except OSError as exc:
            raise ActivityIndexError(
                f"cannot read Activity index {candidate}: {exc}"
            ) from exc
        if len(payload) > _MAX_INDEX_BYTES:
            raise ActivityIndexError(f"Activity index exceeds its size bound: {candidate}")
        return cls.loads(payload)


def runtime_policy_fingerprint(runtime: RuntimeCatalogue) -> str:
    """Return the stable policy hash identifying one runtime catalogue value."""
    canonical = {
        "allowed_capabilities": sorted(runtime.allowed_capabilities),
        "allowed_permissions": sorted(runtime.allowed_permissions),
        "api_version": runtime.api_version,
        "forbidden_file_names": sorted(runtime.forbidden_file_names),
        "forbidden_path_names": sorted(runtime.forbidden_path_names),
        "forbidden_suffixes": sorted(runtime.forbidden_suffixes),
        "maximum_activity_bytes": runtime.maximum_activity_bytes,
    }
    encoded = json.dumps(
        canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_index(
    registrations: Sequence[ActivityRegistration],
    *,
    source: ActivitySource,
    runtime: RuntimeCatalogue,
) -> ActivityIndex:
    """Build a deterministic index snapshot from validated registrations.

    Every registration must already carry the configured source identity and
    trust; a registration from any other source is rejected so a package can
    never smuggle its own trust into the snapshot. Package roots are stored
    relative to the configured source root.
    """
    entries: list[ActivityIndexEntry] = []
    source_root = source.root.resolve()
    for registration in registrations:
        if registration.source_id != source.source_id:
            raise ActivityIndexError(
                f"registration source {registration.source_id!r} "
                f"does not match index source {source.source_id!r}"
            )
        if registration.package_trust is not source.trust:
            raise ActivityIndexError(
                "registration trust does not match the configured source trust"
            )
        manifest = registration.manifest
        package_root = manifest.root.resolve()
        try:
            relpath = package_root.relative_to(source_root).as_posix()
        except ValueError as exc:
            raise ActivityIndexError(
                f"Activity package {manifest.activity_id!r} is outside its source root"
            ) from exc
        _require_safe_relpath(relpath, label="package root")
        entries.append(
            ActivityIndexEntry(
                activity_id=manifest.activity_id,
                package_relpath=relpath,
                package_digest=registration.package_digest,
                title_key=manifest.title_key,
                version=manifest.version,
                runtime_type=manifest.runtime_type,
                api_version=manifest.api_version,
                entrypoint=manifest.entrypoint.as_posix(),
                icon_id=manifest.icon_id,
                categories=tuple(manifest.categories),
                skills=tuple(manifest.skills),
                events=tuple(manifest.events),
                difficulty=manifest.difficulty,
                languages=tuple(manifest.languages),
                required_capabilities=tuple(manifest.required_capabilities),
                optional_capabilities=tuple(manifest.optional_capabilities),
                requested_permissions=tuple(manifest.requested_permissions),
                storage_schema_version=manifest.storage_schema_version,
                input_profile=manifest.input_profile,
                launcher_categories=tuple(manifest.launcher_categories),
                discovery_tags=tuple(manifest.discovery_tags),
                legacy_ids=tuple(manifest.legacy_ids),
                recommended_age_min=manifest.recommended_age_min,
                recommended_age_max=manifest.recommended_age_max,
                difficulty_min=manifest.difficulty_min,
                difficulty_max=manifest.difficulty_max,
                adaptive_difficulty=manifest.adaptive_difficulty,
            )
        )
    entries.sort(key=lambda item: item.activity_id)
    return ActivityIndex(
        schema_version=SCHEMA_VERSION,
        platform_activity_api_version=runtime.api_version,
        source_id=source.source_id,
        package_trust=source.trust,
        generated_from_policy_version=runtime.api_version,
        generated_from_policy_hash=runtime_policy_fingerprint(runtime),
        registrations=tuple(entries),
    )


@dataclass(frozen=True, slots=True)
class ActivityIndexLoader:
    """Reconstruct validated registrations from a stored index snapshot.

    The loader binds every record to the configured Greia source root and
    verifies schema, platform API and policy identity. Package-supplied trust
    is never accepted: the index trust/source must equal the configured
    source, and the reconstructed registrations always carry the configured
    trust/source. No package tree is re-read and no digest is recomputed.
    """

    source: ActivitySource = field()
    expected_api_version: str = field()
    expected_policy_version: str = field()
    expected_policy_hash: str = field()

    @classmethod
    def from_runtime(
        cls, source: ActivitySource, runtime: RuntimeCatalogue
    ) -> "ActivityIndexLoader":
        """Bind a loader to one configured source and runtime policy value."""
        return cls(
            source=source,
            expected_api_version=runtime.api_version,
            expected_policy_version=runtime.api_version,
            expected_policy_hash=runtime_policy_fingerprint(runtime),
        )

    def load_dict(self, raw: Mapping[str, Any]) -> tuple[ActivityRegistration, ...]:
        """Reconstruct registrations from a parsed mapping without tree re-reads."""
        index = ActivityIndex.from_dict(raw)
        return self._bind(index)

    def loads(self, payload: bytes | str) -> tuple[ActivityRegistration, ...]:
        """Reconstruct registrations from a JSON payload without tree re-reads."""
        return self._bind(ActivityIndex.loads(payload))

    def load_file(self, path: Path) -> tuple[ActivityRegistration, ...]:
        """Reconstruct registrations from an index file without tree re-reads."""
        return self._bind(ActivityIndex.load_file(path))

    def _bind(self, index: ActivityIndex) -> tuple[ActivityRegistration, ...]:
        if index.platform_activity_api_version != self.expected_api_version:
            raise ActivityIndexError(
                "Activity index API "
                f"{index.platform_activity_api_version!r} does not match platform "
                f"{self.expected_api_version!r}"
            )
        if index.generated_from_policy_version != self.expected_policy_version:
            raise ActivityIndexError("Activity index policy version mismatch")
        if index.generated_from_policy_hash != self.expected_policy_hash:
            raise ActivityIndexError("Activity index policy hash mismatch")
        if index.source_id != self.source.source_id:
            raise ActivityIndexError(
                f"Activity index source {index.source_id!r} "
                f"does not match configured source {self.source.source_id!r}"
            )
        if index.package_trust is not self.source.trust:
            raise ActivityIndexError(
                "Activity index trust does not match the configured source trust"
            )
        source_root = self.source.root.resolve()
        if not source_root.is_dir():
            raise ActivityIndexError(
                f"Activity source root is missing: {source_root}"
            )
        registrations: list[ActivityRegistration] = []
        seen: dict[str, str] = {}
        for entry in index.registrations:
            _require_safe_relpath(entry.package_relpath, label="package root")
            _require_digest(entry.package_digest)
            if not entry.activity_id or not entry.activity_id.strip():
                raise ActivityIndexError("Activity index entry is missing its id")
            if entry.activity_id in seen:
                raise ActivityIndexError(
                    f"Activity index contains a duplicate id {entry.activity_id!r}"
                )
            seen[entry.activity_id] = entry.package_relpath
            manifest = ActivityManifest(
                activity_id=entry.activity_id,
                legacy_ids=tuple(entry.legacy_ids),
                title_key=entry.title_key,
                version=entry.version,
                runtime_type=entry.runtime_type,
                api_version=entry.api_version,
                entrypoint=_safe_relative_path(entry.entrypoint, label="entrypoint"),
                icon_id=entry.icon_id,
                categories=tuple(entry.categories),
                skills=tuple(entry.skills),
                events=tuple(entry.events),
                difficulty=entry.difficulty,
                languages=tuple(entry.languages),
                required_capabilities=tuple(entry.required_capabilities),
                optional_capabilities=tuple(entry.optional_capabilities),
                requested_permissions=tuple(entry.requested_permissions),
                storage_schema_version=entry.storage_schema_version,
                root=source_root / PurePosixPath(entry.package_relpath).as_posix(),
                input_profile=entry.input_profile,
                launcher_categories=tuple(entry.launcher_categories),
                discovery_tags=tuple(entry.discovery_tags),
                recommended_age_min=entry.recommended_age_min,
                recommended_age_max=entry.recommended_age_max,
                difficulty_min=entry.difficulty_min,
                difficulty_max=entry.difficulty_max,
                adaptive_difficulty=entry.adaptive_difficulty,
            )
            if manifest.api_version != self.expected_api_version:
                raise ActivityIndexError(
                    f"Activity {manifest.activity_id!r} API mismatch for this platform"
                )
            registrations.append(
                ActivityRegistration(
                    manifest=manifest,
                    package_digest=entry.package_digest,
                    package_trust=self.source.trust,
                    source_id=self.source.source_id,
                )
            )
        registrations.sort(key=lambda item: item.manifest.activity_id)
        return tuple(registrations)


def _entry_to_dict(entry: ActivityIndexEntry) -> dict[str, Any]:
    return {
        "activity_id": entry.activity_id,
        "adaptive_difficulty": entry.adaptive_difficulty,
        "api_version": entry.api_version,
        "categories": list(entry.categories),
        "difficulty": entry.difficulty,
        "difficulty_max": entry.difficulty_max,
        "difficulty_min": entry.difficulty_min,
        "discovery_tags": list(entry.discovery_tags),
        "entrypoint": entry.entrypoint,
        "events": [
            {
                "event_id": event.event_id,
                "kind": event.kind,
                "score_order": event.score_order,
            }
            for event in entry.events
        ],
        "icon_id": entry.icon_id,
        "input_profile": entry.input_profile,
        "languages": list(entry.languages),
        "launcher_categories": list(entry.launcher_categories),
        "legacy_ids": list(entry.legacy_ids),
        "optional_capabilities": list(entry.optional_capabilities),
        "package_digest": entry.package_digest,
        "package_relpath": entry.package_relpath,
        "recommended_age_max": entry.recommended_age_max,
        "recommended_age_min": entry.recommended_age_min,
        "requested_permissions": list(entry.requested_permissions),
        "required_capabilities": list(entry.required_capabilities),
        "runtime_type": entry.runtime_type,
        "skills": [
            {"skill_id": skill.skill_id, "weight": skill.weight}
            for skill in entry.skills
        ],
        "storage_schema_version": entry.storage_schema_version,
        "title_key": entry.title_key,
        "version": entry.version,
    }


def _entry_from_dict(raw: Any) -> ActivityIndexEntry:
    if not isinstance(raw, Mapping):
        raise ActivityIndexError("Activity index entry must be an object")
    activity_id = raw.get("activity_id")
    package_relpath = raw.get("package_relpath")
    package_digest = raw.get("package_digest")
    if not isinstance(activity_id, str) or not activity_id.strip():
        raise ActivityIndexError("Activity index entry is missing its id")
    if not isinstance(package_relpath, str) or not package_relpath.strip():
        raise ActivityIndexError("Activity index entry is missing its package path")
    _require_safe_relpath(package_relpath, label="package root")
    if not isinstance(package_digest, str):
        raise ActivityIndexError("Activity index entry is missing its digest")
    _require_digest(package_digest)
    entrypoint = raw.get("entrypoint")
    if not isinstance(entrypoint, str) or not entrypoint.strip():
        raise ActivityIndexError("Activity index entry is missing its entrypoint")
    _safe_relative_path(entrypoint, label="entrypoint")
    skills = tuple(_skill_from_dict(item) for item in _table_list(raw, "skills"))
    events = tuple(_event_from_dict(item) for item in _table_list(raw, "events"))
    return ActivityIndexEntry(
        activity_id=activity_id,
        package_relpath=package_relpath,
        package_digest=package_digest,
        title_key=_required_text(raw, "title_key"),
        version=_required_text(raw, "version"),
        runtime_type=_required_text(raw, "runtime_type"),
        api_version=_required_text(raw, "api_version"),
        entrypoint=entrypoint,
        icon_id=_required_text(raw, "icon_id"),
        categories=_text_list(raw, "categories"),
        skills=skills,
        events=events,
        difficulty=_required_int(raw, "difficulty"),
        languages=_text_list(raw, "languages"),
        required_capabilities=_text_list(raw, "required_capabilities"),
        optional_capabilities=_text_list(raw, "optional_capabilities"),
        requested_permissions=_text_list(raw, "requested_permissions"),
        storage_schema_version=_required_int(raw, "storage_schema_version"),
        input_profile=_required_text(raw, "input_profile"),
        launcher_categories=_text_list(raw, "launcher_categories"),
        discovery_tags=_text_list(raw, "discovery_tags"),
        legacy_ids=_text_list(raw, "legacy_ids"),
        recommended_age_min=_optional_int(raw, "recommended_age_min"),
        recommended_age_max=_optional_int(raw, "recommended_age_max"),
        difficulty_min=_optional_int(raw, "difficulty_min"),
        difficulty_max=_optional_int(raw, "difficulty_max"),
        adaptive_difficulty=_required_bool(raw, "adaptive_difficulty"),
    )


def _skill_from_dict(raw: Any) -> SkillContribution:
    if not isinstance(raw, Mapping):
        raise ActivityIndexError("Activity index skill must be an object")
    skill_id = raw.get("skill_id")
    weight = raw.get("weight")
    if not isinstance(skill_id, str) or not skill_id.strip():
        raise ActivityIndexError("Activity index skill is missing its id")
    if not isinstance(weight, int) or isinstance(weight, bool):
        raise ActivityIndexError("Activity index skill weight must be an integer")
    return SkillContribution(skill_id, weight)


def _event_from_dict(raw: Any) -> ActivityEventDefinition:
    if not isinstance(raw, Mapping):
        raise ActivityIndexError("Activity index event must be an object")
    event_id = raw.get("event_id")
    kind = raw.get("kind")
    score_order = raw.get("score_order")
    if not isinstance(event_id, str) or not event_id.strip():
        raise ActivityIndexError("Activity index event is missing its id")
    if not isinstance(kind, str) or not kind.strip():
        raise ActivityIndexError("Activity index event is missing its kind")
    if score_order is not None and not isinstance(score_order, str):
        raise ActivityIndexError("Activity index event score_order must be text or null")
    return ActivityEventDefinition(event_id, kind, score_order)


def _require_safe_relpath(value: str, *, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ActivityIndexError(f"Activity index {label} must be non-empty text")
    candidate = PurePosixPath(value)
    if candidate.is_absolute():
        raise ActivityIndexError(f"Activity index {label} must be a relative path")
    parts = candidate.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ActivityIndexError(f"Activity index {label} escapes its source root")


def _safe_relative_path(value: str, *, label: str) -> Path:
    _require_safe_relpath(value, label=label)
    return Path(PurePosixPath(value).as_posix())


def _require_digest(value: str) -> None:
    if len(value) != 64:
        raise ActivityIndexError("Activity index digest must be a SHA-256 hex string")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ActivityIndexError(
            "Activity index digest must be a SHA-256 hex string"
        ) from exc
    if value != value.lower() or not value.isalnum():
        raise ActivityIndexError("Activity index digest must be lowercase hex")


def _required_text(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ActivityIndexError(f"Activity index entry field {key} must be non-empty text")
    return value


def _text_list(raw: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = raw.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ActivityIndexError(f"Activity index entry field {key} must be a string list")
    return tuple(value)


def _table_list(raw: Mapping[str, Any], key: str) -> tuple[Any, ...]:
    value = raw.get(key, [])
    if not isinstance(value, list):
        raise ActivityIndexError(f"Activity index entry field {key} must be a list")
    return tuple(value)


def _required_int(raw: Mapping[str, Any], key: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ActivityIndexError(f"Activity index entry field {key} must be an integer")
    return value


def _required_bool(raw: Mapping[str, Any], key: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise ActivityIndexError(f"Activity index entry field {key} must be a boolean")
    return value


def _optional_int(raw: Mapping[str, Any], key: str) -> int | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ActivityIndexError(f"Activity index entry field {key} must be an integer or null")
    return value
