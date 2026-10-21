from __future__ import annotations

import ast
import hashlib
import os
import logging
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .creation_media import CreationMediaRegistry, CreationMediaError
from .input_core import InteractionProfile, SUPPORTED_INTERACTION_PROFILES
from .trust import ActivitySource, PackageTrust

logger = logging.getLogger(__name__)


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
    # Optional semantic hints may help Greia form one bounded sub-Collection
    # layer. They never command a filesystem path or create a root destination.
    discovery_tags: tuple[str, ...] = ()
    # Developmental suitability is independent from challenge/difficulty.
    recommended_age_min: int | None = None
    recommended_age_max: int | None = None
    difficulty_min: int | None = None
    difficulty_max: int | None = None
    adaptive_difficulty: bool = False
    # Compatibility declarations are never authorization to browse child files.
    creations_produces: tuple[str, ...] = ()
    creations_consumes: tuple[str, ...] = ()

    @property
    def launch_path(self) -> Path:
        return self.root / self.entrypoint


@dataclass(frozen=True, slots=True)
class ActivityRegistration:
    manifest: ActivityManifest
    package_digest: str
    package_trust: PackageTrust
    source_id: str
    size_bytes: int = 0
    size_guideline_bytes: int = 0

    @property
    def oversize(self) -> bool:
        """True when the package exceeds the size guideline (warning only)."""
        return bool(self.size_guideline_bytes) and self.size_bytes > self.size_guideline_bytes

    def size_notice(self) -> str | None:
        """Human-readable large-Activity notice, or None within the guideline."""
        if not self.oversize:
            return None
        return (
            f"large Activity: {self.size_bytes / 1048576:.1f} MiB "
            f"(over the {self.size_guideline_bytes / 1048576:g} MiB guideline)"
        )


@dataclass(frozen=True, slots=True)
class ActivityCollisionConflict:
    """Structured evidence for one rejected claimant of a colliding identity.

    ``identity`` is the exact colliding canonical ID or legacy-alias string.
    The remaining fields identify the rejected claimant: platform-assigned
    ``source_id``/``package_trust`` (never manifest-claimed), the validated
    ``package_root`` and the validation-time ``package_digest`` carried
    through from index load or live validation (never recomputed here).
    """

    identity: str
    activity_id: str
    source_id: str
    package_trust: PackageTrust
    package_root: Path
    package_digest: str


@dataclass(frozen=True, slots=True)
class ActivityCollisionResolution:
    """Immutable result of the trust-aware degrade resolver.

    ``accepted`` enters the authoritative catalogue/registry; ``rejected``
    never becomes issuable via ``registration_for`` nor launchable.
    ``conflicts`` carries one structured record per rejected claimant per
    colliding identity; ``degraded`` is true when any conflict exists and
    boot must continue degraded instead of crashing.
    """

    accepted: tuple[ActivityRegistration, ...]
    rejected: tuple[ActivityRegistration, ...]
    conflicts: tuple[ActivityCollisionConflict, ...]
    degraded: bool


def resolve_activity_collisions(
    registrations: Sequence[ActivityRegistration],
) -> ActivityCollisionResolution:
    """Resolve cross-source identity/alias collisions without crashing.

    Pure function shared by normal registry discovery, cold-boot indexed
    composition and later rescans. It performs no validation, no digest
    recomputation and no filesystem access; trust comes only from each
    registration's platform-bound ``package_trust``.

    Exact rule: an identity group with exactly one ``BUILT_IN`` claimant
    and every other claimant ``DEVELOPER_UNSIGNED`` accepts the built-in
    and rejects every developer claimant. Any other multi-claimant group
    (parent/developer/developer, multiple built-ins, mixed trusts, ...) is
    ambiguous: every member of that group is rejected and boot continues
    with the remainder. Duplicate identities are never permitted even on
    matching digests; no trust ordering, promotion or shadowing is applied.
    A registration rejected in any identity group is rejected overall.
    The decision never depends on input order.
    """

    claimants: dict[str, list[ActivityRegistration]] = {}
    for registration in registrations:
        manifest = registration.manifest
        for identity in (manifest.activity_id, *manifest.legacy_ids):
            claimants.setdefault(identity, []).append(registration)
    rejected_by_key: dict[int, ActivityRegistration] = {}
    conflicts: list[ActivityCollisionConflict] = []

    def _conflict(
        identity: str, claimant: ActivityRegistration
    ) -> ActivityCollisionConflict:
        return ActivityCollisionConflict(
            identity=identity,
            activity_id=claimant.manifest.activity_id,
            source_id=claimant.source_id,
            package_trust=claimant.package_trust,
            package_root=claimant.manifest.root,
            package_digest=claimant.package_digest,
        )

    for identity in sorted(claimants):
        group_candidates = claimants[identity]
        unique: dict[int, ActivityRegistration] = {}
        for candidate in group_candidates:
            unique.setdefault(id(candidate), candidate)
        group = list(unique.values())
        if len(group) <= 1:
            continue
        built_ins = [
            item for item in group if item.package_trust is PackageTrust.BUILT_IN
        ]
        developers = [
            item
            for item in group
            if item.package_trust is PackageTrust.DEVELOPER_UNSIGNED
        ]
        ordered = sorted(
            group,
            key=lambda item: (
                item.manifest.activity_id,
                item.source_id,
                item.manifest.root.as_posix(),
            ),
        )
        if (
            len(built_ins) == 1
            and len(developers) >= 1
            and len(built_ins) + len(developers) == len(group)
        ):
            for loser in ordered:
                if loser.package_trust is PackageTrust.BUILT_IN:
                    continue
                rejected_by_key.setdefault(id(loser), loser)
                conflicts.append(_conflict(identity, loser))
        else:
            for loser in ordered:
                rejected_by_key.setdefault(id(loser), loser)
                conflicts.append(_conflict(identity, loser))
    accepted = tuple(item for item in registrations if id(item) not in rejected_by_key)
    rejected = tuple(item for item in registrations if id(item) in rejected_by_key)
    return ActivityCollisionResolution(
        accepted=accepted,
        rejected=rejected,
        conflicts=tuple(conflicts),
        degraded=bool(conflicts),
    )


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
    def default_safe(cls) -> "RuntimeCatalogue":
        """Built-in immutable fallback policy used if on-disk config is empty or unreadable."""
        return cls(
            api_version="0.1",
            forbidden_file_names=frozenset({".ds_store", "thumbs.db"}),
            forbidden_path_names=frozenset(
                {".git", ".hg", ".svn", "node_modules", "vendor", "vendored"}
            ),
            forbidden_suffixes=frozenset({
                ".app",
                ".bash",
                ".bin",
                ".class",
                ".dll",
                ".dylib",
                ".exe",
                ".jar",
                ".run",
                ".sh",
                ".so",
                ".tar",
                ".zip",
            }),
            allowed_capabilities=frozenset({
                "audio.basic",
                "controller",
                "display",
                "keyboard",
                "network",
                "pointer",
                "power.controlled_shutdown",
                "removable_media",
                "touch",
            }),
            allowed_permissions=frozenset({
                "customization.manage",
                "profile.manage_own",
                "removable_media.read",
            }),
            maximum_activity_bytes=67108864,
        )

    @classmethod
    def load(cls, path: Path) -> "RuntimeCatalogue":
        try:
            if not path.is_file() or path.stat().st_size == 0:
                logger.warning(
                    "Runtime catalogue %s is missing or empty; using default safe policy",
                    path,
                )
                return cls.default_safe()
            with path.open("rb") as handle:
                raw = tomllib.load(handle)
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
        except Exception as exc:
            logger.warning(
                "Failed loading runtime catalogue %s: %s; falling back to default safe policy",
                path,
                exc,
            )
            return cls.default_safe()


class ActivityRegistry:
    """Runtime-neutral Activity discovery and package validation."""

    def __init__(
        self,
        activity_roots: Sequence[Path | ActivitySource],
        runtime: RuntimeCatalogue,
        *,
        fail_closed: bool = True,
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
        self._fail_closed = fail_closed
        self._issued: dict[int, ActivityRegistration] = {}
        self._unvalidated_activities: dict[str, str] = {}
        self._rejected_registrations: tuple[ActivityRegistration, ...] = ()
        self._collision_conflicts: tuple[ActivityCollisionConflict, ...] = ()
        self._collision_degraded: bool = False

    @property
    def unvalidated_activities(self) -> Mapping[str, str]:
        """Maps skipped activity root paths to their validation error message."""
        return dict(self._unvalidated_activities)

    @property
    def rejected_registrations(self) -> tuple[ActivityRegistration, ...]:
        """Registrations rejected by the trust-aware collision resolver."""
        return self._rejected_registrations

    @property
    def collision_conflicts(self) -> tuple[ActivityCollisionConflict, ...]:
        """Structured conflict evidence from the last discovery."""
        return self._collision_conflicts

    @property
    def collision_degraded(self) -> bool:
        """Whether the last discovery resolved any identity collision."""
        return self._collision_degraded

    def discover(self, *, fail_closed: bool | None = None) -> tuple[ActivityManifest, ...]:
        return tuple(item.manifest for item in self.discover_registrations(fail_closed=fail_closed))

    def discover_registrations(
        self, *, fail_closed: bool | None = None
    ) -> tuple[ActivityRegistration, ...]:
        strict = self._fail_closed if fail_closed is None else bool(fail_closed)
        collected: list[ActivityRegistration] = []
        self._issued.clear()
        self._unvalidated_activities.clear()
        self._rejected_registrations = ()
        self._collision_conflicts = ()
        self._collision_degraded = False
        for source in self._sources:
            if not source.root.exists():
                continue
            for path in sorted(source.root.glob("*/activity.toml")):
                try:
                    registration = self.validate_registration(path.parent, source)
                    collected.append(registration)
                except Exception as exc:
                    if strict:
                        raise
                    logger.warning(
                        "Skipping invalid/corrupted activity package at %s: %s",
                        path.parent,
                        exc,
                    )
                    self._unvalidated_activities[str(path.parent.resolve())] = str(exc)
                    continue
        # Degrade, don't crash (B04): non-strict discovery resolves
        # identity/alias collisions through the shared pure resolver.
        # Strict discovery preserves fail-closed collision errors so
        # single-source validation, Parent strict loads and the
        # developer-control resolution path keep their hard guarantees;
        # composed boot handles cross-source collisions via the resolver
        # directly (see compose_boot_content) and Parent load damage is
        # still omitted as parent_degraded there.
        if strict:
            identities: dict[str, str] = {}
            registrations: list[ActivityRegistration] = []
            for registration in collected:
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
        resolution = resolve_activity_collisions(tuple(collected))
        for registration in resolution.accepted:
            self._issued[id(registration.manifest)] = registration
        self._rejected_registrations = resolution.rejected
        self._collision_conflicts = resolution.conflicts
        self._collision_degraded = resolution.degraded
        return resolution.accepted

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
        digest, size_bytes = self._validated_tree_digest(root)
        manifest = self._parse_manifest(root)
        self._validate_manifest(manifest, configured)
        registration = ActivityRegistration(
            manifest=manifest,
            package_digest=digest,
            package_trust=configured.trust,
            source_id=configured.source_id,
            size_bytes=size_bytes,
            size_guideline_bytes=self._runtime.maximum_activity_bytes,
        )
        notice = registration.size_notice()
        if notice is not None:
            logger.warning("%s: %s", manifest.activity_id, notice)
        return registration

    def _validated_tree_digest(self, root: Path) -> tuple[str, int]:
        """Tree validation + package digest, reused while the tree is unchanged.

        Every discovery (Parent catalogue, policy, system status, launcher)
        re-validates every package: an ``ast.parse`` of each Python file plus a
        SHA-256 of every byte. On the Atom N270 reference floor that is ~25 s
        for the built-in catalogue and it serialises the single-threaded Parent
        API. The result is memoised per (package root, runtime tree policy)
        against a stat fingerprint of every entry (see ``_tree_fingerprint``);
        any change re-runs the full validation. Failures are never cached.
        """
        runtime = self._runtime
        policy = (
            tuple(sorted(runtime.forbidden_path_names)),
            tuple(sorted(runtime.forbidden_file_names)),
            tuple(sorted(runtime.forbidden_suffixes)),
            runtime.maximum_activity_bytes,
        )
        key = (str(root), policy)
        fingerprint = _tree_fingerprint(root)
        cached = _validated_tree_cache.get(key)
        if cached is not None and cached[0] == fingerprint:
            return cached[1], cached[2]
        total = self._validate_tree(root)
        if not isinstance(total, int):
            total = 0
        digest = package_digest(root)
        if key not in _validated_tree_cache and len(_validated_tree_cache) >= _VALIDATED_TREE_CACHE_LIMIT:
            _validated_tree_cache.pop(next(iter(_validated_tree_cache)))
        _validated_tree_cache[key] = (fingerprint, digest, total)
        return digest, total

    def _source_for(self, root: Path) -> ActivitySource:
        matches = [
            source for source in self._sources
            if root == source.root or source.root in root.parents
        ]
        if not matches:
            raise ActivityValidationError(f"activity is outside configured roots: {root}")
        return max(matches, key=lambda item: len(item.root.parts))

    def _validate_tree(self, root: Path) -> int:
        """Validate the tree and return its byte total (size is advisory)."""
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
            # Every packaged Python file must at least be parseable. Import
            # policy stays a runtime-layer concern; this catches syntactically
            # broken sources at packaging/validation time instead of as a
            # launch-time failure on the device.
            if path.suffix.casefold() == ".py":
                try:
                    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                except (OSError, UnicodeDecodeError, SyntaxError) as exc:
                    raise ActivityValidationError(
                        f"cannot parse Python source {path}: {exc}"
                    ) from exc
        # Owner decision 2026-10-21: the size limit is a guideline. Exceeding it
        # is reported through ActivityRegistration.size_notice(), never refused.
        return total

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
        creations = raw.get("creations", {})
        if not isinstance(creations, dict):
            raise ActivityValidationError("creations must be a table")

        raw_presentation = raw.get("presentation")
        if raw_presentation is None:
            launcher_categories: tuple[str, ...] = ()
            discovery_tags: tuple[str, ...] = ()
        elif isinstance(raw_presentation, dict):
            launcher_categories = _texts(raw_presentation, "categories")
            discovery_tags = _texts(
                raw_presentation, "discovery_tags", allow_empty=True
            )
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
            creations_produces=_texts(creations, "produces", allow_empty=True, scope="creations."),
            creations_consumes=_texts(creations, "consumes", allow_empty=True, scope="creations."),
            root=root,
            input_profile=input_profile,
            launcher_categories=launcher_categories,
            discovery_tags=discovery_tags,
            recommended_age_min=_optional_integer(
                education, "recommended_age_min", 1, 18
            ),
            recommended_age_max=_optional_integer(
                education, "recommended_age_max", 1, 18
            ),
            difficulty_min=_optional_integer(education, "difficulty_min", 1, 10),
            difficulty_max=_optional_integer(education, "difficulty_max", 1, 10),
            adaptive_difficulty=_optional_boolean(
                education, "adaptive_difficulty", default=False
            ),
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
        _unique("presentation.discovery_tags", manifest.discovery_tags)
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
        if len(manifest.discovery_tags) > 8:
            raise ActivityValidationError(
                "presentation.discovery_tags may contain at most eight semantic hints"
            )
        if any(not _bounded_id(value, 64) for value in manifest.discovery_tags):
            raise ActivityValidationError(
                "presentation.discovery_tags contains an invalid semantic hint"
            )
        if (
            manifest.recommended_age_min is not None
            and manifest.recommended_age_max is not None
            and manifest.recommended_age_min > manifest.recommended_age_max
        ):
            raise ActivityValidationError(
                "education.recommended_age_min must not exceed recommended_age_max"
            )
        difficulty_range = (manifest.difficulty_min, manifest.difficulty_max)
        if (difficulty_range[0] is None) != (difficulty_range[1] is None):
            raise ActivityValidationError(
                "education.difficulty_min and difficulty_max must be declared together"
            )
        if manifest.adaptive_difficulty and difficulty_range[0] is None:
            raise ActivityValidationError(
                "education.adaptive_difficulty requires difficulty_min and difficulty_max"
            )
        if not manifest.adaptive_difficulty and difficulty_range[0] is not None:
            raise ActivityValidationError(
                "education difficulty range requires adaptive_difficulty = true"
            )
        if difficulty_range[0] is not None and difficulty_range[1] is not None:
            if difficulty_range[0] > difficulty_range[1]:
                raise ActivityValidationError(
                    "education.difficulty_min must not exceed difficulty_max"
                )
            if not difficulty_range[0] <= manifest.difficulty <= difficulty_range[1]:
                raise ActivityValidationError(
                    "education.difficulty must fall inside the adaptive difficulty range"
                )
        _unique("education.skills ids", tuple(item.skill_id for item in manifest.skills))
        _unique("education.events ids", tuple(item.event_id for item in manifest.events))
        _unique("requirements.required_capabilities", manifest.required_capabilities)
        _unique("requirements.optional_capabilities", manifest.optional_capabilities)
        _unique("permissions.requested", manifest.requested_permissions)
        _unique("creations.produces", manifest.creations_produces)
        _unique("creations.consumes", manifest.creations_consumes)
        for direction, declared in (
            ("produces", manifest.creations_produces),
            ("consumes", manifest.creations_consumes),
        ):
            if len(declared) > 8:
                raise ActivityValidationError(f"creations.{direction} exceeds eight types")
            for media_type in declared:
                try:
                    CreationMediaRegistry().codec_for(media_type)
                except CreationMediaError as exc:
                    raise ActivityValidationError(
                        f"creations.{direction} uses unsupported media type {media_type!r}"
                    ) from exc

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


_VALIDATED_TREE_CACHE_LIMIT = 256
_validated_tree_cache: dict[tuple[str, tuple[object, ...]], tuple[tuple[tuple[object, ...], ...], str, int]] = {}


def clear_activity_validation_cache() -> None:
    """Forget memoised tree validations (tests that observe cold validation)."""
    _validated_tree_cache.clear()


def _tree_fingerprint(root: Path) -> tuple[tuple[object, ...], ...]:
    """Cheap identity of a package tree: every entry's relative path, type,
    size, mtime_ns, ctime_ns and inode (``os.scandir``; symlinks not followed).
    A content rewrite that preserves size and mtime still moves ctime, which
    unprivileged code cannot set."""
    base = str(root)
    prefix = len(base) + 1
    items: list[tuple[object, ...]] = []
    stack = [base]
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                stat = entry.stat(follow_symlinks=False)
                kind = "l" if entry.is_symlink() else "d" if entry.is_dir(follow_symlinks=False) else "f"
                items.append(
                    (entry.path[prefix:], kind, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino)
                )
                if kind == "d":
                    stack.append(entry.path)
    items.sort()
    return tuple(items)


def package_tree_fingerprint(root: Path) -> tuple[tuple[object, ...], ...]:
    """Public stat-only change detector for a package tree (no content read).

    Used as a cache key by memoised validations (the registry tree cache here
    and the launcher's ``LaunchValidationCache``): any differing entry means
    the full validation runs again. Not an integrity check.
    """
    return _tree_fingerprint(root)


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
    container: Mapping[str, object],
    key: str,
    *,
    allow_empty: bool = False,
    scope: str = "",
) -> tuple[str, ...]:
    """Read a string array; ``scope`` names the owning table in the error."""

    value = container.get(key, [] if allow_empty else None)
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ActivityValidationError(f"{scope}{key} must be an array of strings")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ActivityValidationError(f"{scope}{key} must contain only non-empty strings")
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


def _optional_integer(
    container: Mapping[str, object], key: str, minimum: int, maximum: int | None = None
) -> int | None:
    if key not in container:
        return None
    return _integer(container, key, minimum, maximum)


def _optional_boolean(
    container: Mapping[str, object], key: str, *, default: bool
) -> bool:
    value = container.get(key, default)
    if not isinstance(value, bool):
        raise ActivityValidationError(f"{key} must be a boolean")
    return value