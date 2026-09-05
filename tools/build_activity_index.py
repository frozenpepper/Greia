#!/usr/bin/env python3
"""Deterministic built-in Activity index generator.

Build-time serializer for the proof already owned by the 2A gate in
``build/build-image.sh``: it loads the same ``RuntimeCatalogue``, configures
only the built-in ``ActivitySource``, calls the authoritative
``ActivityRegistry`` validation (fail closed on any invalid built-in
package), serializes via the T31 ``activity_index`` model, and writes
atomically through a staging file plus rename.

This tool deliberately contains no second independent manifest validator: no
``activity.toml`` parsing, no tree hygiene checks, no capability/permission
vocabulary checks. All package truth comes from
``ActivityRegistry.discover_registrations``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.activity_index import ActivityIndexError, build_index
from greia_platform.trust import ActivitySource, PackageTrust

BUILT_IN_SOURCE_ID = "greia-system"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Generate the deterministic built-in Activity index.",
    )
    parser.add_argument(
        "--activities",
        type=Path,
        default=project_root / "activities",
        help="Built-in Activity source root (default: <project>/activities).",
    )
    parser.add_argument(
        "--runtime",
        type=Path,
        default=project_root / "runtime" / "child-runtime.toml",
        help="Runtime catalogue path (default: <project>/runtime/child-runtime.toml).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_root / "build" / "activity-index.json",
        help="Destination index file (default: <project>/build/activity-index.json).",
    )
    parser.add_argument(
        "--source-id",
        type=str,
        default=BUILT_IN_SOURCE_ID,
        help="Built-in source identity (default: greia-system).",
    )
    return parser.parse_args(argv)


def generate(*, activities_root: Path, runtime_path: Path, source_id: str):
    """Validate built-ins through the authoritative registry and build the index."""
    if not activities_root.is_dir():
        raise OSError(f"built-in Activity source root is missing: {activities_root}")
    runtime = RuntimeCatalogue.load(runtime_path)
    source = ActivitySource(
        activities_root.resolve(),
        PackageTrust.BUILT_IN,
        source_id,
    )
    registry = ActivityRegistry((source,), runtime)
    # Authoritative validation: fail closed on any invalid built-in package.
    # No per-file manifest parsing happens here; the registry owns it.
    registrations = registry.discover_registrations()
    return build_index(registrations, source=source, runtime=runtime), len(registrations)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        index, count = generate(
            activities_root=args.activities,
            runtime_path=args.runtime,
            source_id=args.source_id,
        )
    except ActivityIndexError as exc:
        print(f"ERROR: built-in Activity index build failed: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        # ActivityValidationError subclasses ValueError and is the fail-closed
        # signal for an invalid built-in package.
        print(f"ERROR: built-in Activity validation failed: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: cannot read built-in Activity source: {exc}", file=sys.stderr)
        return 1
    try:
        # Atomic write only after successful validation+serialization:
        # staging file in the destination directory, then os.replace.
        # ActivityIndex.write_file implements exactly that (.tmp + replace)
        # with deterministic sorted-keys/UTF-8/newline-terminated bytes.
        index.write_file(args.output)
    except OSError as exc:
        print(f"ERROR: cannot write Activity index {args.output}: {exc}", file=sys.stderr)
        try:
            staging = args.output.with_name(args.output.name + ".tmp")
            staging.unlink(missing_ok=True)
        except OSError:
            pass
        return 1
    print(f"WROTE {args.output} {count} activities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
