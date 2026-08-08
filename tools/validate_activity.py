#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from greia_platform.activities import ActivityRegistry, RuntimeCatalogue, package_digest


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one curated Greia OS activity package.")
    parser.add_argument("activity", type=Path)
    parser.add_argument(
        "--runtime",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "runtime" / "child-runtime.toml",
    )
    args = parser.parse_args()
    root = args.activity.resolve(strict=True)
    runtime = RuntimeCatalogue.load(args.runtime)
    registry = ActivityRegistry([root.parent], runtime)
    manifest = registry.validate_package(root)
    print(f"PASS {manifest.activity_id} {manifest.version}")
    print(f"sha256 {package_digest(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
