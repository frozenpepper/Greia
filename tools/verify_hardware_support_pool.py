#!/usr/bin/env python3
"""Verify a Greia hardware-support repository and optionally list package classes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from greia_installer.hardware_support import VerifiedHardwareSupportPool


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--suite")
    parser.add_argument("--architecture")
    parser.add_argument(
        "--list",
        dest="list_class",
        choices=("firmware", "broad-firmware", "microcode", "candidates"),
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    pool = VerifiedHardwareSupportPool.load(
        args.root,
        expected_suite=args.suite,
        expected_architecture=args.architecture,
    )
    if args.list_class == "firmware":
        selected = sorted(pool.provided_firmware)
    elif args.list_class == "broad-firmware":
        selected = sorted(pool.broad_firmware)
    elif args.list_class == "microcode":
        selected = sorted(pool.provided_microcode)
    elif args.list_class == "candidates":
        selected = sorted(pool.provided_candidates)
    else:
        selected = []
    if args.json:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "suite": pool.suite,
                    "architecture": pool.architecture,
                    "package_count": len(pool.packages),
                    "total_bytes": pool.total_bytes,
                    "provided_firmware_packages": sorted(pool.provided_firmware),
                    "broad_firmware_packages": sorted(pool.broad_firmware),
                    "provided_microcode_packages": sorted(pool.provided_microcode),
                    "provided_candidate_packages": sorted(pool.provided_candidates),
                },
                sort_keys=True,
            )
        )
    else:
        for package in selected:
            print(package)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
