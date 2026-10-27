"""Format, bounded inspection and deterministic building for ``.greia_update``.

This module owns package bytes and their typed manifest only.  It does not
install files, choose trust, publish generations or activate a child session.
The privileged updater revalidates each declared component before apply.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import tempfile
import zipfile
from string import Formatter
from types import SimpleNamespace
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

from .activity_package_format import ACTIVITY_PACKAGE_EXTENSION
from .localization import LocaleTag, LocalizationError
from .system_updates import (
    MAX_BUNDLE_BYTES,
    UpdateBundleError,
    inspect_update_bundle_archive,
)


SOFTWARE_UPDATE_EXTENSION = ".greia_update"
SOFTWARE_UPDATE_MEDIA_TYPE = "application/vnd.greia.software-update+zip"
SOFTWARE_UPDATE_MANIFEST = "manifest.json"
SOFTWARE_UPDATE_SCHEMA_VERSION = 1
MAX_SOFTWARE_UPDATE_BYTES = MAX_BUNDLE_BYTES + 1024 * 1024
MAX_SOFTWARE_UPDATE_MANIFEST_BYTES = 1024 * 1024
MAX_SOFTWARE_UPDATE_ENTRIES = 8192
MAX_PYTHON_FILES = 4096
MAX_PYTHON_FILE_BYTES = 32 * 1024 * 1024
MAX_PYTHON_TOTAL_BYTES = 256 * 1024 * 1024
MAX_LANGUAGE_MANIFEST_BYTES = 4096
MAX_LANGUAGE_UI_BYTES = 256 * 1024
MAX_LANGUAGE_RESOURCE_LOCALES = 32
MAX_ACTIVITY_PACKAGE_BYTES = 128 * 1024 * 1024
MAX_ACTIVITY_TOTAL_BYTES = 1536 * 1024 * 1024
MAX_ACTIVITY_PACKAGES = 64
MAX_ACTIVITY_ENTRIES = 4096
MAX_ACTIVITY_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_PATH_CHARACTERS = 220
MAX_COMPRESSION_RATIO = 200
COPY_CHUNK_BYTES = 1024 * 1024
_DETERMINISTIC_ZIP_DATE = (1980, 1, 1, 0, 0, 0)
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# The application generation is the production Python closure. The simulator
# is development-only; native sources, tools, tests and arbitrary source-root
# files are intentionally not package destinations.
PYTHON_SOURCE_ROOTS = (
    "src/greia_platform/",
    "src/greia_launcher/",
    "src/greia_parent/",
    "src/greia_installer/",
)
PYTHON_RUNTIME_ALLOWLIST = frozenset(
    {
        "runtime/achievement-policy.toml",
        "runtime/activity-launch.toml",
        "runtime/alsa/greia-activity-capture.conf",
        "runtime/alsa/greia-activity-overrides.conf",
        "runtime/audio-settings.toml",
        "runtime/child-runtime.toml",
        "runtime/hardware-settings.toml",
        "runtime/history-policy.toml",
        "runtime/permission-policy.toml",
        "runtime/profile-defaults.toml",
        "runtime/progression-policy.toml",
        "runtime/storage-policy.toml",
        "runtime/theme-defaults.toml",
    }
)
# These paths must be present even if a source traversal reports success. They
# are the minimum launch/update route that must survive a Python snapshot.
# The entire four-tree closure is packaged; this guard catches accidental
# changes to the roots or omissions of newly critical entrypoints.
REQUIRED_PYTHON_ENTRYPOINTS = frozenset(
    {
        "src/greia_launcher/main.py",
        "src/greia_parent/production_api.py",
        "src/greia_parent/update_api.py",
        "src/greia_parent/protocol.py",
        "src/greia_platform/software_update_apply.py",
        "src/greia_platform/software_update_jobs.py",
        "src/greia_platform/software_update_generation.py",
        "src/greia_platform/software_update_package.py",
        "src/greia_platform/software_update_package_builder.py",
        "src/greia_platform/update_client.py",
        "src/greia_platform/update_privileged.py",
        "src/greia_platform/system_updates.py",
        "src/greia_platform/update_activation.py",
        "src/greia_platform/boot_transaction.py",
        "src/greia_platform/boot_markers.py",
        "src/greia_platform/activity_packages.py",
        "src/greia_platform/activity_package_format.py",
        "src/greia_platform/activity_index.py",
        "src/greia_platform/activities.py",
        "src/greia_platform/profiles.py",
    }
)
_TARGET_FIELDS = ("profile", "platform_family", "architecture", "board")


class SoftwareUpdatePackageError(ValueError):
    """A software-update archive or its manifest is outside the v1 contract."""


class SoftwareUpdateType(StrEnum):
    PYTHON_PLATFORM = "python_platform"
    ACTIVITIES = "activities"
    COMBINED = "combined"
    FULL_SYSTEM = "full_system"


class ActivityUpdateScope(StrEnum):
    ONE = "one"
    SET = "set"
    ALL = "all"


class ActivityPackageSource(StrEnum):
    BUILT_IN = "built_in"
    PARENT = "parent"


@dataclass(frozen=True, slots=True)
class SoftwareUpdateTarget:
    """Optional exact identity selector; omitted fields impose no restriction."""

    profile: str | None = None
    platform_family: str | None = None
    architecture: str | None = None
    board: str | None = None

    def matches(self, identity: Mapping[str, object]) -> bool:
        """Return whether every declared identity fact exactly matches."""

        return all(
            expected is None or identity.get(name) == expected
            for name, expected in (
                ("profile", self.profile),
                ("platform_family", self.platform_family),
                ("architecture", self.architecture),
                ("board", self.board),
            )
        )

    def as_json_dict(self) -> dict[str, str]:
        return {
            name: value
            for name, value in (
                ("profile", self.profile),
                ("platform_family", self.platform_family),
                ("architecture", self.architecture),
                ("board", self.board),
            )
            if value is not None
        }


@dataclass(frozen=True, slots=True)
class SoftwareUpdatePythonFile:
    """One file in the complete allowlisted Python/runtime snapshot."""

    path: str
    member: str
    size: int
    sha256: str

    def as_json_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "member": self.member,
            "size": self.size,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class SoftwareUpdateActivity:
    """One complete existing ``.greiaactivity`` archive in the update."""

    activity_id: str
    version: str
    member: str
    size: int
    sha256: str

    def as_json_dict(self) -> dict[str, object]:
        return {
            "activity_id": self.activity_id,
            "version": self.version,
            "member": self.member,
            "size": self.size,
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class SoftwareUpdateMember:
    """A bounded nested existing v3 system-update bundle."""

    member: str
    size: int
    sha256: str

    def as_json_dict(self) -> dict[str, object]:
        return {"member": self.member, "size": self.size, "sha256": self.sha256}


@dataclass(frozen=True, slots=True)
class SoftwareUpdatePackageManifest:
    """Typed v1 package manifest with no caller-selected filesystem roots."""

    type: SoftwareUpdateType
    version: str
    release_id: str
    targets: tuple[SoftwareUpdateTarget, ...] = ()
    python_files: tuple[SoftwareUpdatePythonFile, ...] = ()
    activity_scope: ActivityUpdateScope | None = None
    activity_source: ActivityPackageSource | None = None
    activity_items: tuple[SoftwareUpdateActivity, ...] = ()
    full_system: SoftwareUpdateMember | None = None
    schema_version: int = SOFTWARE_UPDATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _validate_manifest(self)

    def as_json_dict(self) -> dict[str, object]:
        raw: dict[str, object] = {
            "schema_version": self.schema_version,
            "type": self.type.value,
            "version": self.version,
            "release_id": self.release_id,
        }
        if self.type is not SoftwareUpdateType.FULL_SYSTEM:
            raw["targets"] = [target.as_json_dict() for target in self.targets]
        if self.type in (SoftwareUpdateType.PYTHON_PLATFORM, SoftwareUpdateType.COMBINED):
            raw["python_platform"] = {
                "files": [item.as_json_dict() for item in self.python_files]
            }
        if self.type in (SoftwareUpdateType.ACTIVITIES, SoftwareUpdateType.COMBINED):
            raw["activities"] = {
                "scope": self.activity_scope.value if self.activity_scope else None,
                "source": self.activity_source.value if self.activity_source else None,
                "items": [item.as_json_dict() for item in self.activity_items],
            }
        if self.type is SoftwareUpdateType.FULL_SYSTEM and self.full_system is not None:
            raw["full_system"] = self.full_system.as_json_dict()
        return raw

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.as_json_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    @classmethod
    def from_json_dict(cls, raw: object) -> "SoftwareUpdatePackageManifest":
        if not isinstance(raw, dict):
            raise SoftwareUpdatePackageError("manifest must be a JSON object")
        schema = raw.get("schema_version")
        if isinstance(schema, bool) or schema != SOFTWARE_UPDATE_SCHEMA_VERSION:
            raise SoftwareUpdatePackageError("unsupported software-update schema")
        try:
            package_type = SoftwareUpdateType(raw.get("type"))
        except (ValueError, TypeError) as exc:
            raise SoftwareUpdatePackageError("unsupported software-update type") from exc
        common = {"schema_version", "type", "version", "release_id"}
        if package_type is not SoftwareUpdateType.FULL_SYSTEM:
            common.add("targets")
        expected = set(common)
        if package_type in (SoftwareUpdateType.PYTHON_PLATFORM, SoftwareUpdateType.COMBINED):
            expected.add("python_platform")
        if package_type in (SoftwareUpdateType.ACTIVITIES, SoftwareUpdateType.COMBINED):
            expected.add("activities")
        if package_type is SoftwareUpdateType.FULL_SYSTEM:
            expected.add("full_system")
        if set(raw) != expected:
            raise SoftwareUpdatePackageError("manifest fields do not match package type")

        targets: tuple[SoftwareUpdateTarget, ...] = ()
        if package_type is not SoftwareUpdateType.FULL_SYSTEM:
            target_values = raw.get("targets", [])
            if not isinstance(target_values, list) or len(target_values) > 16:
                raise SoftwareUpdatePackageError("targets must be a bounded array")
            targets = tuple(_parse_target(item) for item in target_values)

        python_files: tuple[SoftwareUpdatePythonFile, ...] = ()
        if package_type in (SoftwareUpdateType.PYTHON_PLATFORM, SoftwareUpdateType.COMBINED):
            component = raw.get("python_platform")
            if not isinstance(component, dict) or set(component) != {"files"}:
                raise SoftwareUpdatePackageError("python_platform fields are invalid")
            entries = component.get("files")
            if not isinstance(entries, list) or not entries or len(entries) > MAX_PYTHON_FILES:
                raise SoftwareUpdatePackageError("python_platform files are outside Greia bounds")
            python_files = tuple(_parse_python_file(item) for item in entries)

        scope: ActivityUpdateScope | None = None
        source: ActivityPackageSource | None = None
        activity_items: tuple[SoftwareUpdateActivity, ...] = ()
        if package_type in (SoftwareUpdateType.ACTIVITIES, SoftwareUpdateType.COMBINED):
            component = raw.get("activities")
            if not isinstance(component, dict) or set(component) != {"scope", "source", "items"}:
                raise SoftwareUpdatePackageError("activities fields are invalid")
            try:
                scope = ActivityUpdateScope(component.get("scope"))
                source = ActivityPackageSource(component.get("source"))
            except (ValueError, TypeError) as exc:
                raise SoftwareUpdatePackageError("activity scope or source is invalid") from exc
            items = component.get("items")
            if not isinstance(items, list) or not items or len(items) > MAX_ACTIVITY_PACKAGES:
                raise SoftwareUpdatePackageError("activity items are outside Greia bounds")
            activity_items = tuple(_parse_activity(item) for item in items)

        full_system: SoftwareUpdateMember | None = None
        if package_type is SoftwareUpdateType.FULL_SYSTEM:
            full_system = _parse_member(raw.get("full_system"))
        return cls(
            type=package_type,
            version=_text(raw.get("version"), "version", 64),
            release_id=_identifier(raw.get("release_id"), "release_id", 96),
            targets=targets,
            python_files=python_files,
            activity_scope=scope,
            activity_source=source,
            activity_items=activity_items,
            full_system=full_system,
            schema_version=schema,
        )

    def matches_identity(self, identity: Mapping[str, object]) -> bool:
        """App packages with no targets are portable across curated platforms."""

        if self.type is SoftwareUpdateType.FULL_SYSTEM:
            return True
        return not self.targets or any(target.matches(identity) for target in self.targets)


@dataclass(frozen=True, slots=True)
class InspectedSoftwareUpdatePackage:
    """Validated typed manifest and whole-file facts for an outer package."""

    manifest: SoftwareUpdatePackageManifest
    package_sha256: str
    package_size: int


@dataclass(frozen=True, slots=True)
class ActivityPackageInput:
    """Builder input for an existing complete Activity archive."""

    activity_id: str
    path: Path


def ensure_software_update_filename(value: str | Path) -> Path:
    """Return a path ending in Greia's canonical software-update extension."""

    path = Path(value)
    if path.name.casefold().endswith(SOFTWARE_UPDATE_EXTENSION):
        return path
    if path.suffix.casefold() == ".zip":
        return path.with_suffix(SOFTWARE_UPDATE_EXTENSION)
    return path.with_name(path.name + SOFTWARE_UPDATE_EXTENSION)


def build_software_update_package(
    output_path: Path,
    *,
    version: str | None = None,
    release_id: str | None = None,
    python_source_root: Path | None = None,
    activity_packages: Sequence[ActivityPackageInput] = (),
    activity_scope: ActivityUpdateScope | str | None = None,
    activity_source: ActivityPackageSource | str | None = None,
    full_system_bundle: Path | None = None,
    targets: Sequence[SoftwareUpdateTarget] = (),
    approved_activity_ids: frozenset[str] | None = None,
    runtime_path: Path | None = None,
) -> SoftwareUpdatePackageManifest:
    """Build a deterministic package through the focused authoring module."""

    from .software_update_package_builder import build_software_update_package as build

    return build(
        output_path,
        version=version,
        release_id=release_id,
        python_source_root=python_source_root,
        activity_packages=activity_packages,
        activity_scope=activity_scope,
        activity_source=activity_source,
        full_system_bundle=full_system_bundle,
        targets=targets,
        approved_activity_ids=approved_activity_ids,
        runtime_path=runtime_path,
    )


def inspect_software_update_package(
    path: Path, *, runtime_path: Path | None = None
) -> InspectedSoftwareUpdatePackage:
    """Stream and validate the complete outer ZIP and all declared payload hashes."""

    package_path = Path(path)
    _require_regular_source(package_path, MAX_SOFTWARE_UPDATE_BYTES)
    package_size = package_path.stat().st_size
    try:
        with zipfile.ZipFile(package_path, "r", allowZip64=True) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > MAX_SOFTWARE_UPDATE_ENTRIES:
                raise SoftwareUpdatePackageError("package entry count is outside Greia bounds")
            _validate_outer_zip_infos(infos)
            if infos[0].filename != SOFTWARE_UPDATE_MANIFEST:
                raise SoftwareUpdatePackageError("manifest.json must be the first package member")
            manifest_info = infos[0]
            if not 0 < manifest_info.file_size <= MAX_SOFTWARE_UPDATE_MANIFEST_BYTES:
                raise SoftwareUpdatePackageError("manifest size is outside Greia bounds")
            manifest_raw = _read_bounded(archive, SOFTWARE_UPDATE_MANIFEST, MAX_SOFTWARE_UPDATE_MANIFEST_BYTES)
            try:
                raw = json.loads(manifest_raw.decode("utf-8"), object_pairs_hook=_unique_object)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise SoftwareUpdatePackageError("manifest is not valid unique-key JSON") from exc
            manifest = SoftwareUpdatePackageManifest.from_json_dict(raw)
            if manifest_raw != manifest.canonical_bytes():
                raise SoftwareUpdatePackageError("manifest is not canonical JSON")
            expected_members = [SOFTWARE_UPDATE_MANIFEST, *_manifest_members(manifest)]
            if [item.filename for item in infos] != expected_members:
                raise SoftwareUpdatePackageError("package members do not match manifest order")
            _validate_declared_member_sizes(archive, manifest)
            _verify_all_digests(archive, manifest)
            _validate_language_resources(archive, manifest)
            for activity in manifest.activity_items:
                assert manifest.activity_source is not None
                _validate_nested_activity(
                    archive,
                    activity,
                    manifest.activity_source,
                    runtime_path or _default_runtime_path(),
                )
            if manifest.full_system is not None:
                _validate_nested_system_manifest(archive, manifest)
    except (zipfile.BadZipFile, OSError, EOFError) as exc:
        raise SoftwareUpdatePackageError("software-update archive is unreadable") from exc
    digest = _hash_file(package_path, MAX_SOFTWARE_UPDATE_BYTES)
    return InspectedSoftwareUpdatePackage(manifest, digest, package_size)


def _default_runtime_path() -> Path:
    """Resolve the runtime policy paired with this installed source tree."""

    return Path(__file__).resolve().parents[2] / "runtime" / "child-runtime.toml"


def _validate_manifest(manifest: SoftwareUpdatePackageManifest) -> None:
    if manifest.schema_version != SOFTWARE_UPDATE_SCHEMA_VERSION:
        raise SoftwareUpdatePackageError("unsupported software-update schema")
    _text(manifest.version, "version", 64)
    _identifier(manifest.release_id, "release_id", 96)
    if manifest.type is SoftwareUpdateType.FULL_SYSTEM:
        if manifest.targets or manifest.python_files or manifest.activity_items or manifest.full_system is None:
            raise SoftwareUpdatePackageError("full_system manifest components are invalid")
        if manifest.activity_scope is not None or manifest.activity_source is not None:
            raise SoftwareUpdatePackageError("full_system cannot declare Activity facts")
        return
    if manifest.full_system is not None:
        raise SoftwareUpdatePackageError("application packages cannot contain a full-system bundle")
    if len(manifest.targets) > 16:
        raise SoftwareUpdatePackageError("too many target selectors")
    target_values = [tuple(sorted(target.as_json_dict().items())) for target in manifest.targets]
    if len(target_values) != len(set(target_values)):
        raise SoftwareUpdatePackageError("duplicate target selectors")
    for target in manifest.targets:
        _validate_target(target)
    if manifest.type in (SoftwareUpdateType.PYTHON_PLATFORM, SoftwareUpdateType.COMBINED):
        if not manifest.python_files or len(manifest.python_files) > MAX_PYTHON_FILES:
            raise SoftwareUpdatePackageError("Python file list is outside Greia bounds")
        paths = [item.path for item in manifest.python_files]
        if len(paths) != len(set(paths)):
            raise SoftwareUpdatePackageError("duplicate Python destination path")
        members = [item.member for item in manifest.python_files]
        if len(members) != len(set(members)):
            raise SoftwareUpdatePackageError("duplicate Python archive member")
        total = 0
        for item in manifest.python_files:
            _validate_python_file(item)
            total += item.size
        if total > MAX_PYTHON_TOTAL_BYTES:
            raise SoftwareUpdatePackageError("Python payload exceeds Greia bounds")
    elif manifest.python_files:
        raise SoftwareUpdatePackageError("activities package cannot contain Python files")
    if manifest.type in (SoftwareUpdateType.ACTIVITIES, SoftwareUpdateType.COMBINED):
        if manifest.activity_scope is None or manifest.activity_source is None:
            raise SoftwareUpdatePackageError("Activities package requires scope and source")
        if not manifest.activity_items or len(manifest.activity_items) > MAX_ACTIVITY_PACKAGES:
            raise SoftwareUpdatePackageError("Activity list is outside Greia bounds")
        if manifest.type is SoftwareUpdateType.COMBINED and manifest.activity_source is not ActivityPackageSource.BUILT_IN:
            raise SoftwareUpdatePackageError("combined packages may only update built-in Activities")
        ids = [item.activity_id for item in manifest.activity_items]
        if len(ids) != len(set(ids)):
            raise SoftwareUpdatePackageError("duplicate Activity id")
        if manifest.activity_scope is ActivityUpdateScope.ONE and len(ids) != 1:
            raise SoftwareUpdatePackageError("one scope must list exactly one Activity")
        if manifest.activity_scope is ActivityUpdateScope.SET and len(ids) < 2:
            raise SoftwareUpdatePackageError("set scope must list at least two Activities")
        total = 0
        for item in manifest.activity_items:
            _validate_activity_record(item)
            total += item.size
        if total > MAX_ACTIVITY_TOTAL_BYTES:
            raise SoftwareUpdatePackageError("Activity payload exceeds Greia bounds")
    elif manifest.activity_items or manifest.activity_scope is not None or manifest.activity_source is not None:
        raise SoftwareUpdatePackageError("Python-only package cannot contain Activity facts")
    if manifest.type is SoftwareUpdateType.COMBINED and (
        not manifest.python_files or not manifest.activity_items
    ):
        raise SoftwareUpdatePackageError("combined package requires Python and Activity components")


def _parse_target(value: object) -> SoftwareUpdateTarget:
    if not isinstance(value, dict) or not value or set(value) - set(_TARGET_FIELDS):
        raise SoftwareUpdatePackageError("target selector has unknown or missing fields")
    kwargs = {
        name: _identifier(value[name], name, _target_limit(name))
        for name in _TARGET_FIELDS
        if name in value
    }
    target = SoftwareUpdateTarget(**kwargs)
    _validate_target(target)
    return target


def _validate_target(target: SoftwareUpdateTarget) -> None:
    values = target.as_json_dict()
    if not values:
        raise SoftwareUpdatePackageError("target selector must constrain one identity field")
    for name, value in values.items():
        _identifier(value, name, _target_limit(name))


def _parse_python_file(value: object) -> SoftwareUpdatePythonFile:
    if not isinstance(value, dict) or set(value) != {"path", "member", "size", "sha256"}:
        raise SoftwareUpdatePackageError("Python file descriptor fields are invalid")
    item = SoftwareUpdatePythonFile(
        path=_package_path(value.get("path")),
        member=_archive_path(value.get("member")),
        size=_nonnegative_integer(value.get("size"), "Python file size"),
        sha256=_digest(value.get("sha256")),
    )
    _validate_python_file(item)
    return item


def _validate_python_file(item: SoftwareUpdatePythonFile) -> None:
    _package_path(item.path)
    if item.member != f"python/{item.path}":
        raise SoftwareUpdatePackageError("Python archive member does not match fixed destination")
    maximum = (
        MAX_LANGUAGE_MANIFEST_BYTES if item.path.endswith("/manifest.json")
        else MAX_LANGUAGE_UI_BYTES if item.path.endswith("/ui.json")
        else MAX_PYTHON_FILE_BYTES
    )
    if not 0 <= item.size <= maximum:
        raise SoftwareUpdatePackageError("Python file size is outside Greia bounds")
    _digest(item.sha256)


def _validate_language_resources(
    archive: zipfile.ZipFile, manifest: SoftwareUpdatePackageManifest
) -> None:
    resources = {item.path: item for item in manifest.python_files if is_language_resource_path(item.path)}
    if not resources:
        return
    locales = {PurePosixPath(path).parts[3] for path in resources}
    if len(locales) > MAX_LANGUAGE_RESOURCE_LOCALES:
        raise SoftwareUpdatePackageError("language resource count exceeds the runtime limit")
    if "en" not in locales:
        raise SoftwareUpdatePackageError("language resource package must include English")
    decoded: dict[str, object] = {}
    for locale in locales:
        manifest_path = f"src/greia_platform/languages/{locale}/manifest.json"
        ui_path = f"src/greia_platform/languages/{locale}/ui.json"
        if manifest_path not in resources or ui_path not in resources:
            raise SoftwareUpdatePackageError("language package must include both manifest.json and ui.json per locale")
        for path in (manifest_path, ui_path):
            try:
                value = json.loads(archive.read(resources[path].member).decode("utf-8"), object_pairs_hook=_unique_object)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                raise SoftwareUpdatePackageError(f"{path} is not valid unique-key UTF-8 JSON") from exc
            if not isinstance(value, dict) or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
                raise SoftwareUpdatePackageError(f"{path} must be a schema_version 1 JSON object")
            decoded[path] = value
        data = decoded[manifest_path]
        if data.get("locale") != locale:
            raise SoftwareUpdatePackageError(f"{manifest_path} locale must match its canonical directory")
        if any(not isinstance(data.get(key), str) or not data[key].strip() or len(data[key]) > 80 for key in ("name", "native_name", "flag")):
            raise SoftwareUpdatePackageError(f"{manifest_path} display metadata is invalid")
        if type(data.get("order", 1000)) is not int or not 0 <= data.get("order", 1000) <= 10000:
            raise SoftwareUpdatePackageError(f"{manifest_path} order is invalid")
        if data.get("direction", "ltr") not in ("ltr", "rtl"):
            raise SoftwareUpdatePackageError(f"{manifest_path} direction is invalid")
        catalog = decoded[ui_path]
        for section, mapping in catalog.items():
            if section == "schema_version":
                continue
            if not isinstance(section, str) or not isinstance(mapping, dict) or any(
                not isinstance(key, str) or not isinstance(value, str) or len(key) > 160 or len(value) > 8192
                for key, value in mapping.items()
            ):
                raise SoftwareUpdatePackageError(f"{ui_path} contains an invalid UI section or string")
    reference_path = "src/greia_platform/languages/en/ui.json"
    reference = decoded.get(reference_path)
    for locale in locales:
        catalog = decoded[f"src/greia_platform/languages/{locale}/ui.json"]
        for section, mapping in catalog.items():
            if section == "schema_version":
                continue
            for key, text in mapping.items():
                try:
                    _format_fields(text)
                except ValueError as exc:
                    raise SoftwareUpdatePackageError(f"{locale} UI has an invalid format string in {section}/{key}") from exc
    if reference is not None:
        for locale in locales - {"en"}:
            catalog = decoded[f"src/greia_platform/languages/{locale}/ui.json"]
            for section, english_values in reference.items():
                if section == "schema_version":
                    continue
                translated_values = catalog.get(section)
                if not isinstance(translated_values, dict) or not set(english_values).issubset(translated_values):
                    raise SoftwareUpdatePackageError(f"{locale} UI omits English keys in section {section}")
                for key in english_values:
                    english = english_values[key]
                    try:
                        if _format_fields(translated_values[key]) != _format_fields(english):
                            raise SoftwareUpdatePackageError(f"{locale} UI placeholder mismatch in {section}/{key}")
                    except SoftwareUpdatePackageError:
                        raise
                    except ValueError as exc:
                        raise SoftwareUpdatePackageError(f"{locale} UI has an invalid format string in {section}/{key}") from exc


def validate_language_resource_tree(language_root: Path) -> tuple[str, ...]:
    """Validate offered locale JSON files without importing registry code.

    Manifest-less locale directories are unoffered staging scaffolds. Offered
    locales require the paired UI file and return in runtime `(order, locale)`
    order so generation validation can compare the package inventory directly.
    """
    root = Path(language_root)
    if root.is_symlink() or not root.is_dir():
        raise SoftwareUpdatePackageError("language resource root is missing or unsafe")
    records: list[SoftwareUpdatePythonFile] = []
    orders: dict[str, int] = {}
    content: dict[str, bytes] = {}
    for directory in sorted(root.iterdir(), key=lambda item: item.name):
        if directory.is_symlink():
            raise SoftwareUpdatePackageError("language resource directory is a symlink")
        if not directory.is_dir():
            raise SoftwareUpdatePackageError("language resource root contains a non-directory entry")
        manifest_path = directory / "manifest.json"
        if manifest_path.is_symlink():
            raise SoftwareUpdatePackageError("language manifest is a symlink")
        if not manifest_path.exists():
            continue
        locale = directory.name
        if not is_language_resource_path(f"src/greia_platform/languages/{locale}/manifest.json"):
            raise SoftwareUpdatePackageError("language directory is not a canonical locale")
        manifest_data: object = None
        for filename, maximum in (("manifest.json", MAX_LANGUAGE_MANIFEST_BYTES), ("ui.json", MAX_LANGUAGE_UI_BYTES)):
            path = directory / filename
            if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
                raise SoftwareUpdatePackageError(f"language resource is missing, unsafe or oversized: {path}")
            raw = path.read_bytes()
            relative = f"src/greia_platform/languages/{locale}/{filename}"
            content[relative] = raw
            if filename == "manifest.json":
                try:
                    manifest_data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                    raise SoftwareUpdatePackageError(f"invalid language manifest {path}") from exc
        if not isinstance(manifest_data, dict):
            raise SoftwareUpdatePackageError(f"invalid language manifest {manifest_path}")
        order = manifest_data.get("order", 1000)
        if type(order) is not int or not 0 <= order <= 10000:
            raise SoftwareUpdatePackageError(f"language manifest has invalid order: {locale}")
        orders[locale] = order
        for filename in ("manifest.json", "ui.json"):
            relative = f"src/greia_platform/languages/{locale}/{filename}"
            records.append(SoftwareUpdatePythonFile(relative, f"python/{relative}", len(content[relative]), hashlib.sha256(content[relative]).hexdigest()))
    if records and "en" not in orders:
        raise SoftwareUpdatePackageError("English language manifest is required")
    if len(orders) > MAX_LANGUAGE_RESOURCE_LOCALES:
        raise SoftwareUpdatePackageError("language resource count exceeds the runtime limit")
    if records:
        package = SimpleNamespace(python_files=tuple(records))
        archive_bytes = io.BytesIO()
        with zipfile.ZipFile(archive_bytes, "w", compression=zipfile.ZIP_STORED) as writer:
            for record in records:
                relative = record.path
                writer.writestr(record.member, content[relative])
        with zipfile.ZipFile(io.BytesIO(archive_bytes.getvalue()), "r") as reader:
            _validate_language_resources(reader, package)
    return tuple(sorted(orders, key=lambda locale: (orders[locale], locale)))


def _format_fields(value: str) -> frozenset[str]:
    fields: set[str] = set()

    def visit(template: str, depth: int) -> None:
        if depth > 8:
            raise ValueError("format placeholders are nested too deeply")
        for _, name, format_spec, _ in Formatter().parse(template):
            if name is not None:
                fields.add(name)
            if format_spec and "{" in format_spec:
                visit(format_spec, depth + 1)

    visit(value, 0)
    return frozenset(fields)


def _parse_activity(value: object) -> SoftwareUpdateActivity:
    if not isinstance(value, dict) or set(value) != {
        "activity_id", "version", "member", "size", "sha256"
    }:
        raise SoftwareUpdatePackageError("Activity descriptor fields are invalid")
    activity_id = _identifier(value.get("activity_id"), "activity_id", 96)
    item = SoftwareUpdateActivity(
        activity_id=activity_id,
        version=_text(value.get("version"), "Activity version", 64),
        member=_archive_path(value.get("member")),
        size=_integer(value.get("size"), "Activity package size"),
        sha256=_digest(value.get("sha256")),
    )
    _validate_activity_record(item)
    return item


def _validate_activity_record(item: SoftwareUpdateActivity) -> None:
    _identifier(item.activity_id, "activity_id", 96)
    _text(item.version, "Activity version", 64)
    if item.member != f"activities/{item.activity_id}{ACTIVITY_PACKAGE_EXTENSION}":
        raise SoftwareUpdatePackageError("Activity member does not match its fixed identity")
    if not 0 < item.size <= MAX_ACTIVITY_PACKAGE_BYTES:
        raise SoftwareUpdatePackageError("Activity archive size is outside Greia bounds")
    _digest(item.sha256)


def _parse_member(value: object) -> SoftwareUpdateMember:
    if not isinstance(value, dict) or set(value) != {"member", "size", "sha256"}:
        raise SoftwareUpdatePackageError("full_system descriptor fields are invalid")
    member = SoftwareUpdateMember(
        member=_archive_path(value.get("member")),
        size=_integer(value.get("size"), "full-system bundle size"),
        sha256=_digest(value.get("sha256")),
    )
    if member.member != "full_system/bundle.greiaupdate":
        raise SoftwareUpdatePackageError("full-system member name is invalid")
    if not 0 < member.size <= MAX_BUNDLE_BYTES:
        raise SoftwareUpdatePackageError("full-system bundle size is outside Greia bounds")
    return member


def _manifest_members(manifest: SoftwareUpdatePackageManifest) -> list[str]:
    if manifest.type in (SoftwareUpdateType.PYTHON_PLATFORM, SoftwareUpdateType.COMBINED):
        members = [item.member for item in manifest.python_files]
    elif manifest.type is SoftwareUpdateType.ACTIVITIES:
        members = []
    else:
        members = []
    members.extend(item.member for item in manifest.activity_items)
    if manifest.full_system is not None:
        members.append(manifest.full_system.member)
    return sorted(members)


def _validate_outer_zip_infos(infos: list[zipfile.ZipInfo]) -> None:
    seen: set[str] = set()
    for info in infos:
        name = _archive_path(info.filename)
        if name in seen:
            raise SoftwareUpdatePackageError("package contains duplicate member names")
        seen.add(name)
        if info.is_dir() or info.flag_bits & 0x1:
            raise SoftwareUpdatePackageError("package directories/encrypted members are forbidden")
        if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise SoftwareUpdatePackageError("unsupported package compression method")
        mode = (info.external_attr >> 16) & 0o170000
        if mode and mode != stat.S_IFREG:
            raise SoftwareUpdatePackageError("package special files are forbidden")
        if info.file_size > MAX_SOFTWARE_UPDATE_BYTES:
            raise SoftwareUpdatePackageError("package member exceeds Greia bounds")
        if (
            info.file_size > 1024 * 1024
            and info.compress_size > 0
            and info.file_size > info.compress_size * MAX_COMPRESSION_RATIO
        ):
            raise SoftwareUpdatePackageError("package member compression ratio exceeds Greia bounds")


def _validate_declared_member_sizes(
    archive: zipfile.ZipFile, manifest: SoftwareUpdatePackageManifest
) -> None:
    by_name = {item.filename: item for item in archive.infolist()}
    total = 0
    expected_compression: dict[str, int] = {}
    for item in manifest.python_files:
        expected_compression[item.member] = zipfile.ZIP_DEFLATED
        total += _assert_member_size(by_name, item.member, item.size)
    for item in manifest.activity_items:
        expected_compression[item.member] = zipfile.ZIP_STORED
        total += _assert_member_size(by_name, item.member, item.size)
    if manifest.full_system is not None:
        expected_compression[manifest.full_system.member] = zipfile.ZIP_STORED
        total += _assert_member_size(by_name, manifest.full_system.member, manifest.full_system.size)
    if total > MAX_SOFTWARE_UPDATE_BYTES:
        raise SoftwareUpdatePackageError("uncompressed package contents exceed Greia bounds")
    for name, compression in expected_compression.items():
        if by_name[name].compress_type != compression:
            raise SoftwareUpdatePackageError(f"{name} has an unexpected compression method")


def _assert_member_size(
    by_name: Mapping[str, zipfile.ZipInfo], name: str, expected: int
) -> int:
    info = by_name.get(name)
    if info is None or info.file_size != expected:
        raise SoftwareUpdatePackageError(f"{name} size does not match manifest")
    return info.file_size


def _verify_all_digests(
    archive: zipfile.ZipFile, manifest: SoftwareUpdatePackageManifest
) -> None:
    for item in (*manifest.python_files, *manifest.activity_items):
        _verify_member_digest(archive, item.member, item.sha256)
    if manifest.full_system is not None:
        _verify_member_digest(archive, manifest.full_system.member, manifest.full_system.sha256)


def _verify_member_digest(archive: zipfile.ZipFile, name: str, expected: str) -> None:
    digest = hashlib.sha256()
    size = 0
    with archive.open(name, "r") as member:
        while True:
            chunk = member.read(COPY_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    if digest.hexdigest() != expected:
        raise SoftwareUpdatePackageError(f"{name} SHA-256 does not match manifest")


def _validate_nested_activity(
    archive: zipfile.ZipFile,
    item: SoftwareUpdateActivity,
    source_kind: ActivityPackageSource,
    runtime_path: Path,
) -> None:
    try:
        with archive.open(item.member, "r") as member:
            with zipfile.ZipFile(member, "r", allowZip64=False) as activity_archive:
                infos = activity_archive.infolist()
                if not infos or len(infos) > MAX_ACTIVITY_ENTRIES:
                    raise SoftwareUpdatePackageError("nested Activity entry count is outside Greia bounds")
                names: set[str] = set()
                folded: set[str] = set()
                uncompressed = 0
                manifest_info: zipfile.ZipInfo | None = None
                for info in infos:
                    path = _activity_archive_path(info.filename, allow_directory=info.is_dir())
                    if info.filename in names or path.casefold() in folded:
                        raise SoftwareUpdatePackageError("nested Activity contains duplicate paths")
                    names.add(info.filename)
                    folded.add(path.casefold())
                    if info.flag_bits & 0x1:
                        raise SoftwareUpdatePackageError("nested Activity encrypted entries are forbidden")
                    mode = (info.external_attr >> 16) & 0xFFFF
                    file_type = stat.S_IFMT(mode)
                    if file_type and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                        raise SoftwareUpdatePackageError("nested Activity contains a special file")
                    if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                        raise SoftwareUpdatePackageError("nested Activity compression is unsupported")
                    if not info.is_dir():
                        uncompressed += info.file_size
                        if (
                            info.file_size > 1024 * 1024
                            and info.compress_size > 0
                            and info.file_size > info.compress_size * MAX_COMPRESSION_RATIO
                        ):
                            raise SoftwareUpdatePackageError("nested Activity compression ratio exceeds Greia bounds")
                    if path == "activity.toml" and not info.is_dir():
                        manifest_info = info
                if uncompressed > MAX_ACTIVITY_UNCOMPRESSED_BYTES:
                    raise SoftwareUpdatePackageError("nested Activity uncompressed size exceeds Greia bounds")
                if manifest_info is None or manifest_info.file_size > 64 * 1024:
                    raise SoftwareUpdatePackageError("nested Activity root activity.toml is missing or oversized")
                activity_id, version = _validate_activity_archive_contents(
                    activity_archive,
                    item.activity_id,
                    source_kind=source_kind,
                    runtime_path=runtime_path,
                )
                if activity_id != item.activity_id or version != item.version:
                    raise SoftwareUpdatePackageError(
                        "nested Activity identity/version differs from package manifest"
                    )
    except SoftwareUpdatePackageError:
        raise
    except (zipfile.BadZipFile, OSError, EOFError) as exc:
        raise SoftwareUpdatePackageError("nested Activity archive is invalid") from exc


def _validate_activity_archive_contents(
    archive: zipfile.ZipFile,
    expected_activity_id: str,
    *,
    source_kind: ActivityPackageSource,
    runtime_path: Path,
) -> tuple[str, str]:
    """Apply Greia's trusted source, manifest, tree and runtime validators."""

    from greia_launcher.runtime_adapter import (
        PythonRuntimeAdapter,
        PythonRuntimePolicy,
        WebRuntimeAdapter,
    )

    from .activities import ActivityRegistry, RuntimeCatalogue
    from .activity_backend_policy import assert_python_activity_backend_independent
    from .activity_packages import ActivityPackageError, ActivityPackageService
    from .trust import ActivitySource, PackageTrust

    runtime_path = Path(runtime_path)
    if runtime_path.is_symlink() or not runtime_path.is_file():
        raise SoftwareUpdatePackageError("Activity runtime policy is missing or unsafe")
    runtime = RuntimeCatalogue.load(runtime_path)
    trust = (
        PackageTrust.BUILT_IN
        if source_kind is ActivityPackageSource.BUILT_IN
        else PackageTrust.PARENT_TRUSTED_UNSIGNED
    )
    source_id = (
        "greia-system"
        if source_kind is ActivityPackageSource.BUILT_IN
        else ActivityPackageService.SOURCE_ID
    )
    with tempfile.TemporaryDirectory(prefix="greia-software-update-activity-") as directory:
        package_parent = Path(directory) / "source"
        package_parent.mkdir()
        package_root = package_parent / expected_activity_id
        package_root.mkdir()
        extractor = ActivityPackageService(
            state_root=Path(directory) / "unused-state",
            runtime_catalogue=runtime_path,
        )
        try:
            extractor.extract_bounded_archive_contents(
                archive,
                package_root,
                max_entries=MAX_ACTIVITY_ENTRIES,
            )
        except (ActivityPackageError, OSError, zipfile.BadZipFile) as exc:
            raise SoftwareUpdatePackageError(
                f"Activity archive failed bounded extraction: {exc}"
            ) from exc
        activity_source = ActivitySource(package_parent, trust, source_id)
        try:
            registration = ActivityRegistry(
                (activity_source,), runtime
            ).validate_registration(package_root, activity_source)
            manifest = registration.manifest
            if manifest.activity_id != expected_activity_id:
                raise SoftwareUpdatePackageError("Activity archive id does not match package id")
            if manifest.runtime_type == "python":
                PythonRuntimeAdapter(
                    policy=PythonRuntimePolicy.load(runtime_path)
                ).validate_package(manifest)
                assert_python_activity_backend_independent(package_root)
            elif manifest.runtime_type == "web":
                WebRuntimeAdapter().validate_package(manifest)
            else:
                raise SoftwareUpdatePackageError(
                    f"unsupported Activity runtime: {manifest.runtime_type}"
                )
            return manifest.activity_id, manifest.version
        except SoftwareUpdatePackageError:
            raise
        except Exception as exc:
            from .activities import ActivityValidationError
            from greia_launcher.runtime_adapter import RuntimeValidationError

            if isinstance(exc, (ActivityValidationError, RuntimeValidationError)):
                raise SoftwareUpdatePackageError(
                    f"Activity archive failed Greia validation: {exc}"
                ) from exc
            raise


def _validate_nested_system_manifest(
    archive: zipfile.ZipFile, manifest: SoftwareUpdatePackageManifest
) -> None:
    member_record = manifest.full_system
    assert member_record is not None
    try:
        with archive.open(member_record.member, "r") as member:
            with zipfile.ZipFile(member, "r", allowZip64=True) as inner:
                infos = inner.infolist()
                names = [item.filename for item in infos]
                if names not in (
                    ["manifest.json", "payload.ext4.zst"],
                    ["manifest.json", "payload.ext4.zst", "hardware-support.tar.zst"],
                ):
                    raise SoftwareUpdatePackageError("nested full-system bundle is not existing v3 layout")
                inspected = inspect_update_bundle_archive(
                    inner, archive_size=member_record.size
                )
    except UpdateBundleError as exc:
        raise SoftwareUpdatePackageError(
            f"nested full-system bundle failed v3 validation: {exc}"
        ) from exc
    except (zipfile.BadZipFile, OSError, EOFError) as exc:
        raise SoftwareUpdatePackageError("nested full-system bundle is unreadable") from exc
    if inspected.version != manifest.version or inspected.release_id != manifest.release_id:
        raise SoftwareUpdatePackageError("outer full-system identity differs from inner v3 bundle")



def _read_bounded(archive: zipfile.ZipFile, member: str, limit: int) -> bytes:
    info = archive.getinfo(member)
    if info.file_size > limit:
        raise SoftwareUpdatePackageError(f"{member} exceeds Greia bound")
    with archive.open(info, "r") as stream:
        payload = stream.read(limit + 1)
    if len(payload) != info.file_size or len(payload) > limit:
        raise SoftwareUpdatePackageError(f"{member} ended outside its declared size")
    return payload


def _hash_file(path: Path, limit: int) -> str:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as source:
        while True:
            chunk = source.read(COPY_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                raise SoftwareUpdatePackageError("package grew beyond Greia bound during inspection")
            digest.update(chunk)
    return digest.hexdigest()


def _require_regular_source(
    path: Path, maximum: int, *, allow_empty: bool = False
) -> None:
    try:
        info = Path(path).lstat()
    except OSError as exc:
        raise SoftwareUpdatePackageError(f"package source is unavailable: {path}") from exc
    if not stat.S_ISREG(info.st_mode) or Path(path).is_symlink():
        raise SoftwareUpdatePackageError("package source must be a regular non-symlink file")
    minimum = 0 if allow_empty else 1
    if info.st_size < minimum or info.st_size > maximum:
        raise SoftwareUpdatePackageError("package source size is outside Greia bounds")


def _activity_archive_path(name: str, *, allow_directory: bool) -> str:
    if not name or len(name) > MAX_PATH_CHARACTERS or "\\" in name or "\x00" in name:
        raise SoftwareUpdatePackageError("nested Activity contains an invalid archive path")
    normalized = name[:-1] if allow_directory and name.endswith("/") else name
    path = PurePosixPath(normalized)
    parts = tuple(part for part in path.parts if part)
    if (
        path.is_absolute()
        or not parts
        or any(part in {".", ".."} or part.startswith(".") for part in parts)
    ):
        raise SoftwareUpdatePackageError("nested Activity path escapes or hides files")
    return "/".join(parts)


def _package_path(value: object) -> str:
    name = _archive_path(value)
    if not name.endswith(".py") and name not in PYTHON_RUNTIME_ALLOWLIST and not is_language_resource_path(name):
        raise SoftwareUpdatePackageError("Python destination is outside the code/runtime allowlist")
    if not any(name.startswith(root) for root in PYTHON_SOURCE_ROOTS) and name not in PYTHON_RUNTIME_ALLOWLIST:
        raise SoftwareUpdatePackageError("Python destination is outside the production source trees")
    if any(part.startswith(".") for part in PurePosixPath(name).parts):
        raise SoftwareUpdatePackageError("hidden Python source paths are not packageable")
    return name


def is_language_resource_path(value: object) -> bool:
    """Return whether a destination is one of Greia's fixed locale JSON files."""
    if not isinstance(value, str):
        return False
    parts = PurePosixPath(value).parts
    if len(parts) != 5 or parts[:3] != ("src", "greia_platform", "languages"):
        return False
    try:
        locale = str(LocaleTag.parse(parts[3]))
    except LocalizationError:
        return False
    return locale == parts[3] and parts[4] in {"manifest.json", "ui.json"}


def _archive_path(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_PATH_CHARACTERS:
        raise SoftwareUpdatePackageError("archive path is missing or too long")
    if "\\" in value or "\x00" in value:
        raise SoftwareUpdatePackageError("archive path contains an invalid separator")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise SoftwareUpdatePackageError("archive path escapes its fixed package root")
    if path.as_posix() != value:
        raise SoftwareUpdatePackageError("archive path is not canonical POSIX form")
    return value


def _identifier(value: object, name: str, maximum: int) -> str:
    if not isinstance(value, str) or len(value) > maximum or not _IDENTIFIER.fullmatch(value):
        raise SoftwareUpdatePackageError(f"{name} is not a bounded identifier")
    return value


def _text(value: object, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum or "\x00" in value:
        raise SoftwareUpdatePackageError(f"{name} is missing or outside Greia bounds")
    return value


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SoftwareUpdatePackageError(f"{name} must be a positive integer")
    return value


def _nonnegative_integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SoftwareUpdatePackageError(f"{name} must be a non-negative integer")
    return value


def _digest(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise SoftwareUpdatePackageError("SHA-256 must be lower-case 64-character hex")
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            raise SoftwareUpdatePackageError(f"duplicate JSON key: {name}")
        result[name] = value
    return result


def _target_limit(name: str) -> int:
    return {"profile": 96, "platform_family": 64, "architecture": 32, "board": 64}[name]


__all__ = [
    "ActivityPackageInput",
    "ActivityPackageSource",
    "ActivityUpdateScope",
    "InspectedSoftwareUpdatePackage",
    "MAX_SOFTWARE_UPDATE_BYTES",
    "REQUIRED_PYTHON_ENTRYPOINTS",
    "PYTHON_RUNTIME_ALLOWLIST",
    "PYTHON_SOURCE_ROOTS",
    "SOFTWARE_UPDATE_EXTENSION",
    "SOFTWARE_UPDATE_MANIFEST",
    "SOFTWARE_UPDATE_MEDIA_TYPE",
    "SOFTWARE_UPDATE_SCHEMA_VERSION",
    "SoftwareUpdateActivity",
    "SoftwareUpdateMember",
    "SoftwareUpdatePackageError",
    "SoftwareUpdatePackageManifest",
    "SoftwareUpdatePythonFile",
    "SoftwareUpdateTarget",
    "SoftwareUpdateType",
    "build_software_update_package",
    "ensure_software_update_filename",
    "inspect_software_update_package",
    "is_language_resource_path",
    "validate_language_resource_tree",
]
