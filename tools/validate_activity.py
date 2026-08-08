#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from greia_platform.activities import ActivityRegistry, RuntimeCatalogue, package_digest
from greia_platform.trust import ActivitySource, PackageTrust


def validation_source(activity_root: Path, project_root: Path) -> ActivitySource:
    """Return the platform-owned source identity for standalone validation.

    Repository-bundled Activities are Greia built-ins and may legitimately carry
    trusted compatibility aliases. An arbitrary package passed to this tool stays
    developer-unsigned; merely invoking the validator must never upgrade trust.
    """

    root = activity_root.resolve(strict=True)
    bundled_root = (project_root / "activities").resolve(strict=True)
    if root.parent == bundled_root:
        return ActivitySource(bundled_root, PackageTrust.BUILT_IN, "greia-system")
    return ActivitySource(root.parent, PackageTrust.DEVELOPER_UNSIGNED, "standalone-validation")


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Validate one curated Greia OS activity package.")
    parser.add_argument("activity", type=Path)
    parser.add_argument(
        "--runtime",
        type=Path,
        default=project_root / "runtime" / "child-runtime.toml",
    )
    args = parser.parse_args()
    root = args.activity.resolve(strict=True)
    runtime = RuntimeCatalogue.load(args.runtime)
    source = validation_source(root, project_root)
    registry = ActivityRegistry([source], runtime)
    manifest = registry.validate_registration(root, source).manifest
    print(f"PASS {manifest.activity_id} {manifest.version}")
    print(f"sha256 {package_digest(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
