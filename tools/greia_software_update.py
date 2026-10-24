#!/usr/bin/env python3
"""Build and inspect lightweight Greia ``.greia_update`` packages."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from greia_platform.activities import ActivityRegistry, RuntimeCatalogue  # noqa: E402
from greia_platform.activity_index import ActivityIndexLoader, ActivityIndexError  # noqa: E402
from greia_platform.activity_package_format import ACTIVITY_PACKAGE_EXTENSION  # noqa: E402
from greia_platform.system_updates import UpdateBundleError  # noqa: E402
from greia_platform.trust import ActivitySource, PackageTrust  # noqa: E402
from greia_platform.software_update_package import (  # noqa: E402
    ActivityPackageInput,
    ActivityPackageSource,
    ActivityUpdateScope,
    InspectedSoftwareUpdatePackage,
    SoftwareUpdatePackageError,
    SoftwareUpdateTarget,
    build_software_update_package,
    ensure_software_update_filename,
    inspect_software_update_package,
)


BUILT_IN_SOURCE_ID = "greia-system"
PARENT_SOURCE_ID = "greia-parent-package-service"
_ZIP_DATE = (1980, 1, 1, 0, 0, 0)
_COPY_BYTES = 1024 * 1024
_ACTIVITY_AUTHORING_CACHES = frozenset(
    {"__pycache__", ".ruff_cache", ".mypy_cache", ".pytest_cache"}
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    python = commands.add_parser("build-python-platform", help="build the complete production Python/runtime snapshot")
    _add_app_identity(python)
    python.add_argument("--source-root", type=Path, default=PROJECT_ROOT)
    python.add_argument("--output", type=Path, required=True)
    _add_target_arguments(python)

    activities = commands.add_parser("build-activities", help="build one/set/all Activity updates")
    _add_app_identity(activities)
    activities.add_argument("--scope", choices=[item.value for item in ActivityUpdateScope], required=True)
    activities.add_argument("--source", choices=[item.value for item in ActivityPackageSource], required=True)
    activities.add_argument("--activity", action="append", default=[], metavar="ID=PATH",
                            help="existing .greiaactivity or validated Activity directory; repeat for a set")
    all_source = activities.add_mutually_exclusive_group()
    all_source.add_argument("--all-from-installed-root", type=Path,
                            help="root filesystem whose built-in Activity index defines the complete current set")
    all_source.add_argument("--all-current-activities", action="store_true",
                            help="package every Activity in the validated current source inventory")
    activities.add_argument("--activities-root", type=Path,
                            help="candidate Activity source tree; defaults to <project>/activities")
    activities.add_argument("--runtime", type=Path, default=PROJECT_ROOT / "runtime" / "child-runtime.toml")
    activities.add_argument("--output", type=Path, required=True)
    _add_target_arguments(activities)

    combined = commands.add_parser("build-combined", help="build one atomic Python plus built-in Activity update")
    _add_app_identity(combined)
    combined.add_argument("--source-root", type=Path, default=PROJECT_ROOT)
    combined.add_argument("--activity", action="append", default=[], metavar="ID=PATH",
                          help="existing .greiaactivity or validated built-in Activity directory")
    combined.add_argument("--scope", choices=[item.value for item in ActivityUpdateScope], required=True)
    all_source = combined.add_mutually_exclusive_group()
    all_source.add_argument("--all-from-installed-root", type=Path,
                            help="root filesystem whose built-in Activity index defines the complete current set")
    all_source.add_argument("--all-current-activities", action="store_true",
                            help="package every Activity in the validated current source inventory")
    combined.add_argument("--activities-root", type=Path)
    combined.add_argument("--runtime", type=Path, default=PROJECT_ROOT / "runtime" / "child-runtime.toml")
    combined.add_argument("--output", type=Path, required=True)
    _add_target_arguments(combined)

    full_system = commands.add_parser("wrap-full-system", help="wrap an existing inspected v3 .greiaupdate bundle")
    full_system.add_argument("--bundle", type=Path, required=True)
    full_system.add_argument("--output", type=Path, required=True)

    inspect = commands.add_parser("inspect", help="validate package structure and member digests")
    inspect.add_argument("package", type=Path)
    return parser


def _add_app_identity(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--version", required=True)
    parser.add_argument("--release-id", required=True)


def _add_target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile")
    parser.add_argument("--platform-family")
    parser.add_argument("--architecture")
    parser.add_argument("--board")


def _target(args: argparse.Namespace) -> tuple[SoftwareUpdateTarget, ...]:
    values = {
        "profile": args.profile,
        "platform_family": args.platform_family,
        "architecture": args.architecture,
        "board": args.board,
    }
    selected = {name: value for name, value in values.items() if value is not None}
    return (SoftwareUpdateTarget(**selected),) if selected else ()


def _parse_activity_inputs(values: list[str]) -> tuple[ActivityPackageInput, ...]:
    parsed: list[ActivityPackageInput] = []
    for value in values:
        activity_id, separator, path = value.partition("=")
        if not separator or not activity_id or not path:
            raise SoftwareUpdatePackageError("--activity must be ID=PATH")
        parsed.append(ActivityPackageInput(activity_id, Path(path)))
    return tuple(parsed)


def _installed_activity_inventory(rootfs: Path) -> tuple[Path, Path, Path, frozenset[str]]:
    root = Path(rootfs)
    activities_root = root / "opt" / "greia-os" / "activities"
    runtime_path = root / "opt" / "greia-os" / "runtime" / "child-runtime.toml"
    index_path = root / "usr" / "share" / "greia" / "activity-index-v1.json"
    for path in (activities_root, runtime_path, index_path):
        if not path.exists():
            raise SoftwareUpdatePackageError(f"installed-root inventory is missing {path}")
    runtime = RuntimeCatalogue.load(runtime_path)
    source = ActivitySource(activities_root, PackageTrust.BUILT_IN, BUILT_IN_SOURCE_ID)
    indexed = ActivityIndexLoader.from_runtime(source, runtime).load_file(index_path)
    expected = {
        item.manifest.activity_id: item
        for item in indexed
    }
    observed = ActivityRegistry((source,), runtime).discover_registrations()
    actual = {item.manifest.activity_id: item for item in observed}
    if set(expected) != set(actual):
        raise SoftwareUpdatePackageError("installed Activity index does not match current built-in trees")
    for activity_id, indexed_item in expected.items():
        live_item = actual[activity_id]
        if (
            indexed_item.manifest.version != live_item.manifest.version
            or indexed_item.package_digest != live_item.package_digest
        ):
            raise SoftwareUpdatePackageError(f"installed Activity index is stale for {activity_id}")
    return activities_root, runtime_path, index_path, frozenset(expected)


def _validated_candidate_activities(
    activities_root: Path,
    runtime_path: Path,
    *,
    expected_ids: frozenset[str] | None,
) -> tuple[tuple[object, ...], RuntimeCatalogue]:
    runtime = RuntimeCatalogue.load(runtime_path)
    source = ActivitySource(activities_root, PackageTrust.BUILT_IN, BUILT_IN_SOURCE_ID)
    registrations = ActivityRegistry((source,), runtime).discover_registrations()
    observed_ids = frozenset(item.manifest.activity_id for item in registrations)
    if expected_ids is not None and observed_ids != expected_ids:
        missing = sorted(expected_ids - observed_ids)
        extra = sorted(observed_ids - expected_ids)
        raise SoftwareUpdatePackageError(
            f"candidate Activity set differs from installed index (missing={missing}, extra={extra})"
        )
    return tuple(registrations), runtime


def _write_activity_archive(activity_root: Path, output: Path) -> None:
    """Write one validated Activity directory in the existing root-ZIP layout."""

    files: list[Path] = []
    def fail_walk(error: OSError) -> None:
        raise SoftwareUpdatePackageError(
            f"could not traverse Activity source tree: {error}"
        ) from error

    for current, dirs, names in os.walk(
        activity_root, followlinks=False, onerror=fail_walk
    ):
        current_path = Path(current)
        for dirname in tuple(dirs):
            path = current_path / dirname
            if path.is_symlink():
                raise SoftwareUpdatePackageError("Activity source contains a symlink directory")
            if dirname in _ACTIVITY_AUTHORING_CACHES:
                dirs.remove(dirname)
        for filename in names:
            path = current_path / filename
            if path.is_symlink():
                raise SoftwareUpdatePackageError("Activity source contains a symlink file")
            if filename.endswith(".pyc") and "__pycache__" in path.parts:
                continue
            if not path.is_file():
                raise SoftwareUpdatePackageError("Activity source contains a non-regular file")
            files.append(path)
            if len(files) > 4096:
                raise SoftwareUpdatePackageError("Activity source file count exceeds update package bound")
    if not files or not (activity_root / "activity.toml").is_file():
        raise SoftwareUpdatePackageError("Activity source has no root activity.toml or files")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=False
    ) as archive:
        for source_path in sorted(files, key=lambda item: item.relative_to(activity_root).as_posix()):
            member_name = source_path.relative_to(activity_root).as_posix()
            info = zipfile.ZipInfo(member_name, _ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            with source_path.open("rb") as source, archive.open(info, "w") as target:
                while True:
                    chunk = source.read(_COPY_BYTES)
                    if not chunk:
                        break
                    target.write(chunk)


def _prepare_activity_inputs(
    items: tuple[ActivityPackageInput, ...],
    *,
    source: ActivityPackageSource,
    runtime_path: Path,
    temporary_root: Path,
    prevalidated_paths: dict[str, Path] | None = None,
) -> tuple[ActivityPackageInput, ...]:
    prepared: list[ActivityPackageInput] = []
    trust = (
        PackageTrust.BUILT_IN
        if source is ActivityPackageSource.BUILT_IN
        else PackageTrust.PARENT_TRUSTED_UNSIGNED
    )
    source_id = BUILT_IN_SOURCE_ID if source is ActivityPackageSource.BUILT_IN else PARENT_SOURCE_ID
    runtime = RuntimeCatalogue.load(runtime_path)
    for item in items:
        if item.path.is_dir():
            package_root = item.path.resolve(strict=True)
            validated_path = (prevalidated_paths or {}).get(item.activity_id)
            if validated_path is not None:
                if package_root != validated_path.resolve(strict=True):
                    raise SoftwareUpdatePackageError("validated Activity path changed during package build")
            else:
                authoritative_source = ActivitySource(package_root.parent, trust, source_id)
                registration = ActivityRegistry((authoritative_source,), runtime).validate_registration(
                    package_root, authoritative_source
                )
                if registration.manifest.activity_id != item.activity_id:
                    raise SoftwareUpdatePackageError("Activity directory id does not match --activity id")
            output = temporary_root / f"{item.activity_id}{ACTIVITY_PACKAGE_EXTENSION}"
            _write_activity_archive(package_root, output)
            prepared.append(ActivityPackageInput(item.activity_id, output))
        else:
            prepared.append(item)
    return tuple(prepared)


def _build_app_command(args: argparse.Namespace, *, combined: bool = False) -> int:
    scope = ActivityUpdateScope(args.scope) if hasattr(args, "scope") else None
    source = (
        ActivityPackageSource.BUILT_IN
        if combined
        else ActivityPackageSource(args.source)
        if hasattr(args, "source")
        else None
    )
    target = _target(args)
    inputs: tuple[ActivityPackageInput, ...] = ()
    approved_ids: frozenset[str] | None = None
    prevalidated_paths: dict[str, Path] = {}
    with tempfile.TemporaryDirectory(prefix="greia-software-update-") as directory:
        temporary_root = Path(directory)
        if scope is ActivityUpdateScope.ALL:
            if source is not ActivityPackageSource.BUILT_IN:
                raise SoftwareUpdatePackageError("all scope is only available for built-in Activities")
            if args.activity or not (
                args.all_from_installed_root is not None
                or args.all_current_activities
            ):
                raise SoftwareUpdatePackageError(
                    "all scope requires a validated installed-root or current-source inventory"
                )
            candidate_root = args.activities_root or PROJECT_ROOT / "activities"
            if args.all_from_installed_root is not None:
                _installed_root, _installed_runtime, _index, approved_ids = _installed_activity_inventory(
                    args.all_from_installed_root
                )
                registrations, _candidate_runtime = _validated_candidate_activities(
                    candidate_root,
                    args.runtime,
                    expected_ids=approved_ids,
                )
            else:
                registrations, _candidate_runtime = _validated_candidate_activities(
                    candidate_root,
                    args.runtime,
                    expected_ids=None,
                )
                approved_ids = frozenset(
                    item.manifest.activity_id for item in registrations
                )
                if not approved_ids:
                    raise SoftwareUpdatePackageError(
                        "current source inventory contains no valid Activities"
                    )
            inputs = tuple(
                ActivityPackageInput(item.manifest.activity_id, item.manifest.root)
                for item in registrations
            )
            prevalidated_paths = {
                item.manifest.activity_id: item.manifest.root for item in registrations
            }
        elif hasattr(args, "activity") and args.activity:
            inputs = _parse_activity_inputs(args.activity)
        elif scope is not None:
            raise SoftwareUpdatePackageError("one/set scope requires explicit --activity inputs")

        if inputs:
            assert source is not None
            inputs = _prepare_activity_inputs(
                inputs,
                source=source,
                runtime_path=args.runtime,
                temporary_root=temporary_root,
                prevalidated_paths=prevalidated_paths,
            )
        build_software_update_package(
            args.output,
            version=args.version,
            release_id=args.release_id,
            python_source_root=args.source_root if combined or args.command == "build-python-platform" else None,
            activity_packages=inputs,
            activity_scope=scope,
            activity_source=source,
            targets=target,
            approved_activity_ids=approved_ids,
            runtime_path=getattr(args, "runtime", None),
        )
        output = ensure_software_update_filename(args.output)
        _print_result(output, inspect_software_update_package(output))
    return 0


def _print_result(path: Path, result: InspectedSoftwareUpdatePackage) -> None:
    print(json.dumps({
        "path": str(path),
        "type": result.manifest.type.value,
        "version": result.manifest.version,
        "release_id": result.manifest.release_id,
        "package_size": result.package_size,
        "package_sha256": result.package_sha256,
        "activity_count": len(result.manifest.activity_items),
        "python_file_count": len(result.manifest.python_files),
    }, ensure_ascii=False, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_software_update_package(args.package)
            print(json.dumps({
                "type": result.manifest.type.value,
                "version": result.manifest.version,
                "release_id": result.manifest.release_id,
                "package_size": result.package_size,
                "package_sha256": result.package_sha256,
                "manifest": result.manifest.as_json_dict(),
            }, ensure_ascii=False, sort_keys=True, indent=2))
            return 0
        if args.command == "wrap-full-system":
            build_software_update_package(
                args.output,
                full_system_bundle=args.bundle,
            )
            output = ensure_software_update_filename(args.output)
            _print_result(output, inspect_software_update_package(output))
            return 0
        return _build_app_command(args, combined=args.command == "build-combined")
    except (ActivityIndexError, SoftwareUpdatePackageError, UpdateBundleError, OSError, ValueError) as exc:
        print(f"ERROR: software-update package: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
