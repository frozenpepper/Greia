from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .input_core import InteractionProfile, SUPPORTED_INTERACTION_PROFILES
from .trust import ActivitySource, PackageTrust


class ActivityValidationError(ValueError):
    """An Activity package does not satisfy Greia's shared package contract."""


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
    input_profile: str = InteractionProfile.HYBRID.value
    # Launcher navigation is intentionally separate from educational taxonomy.
    # Empty means an older package that should temporarily fall back to
    # education.categories for compatibility.
    launcher_categories: tuple[str, ...] = ()

    @property
    def launch_path(self) -> Path:
        return self.root / self.entrypoint


@dataclass(frozen=True, slots=True)
class ActivityRegistration:
    manifest: ActivityManifest
    package_digest: str
    package_trust: PackageTrust
    source_id: str


@dataclass(frozen=True, slots=True)
class RuntimeCatalogue:
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
        runtime = _table(raw, "runtime")
        validation = _table(raw, "validation")
        capabilities = _table(raw, "capabilities")
        permissions = _table(raw, "permissions")
        result = cls(
            api_version=_text(runtime, "api_version"),
            forbidden_file_names=_folded(validation, "forbidden_file_names"),
            forbidden_path_names=_folded(validation, "forbidden_path_names"),
            forbidden_suffixes=_folded(validation, "forbidden_suffixes"),
            allowed_capabilities=frozenset(_texts(capabilities, "allowed")),
            allowed_permissions=frozenset(_texts(permissions, "allowed")),
            maximum_activity_bytes=_integer(validation, "maximum_activity_bytes", 1),
        )
        overlap = result.allowed_capabilities & result.allowed_permissions
        if overlap:
            raise ActivityValidationError(
                "capability and permission vocabularies overlap: " + ", ".join(sorted(overlap))
            )
        return result


class ActivityRegistry:
    """Runtime-neutral Activity discovery and package validation."""

    def __init__(
        self,
        activity_roots: Sequence[Path | ActivitySource],
        runtime: RuntimeCatalogue,
    ):
        sources: list[ActivitySource] = []
        for index, value in enumerate(activity_roots):
            if isinstance(value, ActivitySource):
                sources.append(value)
            else:
                sources.append(
                    ActivitySource(
                        value,
                        trust=PackageTrust.DEVELOPER_UNSIGNED,
                        source_id=f"development-{index}",
                    )
                )
        self._sources = tuple(sources)
        self._roots = tuple(source.root for source in sources)
        self._runtime = runtime
        self._issued: dict[int, ActivityRegistration] = {}

    def discover(self) -> tuple[ActivityManifest, ...]:
        return tuple(item.manifest for item in self.discover_registrations())

    def discover_registrations(self) -> tuple[ActivityRegistration, ...]:
        registrations: list[ActivityRegistration] = []
        identities: dict[str, str] = {}
        self._issued.clear()
        for source in self._sources:
            if not source.root.exists():
                continue
            for path in sorted(source.root.glob("*/activity.toml")):
                registration = self.validate_registration(path.parent, source)
                manifest = registration.manifest
                for identity in (manifest.activity_id, *manifest.legacy_ids):
                    if identity in identities:
                        raise ActivityValidationError(
                            f"Activity identity/alias collision {identity!r}: "
                            f"{identities[identity]} and {manifest.activity_id}"
                        )
                    identities[identity] = manifest.activity_id
                registrations.append(registration)
                self._issued[id(manifest)] = registration
        return tuple(registrations)

    def registration_for(self, manifest: ActivityManifest) -> ActivityRegistration:
        registration = self._issued.get(id(manifest))
        if registration is None or registration.manifest is not manifest:
            raise ActivityValidationError("Activity manifest was not issued by this registry")
        return registration

    def discovery_token(self) -> tuple[tuple[str, int, int, int], ...]:
        items: list[tuple[str, int, int, int]] = []
        for parent in self._roots:
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
        return self.validate_registration(root).manifest

    def validate_registration(
        self,
        activity_root: Path,
        source: ActivitySource | None = None,
    ) -> ActivityRegistration:
        root = activity_root.resolve(strict=True)
        configured = self._source_for(root)
        if source is not None:
            if source not in self._sources:
                raise ActivityValidationError("Activity source is not configured in this registry")
            if source != configured:
                raise ActivityValidationError(
                    "Activity source is not the authoritative configured source for this package"
                )
        self._validate_tree(root)
        manifest = self._parse_manifest(root)
        self._validate_manifest(manifest, configured)
        return ActivityRegistration(
            manifest=manifest,
            package_digest=package_digest(root),
            package_trust=configured.trust,
            source_id=configured.source_id,
        )

    def _source_for(self, root: Path) -> ActivitySource:
        matches = [
            source for source in self._sources
            if root == source.root or source.root in root.parents
        ]
        if not matches:
            raise ActivityValidationError(f"activity is outside configured roots: {root}")
        return max(matches, key=lambda item: len(item.root.parts))

    def _validate_tree(self, root: Path) -> None:
        total = 0
        for path in sorted(root.rglob("*")):
            if "__pycache__" in path.parts:
                continue
            if path.is_symlink():
                raise ActivityValidationError(f"symlinks are forbidden: {path}")
            name = path.name.casefold()
            if path.is_dir() and name in self._runtime.forbidden_path_names:
                raise ActivityValidationError(f"forbidden package directory: {path.name}")
            if not path.is_file():
                continue
            if name in self._runtime.forbidden_file_names:
                raise ActivityValidationError(f"forbidden package file: {path.name}")
            try:
                metadata = path.stat()
            except OSError as exc:
                raise ActivityValidationError(f"cannot inspect package file {path}: {exc}") from exc
            total += metadata.st_size
            if path.suffix.casefold() in self._runtime.forbidden_suffixes:
                raise ActivityValidationError(f"forbidden package suffix: {path}")
            if metadata.st_mode & 0o111:
                raise ActivityValidationError(f"executable activity files are forbidden: {path}")
        if total > self._runtime.maximum_activity_bytes:
            raise ActivityValidationError(
                f"activity is {total} bytes; limit is {self._runtime.maximum_activity_bytes}"
            )

    def _parse_manifest(self, root: Path) -> ActivityManifest:
        path = root / "activity.toml"
        try:
            with path.open("rb") as handle:
                raw = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ActivityValidationError(f"invalid activity manifest {path}: {exc}") from exc

        activity = _table(raw, "activity")
        education = _table(raw, "education")
        runtime = _table(raw, "runtime")
        requirements = _table(raw, "requirements")
        permissions = _table(raw, "permissions")
        storage = _table(raw, "storage")

        raw_presentation = raw.get("presentation")
        if raw_presentation is None:
            launcher_categories: tuple[str, ...] = ()
        elif isinstance(raw_presentation, dict):
            launcher_categories = _texts(raw_presentation, "categories")
        else:
            raise ActivityValidationError("presentation must be a table")

        raw_input = raw.get("input")
        if raw_input is None:
            # API 0.1 compatibility for existing packages. New packages should
            # declare this explicitly so the platform can choose consistent
            # keyboard/pointer/controller behavior before runtime launch.
            input_profile = InteractionProfile.HYBRID.value
        elif isinstance(raw_input, dict):
            input_profile = _text(raw_input, "profile")
        else:
            raise ActivityValidationError("input must be a table")
        if "capabilities" in runtime:
            raise ActivityValidationError("runtime.capabilities is obsolete")
        if "rewards" in education:
            raise ActivityValidationError("education.rewards is forbidden")
        skills = tuple(
            SkillContribution(
                _text(item, "id"),
                _integer(item, "weight", 1, 10),
            )
            for item in _tables(education, "skills", allow_empty=False)
        )
        events = tuple(
            _event(item) for item in _tables(education, "events", allow_empty=True)
        )
        return ActivityManifest(
            activity_id=_text(activity, "id"),
            legacy_ids=_texts(activity, "legacy_ids", allow_empty=True),
            title_key=_text(activity, "title_key"),
            version=_text(activity, "version"),
            runtime_type=_text(runtime, "type"),
            api_version=_text(runtime, "api_version"),
            entrypoint=Path(_text(runtime, "entrypoint")),
            icon_id=_text(activity, "icon"),
            categories=_texts(education, "categories"),
            skills=skills,
            events=events,
            difficulty=_integer(education, "difficulty", 1, 10),
            languages=_texts(activity, "languages"),
            required_capabilities=_texts(
                requirements, "required_capabilities", allow_empty=True
            ),
            optional_capabilities=_texts(
                requirements, "optional_capabilities", allow_empty=True
            ),
            requested_permissions=_texts(
                permissions, "requested", allow_empty=True
            ),
            storage_schema_version=_integer(storage, "schema_version", 1),
            root=root,
            input_profile=input_profile,
            launcher_categories=launcher_categories,
        )

    def _validate_manifest(self, manifest: ActivityManifest, source: ActivitySource) -> None:
        if not _canonical_id(manifest.activity_id):
            raise ActivityValidationError("activity.id must be a lower-case reverse-DNS identifier")
        _unique("activity.legacy_ids", manifest.legacy_ids)
        if manifest.activity_id in manifest.legacy_ids:
            raise ActivityValidationError("canonical Activity ID cannot also be a legacy alias")
        if any(not _bounded_id(value, 160) for value in manifest.legacy_ids):
            raise ActivityValidationError("activity.legacy_ids contains an invalid identifier")
        if manifest.legacy_ids and source.trust is not PackageTrust.BUILT_IN:
            raise ActivityValidationError("legacy Activity aliases require built-in package origin")
        if manifest.api_version != self._runtime.api_version:
            raise ActivityValidationError(
                f"activity API {manifest.api_version} does not match platform {self._runtime.api_version}"
            )
        if not _bounded_id(manifest.runtime_type, 64):
            raise ActivityValidationError("runtime.type must be a lower-case identifier")
        if manifest.entrypoint.is_absolute() or ".." in manifest.entrypoint.parts:
            raise ActivityValidationError("runtime.entrypoint must be a safe relative path")
        try:
            launch_path = manifest.launch_path.resolve(strict=True)
        except OSError as exc:
            raise ActivityValidationError("runtime.entrypoint does not exist") from exc
        if manifest.root not in launch_path.parents or not launch_path.is_file():
            raise ActivityValidationError("runtime.entrypoint must be a file inside the package")
        if manifest.input_profile not in SUPPORTED_INTERACTION_PROFILES:
            raise ActivityValidationError(
                "unsupported input.profile: " + repr(manifest.input_profile)
            )

        _unique("activity.languages", manifest.languages)
        _unique("education.categories", manifest.categories)
        _unique("presentation.categories", manifest.launcher_categories)
        if len(manifest.launcher_categories) > 4:
            raise ActivityValidationError(
                "presentation.categories may contain at most four launcher categories"
            )
        if any(
            not _bounded_id(value, 64) for value in manifest.launcher_categories
        ):
            raise ActivityValidationError(
                "presentation.categories contains an invalid launcher category id"
            )
        _unique("education.skills ids", tuple(item.skill_id for item in manifest.skills))
        _unique("education.events ids", tuple(item.event_id for item in manifest.events))
        _unique("requirements.required_capabilities", manifest.required_capabilities)
        _unique("requirements.optional_capabilities", manifest.optional_capabilities)
        _unique("permissions.requested", manifest.requested_permissions)

        required = set(manifest.required_capabilities)
        optional = set(manifest.optional_capabilities)
        overlap = required & optional
        if overlap:
            raise ActivityValidationError(
                "capabilities cannot be both required and optional: " + ", ".join(sorted(overlap))
            )
        unknown = (required | optional) - self._runtime.allowed_capabilities
        if unknown:
            raise ActivityValidationError(
                "unknown Activity capabilities: " + ", ".join(sorted(unknown))
            )
        unknown_permissions = set(manifest.requested_permissions) - self._runtime.allowed_permissions
        if unknown_permissions:
            raise ActivityValidationError(
                "unknown Activity permissions: " + ", ".join(sorted(unknown_permissions))
            )


def package_digest(root: Path) -> str:
    hasher = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        hasher.update(len(relative).to_bytes(4, "big"))
        hasher.update(relative)
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
    return hasher.hexdigest()


def _event(raw: Mapping[str, object]) -> ActivityEventDefinition:
    event_id = _text(raw, "id")
    kind = _text(raw, "kind")
    if not _bounded_id(event_id, 160):
        raise ActivityValidationError(f"invalid event id: {event_id!r}")
    if kind not in {"completion", "creation", "milestone", "score"}:
        raise ActivityValidationError(f"unsupported event kind: {kind!r}")
    raw_order = raw.get("score_order")
    if kind == "score":
        if raw_order not in {"higher_better", "lower_better"}:
            raise ActivityValidationError("score events require score_order")
        order = str(raw_order)
    else:
        if raw_order is not None:
            raise ActivityValidationError("non-score events cannot declare score_order")
        order = None
    return ActivityEventDefinition(event_id, kind, order)


def _canonical_id(value: str) -> bool:
    parts = value.split(".") if isinstance(value, str) else []
    return len(parts) >= 3 and len(value) <= 160 and all(_dns_part(part) for part in parts)


def _dns_part(value: str) -> bool:
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-")
    return (
        bool(value)
        and len(value) <= 63
        and value[0].isalnum()
        and value[-1].isalnum()
        and all(character in allowed for character in value)
    )


def _bounded_id(value: str, maximum: int) -> bool:
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    return (
        isinstance(value, str)
        and 0 < len(value) <= maximum
        and value[0].isalnum()
        and value[-1].isalnum()
        and all(character in allowed for character in value)
    )


def _unique(label: str, values: tuple[str, ...]) -> None:
    if len(values) != len(set(values)):
        raise ActivityValidationError(f"{label} must not contain duplicates")


def _table(container: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = container.get(key)
    if not isinstance(value, dict):
        raise ActivityValidationError(f"{key} must be a table")
    return value


def _tables(
    container: Mapping[str, object], key: str, *, allow_empty: bool
) -> tuple[Mapping[str, object], ...]:
    value = container.get(key, [] if allow_empty else None)
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ActivityValidationError(f"{key} must be an array of tables")
    if not all(isinstance(item, dict) for item in value):
        raise ActivityValidationError(f"{key} must contain only tables")
    return tuple(value)  # type: ignore[arg-type]


def _text(container: Mapping[str, object], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ActivityValidationError(f"{key} must be non-empty text")
    return value.strip()


def _texts(
    container: Mapping[str, object], key: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    value = container.get(key, [] if allow_empty else None)
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ActivityValidationError(f"{key} must be an array of strings")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ActivityValidationError(f"{key} must contain only non-empty strings")
    return tuple(item.strip() for item in value)


def _folded(container: Mapping[str, object], key: str) -> frozenset[str]:
    values = tuple(value.casefold() for value in _texts(container, key, allow_empty=True))
    if len(values) != len(set(values)):
        raise ActivityValidationError(f"{key} must not contain duplicates")
    return frozenset(values)


def _integer(
    container: Mapping[str, object], key: str, minimum: int, maximum: int | None = None
) -> int:
    value = container.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ActivityValidationError(f"{key} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        raise ActivityValidationError(f"{key} is outside its allowed range")
    return value
