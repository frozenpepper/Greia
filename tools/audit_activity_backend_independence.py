#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from greia_platform.activity_backend_policy import (
    BackendFindingSeverity,
    scan_python_activity_backend_policy,
)


def _activity_roots(root: Path) -> tuple[Path, ...]:
    if (root / "activity.toml").is_file():
        return (root,)
    return tuple(
        path
        for path in sorted(root.iterdir())
        if path.is_dir() and (path / "activity.toml").is_file()
    )


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description=(
            "Inventory Greia Activity display/input backend coupling without "
            "executing Activity source."
        )
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=project_root / "activities",
        help="one Activity root or a directory containing Activity roots",
    )
    parser.add_argument(
        "--strict-migration",
        action="store_true",
        help="also fail while known R7 migration debt remains",
    )
    args = parser.parse_args()

    root = args.root.resolve(strict=True)
    activities = _activity_roots(root)
    if not activities:
        parser.error(f"no Activity packages found under {root}")

    totals: Counter[BackendFindingSeverity] = Counter()
    affected: Counter[BackendFindingSeverity] = Counter()
    for activity_root in activities:
        findings = scan_python_activity_backend_policy(activity_root)
        per_activity = Counter(item.severity for item in findings)
        for severity in per_activity:
            affected[severity] += 1
        for finding in findings:
            totals[finding.severity] += 1
            try:
                display_path = finding.path.relative_to(project_root)
            except ValueError:
                display_path = finding.path
            print(
                f"{finding.severity.value.upper()} "
                f"{display_path}:{finding.line} [{finding.code}] {finding.detail}"
            )

    blockers = totals[BackendFindingSeverity.BLOCKER]
    migrations = totals[BackendFindingSeverity.MIGRATION]
    print(
        "SUMMARY "
        f"activities={len(activities)} "
        f"blockers={blockers} "
        f"blocker_activities={affected[BackendFindingSeverity.BLOCKER]} "
        f"migration_findings={migrations} "
        f"migration_activities={affected[BackendFindingSeverity.MIGRATION]}"
    )

    if blockers:
        return 1
    if args.strict_migration and migrations:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
