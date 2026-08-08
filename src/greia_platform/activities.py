from __future__ import annotations

import ast
import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .trust import ActivitySource, PackageTrust


class ActivityValidationError(ValueError):
    """Raised when an activity violates the platform package contract."""


@dataclass(frozen=True, slots=True)
class SkillContribution:
    skill_id: str
    weight: int


@dataclass(frozen=True, slots=True)
class RewardDefinition:
    reward_id: str
    amount: int


@dataclass(frozen=True, slots=True)
class ActivityManifest:
    activity_id: str
    title_key: str
    version: str
    runtime_type: str
    api_version: str
    entrypoint: Path
    icon_id: str
    categories: tuple[str, ...]
    skills: tuple[SkillContribution, ...]
    rewards: tuple[RewardDefinition, ...]
    difficulty: int
    languages: tuple[str, ...]
    capabilities: tuple[str, ...]
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
    api_version: str
    allowed_import_roots: frozenset[str]
    forbidden_import_roots: frozenset[str]
    forbidden_file_names: frozenset[str]
    forbidden_path_names: frozenset[str]
    forbidden_suffixes: frozenset[str]
    allowed_capabilities: frozenset[str]
    privileged_capabilities: frozenset[str]
    maximum_activity_bytes: int

    @classmethod
    def load(cls, path: Path) -> "RuntimeCatalogue":
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
        runtime = _mapping(raw, "runtime")
        validation = _mapping(raw, "validation")
        capabilities = _mapping(raw, "capabilities")
        catalogue = cls(
            api_version=_string(runtime, "api_version"),
            allowed_import_roots=frozenset(_string_list(runtime, "allowed_import_roots")),
            forbidden_import_roots=frozenset(_string_list(runtime, "forbidden_import_roots")),
            forbidden_file_names=frozenset(name.casefold() for name in _string_list(validation, "forbidden_file_names")),
            forbidden_path_names=frozenset(name.casefold() for name in _string_list(validation, "forbidden_path_names")),
            forbidden_suffixes=frozenset(name.casefold() for name in _string_list(validation, "forbidden_suffixes")),
            allowed_capabilities=frozenset(_string_list(capabilities, "allowed")),
            privileged_capabilities=frozenset(_string_list(capabilities, "privileged")),
            maximum_activity_bytes=_integer(validation, "maximum_activity_bytes", minimum=1),
        )
        import_overlap = catalogue.allowed_import_roots & catalogue.forbidden_import_roots
        if import_overlap:
            raise ActivityValidationError(
                "runtime import roots cannot be both allowed and forbidden: "
                + ", ".join(sorted(import_overlap))
            )
        unknown_privileged = catalogue.privileged_capabilities - catalogue.allowed_capabilities
        if unknown_privileged:
            raise ActivityValidationError(
                "privileged capabilities must also be allowed: "
                + ", ".join(sorted(unknown_privileged))
            )
        return catalogue


class ActivityRegistry:
    """Discovers and validates curated activity packages.

    Phase 0 validates Python-adapter Activity packages against the curated
    platform runtime. The manifest keeps an explicit runtime type so image
    profiles can reason about runtime inclusion without changing Activity-level
    storage/progression/package contracts when more adapters arrive.
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
        registrations = self.discover_registrations()
        return tuple(registration.manifest for registration in registrations)

    def discover_registrations(self) -> tuple[ActivityRegistration, ...]:
        registrations: list[ActivityRegistration] = []
        seen_ids: set[str] = set()
        self._registrations_by_manifest_object.clear()
        for source in self._activity_sources:
            parent = source.root
            if not parent.exists():
                continue
            for manifest_path in sorted(parent.glob("*/activity.toml")):
                registration = self.validate_registration(manifest_path.parent, source)
                manifest = registration.manifest
                if manifest.activity_id in seen_ids:
                    raise ActivityValidationError(
                        f"duplicate activity id: {manifest.activity_id}"
                    )
                seen_ids.add(manifest.activity_id)
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
        """Return a cheap token for activity-folder additions/replacements.

        Full AST/package validation is intentionally not run every two seconds on
        the Atom reference machine. Curated installers should replace activity
        directories atomically; manifest and package-directory mtimes detect that
        contract while preserving hot discovery.
        """

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
                items.append(
                    (
                        manifest.as_posix(),
                        stat.st_mtime_ns,
                        stat.st_size,
                        root_mtime,
                    )
                )
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
        self._validate_manifest(manifest)
        self._validate_python_imports(root)
        return ActivityRegistration(
            manifest=manifest,
            package_digest=package_digest(root),
            package_trust=source.trust,
            source_id=source.source_id,
        )

    def _source_for_root(self, root: Path) -> ActivitySource:
        matches = [
            source
            for source in self._activity_sources
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
        reserved_modules = {name.casefold() for name in self._runtime.allowed_import_roots}
        try:
            top_level = tuple(root.iterdir())
        except OSError as exc:
            raise ActivityValidationError(f"cannot inspect activity package: {exc}") from exc
        for path in top_level:
            module_name = path.name.casefold() if path.is_dir() else path.stem.casefold()
            if module_name in reserved_modules:
                raise ActivityValidationError(
                    f"activity package may not shadow curated module {module_name!r}: {path.name}"
                )
        for path in root.rglob("*"):
            if path.is_symlink():
                raise ActivityValidationError(f"symlinks are forbidden: {path}")
            folded_name = path.name.casefold()
            if folded_name in self._runtime.forbidden_file_names:
                raise ActivityValidationError(f"forbidden package file: {path.name}")
            if path.is_dir() and folded_name in self._runtime.forbidden_path_names:
                raise ActivityValidationError(f"forbidden package directory: {path.name}")
            if path.is_file():
                metadata = path.stat()
                total_bytes += metadata.st_size
                if path.suffix.casefold() in self._runtime.forbidden_suffixes:
                    raise ActivityValidationError(f"bundled executable/dependency archive forbidden: {path}")
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

        skills = tuple(
            SkillContribution(
                skill_id=_string(item, "id"),
                weight=_integer(item, "weight", minimum=1, maximum=10),
            )
            for item in _mapping_list(education, "skills")
        )
        rewards = tuple(
            RewardDefinition(
                reward_id=_string(item, "id"),
                amount=_integer(item, "amount", minimum=0, maximum=1000),
            )
            for item in _mapping_list(education, "rewards")
        )

        return ActivityManifest(
            activity_id=_string(activity, "id"),
            title_key=_string(activity, "title_key"),
            version=_string(activity, "version"),
            runtime_type=_optional_string(runtime, "type", default="python"),
            api_version=_string(runtime, "api_version"),
            entrypoint=Path(_string(runtime, "entrypoint")),
            icon_id=_string(activity, "icon"),
            categories=tuple(_string_list(education, "categories")),
            skills=skills,
            rewards=rewards,
            difficulty=_integer(education, "difficulty", minimum=1, maximum=10),
            languages=tuple(_string_list(activity, "languages")),
            capabilities=tuple(_string_list(runtime, "capabilities")),
            root=root,
        )

    def _validate_manifest(self, manifest: ActivityManifest) -> None:
        if manifest.runtime_type != "python":
            raise ActivityValidationError(
                f"activity {manifest.activity_id} targets runtime {manifest.runtime_type!r}; "
                "the Phase 0 registry implements only the Python adapter"
            )
        if not _is_safe_identifier(manifest.activity_id):
            raise ActivityValidationError(
                "activity.id may contain lowercase ASCII letters, digits, dots, underscores, and hyphens"
            )
        if manifest.api_version != self._runtime.api_version:
            raise ActivityValidationError(
                f"activity {manifest.activity_id} targets API {manifest.api_version}; "
                f"runtime provides {self._runtime.api_version}"
            )
        if manifest.entrypoint.is_absolute() or ".." in manifest.entrypoint.parts:
            raise ActivityValidationError("runtime.entrypoint must be a safe relative path")
        launch_path = manifest.launch_path.resolve()
        if manifest.root not in launch_path.parents:
            raise ActivityValidationError("runtime.entrypoint escapes the activity package")
        if launch_path.suffix != ".py" or not launch_path.is_file():
            raise ActivityValidationError(f"entrypoint is not a Python file: {launch_path}")
        if not manifest.skills:
            raise ActivityValidationError("education.skills must contain at least one skill")
        if not manifest.languages:
            raise ActivityValidationError("activity.languages must not be empty")
        if len(set(manifest.capabilities)) != len(manifest.capabilities):
            raise ActivityValidationError("runtime.capabilities must not contain duplicates")
        unknown = sorted(set(manifest.capabilities) - self._runtime.allowed_capabilities)
        if unknown:
            raise ActivityValidationError(
                "activity requests unknown capabilities: " + ", ".join(unknown)
            )

    def _validate_python_imports(self, root: Path) -> None:
        for path in sorted(root.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (OSError, UnicodeDecodeError, SyntaxError) as exc:
                raise ActivityValidationError(f"cannot parse {path}: {exc}") from exc
            for node in ast.walk(tree):
                root_name: str | None = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self._validate_import_root(alias.name.split(".", 1)[0], path)
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        continue
                    if node.module:
                        root_name = node.module.split(".", 1)[0]
                elif isinstance(node, ast.Call) and _is_dynamic_import_call(node):
                    raise ActivityValidationError(f"dynamic imports are forbidden: {path}:{node.lineno}")
                if root_name:
                    self._validate_import_root(root_name, path)

    def _validate_import_root(self, root_name: str, path: Path) -> None:
        if root_name in self._runtime.forbidden_import_roots:
            raise ActivityValidationError(f"forbidden import {root_name!r} in {path}")
        if root_name not in self._runtime.allowed_import_roots:
            raise ActivityValidationError(
                f"import {root_name!r} is outside the curated child runtime in {path}"
            )


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


def _is_dynamic_import_call(node: ast.Call) -> bool:
    function = node.func
    if isinstance(function, ast.Name):
        return function.id == "__import__"
    if isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name):
        return function.value.id == "importlib" and function.attr in {"import_module", "reload"}
    return False


def _is_safe_identifier(value: str) -> bool:
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    return bool(value) and value[0].isalnum() and all(char in allowed for char in value)


def _mapping(container: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = container.get(key)
    if not isinstance(value, dict):
        raise ActivityValidationError(f"{key} must be a table")
    return value


def _mapping_list(container: Mapping[str, object], key: str) -> tuple[Mapping[str, object], ...]:
    value = container.get(key)
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
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        raise ActivityValidationError(f"{key} must be a non-empty array of strings")
    return tuple(item.strip() for item in value)


def _optional_string(container: Mapping[str, object], key: str, *, default: str) -> str:
    value = container.get(key, default)
    if not isinstance(value, str) or not value:
        raise ActivityValidationError(f"{key} must be a non-empty string")
    return value


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
