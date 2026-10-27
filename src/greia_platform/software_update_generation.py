"""Build complete, hard-linked application generations for ``.greia_update``.

This module prepares immutable application trees but never publishes the live
``/opt/greia-os`` pointer.  The stable system bootstrap owns that transaction
boundary so recovery still works after this module itself is replaced.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

from .activities import ActivityRegistry, RuntimeCatalogue
from .activity_index import build_index
from .activity_packages import ActivityPackageError, ActivityPackageService
from .software_update_package import (
    MAX_ACTIVITY_ENTRIES,
    MAX_ACTIVITY_PACKAGE_BYTES,
    MAX_ACTIVITY_UNCOMPRESSED_BYTES,
    PYTHON_RUNTIME_ALLOWLIST,
    PYTHON_SOURCE_ROOTS,
    REQUIRED_PYTHON_ENTRYPOINTS,
    is_language_resource_path,
    InspectedSoftwareUpdatePackage,
    SoftwareUpdateActivity,
    SoftwareUpdatePackageManifest,
    SoftwareUpdateType,
    inspect_software_update_package,
)
from .trust import ActivitySource, PackageTrust


_BUILT_IN_SOURCE_ID = "greia-system"
_GENERATION_PREFIX = "app-"
_STAGING_PREFIX = ".staging-app-"
_FREE_SPACE_RESERVE_BYTES = 8 * 1024 * 1024
_INDEX_RESERVE_BYTES = 2 * 1024 * 1024
_CHUNK_BYTES = 1024 * 1024
class SoftwareUpdateGenerationError(RuntimeError):
    """A candidate application generation cannot be staged safely."""


@dataclass(frozen=True, slots=True)
class GenerationLayout:
    """Injectable paths for the one-pointer application generation layout."""

    application_root: Path = Path("/opt/greia-os")
    generation_root: Path = Path("/opt/greia-software/generations")
    activity_package_state: Path = Path("/var/lib/greia-os/activity-packages")


@dataclass(frozen=True, slots=True)
class StagedApplicationGeneration:
    """Identity and capacity estimate for a complete, not-yet-active tree."""

    generation_id: str
    generation_path: Path
    previous_generation_id: str
    required_bytes: int


class ApplicationGenerationBuilder:
    """Stage Python/runtime and built-in Activities under one generation ID."""

    def __init__(self, layout: GenerationLayout = GenerationLayout()) -> None:
        self.layout = layout

    def current_generation_id(self) -> str:
        """Resolve the active generation from the fixed application symlink."""

        root = self.layout.application_root
        try:
            info = root.lstat()
        except OSError as exc:
            raise SoftwareUpdateGenerationError(
                "installed application root is unavailable"
            ) from exc
        if not stat.S_ISLNK(info.st_mode):
            raise SoftwareUpdateGenerationError(
                "application root has not completed generation bootstrap"
            )
        target = root.resolve(strict=True)
        generations = self.layout.generation_root.resolve(strict=True)
        try:
            target.relative_to(generations)
        except ValueError as exc:
            raise SoftwareUpdateGenerationError(
                "application root points outside the generation directory"
            ) from exc
        if not target.is_dir() or target.is_symlink():
            raise SoftwareUpdateGenerationError("active application generation is invalid")
        return target.name

    def stage(
        self,
        package_path: Path,
        inspected: InspectedSoftwareUpdatePackage | None = None,
        *,
        job_id: str,
    ) -> StagedApplicationGeneration:
        """Build a fully validated immutable candidate without activating it."""

        if not _is_job_id(job_id):
            raise SoftwareUpdateGenerationError("software update job id is invalid")
        package_path = Path(package_path)
        inspected = inspected or inspect_software_update_package(package_path)
        manifest = inspected.manifest
        if manifest.type is SoftwareUpdateType.ACTIVITIES and manifest.activity_source.value == "parent":
            raise SoftwareUpdateGenerationError(
                "Parent-installed Activity updates use the PERSIST package generation"
            )
        if manifest.type is SoftwareUpdateType.FULL_SYSTEM:
            raise SoftwareUpdateGenerationError(
                "full-system packages are staged by the existing A/B writer"
            )

        previous_id = self.current_generation_id()
        previous_root = self.layout.generation_root / previous_id
        final_id = _GENERATION_PREFIX + job_id
        final_root = self.layout.generation_root / final_id
        if final_root.exists() or final_root.is_symlink():
            if final_root.is_symlink():
                raise SoftwareUpdateGenerationError(
                    "candidate generation destination is a symbolic link"
                )
            # The root worker is idempotent after a crash between generation
            # staging and pointer publication.  The deterministic tree must
            # still validate against the currently accepted package bytes.
            if _read_generation_receipt(final_root) != {
                "schema_version": 1,
                "job_id": job_id,
                "package_sha256": inspected.package_sha256,
                "release_id": manifest.release_id,
                "version": manifest.version,
            }:
                raise SoftwareUpdateGenerationError(
                    "existing candidate generation does not match this accepted package"
                )
            self._validate_application_root(final_root)
            return StagedApplicationGeneration(final_id, final_root, previous_id, 0)

        staging = self.layout.generation_root / (_STAGING_PREFIX + job_id)
        if staging.exists():
            _remove_staging_tree(staging)
        self.layout.generation_root.mkdir(parents=True, exist_ok=True)
        if self.layout.generation_root.stat().st_dev != previous_root.stat().st_dev:
            raise SoftwareUpdateGenerationError(
                "application generations must share a filesystem with the active generation"
            )

        required_bytes = self._estimate_changed_bytes(
            package_path, manifest, previous_root
        ) + _INDEX_RESERVE_BYTES + _FREE_SPACE_RESERVE_BYTES
        if shutil.disk_usage(self.layout.generation_root).free < required_bytes:
            raise SoftwareUpdateGenerationError(
                "not enough free space to retain the previous application generation"
            )

        try:
            _clone_tree_hardlinked(previous_root, staging)
            with zipfile.ZipFile(package_path, "r", allowZip64=False) as archive:
                if manifest.type in (
                    SoftwareUpdateType.PYTHON_PLATFORM,
                    SoftwareUpdateType.COMBINED,
                ):
                    declared_python_paths = {item.path for item in manifest.python_files}
                    missing_entrypoints = REQUIRED_PYTHON_ENTRYPOINTS - declared_python_paths
                    if missing_entrypoints:
                        raise SoftwareUpdateGenerationError(
                            "Python update omits required launcher, Parent, or updater modules"
                        )
                    declared_runtime_paths = {
                        item.path
                        for item in manifest.python_files
                        if item.path.startswith("runtime/")
                    }
                    if declared_runtime_paths != set(PYTHON_RUNTIME_ALLOWLIST):
                        raise SoftwareUpdateGenerationError(
                            "Python update must contain the complete runtime configuration snapshot"
                        )
                    for item in manifest.python_files:
                        self._apply_python_file(
                            archive,
                            item.path,
                            item.member,
                            item.size,
                            item.sha256,
                            previous_root,
                            staging,
                        )
                    self._validate_language_resources(
                        staging,
                        {item.path for item in manifest.python_files},
                    )
                    self._remove_obsolete_python_sources(staging, declared_python_paths)
                    self._validate_python_sources(staging)
                if manifest.activity_items:
                    self._apply_builtin_activities(
                        archive, manifest, previous_root, staging, job_id
                    )
            _write_generation_receipt(
                staging,
                {
                    "schema_version": 1,
                    "job_id": job_id,
                    "package_sha256": inspected.package_sha256,
                    "release_id": manifest.release_id,
                    "version": manifest.version,
                },
            )
            self._validate_application_root(staging)
            _seal_read_only(staging)
            _fsync_tree_directories(staging)
            os.replace(staging, final_root)
            _fsync_directory(self.layout.generation_root)
        except BaseException:
            if staging.exists():
                _remove_staging_tree(staging)
            if final_root.exists() and not final_root.is_symlink():
                _remove_staging_tree(final_root)
            raise
        return StagedApplicationGeneration(
            final_id, final_root, previous_id, required_bytes
        )

    @staticmethod
    def _remove_obsolete_python_sources(
        staging_root: Path, declared_paths: set[str]
    ) -> None:
        """Apply the manifest's complete source snapshot, removing old modules."""

        for source_root in PYTHON_SOURCE_ROOTS:
            root = staging_root / source_root
            if root.is_symlink() or not root.is_dir():
                raise SoftwareUpdateGenerationError(
                    "Python update source root is missing or unsafe"
                )
            for path in root.rglob("*.py"):
                if path.is_symlink():
                    raise SoftwareUpdateGenerationError(
                        "installed Python source contains a symbolic link"
                    )
                relative = path.relative_to(staging_root).as_posix()
                if relative not in declared_paths:
                    path.unlink()

    @staticmethod
    def _validate_python_sources(staging_root: Path) -> None:
        """Compile the staged production Python snapshot without importing it."""

        required_roots = tuple(
            staging_root / source_root / "__init__.py"
            for source_root in PYTHON_SOURCE_ROOTS
        )
        if any(not path.is_file() for path in required_roots):
            raise SoftwareUpdateGenerationError(
                "Python snapshot omits a production package initializer"
            )
        for source_root in PYTHON_SOURCE_ROOTS:
            for path in (staging_root / source_root).rglob("*.py"):
                try:
                    source = path.read_bytes()
                    compile(source, str(path), "exec", dont_inherit=True)
                except (OSError, SyntaxError, ValueError) as exc:
                    raise SoftwareUpdateGenerationError(
                        f"Python source does not compile: {path.name}"
                    ) from exc

    @staticmethod
    def _validate_language_resources(
        staging_root: Path, declared_paths: set[str]
    ) -> None:
        """Validate the candidate's JSON registry and UI catalog before publication.

        The bootstrap validates staged JSON through the package validator. It
        never imports Python from the candidate tree.
        """
        declared = {path for path in declared_paths if is_language_resource_path(path)}
        language_root = staging_root / "src/greia_platform/languages"
        _remove_obsolete_language_resources(language_root, declared)
        registry_source = staging_root / "src/greia_platform/system_language.py"
        expects_registry = False
        try:
            expects_registry = (
                registry_source.is_file()
                and "load_system_languages" in registry_source.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError) as exc:
            raise SoftwareUpdateGenerationError("cannot inspect staged language registry source") from exc
        if not declared and not expects_registry:
            return  # Historical code snapshots without a manifest registry remain valid.
        if not declared:
            raise SoftwareUpdateGenerationError("Python update omits required language JSON resources")
        try:
            from .software_update_package import (
                SoftwareUpdatePackageError,
                validate_language_resource_tree,
            )

            locales = validate_language_resource_tree(language_root)
            expected_paths = {
                f"src/greia_platform/languages/{locale}/{name}"
                for locale in locales
                for name in ("manifest.json", "ui.json")
            }
            if declared != expected_paths:
                missing = sorted(expected_paths - declared)
                extra = sorted(declared - expected_paths)
                raise ValueError(
                    f"language resource snapshot mismatch (missing={missing}, extra={extra})"
                )
        except (
            OSError,
            ValueError,
            UnicodeError,
            TypeError,
            SoftwareUpdatePackageError,
        ) as exc:
            raise SoftwareUpdateGenerationError(f"candidate language resources are invalid: {exc}") from exc

    def _estimate_changed_bytes(
        self,
        package_path: Path,
        manifest: SoftwareUpdatePackageManifest,
        previous_root: Path,
    ) -> int:
        """Preflight changed uncompressed bytes before creating a generation."""

        required = 0
        for item in manifest.python_files:
            relative = _safe_python_destination(item.path)
            existing = previous_root.joinpath(*relative.parts)
            if not _same_file(existing, item.size, item.sha256):
                required += item.size
        if not manifest.activity_items:
            return required
        old_activity_paths = self._builtin_activity_paths(previous_root)
        with zipfile.ZipFile(package_path, "r", allowZip64=False) as outer:
            for item in manifest.activity_items:
                old_root = old_activity_paths.get(item.activity_id)
                nested = outer.open(item.member, "r")
                with zipfile.ZipFile(nested, "r", allowZip64=False) as activity_zip:
                    required += self._estimate_activity_bytes(activity_zip, old_root)
        return required

    def _estimate_activity_bytes(
        self, archive: zipfile.ZipFile, previous_root: Path | None
    ) -> int:
        entries = archive.infolist()
        if not entries or len(entries) > MAX_ACTIVITY_ENTRIES:
            raise SoftwareUpdateGenerationError(
                "Activity archive entry count exceeds the software-update bound"
            )
        seen: set[str] = set()
        total_uncompressed = 0
        required = 0
        for info in entries:
            relative = ActivityPackageService._safe_archive_path(info)
            canonical = relative.as_posix().casefold()
            if canonical in seen:
                raise SoftwareUpdateGenerationError(
                    "Activity archive contains duplicate portable paths"
                )
            seen.add(canonical)
            if info.is_dir():
                continue
            total_uncompressed += info.file_size
            if total_uncompressed > MAX_ACTIVITY_UNCOMPRESSED_BYTES:
                raise SoftwareUpdateGenerationError(
                    "Activity archive exceeds the software-update extraction bound"
                )
            existing = (
                previous_root.joinpath(*relative.parts)
                if previous_root is not None
                else None
            )
            if existing is None or not _same_archive_file(archive, info, existing):
                required += info.file_size
        return required

    def _apply_python_file(
        self,
        archive: zipfile.ZipFile,
        relative_path: str,
        member: str,
        size: int,
        expected_sha256: str,
        previous_root: Path,
        staging_root: Path,
    ) -> None:
        relative = _safe_python_destination(relative_path)
        source = previous_root.joinpath(*relative.parts)
        destination = staging_root.joinpath(*relative.parts)
        if _same_file(source, size, expected_sha256):
            return  # The hard-link clone already points at identical bytes.
        if destination.parent.is_symlink():
            raise SoftwareUpdateGenerationError(
                "Python destination traverses a symlink"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{expected_sha256[:12]}.tmp")
        temporary.unlink(missing_ok=True)
        digest = hashlib.sha256()
        total = 0
        try:
            with archive.open(member, "r") as source_stream, temporary.open("xb") as sink:
                while True:
                    chunk = source_stream.read(_CHUNK_BYTES)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > size:
                        raise SoftwareUpdateGenerationError(
                            "Python update member exceeds its declared size"
                        )
                    digest.update(chunk)
                    sink.write(chunk)
                sink.flush()
                os.fsync(sink.fileno())
            if total != size or digest.hexdigest() != expected_sha256:
                raise SoftwareUpdateGenerationError(
                    "Python update member does not match its declared digest"
                )
            os.chmod(temporary, 0o444)
            os.replace(temporary, destination)
            _fsync_directory(destination.parent)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    def _apply_builtin_activities(
        self,
        archive: zipfile.ZipFile,
        manifest: SoftwareUpdatePackageManifest,
        previous_root: Path,
        staging_root: Path,
        job_id: str,
    ) -> None:
        activities_root = staging_root / "activities"
        previous_activities = previous_root / "activities"
        previous_paths = self._builtin_activity_paths(previous_root)
        if manifest.activity_scope is not None and manifest.activity_scope.value == "all":
            declared = {item.activity_id for item in manifest.activity_items}
            if declared != set(previous_paths):
                raise SoftwareUpdateGenerationError(
                    "all scope must update the complete installed built-in Activity inventory"
                )
        runtime_path = staging_root / "runtime" / "child-runtime.toml"
        runtime = RuntimeCatalogue.load(runtime_path)
        package_service = ActivityPackageService(
            state_root=self.layout.activity_package_state,
            runtime_catalogue=runtime_path,
        )
        for index, item in enumerate(manifest.activity_items):
            old_relpath = previous_paths.get(item.activity_id)
            output_name = old_relpath.name if old_relpath is not None else item.activity_id
            destination = activities_root / output_name
            if old_relpath is None and destination.exists():
                raise SoftwareUpdateGenerationError(
                    "new Activity folder collides with an existing package"
                )
            temporary = staging_root / f".activity-{job_id}-{index:03d}"
            if temporary.exists():
                _remove_staging_tree(temporary)
            temporary.mkdir(mode=0o755)
            package_root = temporary / output_name
            package_root.mkdir(mode=0o755)
            old_tree = previous_activities / old_relpath if old_relpath else None
            try:
                nested = archive.open(item.member, "r")
                with zipfile.ZipFile(nested, "r", allowZip64=False) as activity_zip:
                    package_service.extract_bounded_archive_contents(
                        activity_zip,
                        package_root,
                        reuse_root=old_tree,
                        max_entries=MAX_ACTIVITY_ENTRIES,
                    )
                registrations = self._discover_builtin(temporary, runtime)
                if len(registrations) != 1:
                    raise SoftwareUpdateGenerationError(
                        "Activity package does not contain exactly one built-in Activity"
                    )
                registration = registrations[0]
                if (
                    registration.manifest.activity_id != item.activity_id
                    or registration.manifest.version != item.version
                ):
                    raise SoftwareUpdateGenerationError(
                        "Activity package identity/version does not match its update record"
                    )
                if old_relpath is not None:
                    _remove_staging_tree(destination)
                os.replace(package_root, destination)
            except BaseException:
                if temporary.exists():
                    _remove_staging_tree(temporary)
                raise
        registrations = self._discover_builtin(activities_root, runtime)
        indexed = build_index(
            registrations,
            source=ActivitySource(
                activities_root.resolve(), PackageTrust.BUILT_IN, _BUILT_IN_SOURCE_ID
            ),
            runtime=runtime,
        )
        indexed.write_file(staging_root / "activity-index-v1.json")

    def _builtin_activity_paths(self, root: Path) -> dict[str, Path]:
        activities = root / "activities"
        runtime = RuntimeCatalogue.load(root / "runtime" / "child-runtime.toml")
        registrations = self._discover_builtin(activities, runtime)
        return {
            item.manifest.activity_id: item.manifest.root.relative_to(activities.resolve())
            for item in registrations
        }

    @staticmethod
    def _discover_builtin(root: Path, runtime: RuntimeCatalogue):
        if root.is_symlink() or not root.is_dir():
            raise SoftwareUpdateGenerationError("built-in Activity root is invalid")
        source = ActivitySource(root.resolve(), PackageTrust.BUILT_IN, _BUILT_IN_SOURCE_ID)
        try:
            return ActivityRegistry((source,), runtime).discover_registrations()
        except (ValueError, OSError) as exc:
            raise SoftwareUpdateGenerationError(
                f"built-in Activity validation failed: {exc}"
            ) from exc

    def _validate_application_root(self, root: Path) -> None:
        if not root.is_dir() or root.is_symlink():
            raise SoftwareUpdateGenerationError("candidate application root is invalid")
        runtime = RuntimeCatalogue.load(root / "runtime" / "child-runtime.toml")
        self._discover_builtin(root / "activities", runtime)
        required = (
            root / "src" / "greia_platform" / "__init__.py",
            root / "src" / "greia_launcher" / "__init__.py",
            root / "src" / "greia_parent" / "__init__.py",
            root / "src" / "greia_installer" / "__init__.py",
            root / "runtime" / "parent-app-client.toml",
            root / "runtime" / "parent-app-client.manifest.json",
            root / "activity-index-v1.json",
        )
        required_entrypoints = tuple(
            root.joinpath(*PurePosixPath(relative).parts)
            for relative in REQUIRED_PYTHON_ENTRYPOINTS
        )
        if any(not path.is_file() for path in (*required, *required_entrypoints)):
            raise SoftwareUpdateGenerationError(
                "candidate application generation is missing an installed component"
            )

    def _validate_application_root_for_stage(self, root: Path) -> None:
        """Compatibility alias retained for recovery-focused test fixtures."""
        self._validate_application_root(root)


def _safe_python_destination(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or "\\" in value
        or "\x00" in value
        or any(part in {"", ".", ".."} or part.startswith(".") for part in path.parts)
    ):
        raise SoftwareUpdateGenerationError("Python update path is not portable")
    candidate = path.as_posix()
    if not (
        any(candidate.startswith(root) for root in PYTHON_SOURCE_ROOTS)
        or candidate in PYTHON_RUNTIME_ALLOWLIST
        or is_language_resource_path(candidate)
    ):
        raise SoftwareUpdateGenerationError(
            "Python update destination is outside the fixed Greia allowlist"
        )
    if candidate in {
        "runtime/parent-app-client.toml",
        "runtime/parent-app-client.manifest.json",
    }:
        raise SoftwareUpdateGenerationError(
            "the installed Parent web client integrity pins are outside Python updates"
        )
    return path


def _remove_obsolete_language_resources(language_root: Path, declared: set[str]) -> None:
    """Apply the package's complete locale snapshot inside private staging only."""
    from .localization import LocaleTag

    if not language_root.exists():
        return
    if language_root.is_symlink() or not language_root.is_dir():
        raise SoftwareUpdateGenerationError("language resource root is unsafe")
    for directory in language_root.iterdir():
        if directory.is_symlink():
            raise SoftwareUpdateGenerationError("language resource directory is a symbolic link")
        if not directory.is_dir():
            continue
        try:
            locale = LocaleTag.parse(directory.name).value
        except ValueError:
            continue  # Non-locale authoring content is outside the managed snapshot.
        if locale != directory.name:
            continue
        for filename in ("manifest.json", "ui.json"):
            relative = f"src/greia_platform/languages/{locale}/{filename}"
            if relative not in declared:
                resource = directory / filename
                if resource.is_symlink():
                    raise SoftwareUpdateGenerationError("language resource file is a symbolic link")
                resource.unlink(missing_ok=True)
        try:
            directory.rmdir()  # Remove only if no unrelated content remains.
        except OSError:
            pass


def _is_job_id(value: str) -> bool:
    return len(value) == 32 and all(ch in "0123456789abcdef" for ch in value)


def _write_generation_receipt(root: Path, payload: dict[str, object]) -> None:
    path = root / ".greia-update-generation.json"
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    _fsync_directory(root)


def _read_generation_receipt(root: Path) -> dict[str, object] | None:
    path = root / ".greia-update-generation.json"
    try:
        status = path.lstat()
        if not stat.S_ISREG(status.st_mode) or status.st_size > 4096:
            return None
        raw = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _same_file(path: Path, size: int, digest: str) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return stat.S_ISREG(info.st_mode) and info.st_size == size and _sha256(path) == digest


def _same_archive_file(
    archive: zipfile.ZipFile, info: zipfile.ZipInfo, path: Path
) -> bool:
    try:
        status = path.lstat()
    except OSError:
        return False
    if not stat.S_ISREG(status.st_mode) or status.st_size != info.file_size:
        return False
    digest = hashlib.sha256()
    total = 0
    with archive.open(info, "r") as source:
        while True:
            chunk = source.read(_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            digest.update(chunk)
    return total == info.file_size and digest.hexdigest() == _sha256(path)


def _clone_tree_hardlinked(source: Path, destination: Path) -> None:
    """Clone directories and hard-link ordinary files on the same filesystem."""

    if source.is_symlink() or not source.is_dir():
        raise SoftwareUpdateGenerationError("active application generation is invalid")
    source_device = source.stat().st_dev
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir(mode=0o755)
    for current, directory_names, file_names in os.walk(source, followlinks=False):
        current_path = Path(current)
        relative = current_path.relative_to(source)
        target_dir = destination / relative
        target_dir.mkdir(exist_ok=True, mode=0o755)
        for name in list(directory_names):
            item = current_path / name
            target = target_dir / name
            if item.is_symlink():
                os.symlink(os.readlink(item), target)
                directory_names.remove(name)
            else:
                target.mkdir(exist_ok=True, mode=0o755)
        for name in file_names:
            item = current_path / name
            target = target_dir / name
            status = item.lstat()
            if stat.S_ISLNK(status.st_mode):
                os.symlink(os.readlink(item), target)
                continue
            if not stat.S_ISREG(status.st_mode):
                raise SoftwareUpdateGenerationError(
                    "active application contains a special file"
                )
            if status.st_dev != source_device:
                raise SoftwareUpdateGenerationError(
                    "application generation files cross filesystem boundaries"
                )
            os.link(item, target)


def _seal_read_only(root: Path) -> None:
    """Seal directory publication boundaries without chmodding shared inodes.

    Unchanged files are hard links into the still-recoverable old generation;
    chmod on one link changes the inode's mode for both generations. File
    modes therefore stay as composed, while only the candidate's private
    directory entries are made non-writable.
    """

    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if path.is_symlink():
            continue
        if path.is_dir():
            os.chmod(path, 0o555)
    os.chmod(root, 0o555)


def _remove_staging_tree(root: Path) -> None:
    """Remove an unpublished hard-link tree without chmodding shared files."""

    if not root.exists():
        return
    for path in root.rglob("*"):
        if path.is_dir() and not path.is_symlink():
            try:
                os.chmod(path, 0o755)
            except OSError:
                pass
    try:
        os.chmod(root, 0o755)
    except OSError:
        pass
    shutil.rmtree(root, ignore_errors=False)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_tree_directories(root: Path) -> None:
    directories = [path for path in root.rglob("*") if path.is_dir() and not path.is_symlink()]
    for path in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        _fsync_directory(path)
    _fsync_directory(root)
