from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .trust import ActivitySource, PackageTrust


class ActivityValidationError(ValueError):
    """Raised when an Activity violates the runtime-neutral package contract."""


@dataclass(frozen=True, slots=True)
class SkillContribution:
    skill_id: str
    weight: int


@dataclass(frozen=True, slots=True)
class ActivityEventDefinition:
    event_id: str
    kind: str
    score_order: str | None = None


@dataclass(frozen=True, slots=True)
class ActivityManifest:
    activity_id: str
    legacy_ids: tuple[str, ...]
    title_key: str
    version: str
    runtime_type: str
    api_version: str
    entrypoint: Path
    icon_id: str
    categories: tuple[str, ...]
    skills: tuple[SkillContribution, ...]
    events: tuple[ActivityEventDefinition, ...]
    difficulty: int
    languages: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    optional_capabilities: tuple[str, ...]
    requested_permissions: tuple[str, ...]
    storage_schema_version: int
    root: Path

    @property
    def launch_path(self) -> Path:
        return self.root / self.entrypoint


@dataclass(frozen=True, slots=True)
class ActivityRegistration:
    """Validated package identity plus platform-owned origin/trust metadata."""

    manifest: ActivityManifest
    package_digest: str
    package_trust: PackageTrust
    source_id: str


@dataclass(frozen=True, slots=True)
class RuntimeCatalogue:
    """Runtime-neutral package/API vocabulary shared by every Activity runtime."""

    api_version: str
    forbidden_file_names: frozenset[str]
    forbidden_path_names: frozenset[str]
    forbidden_suffixes: frozenset[str]
    allowed_capabilities: frozenset[str]
    allowed_permissions: frozenset[str]
    maximum_activity_bytes: int

    @classmethod
    def load(cls, path: Path) -> "RuntimeCatalogue":
        try:
            with path.open("rb") as handle:
                raw = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ActivityValidationError(f"invalid runtime catalogue {path}: {exc}") from exc
        runtime = _mapping(raw, "runtime")
        validation = _mapping(raw, "validation")
        capabilities = _mapping(raw, "capabilities")
        permissions = _mapping(raw, "permissions")
        catalogue = cls(
            api_version=_string(runtime, "api_version"),
            forbidden_file_names=frozenset(
                name.casefold() for name in _string_list(validation, "forbidden_file_names")
            ),
            forbidden_path_names=frozenset(
                name.casefold() for name in _string_list(validation, "forbidden_path_names")
            ),
            forbidden_suffixes=frozenset(
                suffix.casefold() for suffix in _string_list(validation, "forbidden_suffixes")
            ),
            allowed_capabilities=frozenset(_string_list(capabilities, "allowed")),
            allowed_permissions=frozenset(_string_list(permissions, "allowed")),
            maximum_activity_bytes=_integer(validation, "maximum_activity_bytes", minimum=1),
        )
        overlap = catalogue.allowed_capabilities & catalogue.allowed_permissions
        if overlap:
            raise ActivityValidationError(
                "capability and permission vocabularies must be disjoint: "
                + ", ".join(sorted(overlap))
            )
        return catalogue


class ActivityRegistry:
    """Discover and validate runtime-neutral Greia Activity package facts.

    The registry owns package provenance, manifest semantics, path safety, package
    footprint, stable identity and platform vocabulary. Runtime-specific source
    policy (for example Python AST/import validation or future Web content rules)
    belongs to the selected runtime adapter/manager in ``greia_launcher``.
    """

    def __init__(
        self,
        activity_roots: Sequence[Path | ActivitySource],
        runtime: RuntimeCatalogue,
    ):
        sources: list[ActivitySource] = []
        for index, source in enumerate(activity_roots):
            if isinstance(source, ActivitySource):
                sources.append(source)
            else:
                sources.append(
                    ActivitySource(
                        root=source,
                        trust=PackageTrust.DEVELOPER_UNSIGNED,
                        source_id=f"development-{index}",
                    )
                )
        self._activity_sources = tuple(sources)
        self._activity_roots = tuple(source.root for source in sources)
        self._runtime = runtime
        self._registrations_by_manifest_object: dict[int, ActivityRegistration] = {}

    def discover(self) -> tuple[ActivityManifest, ...]:
        return tuple(registration.manifest for registration in self.discover_registrations())

    def discover_registrations(self) -> tuple[ActivityRegistration, ...]:
        registrations: list[ActivityRegistration] = []
        identities: dict[str, str] = {}
        self._registrations_by_manifest_object.clear()
        for source in self._activity_sources:
            parent = source.root
            if not parent.exists():
                continue
            for manifest_path in sorted(parent.glob("*/activity.toml")):
                registration = self.validate_registration(manifest_path.parent, source)
                manifest = registration.manifest
                for identity in (manifest.activity_id, *manifest.legacy_ids):
                    previous = identities.get(identity)
                    if previous is not None and previous != manifest.activity_id:
                        raise ActivityValidationError(
                            f"Activity identity/alias collision {identity!r}: "
                            f"{previous} and {manifest.activity_id}"
                        )
                    identities[identity] = manifest.activity_id
                registrations.append(registration)
                self._registrations_by_manifest_object[id(manifest)] = registration
        return tuple(registrations)

    def registration_for(self, manifest: ActivityManifest) -> ActivityRegistration:
        registration = self._registrations_by_manifest_object.get(id(manifest))
        if registration is None or registration.manifest is not manifest:
            raise ActivityValidationError(
                "Activity manifest was not issued by this registry discovery pass"
            )
        return registration

    def discovery_token(self) -> tuple[tuple[str, int, int, int], ...]:
        items: list[tuple[str, int, int, int]] = []
        for parent in self._activity_roots:
            if not parent.exists():
                continue
            try:
                manifests = sorted(parent.glob("*/activity.toml"))
            except OSError:
                continue
            for manifest in manifests:
                try:
                    stat = manifest.stat()
                    root_mtime = manifest.parent.stat().st_mtime_ns
                except OSError:
                    continue
                items.append((manifest.as_posix(), stat.st_mtime_ns, stat.st_size, root_mtime))
        return tuple(items)

    def validate_package(self, activity_root: Path) -> ActivityManifest:
        root = activity_root.resolve(strict=True)
        source = self._source_for_root(root)
        return self.validate_registration(root, source).manifest

    def validate_registration(
        self,
        activity_root: Path,
        source: ActivitySource | None = None,
    ) -> ActivityRegistration:
        root = activity_root.resolve(strict=True)
        self._assert_under_activity_roots(root)
        source = source or self._source_for_root(root)
        self._validate_tree(root)
        manifest = self._parse_manifest(root)
        self._validate_manifest(manifest, source)
        return ActivityRegistration(
            manifest=manifest,
            package_digest=package_digest(root),
            package_trust=source.trust,
            source_id=source.source_id,
        )

    def _source_for_root(self, root: Path) -> ActivitySource:
        matches = [
            source for source in self._activity_sources
            if root == source.root or source.root in root.parents
        ]
        if not matches:
            raise ActivityValidationError(f"activity is outside configured roots: {root}")
        return max(matches, key=lambda source: len(source.root.parts))

    def _assert_under_activity_roots(self, root: Path) -> None:
        if not any(root == parent or parent in root.parents for parent in self._activity_roots):
            raise ActivityValidationError(f"activity is outside configured roots: {root}")

    def _validate_tree(self, root: Path) -> None:
        total_bytes = 0
        for path in root.rglob("*"):
            if path.is_symlink():
                raise ActivityValidationError(f"symlinks are forbidden: {path}")
            folded_name = path.name.casefold()
            if folded_name in self._runtime.forbidden_file_names:
                raise ActivityValidationError(f"forbidden package file: {path.name}")
            if path.is_dir() and folded_name in self._runtime.forbidden_path_names:
                raise ActivityValidationError(f"forbidden package directory: {path.name}")
            if path.is_file():
                try:
                    metadata = path.stat()
                except OSError as exc:
                    raise ActivityValidationError(f"cannot inspect package file {path}: {exc}") from exc
                total_bytes += metadata.st_size
                if path.suffix.casefold() in self._runtime.forbidden_suffixes:
                    raise ActivityValidationError(
                        f"bundled executable/dependency archive forbidden: {path}"
                    )
                if metadata.st_mode & 0o111:
                    raise ActivityValidationError(f"executable activity files are forbidden: {path}")
        if total_bytes > self._runtime.maximum_activity_bytes:
            raise ActivityValidationError(
                f"activity is {total_bytes} bytes; limit is {self._runtime.maximum_activity_bytes}"
            )

    def _parse_manifest(self, root: Path) -> ActivityManifest:
        path = root / "activity.toml"
        try:
            with path.open("rb") as handle:
                raw = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ActivityValidationError(f"invalid activity manifest {path}: {exc}") from exc

        activity = _mapping(raw, "activity")
        education = _mapping(raw, "education")
        runtime = _mapping(raw, "runtime")
        requirements = _mapping(raw, "requirements")
        permissions = _mapping(raw, "permissions")
        storage = _mapping(raw, "storage")

        if "capabilities" in runtime:
            raise ActivityValidationError(
                "runtime.capabilities is obsolete; use requirements.required_capabilities/optional_capabilities"
            )
        if "rewards" in education:
            raise ActivityValidationError(
                "education.rewards is forbidden; Activities report factual events"
            )

        skills = tuple(
            SkillContribution(
                skill_id=_string(item, "id"),
                weight=_integer(item, "weight", minimum=1, maximum=10),
            )
            for item in _mapping_list(education, "skills")
        )
        events = tuple(_parse_event(item) for item in _mapping_list_allow_empty(education, "events"))

        return ActivityManifest(
            activity_id=_string(activity, "id"),
            legacy_ids=_string_list_allow_empty(activity, "legacy_ids", default=()),
            title_key=_string(activity, "title_key"),
            version=_string(activity, "version"),
            runtime_type=_string(runtime, "type"),
            api_version=_string(runtime, "api_version"),
            entrypoint=Path(_string(runtime, "entrypoint")),
            icon_id=_string(activity, "icon"),
            categories=tuple(_string_list(education, "categories")),
            skills=skills,
            events=events,
            difficulty=_integer(education, "difficulty", minimum=1, maximum=10),
            languages=tuple(_string_list(activity, "languages")),
            required_capabilities=_string_list_allow_empty(
                requirements, "required_capabilities", default=()
            ),
            optional_capabilities=_string_list_allow_empty(
                requirements, "optional_capabilities", default=()
            ),
            requested_permissions=_string_list_allow_empty(
                permissions, "requested", default=()
            ),
            storage_schema_version=_integer(storage, "schema_version", minimum=1),
            root=root,
        )

    def _validate_manifest(self, manifest: ActivityManifest, source: ActivitySource) -> None:
        if not _is_canonical_activity_id(manifest.activity_id):
            raise ActivityValidationError(
                "activity.id must be a permanent lower-case reverse-DNS identifier"
            )
        if len(set(manifest.legacy_ids)) != len(manifest.legacy_ids):
            raise ActivityValidationError("activity.legacy_ids must not contain duplicates")
        if manifest.activity_id in manifest.legacy_ids:
            raise ActivityValidationError("canonical Activity ID may not also be a legacy alias")
        for legacy_id in manifest.legacy_ids:
            if not _is_legacy_activity_id(legacy_id):
                raise ActivityValidationError(f"invalid legacy Activity ID: {legacy_id!r}")
        if manifest.legacy_ids and source.trust is not PackageTrust.BUILT_IN:
            raise ActivityValidationError(
                "legacy Activity IDs are migration authority and require BUILT_IN package origin"
            )
        if manifest.api_version != self._runtime.api_version:
            raise ActivityValidationError(
                f"activity {manifest.activity_id} targets API {manifest.api_version}; "
                f"platform provides {self._runtime.api_version}"
            )
        if not _is_runtime_type(manifest.runtime_type):
            raise ActivityValidationError("runtime.type must be a bounded lower-case identifier")
        if manifest.entrypoint.is_absolute() or ".." in manifest.entrypoint.parts:
            raise ActivityValidationError("runtime.entrypoint must be a safe relative path")
        try:
            launch_path = manifest.launch_path.resolve(strict=True)
        except OSError as exc:
            raise ActivityValidationError(
                f"runtime.entrypoint does not resolve to a package file: {manifest.entrypoint}"
            ) from exc
        if manifest.root not in launch_path.parents or not launch_path.is_file():
            raise ActivityValidationError("runtime.entrypoint must resolve to a file inside the package")
        if not manifest.skills:
            raise ActivityValidationError("education.skills must contain at least one skill")
        if not manifest.languages:
            raise ActivityValidationError("activity.languages must not be empty")

        _require_unique("requirements.required_capabilities", manifest.required_capabilities)
        _require_unique("requirements.optional_capabilities", manifest.optional_capabilities)
        _require_unique("permissions.requested", manifest.requested_permissions)
        capability_overlap = set(manifest.required_capabilities) & set(manifest.optional_capabilities)
        if capability_overlap:
            raise ActivityValidationError(
                "capabilities cannot be both required and optional: "
                + ", ".join(sorted(capability_overlap))
            )
        unknown_capabilities = (
            set(manifest.required_capabilities)
            | set(manifest.optional_capabilities)
        ) - self._runtime.allowed_capabilities
        if unknown_capabilities:
            raise ActivityValidationError(
                "activity requests unknown capabilities: "
                + ", ".join(sorted(unknown_capabilities))
            )
        unknown_permissions = (
            set(manifest.requested_permissions) - self._runtime.allowed_permissions
        )
        if unknown_permissions:
            raise ActivityValidationError(
                "activity requests unknown permissions: "
                + ", ".join(sorted(unknown_permissions))
            )
        event_ids = tuple(event.event_id for event in manifest.events)
        _require_unique("education.events ids", event_ids)


def package_digest(root: Path) -> str:
    """Return a stable digest used by future signed package catalogues."""

    hasher = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        hasher.update(len(relative).to_bytes(4, "big"))
        hasher.update(relative)
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
    return hasher.hexdigest()


def _parse_event(raw: Mapping[str, object]) -> ActivityEventDefinition:
    event_id = _string(raw, "id")
    kind = _string(raw, "kind")
    if not _is_event_id(event_id):
        raise ActivityValidationError(f"invalid education event id: {event_id!r}")
    if kind not in {"completion", "creation", "milestone", "score"}:
        raise ActivityValidationError(f"unsupported education event kind: {kind!r}")
    score_order_raw = raw.get("score_order")
    if score_order_raw is None:
        score_order = None
    elif isinstance(score_order_raw, str) and score_order_raw in {
        "higher_better",
        "lower_better",
    }:
        score_order = score_order_raw
    else:
        raise ActivityValidationError(
            "education event score_order must be higher_better or lower_better"
        )
    if kind == "score" and score_order is None:
        raise ActivityValidationError("score events require score_order")
    if kind != "score" and score_order is not None:
        raise ActivityValidationError("non-score events may not declare score_order")
    return ActivityEventDefinition(event_id=event_id, kind=kind, score_order=score_order)


def _require_unique(label: str, values: tuple[str, ...]) -> None:
    if len(set(values)) != len(values):
        raise ActivityValidationError(f"{label} must not contain duplicates")


def _is_canonical_activity_id(value: str) -> bool:
    if not isinstance(value, str) or len(value) > 160:
        return False
    parts = value.split(".")
    if len(parts) < 3:
        return False
    return all(_is_dns_like_segment(part) for part in parts)


def _is_dns_like_segment(value: str) -> bool:
    if not value or len(value) > 63:
        return False
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-")
    return (
        value[0].isalnum()
        and value[-1].isalnum()
        and all(char in allowed for char in value)
    )


def _is_legacy_activity_id(value: str) -> bool:
    if not isinstance(value, str) or not value or len(value) > 160:
        return False
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    return value[0].isalnum() and value[-1].isalnum() and all(c in allowed for c in value)


def _is_runtime_type(value: str) -> bool:
    if not isinstance(value, str) or not value or len(value) > 64:
        return False
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    return value[0].isalnum() and value[-1].isalnum() and all(c in allowed for c in value)


def _is_event_id(value: str) -> bool:
    return _is_legacy_activity_id(value)


def _mapping(container: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = container.get(key)
    if not isinstance(value, dict):
        raise ActivityValidationError(f"{key} must be a table")
    return value


def _mapping_list(container: Mapping[str, object], key: str) -> tuple[Mapping[str, object], ...]:
    value = container.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, dict) for item in value):
        raise ActivityValidationError(f"{key} must be a non-empty array of tables")
    return tuple(value)  # type: ignore[arg-type]


def _mapping_list_allow_empty(
    container: Mapping[str, object], key: str
) -> tuple[Mapping[str, object], ...]:
    value = container.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ActivityValidationError(f"{key} must be an array of tables")
    return tuple(value)  # type: ignore[arg-type]


def _string(container: Mapping[str, object], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ActivityValidationError(f"{key} must be a non-empty string")
    return value.strip()


def _string_list(container: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = container.get(key)
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ActivityValidationError(f"{key} must be a non-empty array of strings")
    return tuple(item.strip() for item in value)


def _string_list_allow_empty(
    container: Mapping[str, object],
    key: str,
    *,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    value = container.get(key)
    if value is None:
        return default
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ActivityValidationError(f"{key} must be an array of strings")
    return tuple(item.strip() for item in value)


def _integer(
    container: Mapping[str, object],
    key: str,
    *,
    minimum: int,
    maximum: int | None = None,
) -> int:
    value = container.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ActivityValidationError(f"{key} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        upper = f" and <= {maximum}" if maximum is not None else ""
        raise ActivityValidationError(f"{key} must be >= {minimum}{upper}")
    return value
