#!/usr/bin/env python3
"""Stage exactly the first-party Activities selected for an official release.

Repository Activities outside the selection remain source-available but are not
copied into the staged built-in root. The selected staged tree is revalidated
through ActivityRegistry, and expected IDs/package directories must match
exactly before the output root is atomically published.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.activity_release import (
    FirstPartyReleaseSelection,
    ReleaseSelectionError,
)
from greia_platform.trust import ActivitySource, PackageTrust


BUILT_IN_SOURCE_ID = "greia-system"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Stage the explicit first-party release Activity subset."
    )
    parser.add_argument(
        "--selection",
        type=Path,
        default=project / "build" / "first-party-release-activities.toml",
    )
    parser.add_argument(
        "--activities",
        type=Path,
        default=project / "activities",
    )
    parser.add_argument(
        "--runtime",
        type=Path,
        default=project / "runtime" / "child-runtime.toml",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="Developer/review only: permit a draft (possibly empty) selection.",
    )
    return parser.parse_args(argv)


def _require_clean_package_tree(root: Path) -> None:
    if root.is_symlink() or not root.is_dir():
        raise ReleaseSelectionError(
            f"selected Activity package is not a real directory: {root.name}"
        )
    for candidate in root.rglob("*"):
        if candidate.is_symlink():
            raise ReleaseSelectionError(
                f"selected Activity package contains a symlink: "
                f"{root.name}/{candidate.relative_to(root).as_posix()}"
            )


def stage_release_activities(
    *,
    selection_path: Path,
    activities_root: Path,
    runtime_path: Path,
    output_root: Path,
    allow_draft: bool,
) -> tuple[str, tuple[str, ...]]:
    selection = FirstPartyReleaseSelection.load(selection_path)
    if not allow_draft:
        selection.require_approved()

    source_input = Path(activities_root)
    if source_input.is_symlink():
        raise ReleaseSelectionError("built-in Activity source root is unsafe")
    source_root = source_input.resolve(strict=True)
    if not source_root.is_dir():
        raise ReleaseSelectionError("built-in Activity source root is unsafe")

    output_input = Path(output_root)
    if output_input.is_symlink() or output_input.exists():
        raise ReleaseSelectionError(
            "release Activity staging output already exists"
        )
    output = output_input.resolve(strict=False)
    output.parent.mkdir(parents=True, exist_ok=True)

    temporary: Path | None = Path(
        tempfile.mkdtemp(
            prefix=f".{output.name}.",
            dir=output.parent,
        )
    )
    try:
        for item in selection.activities:
            source_package = source_root / item.package_relpath
            _require_clean_package_tree(source_package)
            shutil.copytree(
                source_package,
                temporary / item.package_relpath,
                symlinks=False,
            )

        runtime = RuntimeCatalogue.load(runtime_path)
        staged_source = ActivitySource(
            temporary,
            PackageTrust.BUILT_IN,
            BUILT_IN_SOURCE_ID,
        )
        registry = ActivityRegistry((staged_source,), runtime)
        registrations = registry.discover_registrations()
        discovered = {
            registration.manifest.activity_id:
            registration.manifest.root.name
            for registration in registrations
        }
        expected = {
            item.activity_id: item.package_relpath
            for item in selection.activities
        }
        if discovered != expected:
            raise ReleaseSelectionError(
                "staged Activity identities/packages do not match release selection"
            )

        temporary.rename(output)
        temporary = None
        return selection.release_id, tuple(sorted(discovered))
    finally:
        if temporary is not None and temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        release_id, activity_ids = stage_release_activities(
            selection_path=args.selection,
            activities_root=args.activities,
            runtime_path=args.runtime,
            output_root=args.output,
            allow_draft=bool(args.allow_draft),
        )
    except (OSError, ReleaseSelectionError, ValueError) as exc:
        print(f"ERROR: release Activity staging failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"STAGED {release_id} {len(activity_ids)} activities "
        + " ".join(activity_ids)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
