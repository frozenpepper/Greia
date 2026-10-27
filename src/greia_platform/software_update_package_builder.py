"""Deterministic authoring helpers for bounded ``.greia_update`` packages."""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
import zipfile
from pathlib import Path
from typing import Sequence

from .activity_package_format import ACTIVITY_PACKAGE_EXTENSION
from .system_updates import MAX_BUNDLE_BYTES, inspect_update_bundle
from .software_update_package import (
    MAX_ACTIVITY_PACKAGE_BYTES,
    MAX_SOFTWARE_UPDATE_MANIFEST_BYTES,
    MAX_PYTHON_FILE_BYTES,
    MAX_PYTHON_FILES,
    MAX_SOFTWARE_UPDATE_BYTES,
    PYTHON_RUNTIME_ALLOWLIST,
    PYTHON_SOURCE_ROOTS,
    REQUIRED_PYTHON_ENTRYPOINTS,
    ActivityPackageInput,
    ActivityPackageSource,
    ActivityUpdateScope,
    SoftwareUpdateActivity,
    SoftwareUpdateMember,
    SoftwareUpdatePackageError,
    SoftwareUpdatePackageManifest,
    SoftwareUpdatePythonFile,
    SoftwareUpdateTarget,
    SoftwareUpdateType,
    _identifier,
    _package_path,
    is_language_resource_path,
    _require_regular_source,
    _text,
    ensure_software_update_filename,
    _validate_activity_archive_contents,
    inspect_software_update_package,
)


_COPY_CHUNK_BYTES = 1024 * 1024
_DETERMINISTIC_ZIP_DATE = (1980, 1, 1, 0, 0, 0)


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
    """Build one deterministic package from explicitly typed source inputs.

    Python packages snapshot all four production Python trees and the fixed
    runtime configuration allowlist. Activity package inputs are complete
    ``.greiaactivity`` archives validated through Greia's registry and runtime
    validators. The caller supplies the approved built-in ID set for ``all``.
    Full-system inputs use the existing v3 inspector and are stored unchanged.
    """

    activities = tuple(sorted(activity_packages, key=lambda item: item.activity_id))
    if full_system_bundle is not None:
        if (
            python_source_root is not None
            or activities
            or targets
            or approved_activity_ids is not None
        ):
            raise SoftwareUpdatePackageError("full_system cannot be mixed with app components")
        inspected_system = inspect_update_bundle(Path(full_system_bundle))
        inner_manifest = inspected_system.manifest
        if version is not None and version != inner_manifest.version:
            raise SoftwareUpdatePackageError("outer version must match inner v3 bundle")
        if release_id is not None and release_id != inner_manifest.release_id:
            raise SoftwareUpdatePackageError("outer release_id must match inner v3 bundle")
        version = inner_manifest.version
        release_id = inner_manifest.release_id
        _require_regular_source(Path(full_system_bundle), MAX_BUNDLE_BYTES)
        size, digest = _file_facts(Path(full_system_bundle), MAX_BUNDLE_BYTES)
        member = SoftwareUpdateMember("full_system/bundle.greiaupdate", size, digest)
        manifest = SoftwareUpdatePackageManifest(
            type=SoftwareUpdateType.FULL_SYSTEM,
            version=version,
            release_id=release_id,
            full_system=member,
        )
        sources: tuple[tuple[str, Path, int, bool], ...] = (
            (member.member, Path(full_system_bundle), zipfile.ZIP_STORED, False),
        )
    else:
        if not version or not release_id:
            raise SoftwareUpdatePackageError("app packages require version and release_id")
        version = _text(version, "version", 64)
        release_id = _identifier(release_id, "release_id", 96)
        python_files: tuple[SoftwareUpdatePythonFile, ...] = ()
        python_sources: dict[str, Path] = {}
        if python_source_root is not None:
            python_sources = _collect_python_snapshot(Path(python_source_root))
            python_files = tuple(
                _python_file_record(path, source)
                for path, source in sorted(python_sources.items())
            )
        scope: ActivityUpdateScope | None = None
        source: ActivityPackageSource | None = None
        if activities:
            try:
                scope = ActivityUpdateScope(activity_scope)
                source = ActivityPackageSource(activity_source)
            except (ValueError, TypeError) as exc:
                raise SoftwareUpdatePackageError("Activity packages require scope and source") from exc
        activities_metadata = tuple(
            _inspect_activity_input(
                item,
                source=source,
                runtime_path=runtime_path or _default_runtime_path(),
            )
            for item in activities
        )
        if not python_files and not activities_metadata:
            raise SoftwareUpdatePackageError("package has no application components")
        if python_files and activities_metadata:
            package_type = SoftwareUpdateType.COMBINED
        elif python_files:
            package_type = SoftwareUpdateType.PYTHON_PLATFORM
        else:
            package_type = SoftwareUpdateType.ACTIVITIES

        if activities_metadata:
            assert scope is not None and source is not None
            ids = frozenset(item[0] for item in activities_metadata)
            if scope is ActivityUpdateScope.ALL:
                if source is not ActivityPackageSource.BUILT_IN:
                    raise SoftwareUpdatePackageError("all scope is limited to built-in Activities")
                if not approved_activity_ids or ids != approved_activity_ids:
                    raise SoftwareUpdatePackageError(
                        "all scope must exactly match the installed approved built-in Activity index"
                    )
        elif activity_scope is not None or activity_source is not None or approved_activity_ids is not None:
            raise SoftwareUpdatePackageError("Activity scope/source supplied without Activities")

        activity_items = tuple(
            SoftwareUpdateActivity(
                activity_id=activity_id,
                version=activity_version,
                member=f"activities/{activity_id}{ACTIVITY_PACKAGE_EXTENSION}",
                size=size,
                sha256=digest,
            )
            for activity_id, activity_version, _path, size, digest in activities_metadata
        )
        manifest = SoftwareUpdatePackageManifest(
            type=package_type,
            version=version,
            release_id=release_id,
            targets=tuple(targets),
            python_files=python_files,
            activity_scope=scope,
            activity_source=source,
            activity_items=activity_items,
        )
        source_by_member: dict[str, tuple[Path, int, str, bool]] = {}
        for item in python_files:
            source_by_member[item.member] = (
                python_sources[item.path], zipfile.ZIP_DEFLATED, item.sha256, True
            )
        for activity_id, _activity_version, path, _size, digest in activities_metadata:
            source_by_member[f"activities/{activity_id}{ACTIVITY_PACKAGE_EXTENSION}"] = (
                path,
                zipfile.ZIP_STORED,
                digest,
                False,
            )
        sources = tuple(
            (member_name, source_path, compression, allow_empty)
            for member_name, (source_path, compression, _digest, allow_empty)
            in sorted(source_by_member.items())
        )

    manifest_bytes = manifest.canonical_bytes()
    if len(manifest_bytes) > MAX_SOFTWARE_UPDATE_MANIFEST_BYTES:
        raise SoftwareUpdatePackageError("manifest exceeds Greia bounds")
    output = ensure_software_update_filename(output_path)
    _write_package(output, manifest_bytes, sources)
    inspected = inspect_software_update_package(output, runtime_path=runtime_path)
    if inspected.manifest != manifest:
        output.unlink(missing_ok=True)
        raise SoftwareUpdatePackageError("built package did not round-trip its manifest")
    return manifest


def _collect_python_snapshot(root: Path) -> dict[str, Path]:
    if root.is_symlink() or not root.is_dir():
        raise SoftwareUpdatePackageError("Python source root must be a real directory")
    files: dict[str, Path] = {}

    def fail_walk(error: OSError) -> None:
        raise SoftwareUpdatePackageError(
            f"could not traverse Python source tree: {error}"
        ) from error

    for relative_root in PYTHON_SOURCE_ROOTS:
        source_root = root / relative_root
        if source_root.is_symlink() or not source_root.is_dir():
            raise SoftwareUpdatePackageError(f"required production Python tree is missing: {relative_root}")
        for current, dirs, names in os.walk(
            source_root, followlinks=False, onerror=fail_walk
        ):
            current_path = Path(current)
            for dirname in tuple(dirs):
                entry = current_path / dirname
                if entry.is_symlink():
                    raise SoftwareUpdatePackageError("Python source tree contains a symlink directory")
                if dirname in {"__pycache__", ".git"} or dirname.startswith("."):
                    dirs.remove(dirname)
            for filename in names:
                source = current_path / filename
                if source.is_symlink():
                    raise SoftwareUpdatePackageError("Python source tree contains a symlink file")
                if source.suffix != ".py":
                    continue
                relative = source.relative_to(root).as_posix()
                _package_path(relative)
                files[relative] = source
                if len(files) > MAX_PYTHON_FILES:
                    raise SoftwareUpdatePackageError("Python source file count exceeds Greia bounds")
    for relative in sorted(PYTHON_RUNTIME_ALLOWLIST):
        source = root / relative
        if not source.exists():
            raise SoftwareUpdatePackageError(f"required production runtime file is missing: {relative}")
        if source.is_symlink() or not source.is_file():
            raise SoftwareUpdatePackageError(f"allowlisted runtime file is not regular: {relative}")
        files[relative] = source
    language_root = root / "src" / "greia_platform" / "languages"
    if language_root.is_symlink() or not language_root.is_dir():
        raise SoftwareUpdatePackageError("required language resource directory is missing or not regular")
    for locale_dir in sorted(language_root.iterdir(), key=lambda item: item.name):
        if locale_dir.is_symlink() or not locale_dir.is_dir():
            raise SoftwareUpdatePackageError("language resource inventory contains a non-directory entry")
        manifest = locale_dir / "manifest.json"
        if manifest.is_symlink():
            raise SoftwareUpdatePackageError("language manifest must be a regular file")
        if not manifest.exists():
            continue  # Unoffered language scaffolds are not package data.
        for filename in ("manifest.json", "ui.json"):
            source = locale_dir / filename
            relative = source.relative_to(root).as_posix()
            if not is_language_resource_path(relative):
                raise SoftwareUpdatePackageError(f"language resource path is not canonical: {relative}")
            if source.is_symlink() or not source.is_file():
                raise SoftwareUpdatePackageError(f"required language resource is not a regular file: {relative}")
            files[relative] = source
    if not any(
        path == "src/greia_platform/languages/en/manifest.json" for path in files
    ):
        raise SoftwareUpdatePackageError("Python snapshot must include offered English language data")
    if not files:
        raise SoftwareUpdatePackageError("Python source snapshot is empty")
    missing = REQUIRED_PYTHON_ENTRYPOINTS - files.keys()
    if missing:
        raise SoftwareUpdatePackageError(
            "Python source snapshot is missing required production entrypoints: "
            + ", ".join(sorted(missing))
        )
    return files


def _python_file_record(path: str, source: Path) -> SoftwareUpdatePythonFile:
    size, digest = _file_facts(source, MAX_PYTHON_FILE_BYTES, allow_empty=True)
    return SoftwareUpdatePythonFile(path, f"python/{path}", size, digest)


def _inspect_activity_input(
    item: ActivityPackageInput,
    *,
    source: ActivityPackageSource | None,
    runtime_path: Path,
) -> tuple[str, str, Path, int, str]:
    activity_id = _identifier(item.activity_id, "activity_id", 96)
    path = Path(item.path)
    if not path.name.casefold().endswith(ACTIVITY_PACKAGE_EXTENSION):
        raise SoftwareUpdatePackageError("Activity input must use .greiaactivity extension")
    size, digest = _file_facts(path, MAX_ACTIVITY_PACKAGE_BYTES)
    if source is None:
        raise SoftwareUpdatePackageError("Activity package source is required")
    try:
        with zipfile.ZipFile(path, "r", allowZip64=False) as archive:
            validated_id, activity_version = _validate_activity_archive_contents(
                archive,
                activity_id,
                source_kind=source,
                runtime_path=runtime_path,
            )
    except (KeyError, zipfile.BadZipFile, OSError) as exc:
        raise SoftwareUpdatePackageError("Activity input is missing a valid root activity.toml") from exc
    if validated_id != activity_id:
        raise SoftwareUpdatePackageError("Activity archive id does not match requested id")
    activity_version = _text(activity_version, "Activity version", 64)
    return activity_id, activity_version, path, size, digest


def _default_runtime_path() -> Path:
    return Path(__file__).resolve().parents[2] / "runtime" / "child-runtime.toml"


def _write_package(
    output: Path,
    manifest_bytes: bytes,
    sources: Sequence[tuple[str, Path, int, bool]],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.is_symlink():
        raise SoftwareUpdatePackageError(f"output already exists: {output}")
    published = False
    with tempfile.NamedTemporaryFile(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True
        ) as archive:
            _write_bytes_member(archive, "manifest.json", manifest_bytes, zipfile.ZIP_DEFLATED)
            for member, source, compression, allow_empty in sources:
                _write_path_member(
                    archive, member, source, compression, allow_empty=allow_empty
                )
        if temporary.stat().st_size <= 0 or temporary.stat().st_size > MAX_SOFTWARE_UPDATE_BYTES:
            raise SoftwareUpdatePackageError("generated software-update package exceeds Greia bounds")
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.link(temporary, output)
        published = True
        directory_fd = os.open(output.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        if published:
            output.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)


def _write_bytes_member(
    archive: zipfile.ZipFile, name: str, payload: bytes, compression: int
) -> None:
    info = _zip_info(name, compression)
    archive.writestr(info, payload, compress_type=compression, compresslevel=9)


def _write_path_member(
    archive: zipfile.ZipFile,
    name: str,
    path: Path,
    compression: int,
    *,
    allow_empty: bool = False,
) -> None:
    _require_regular_source(path, MAX_SOFTWARE_UPDATE_BYTES, allow_empty=allow_empty)
    expected_size, expected_digest = _file_facts(
        path, MAX_SOFTWARE_UPDATE_BYTES, allow_empty=allow_empty
    )
    info = _zip_info(name, compression)
    digest = hashlib.sha256()
    written = 0
    try:
        with Path(path).open("rb") as source, archive.open(info, "w", force_zip64=True) as target:
            while True:
                chunk = source.read(_COPY_CHUNK_BYTES)
                if not chunk:
                    break
                target.write(chunk)
                digest.update(chunk)
                written += len(chunk)
    except OSError as exc:
        raise SoftwareUpdatePackageError(f"could not read package input: {path}") from exc
    if written != expected_size or digest.hexdigest() != expected_digest:
        raise SoftwareUpdatePackageError(f"package input changed while building: {path}")


def _zip_info(name: str, compression: int) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, _DETERMINISTIC_ZIP_DATE)
    info.compress_type = compression
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


def _file_facts(
    path: Path, maximum: int, *, allow_empty: bool = False
) -> tuple[int, str]:
    path = Path(path)
    _require_regular_source(path, maximum, allow_empty=allow_empty)
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as source:
        opened = os.fstat(source.fileno())
        current = path.lstat()
        if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
            raise SoftwareUpdatePackageError("package source changed while opening")
        while True:
            chunk = source.read(_COPY_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > maximum:
                raise SoftwareUpdatePackageError("package source exceeds Greia bound")
            digest.update(chunk)
        if total != opened.st_size:
            raise SoftwareUpdatePackageError("package source changed while reading")
    return total, digest.hexdigest()


__all__ = ["build_software_update_package"]
